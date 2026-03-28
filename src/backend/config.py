"""Voice Aura - 配置管理"""

import os
import json

CONFIG_FILE = os.path.expanduser("~/.voice_config.json")

KEY_OPTIONS = {
    "右 Command": "cmd_r",
    "左 Command": "cmd_l",
    "右 Option": "alt_r",
    "左 Option": "alt_l",
    "Control": "ctrl",
    "Shift": "shift",
}

MODEL_OPTIONS = {
    "Qwen3-ASR-1.7B (精确)": "Qwen/Qwen3-ASR-1.7B",
    "Qwen3-ASR-0.6B (极速)": "Qwen/Qwen3-ASR-0.6B",
}


def get_default_config():
    """获取默认配置（从项目配置文件加载）"""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "config", "default_config.json",
    )
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "trigger_key": "cmd_r",
        "model": "Qwen/Qwen3-ASR-1.7B",
        "replacements": {},
        "remove_fillers": True,
        "space_reposition": True,
    }


def load_config():
    """加载配置文件"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                if "model" not in config:
                    config["model"] = list(MODEL_OPTIONS.values())[0]
                return config
        except Exception:
            pass
    return get_default_config()


def is_fresh_install():
    """判断是否为全新安装（配置文件不存在）"""
    return not os.path.exists(CONFIG_FILE)


def save_config(config):
    """保存配置文件"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
