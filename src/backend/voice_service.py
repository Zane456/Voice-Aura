"""Voice Aura - 语音服务核心（后端）"""

import os
import re
import time
import subprocess
import tempfile
import threading

# 常见中文语气词 / 填充词
_FILLERS = ["呃", "额", "嗯", "啊啊", "哎"]


def remove_fillers(text):
    """去除语音中的语气词，并清理多余标点"""
    for f in _FILLERS:
        text = text.replace(f, "")
    text = re.sub(r"[，,]{2,}", "，", text)
    text = re.sub(r"[。.]{2,}", "。", text)
    text = re.sub(r"^[，,。.、]+", "", text)
    return text.strip()


class VoiceService:
    """语音输入服务，运行在后台线程中"""

    def __init__(self, overlay=None, on_error=None, on_progress=None):
        self._overlay = overlay
        self._on_error = on_error
        self._on_progress = on_progress
        self._thread = None
        self._stop_event = threading.Event()
        self.model = None
        self.listener = None
        self.stream = None
        self.recording = False
        self.audio_chunks = []
        self.lock = threading.Lock()
        self.remove_fillers_enabled = True
        self.space_reposition_enabled = True

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

    def _report(self, stage, pct, detail):
        """向 GUI 报告进度：stage=download/load/idle, pct=0-100 或 -1"""
        if self._on_progress:
            self._on_progress(stage, pct, detail)

    @staticmethod
    def _is_model_cached(model_name):
        """检查模型是否已在 HuggingFace 缓存中"""
        snaps = os.path.expanduser(
            f"~/.cache/huggingface/hub/models--{model_name.replace('/', '--')}/snapshots"
        )
        if not os.path.isdir(snaps):
            return False
        for d in os.listdir(snaps):
            snap = os.path.join(snaps, d)
            if os.path.isdir(snap) and len(os.listdir(snap)) > 3:
                return True
        return False

    def _download_with_progress(self, model_name):
        """下载模型并通过轮询缓存目录报告进度"""
        from huggingface_hub import snapshot_download, HfApi

        # 获取模型总大小
        total_size = 0
        try:
            info = HfApi().model_info(model_name, files_metadata=True)
            total_size = sum(s.size for s in info.siblings if s.size)
        except Exception:
            pass

        blobs_dir = os.path.expanduser(
            f"~/.cache/huggingface/hub/models--{model_name.replace('/', '--')}/blobs"
        )
        done = threading.Event()

        def poll():
            while not done.is_set() and not self._stop_event.is_set():
                downloaded = 0
                if os.path.isdir(blobs_dir):
                    for fname in os.listdir(blobs_dir):
                        try:
                            downloaded += os.path.getsize(
                                os.path.join(blobs_dir, fname))
                        except OSError:
                            pass
                if total_size > 0:
                    pct = min(99, int(downloaded / total_size * 100))
                    detail = f"{downloaded / 1e9:.1f} GB / {total_size / 1e9:.1f} GB"
                    self._report("download", pct, detail)
                else:
                    self._report("download", -1, "下载中...")
                done.wait(0.5)

        poll_thread = threading.Thread(target=poll, daemon=True)
        poll_thread.start()
        try:
            snapshot_download(model_name)
        finally:
            done.set()
        self._report("download", 100, "下载完成")

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
        hotwords = config.get("hotwords", [])
        self.remove_fillers_enabled = config.get("remove_fillers", True)
        self.space_reposition_enabled = config.get("space_reposition", True)

        # 构建热词 context 字符串
        context_str = ""
        if hotwords:
            context_str = " ".join(hotwords)

        # ── 下载模型（如未缓存）──
        if not self._is_model_cached(model_name):
            self._report("download", 0, "准备下载...")
            try:
                self._download_with_progress(model_name)
            except Exception as e:
                if self._on_error:
                    self._on_error(f"模型下载失败: {e}")
                self._report("idle", 0, "")
                return
            if self._stop_event.is_set():
                return

        # ── 加载模型 ──
        self._report("load", -1, "加载模型到内存中...")
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
            self._report("idle", 0, "")
            return
        self._report("idle", 0, "")

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

        def on_reposition():
            """录音中按空格 → 在鼠标当前位置点击一下，重新定位文字光标
            返回 True 表示已处理（吞掉按键），False 表示跳过（放行按键）"""
            if not self.space_reposition_enabled:
                return False
            import Quartz
            pos = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
            down = Quartz.CGEventCreateMouseEvent(
                None, Quartz.kCGEventLeftMouseDown, pos, Quartz.kCGMouseButtonLeft)
            up = Quartz.CGEventCreateMouseEvent(
                None, Quartz.kCGEventLeftMouseUp, pos, Quartz.kCGMouseButtonLeft)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)
            return True

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
                        results = self.model.transcribe(
                            audio=tmp_path, language="Chinese",
                            context=context_str if context_str else "",
                        )
                    finally:
                        os.unlink(tmp_path)

                    if results and results[0].text:
                        text = results[0].text
                        if self.remove_fillers_enabled:
                            text = remove_fillers(text)
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
            on_reposition=on_reposition,
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
