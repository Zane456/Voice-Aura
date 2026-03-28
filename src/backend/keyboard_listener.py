#!/usr/bin/env python3
"""
macOS 键盘监听器 - 使用 CGEventTap 直接监听
替代 pynput，避免 macOS 26+ 上 TSM 线程安全崩溃
"""

import threading
import Quartz

# macOS 虚拟键码
KEY_CODES = {
    "cmd_r": 0x36,
    "cmd_l": 0x37,
    "alt_r": 0x3D,
    "alt_l": 0x3A,
    "ctrl": 0x3B,
    "shift": 0x38,
}

SPACE_KEYCODE = 0x31

# 对应的 CGEventFlags 位掩码
KEY_FLAGS = {
    "cmd_r": Quartz.kCGEventFlagMaskCommand,
    "cmd_l": Quartz.kCGEventFlagMaskCommand,
    "alt_r": Quartz.kCGEventFlagMaskAlternate,
    "alt_l": Quartz.kCGEventFlagMaskAlternate,
    "ctrl": Quartz.kCGEventFlagMaskControl,
    "shift": Quartz.kCGEventFlagMaskShift,
}


class KeyboardListener:
    """使用 CGEventTap 的轻量键盘监听器

    关键设计：回调只设置标志位，立即返回。
    on_release 在独立线程中执行，避免阻塞事件循环导致 macOS 禁用事件监听。
    """

    def __init__(self, key_name="cmd_r", on_press=None, on_release=None,
                 on_reposition=None):
        self._key_code = KEY_CODES.get(key_name, 0x36)
        self._flag_mask = KEY_FLAGS.get(key_name, Quartz.kCGEventFlagMaskCommand)
        self._on_press = on_press
        self._on_release = on_release
        self._on_reposition = on_reposition
        self._pressed = False
        self._space_swallowed = False
        self._tap = None
        self._source = None
        self._run_loop = None
        self._thread = None
        self._stop = threading.Event()

    def start(self):
        self._stop.clear()
        self._pressed = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._run_loop:
            try:
                Quartz.CFRunLoopStop(self._run_loop)
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _run(self):
        event_mask = (
            (1 << Quartz.kCGEventFlagsChanged)
            | (1 << Quartz.kCGEventKeyDown)
            | (1 << Quartz.kCGEventKeyUp)
        )
        release_event = threading.Event()

        def callback(proxy, event_type, event, refcon):
            # 录音中按空格 → 触发重新定位，根据返回值决定是否吞掉按键
            if event_type in (Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp):
                if self._pressed:
                    keycode = Quartz.CGEventGetIntegerValueField(
                        event, Quartz.kCGKeyboardEventKeycode
                    )
                    if keycode == SPACE_KEYCODE:
                        if event_type == Quartz.kCGEventKeyDown and self._on_reposition:
                            try:
                                handled = self._on_reposition()
                            except Exception:
                                handled = False
                            if handled:
                                self._space_swallowed = True
                                return None
                            self._space_swallowed = False
                        elif event_type == Quartz.kCGEventKeyUp and self._space_swallowed:
                            self._space_swallowed = False
                            return None
                return event

            # 修饰键状态变化 → 检测触发键按下/释放
            keycode = Quartz.CGEventGetIntegerValueField(
                event, Quartz.kCGKeyboardEventKeycode
            )
            if keycode == self._key_code:
                flags = Quartz.CGEventGetFlags(event)
                is_pressed = bool(flags & self._flag_mask)

                if is_pressed and not self._pressed:
                    self._pressed = True
                    # on_press 通常是轻量操作，直接在回调中执行
                    if self._on_press:
                        try:
                            self._on_press()
                        except Exception:
                            pass
                elif not is_pressed and self._pressed:
                    self._pressed = False
                    # on_release 可能很重（模型推理），通过 event 通知工作线程
                    release_event.set()

            return event

        self._tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault,
            event_mask,
            callback,
            None,
        )

        if not self._tap:
            print("❌ 无法创建键盘监听（需要辅助功能权限）")
            return

        self._run_loop = Quartz.CFRunLoopGetCurrent()
        self._source = Quartz.CFMachPortCreateRunLoopSource(None, self._tap, 0)
        Quartz.CFRunLoopAddSource(
            self._run_loop, self._source, Quartz.kCFRunLoopCommonModes
        )
        Quartz.CGEventTapEnable(self._tap, True)

        # 主循环：处理事件 + 在独立线程中执行重量级回调
        while not self._stop.is_set():
            Quartz.CFRunLoopRunInMode(
                Quartz.kCFRunLoopDefaultMode, 0.5, False
            )

            if release_event.is_set():
                release_event.clear()
                # 在独立线程中执行 on_release，避免阻塞事件循环
                if self._on_release:
                    t = threading.Thread(target=self._on_release, daemon=True)
                    t.start()

        # 清理
        try:
            Quartz.CGEventTapEnable(self._tap, False)
            Quartz.CFRunLoopRemoveSource(
                self._run_loop, self._source, Quartz.kCFRunLoopCommonModes
            )
        except Exception:
            pass
