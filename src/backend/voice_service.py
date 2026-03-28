"""Voice Aura - 语音服务核心（后端）"""

import os
import time
import subprocess
import tempfile
import threading


class VoiceService:
    """语音输入服务，运行在后台线程中"""

    def __init__(self, overlay=None, on_error=None):
        self._overlay = overlay
        self._on_error = on_error
        self._thread = None
        self._stop_event = threading.Event()
        self.model = None
        self.listener = None
        self.stream = None
        self.recording = False
        self.audio_chunks = []
        self.lock = threading.Lock()

    @property
    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.is_running:
            return True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop_event.set()
        if self.listener:
            self.listener.stop()
            self.listener = None
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        self.model = None

    def _run(self):
        import numpy as np
        import torch
        import soundfile as sf
        import sounddevice as sd
        from qwen_asr import Qwen3ASRModel
        from backend.keyboard_listener import KeyboardListener
        from backend.config import load_config

        config = load_config()
        model_name = config.get("model", "Qwen/Qwen3-ASR-1.7B")
        trigger_key = config.get("trigger_key", "cmd_r")
        replacements = config.get("replacements", {})

        # 加载模型
        if torch.backends.mps.is_available():
            device, dtype = "mps", torch.float16
        elif torch.cuda.is_available():
            device, dtype = "cuda", torch.bfloat16
        else:
            device, dtype = "cpu", torch.float32

        try:
            self.model = Qwen3ASRModel.from_pretrained(
                model_name, dtype=dtype, device_map=device,
                max_inference_batch_size=8, max_new_tokens=128,
            )
        except Exception as e:
            if self._on_error:
                self._on_error(f"模型加载失败: {e}")
            return

        if self._stop_event.is_set():
            return

        overlay = self._overlay

        def on_press():
            if self._stop_event.is_set():
                return
            with self.lock:
                if not self.recording:
                    self.recording = True
                    self.audio_chunks = []
                    if overlay:
                        overlay.show()

        def on_release():
            chunks_copy = []
            with self.lock:
                if self.recording:
                    self.recording = False
                    chunks_copy = self.audio_chunks.copy()
                    self.audio_chunks = []

            if overlay:
                overlay.hide()

            if chunks_copy:
                audio_data = np.concatenate(chunks_copy)
                try:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        tmp_path = f.name
                    sf.write(tmp_path, audio_data, 16000)
                    try:
                        results = self.model.transcribe(audio=tmp_path, language="Chinese")
                    finally:
                        os.unlink(tmp_path)

                    if results and results[0].text:
                        text = results[0].text
                        for wrong, correct in replacements.items():
                            text = text.replace(wrong, correct)
                        type_text(text)
                except Exception as e:
                    print(f"⚠️ 识别失败: {e}")

        def audio_callback(indata, frames, time_info, status):
            with self.lock:
                if self.recording:
                    self.audio_chunks.append(indata[:, 0].copy())

        self.listener = KeyboardListener(
            key_name=trigger_key, on_press=on_press, on_release=on_release,
        )
        try:
            self.listener.start()
        except Exception as e:
            if self._on_error:
                self._on_error(f"键盘监听启动失败（需要辅助功能权限）: {e}")
            return

        if self._stop_event.is_set():
            return

        try:
            self.stream = sd.InputStream(
                samplerate=16000, channels=1, dtype=np.float32,
                callback=audio_callback,
            )
            self.stream.start()
        except Exception as e:
            if self._on_error:
                self._on_error(f"音频流启动失败（需要麦克风权限）: {e}")
            else:
                print(f"❌ 音频流启动失败（需要麦克风权限）: {e}")
            self.listener.stop()
            return

        # 等待停止信号
        self._stop_event.wait()

        # 清理
        try:
            self.stream.stop()
            self.stream.close()
        except Exception:
            pass
        self.listener.stop()


def type_text(text):
    """将文字输入到当前光标位置"""
    try:
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        process.communicate(text.encode('utf-8'))
        time.sleep(0.1)
        result = subprocess.run([
            "osascript", "-e",
            'tell application "System Events" to keystroke "v" using command down'
        ], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            subprocess.Popen([
                "osascript", "-e",
                'display notification "文字已复制到剪贴板，请手动 Cmd+V 粘贴" with title "Voice Aura"'
            ])
    except subprocess.TimeoutExpired:
        print("⚠️ 粘贴超时，文字已复制到剪贴板")
    except Exception as e:
        print(f"⚠️ 输入失败: {e}")
