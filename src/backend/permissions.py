#!/usr/bin/env python3
"""macOS 权限管理 - 检查辅助功能与麦克风权限"""

import ctypes
import subprocess


def check_accessibility():
    """检查辅助功能权限（AXIsProcessTrusted）"""
    try:
        _lib = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
        )
        _lib.AXIsProcessTrusted.restype = ctypes.c_bool
        return _lib.AXIsProcessTrusted()
    except Exception:
        return False


def open_accessibility_settings():
    """打开系统设置 → 隐私与安全性 → 辅助功能"""
    subprocess.Popen([
        "open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
    ])


def open_microphone_settings():
    """打开系统设置 → 隐私与安全性 → 麦克风"""
    subprocess.Popen([
        "open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
    ])
