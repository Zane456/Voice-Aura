#!/usr/bin/env python3
"""
Qwen3-ASR 按键语音输入（CLI 模式）
按住右 Command 键说话，松开后自动识别并输入到光标位置
使用 Qwen3-ASR 模型（业界最佳中文识别）
"""

import os
import sys
import threading
import time
import tempfile
import numpy as np
import torch
import soundfile as sf

# 路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from backend.permissions import check_accessibility, open_accessibility_settings
from backend.config import load_config
from backend.voice_service import type_text

KEY_NAMES = {
    "cmd_r": "右 Command",
    "cmd_l": "左 Command",
    "alt_r": "右 Option",
    "alt_l": "左 Option",
    "ctrl": "Control",
    "shift": "Shift",
}


class RecordingOverlay:
    """使用浮动窗口(NSPanel)作为录音指示器，完全控制显隐"""

    def __init__(self):
        self._impl = None

    def _get_impl(self):
        if self._impl is None:
            from frontend.recording_overlay import RecordingOverlay as NSPanelOverlay
            self._impl = NSPanelOverlay()
        return self._impl

    def show(self):
        self._get_impl().show()

    def hide(self):
        self._get_impl().hide()


def main():
    import sounddevice as sd
    from qwen_asr import Qwen3ASRModel
    from backend.keyboard_listener import KeyboardListener

    config = load_config()
    replacements = config.get("replacements", {})
    trigger_key = config.get("trigger_key", "cmd_r")
    model_name = config.get("model", "Qwen/Qwen3-ASR-1.7B")

    trigger_key_name = KEY_NAMES.get(trigger_key, "右 Command")

    print("=" * 50)
    print("🎤 Qwen3-ASR 按键语音输入")
    print("=" * 50)
    print("")
    print(f"📂 加载模型: {model_name}")
    print("⏳ 首次运行需下载模型（约 3-4GB），请耐心等待...")
    print("")

    # 检测设备并加载模型
    if torch.backends.mps.is_available():
        device = "mps"
        dtype = torch.float16
        print("✅ 使用 Apple Metal (MPS) 加速")
    elif torch.cuda.is_available():
        device = "cuda"
        dtype = torch.bfloat16
        print("✅ 使用 CUDA GPU 加速")
    else:
        device = "cpu"
        dtype = torch.float32
        print("ℹ️  使用 CPU")

    try:
        print("📥 下载/加载模型中（首次约需 3-10 分钟）...")
        model = Qwen3ASRModel.from_pretrained(
            model_name,
            dtype=dtype,
            device_map=device,
            max_inference_batch_size=8,
            max_new_tokens=128,
        )
        print("✅ 模型加载完成！")
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        print("\n可能的解决方案：")
        print("1. 检查网络连接（需要从 Hugging Face 下载模型）")
        print("2. 使用镜像: HF_ENDPOINT=https://hf-mirror.com ./run_qwen.sh")
        print("3. 切换到小模型: 编辑 ~/.voice_config.json 中 model 为 'Qwen/Qwen3-ASR-0.6B'")
        return

    # 创建录音浮窗指示器
    print("🎨 加载录音指示器...")
    overlay = RecordingOverlay()
    print("✅ 指示器就绪")

    print("")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🔵 按住【{trigger_key_name}键】 开始录音")
    print("🔴 松开后自动识别并输入到光标位置")
    print("💡 按 Ctrl+C 退出程序")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    recording = False
    audio_chunks = []
    lock = threading.Lock()

    def on_press():
        nonlocal recording, audio_chunks
        with lock:
            if not recording:
                recording = True
                audio_chunks = []
                print("\n🎙️ 录音中... 请说话...")
                overlay.show()

    def on_release():
        nonlocal recording, audio_chunks
        chunks_copy = []
        with lock:
            if recording:
                recording = False
                print("⏹️ 停止，识别中...")
                chunks_copy = audio_chunks.copy()
                audio_chunks = []

        overlay.hide()

        if len(chunks_copy) > 0:
            audio_data = np.concatenate(chunks_copy)

            try:
                # 保存为临时 WAV 文件
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_path = f.name
                sf.write(tmp_path, audio_data, 16000)

                try:
                    # 使用 Qwen3-ASR 识别（锁定中文加速）
                    results = model.transcribe(
                        audio=tmp_path,
                        language="Chinese",
                    )
                finally:
                    # 确保清理临时文件
                    os.unlink(tmp_path)

                if results and results[0].text:
                    text = results[0].text
                    lang = results[0].language if hasattr(results[0], 'language') else ""
                    for wrong, correct in replacements.items():
                        text = text.replace(wrong, correct)
                    if lang:
                        print(f"🌐 语言: {lang}")
                    print(f"📝 {text}")
                    type_text(text)
                else:
                    print("❌ 未识别到内容")
            except Exception as e:
                print(f"⚠️ 识别失败: {e}")

            print("🎧 等待按键...")

    def audio_callback(indata, frames, time_info, status):
        nonlocal recording, audio_chunks
        with lock:
            if recording:
                audio_chunks.append(indata[:, 0].copy())

    # 启动键盘监听
    listener = KeyboardListener(
        key_name=trigger_key,
        on_press=on_press,
        on_release=on_release,
    )
    listener.start()

    print("\n🎧 等待按键...")

    # 录音循环
    with sd.InputStream(
        samplerate=16000,
        channels=1,
        dtype=np.float32,
        callback=audio_callback
    ):
        try:
            while listener._thread and listener._thread.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 退出程序")


if __name__ == "__main__":
    print("")
    print("⚠️  首次运行需要授权：")
    print("   系统设置 → 隐私与安全性 → 辅助功能 → 添加终端")
    print("   系统设置 → 隐私与安全性 → 麦克风 → 添加终端")
    print("")

    # 检查辅助功能权限
    if not check_accessibility():
        print("❌ 未获得辅助功能权限，正在打开系统设置...")
        open_accessibility_settings()
        print("   请在系统设置中授权后重新运行")
        sys.exit(1)

    time.sleep(1)
    main()
