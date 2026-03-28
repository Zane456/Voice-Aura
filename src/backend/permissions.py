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


def check_microphone_status():
    """检查麦克风权限状态
    Returns: 'authorized', 'denied', 'not_determined', or 'unknown'
    """
    try:
        import objc
        objc.loadBundle(
            'AVFoundation', {},
            bundle_path='/System/Library/Frameworks/AVFoundation.framework'
        )
        AVCaptureDevice = objc.lookUpClass('AVCaptureDevice')
        status = AVCaptureDevice.authorizationStatusForMediaType_("soun")
        return {
            0: 'not_determined', 1: 'restricted',
            2: 'denied', 3: 'authorized',
        }.get(status, 'unknown')
    except Exception:
        return 'unknown'


def check_microphone():
    """检查麦克风权限是否已授权"""
    return check_microphone_status() == 'authorized'


def request_microphone_permission():
    """请求麦克风权限（首次调用触发系统弹窗，已拒绝则打开设置）"""
    status = check_microphone_status()
    if status == 'not_determined':
        try:
            import objc
            objc.loadBundle(
                'AVFoundation', {},
                bundle_path='/System/Library/Frameworks/AVFoundation.framework'
            )
            AVCaptureDevice = objc.lookUpClass('AVCaptureDevice')
            AVCaptureDevice.requestAccessForMediaType_completionHandler_(
                "soun", lambda granted: None
            )
        except Exception:
            open_microphone_settings()
    else:
        open_microphone_settings()
