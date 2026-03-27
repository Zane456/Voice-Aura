#!/usr/bin/env python3
"""
FunASR 按键语音输入
按住右 Command 键说话， 松开后自动识别并输入到光标位置
"""

import os
import subprocess
import threading
import time
import json
import numpy as np

# 配置文件路径
CONFIG_FILE = os.path.expanduser("~/.voice_config.json")

# 默认配置
DEFAULT_CONFIG = {
    "trigger_key": "cmd_r",
    "replacements": {
        "cloud code": "Claude Code",
        "cloud cold": "Claude Code",
        "克劳德": "Claude",
        "n八n": "n8n",
        "N八n": "n8n",
        "质朴": "智谱",
        "G L M": "GLM",
        "open router": "OpenRouter",
        "openrouter": "OpenRouter",
        "code x": "CodeX",
        "sonnet": "Sonnet",
        "opus": "Opus",
    }
}

# 按键映射
KEY_MAP = {
    "cmd_r": "cmd_r",
    "cmd_l": "cmd_l",
    "alt_r": "alt_r",
    "alt_l": "alt_l",
    "ctrl": "ctrl",
    "shift": "shift",
}

def load_config():
    """加载配置文件"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_CONFIG.copy()

# 全局变量
recording = False
audio_chunks = []
lock = threading.Lock()
hotwords = []  # 热词列表
HOTWORDS_FILE = os.path.expanduser("~/hotwords.txt")

# 从配置文件加载
config = load_config()
REPLACEMENTS = config.get("replacements", DEFAULT_CONFIG["replacements"])
TRIGGER_KEY = config.get("trigger_key", DEFAULT_CONFIG["trigger_key"])

def post_process(text):
    """后处理：替换常见的误识别"""
    for wrong, correct in REPLACEMENTS.items():
        text = text.replace(wrong, correct)
    return text

def load_hotwords():
    """加载热词"""
    if os.path.exists(HOTWORDS_FILE):
        with open(HOTWORDS_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    return []


def main():
    global recording, audio_chunks, hotwords, REPLACEMENTS, TRIGGER_KEY
    import sounddevice as sd
    from funasr import AutoModel
    from pynput import keyboard

    # 重新加载配置（支持热更新）
    config = load_config()
    REPLACEMENTS = config.get("replacements", DEFAULT_CONFIG["replacements"])
    TRIGGER_KEY = config.get("trigger_key", DEFAULT_CONFIG["trigger_key"])

    # 按键映射
    KEY_MAP = {
        "cmd_r": keyboard.Key.cmd_r,
        "cmd_l": keyboard.Key.cmd_l,
        "alt_r": keyboard.Key.alt_r,
        "alt_l": keyboard.Key.alt_l,
        "ctrl": keyboard.Key.ctrl,
        "shift": keyboard.Key.shift,
    }
    trigger_key_obj = KEY_MAP.get(TRIGGER_KEY, keyboard.Key.cmd_r)

    # 按键名称映射（用于显示）
    KEY_NAMES = {
        "cmd_r": "右 Command",
        "cmd_l": "左 Command",
        "alt_r": "右 Option",
        "alt_l": "左 Option",
        "ctrl": "Control",
        "shift": "Shift",
    }
    trigger_key_name = KEY_NAMES.get(TRIGGER_KEY, "右 Command")

    print("=" * 50)
    print("🎤 FunASR 按键语音输入")
    print("=" * 50)
    print("")
    print("📂 初始化模型中...")

    # 加载热词
    hotwords = load_hotwords()
    if hotwords:
        print(f"🔥 已加载 {len(hotwords)} 个热词")

    # 使用已下载的模型
    model = AutoModel(
        model="iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        punc_model="iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        disable_update=True,
    )

    print("✅ 模型加载完成！")
    print("")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🔵 按住【{trigger_key_name}键】 开始录音")
    print("🔴 松开后自动识别并输入到光标位置")
    print("💡 按 Ctrl+C 退出程序")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    def on_press(key):
        global recording, audio_chunks
        if key == trigger_key_obj:
            with lock:
                if not recording:
                    recording = True
                    audio_chunks = []
                    print("\n🎙️ 录音中... 请说话...")

    def on_release(key):
        global recording, audio_chunks
        if key == trigger_key_obj:
            with lock:
                if recording:
                    recording = False
                    print("⏹️ 嚜止，识别中...")
                    chunks_copy = audio_chunks.copy()
                    audio_chunks = []

            if len(chunks_copy) > 0:
                audio_data = np.concatenate(chunks_copy)

                # 传递热词字符串给模型（FunASR 要求空格分隔的字符串格式）
                hotword_str = ' '.join([' '.join(w.split()[:-1]) if w.split()[-1].isdigit() else w for w in hotwords])
                result = model.generate(
                    input=audio_data,
                    hotword=hotword_str if hotword_str else None
                )
                if result and result[0]["text"]:
                    text = result[0]["text"]
                    text = post_process(text)  # 后处理替换
                    print(f"📝 {text}")
                    type_text(text)
                else:
                    print("❌ 未识别到内容")
                print("🎧 等待按键...")

    def audio_callback(indata, frames, time_info, status):
        global recording, audio_chunks
        with lock:
            if recording:
                audio_chunks.append(indata[:, 0].copy())

    def type_text(text):
        """将文字输入到当前光标位置"""
        try:
            # 复制到剪贴板
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            process.communicate(text.encode('utf-8'))
            # 模拟 Cmd+V 粘贴
            time.sleep(0.1)
            subprocess.run([
                "osascript", "-e",
                'tell application "System Events" to keystroke "v" using command down'
            ])
        except Exception as e:
            print(f"⚠️ 输入失败: {e}")
            print(f"   请手动粘贴: {text}")

    # 启动键盘监听
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
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
            listener.join()
        except KeyboardInterrupt:
            print("\n👋 退出程序")


if __name__ == "__main__":
    print("")
    print("⚠️  首次运行需要授权：")
    print("   系统设置 → 隐私与安全性 → 辅助功能 → 添加终端")
    print("   系统设置 → 隐私与安全性 → 麦克风 → 添加终端")
    print("")
    time.sleep(1)
    main()
