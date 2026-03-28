#!/usr/bin/env python3
"""
浮动录音指示器 - 使用 NSPanel 替代 macOS 通知
通知会在 ~4 秒后自动消失，无法控制。NSPanel 完全由程序控制显隐。
"""

import math
import threading
import objc
from AppKit import (
    NSPanel, NSScreen, NSColor, NSView,
    NSWindowStyleMaskBorderless, NSWindowStyleMaskNonactivatingPanel,
    NSBackingStoreBuffered,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorStationary,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSFloatingWindowLevel,
    NSVisualEffectView,
    NSVisualEffectMaterialHUDWindow,
    NSVisualEffectBlendingModeBehindWindow,
    NSVisualEffectStateActive,
    NSMakeRect, NSBezierPath, NSGraphicsContext,
    NSTimer, NSRunLoop, NSRunLoopCommonModes,
)
from CoreFoundation import CFRunLoopGetMain, CFRunLoopWakeUp, CFRunLoopPerformBlock, kCFRunLoopCommonModes


class WaveformView(NSView):
    """蓝色波形条动画，指示录音中"""

    BAR_COUNT = 5
    BAR_WIDTH = 4
    BAR_GAP = 3
    MAX_BAR_HEIGHT = 20
    MIN_BAR_HEIGHT = 4

    def initWithFrame_(self, frame):
        self = objc.super(WaveformView, self).initWithFrame_(frame)
        if self is None:
            return None
        self._bar_heights = [self.MIN_BAR_HEIGHT] * self.BAR_COUNT
        self._animating = False
        self._timer = None
        self._time = 0.0
        return self

    def drawRect_(self, rect):
        context = NSGraphicsContext.currentContext()
        if context is None:
            return
        total_width = self.BAR_COUNT * self.BAR_WIDTH + (self.BAR_COUNT - 1) * self.BAR_GAP
        start_x = (rect.size.width - total_width) / 2

        for i in range(self.BAR_COUNT):
            height = self._bar_heights[i]
            x = start_x + i * (self.BAR_WIDTH + self.BAR_GAP)
            y = (rect.size.height - height) / 2

            alpha = 0.6 + 0.4 * (height / self.MAX_BAR_HEIGHT)
            NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.23, 0.51, 0.96, alpha
            ).setFill()

            bar_rect = NSMakeRect(x, y, self.BAR_WIDTH, height)
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                bar_rect, 2, 2
            ).fill()

    def startAnimation(self):
        if self._animating:
            return
        self._animating = True
        self._time = 0.0
        self._timer = NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(
            0.06, self, b"animationStep:", None, True
        )
        NSRunLoop.mainRunLoop().addTimer_forMode_(self._timer, NSRunLoopCommonModes)

    def stopAnimation(self):
        self._animating = False
        if self._timer:
            self._timer.invalidate()
            self._timer = None
        self._bar_heights = [self.MIN_BAR_HEIGHT] * self.BAR_COUNT
        self.setNeedsDisplay_(True)

    def animationStep_(self, timer):
        if not self._animating:
            return
        self._time += 0.06
        for i in range(self.BAR_COUNT):
            phase = self._time * 4.0 + i * 0.9
            normalized = (math.sin(phase) + 1) / 2
            self._bar_heights[i] = self.MIN_BAR_HEIGHT + normalized * (self.MAX_BAR_HEIGHT - self.MIN_BAR_HEIGHT)
        self.setNeedsDisplay_(True)


class RecordingOverlay:
    """
    浮动录音指示器：按住按键时显示，松手时立即消失。
    可从任意线程调用 show()/hide()。
    """

    PANEL_WIDTH = 60
    PANEL_HEIGHT = 36
    CORNER_RADIUS = 18
    MARGIN_TOP = 12

    def __init__(self):
        self._panel = None
        self._waveform_view = None
        self._built = False
        self._visible = False

    def show(self):
        self._on_main(self._show)

    def hide(self):
        self._on_main(self._hide)

    # ── 线程调度 ──

    def _on_main(self, fn):
        if threading.current_thread() is threading.main_thread():
            fn()
        else:
            loop = CFRunLoopGetMain()
            CFRunLoopPerformBlock(loop, kCFRunLoopCommonModes, fn)
            CFRunLoopWakeUp(loop)

    # ── 构建 UI ──

    def _build(self):
        if self._built:
            return

        screen = NSScreen.mainScreen()
        sf = screen.frame()
        vf = screen.visibleFrame()

        panel_x = (sf.size.width - self.PANEL_WIDTH) / 2
        panel_y = vf.origin.y + vf.size.height - self.PANEL_HEIGHT - self.MARGIN_TOP

        style = NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel
        self._panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(panel_x, panel_y, self.PANEL_WIDTH, self.PANEL_HEIGHT),
            style, NSBackingStoreBuffered, False,
        )
        self._panel.setLevel_(NSFloatingWindowLevel)
        self._panel.setOpaque_(False)
        self._panel.setBackgroundColor_(NSColor.clearColor())
        self._panel.setHasShadow_(True)
        self._panel.setIgnoresMouseEvents_(True)
        self._panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorStationary
            | NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        content_rect = NSMakeRect(0, 0, self.PANEL_WIDTH, self.PANEL_HEIGHT)

        vibrancy = NSVisualEffectView.alloc().initWithFrame_(content_rect)
        vibrancy.setMaterial_(NSVisualEffectMaterialHUDWindow)
        vibrancy.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        vibrancy.setState_(NSVisualEffectStateActive)
        vibrancy.setWantsLayer_(True)
        vibrancy.layer().setCornerRadius_(self.CORNER_RADIUS)
        vibrancy.layer().setMasksToBounds_(True)
        self._panel.setContentView_(vibrancy)

        # 蓝色波形条
        self._waveform_view = WaveformView.alloc().initWithFrame_(content_rect)
        vibrancy.addSubview_(self._waveform_view)

        self._built = True

    def _reposition(self):
        screen = NSScreen.mainScreen()
        sf = screen.frame()
        vf = screen.visibleFrame()
        panel_x = (sf.size.width - self.PANEL_WIDTH) / 2
        panel_y = vf.origin.y + vf.size.height - self.PANEL_HEIGHT - self.MARGIN_TOP
        self._panel.setFrameOrigin_((panel_x, panel_y))

    # ── 显隐控制 ──

    def _show(self):
        self._build()
        self._reposition()
        self._panel.setAlphaValue_(0.0)
        self._panel.orderFrontRegardless()
        self._visible = True
        self._panel.animator().setAlphaValue_(1.0)
        self._waveform_view.startAnimation()

    def _hide(self):
        if not self._built or not self._visible:
            return
        self._visible = False
        self._waveform_view.stopAnimation()
        self._panel.orderOut_(None)
