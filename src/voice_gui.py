#!/usr/bin/env python3
"""
语音输入管理器 GUI
管理语音识别服务的启动/停止、触发按键、替换规则
"""

import os
import sys
import json
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

# 获取脚本所在目录和项目根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

# 配置文件路径（保持用户目录）
CONFIG_FILE = os.path.expanduser("~/.voice_config.json")

# 使用当前 Python 解释器
PYTHON_PATH = sys.executable

# 脚本路径（相对于项目目录）
VOICE_INPUT_SCRIPT = os.path.join(SCRIPT_DIR, "voice_input.py")

# 默认配置
DEFAULT_CONFIG = {
    "trigger_key": "cmd_r",
    "replacements": {}
}

# 按键选项
KEY_OPTIONS = {
    "右 Command": "cmd_r",
    "左 Command": "cmd_l",
    "右 Option": "alt_r",
    "左 Option": "alt_l",
    "Control": "ctrl",
    "Shift": "shift",
}


def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """保存配置"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def is_service_running():
    """检查服务是否在运行"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "voice_input.py"],
            capture_output=True,
            text=True
        )
        return bool(result.stdout.strip())
    except:
        return False


def start_service():
    """启动服务"""
    if is_service_running():
        return True

    if not os.path.exists(VOICE_INPUT_SCRIPT):
        messagebox.showerror("错误", f"找不到服务脚本:\n{VOICE_INPUT_SCRIPT}")
        return False

    try:
        subprocess.Popen(
            [PYTHON_PATH, VOICE_INPUT_SCRIPT],
            stdout=open("/tmp/voice_input.log", "w"),
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        return True
    except Exception as e:
        messagebox.showerror("错误", f"启动服务失败: {e}")
        return False


def stop_service():
    """停止服务"""
    try:
        subprocess.run(["pkill", "-9", "-f", "voice_input.py"], capture_output=True)
        return True
    except Exception as e:
        messagebox.showerror("错误", f"停止服务失败: {e}")
        return False


class VoiceInputManager:
    def __init__(self, root):
        self.root = root
        self.root.title("语音输入管理器")
        self.root.geometry("500x600")
        self.root.resizable(True, True)

        self.config = load_config()

        self.setup_ui()
        self.update_status()

    def setup_ui(self):
        """设置界面"""
        # 标题
        title_frame = tk.Frame(self.root)
        title_frame.pack(fill=tk.X, padx=20, pady=15)
        tk.Label(title_frame, text="🎤 语音输入管理器", font=("Arial", 18, "bold")).pack()

        # === 服务控制区域 ===
        service_frame = tk.LabelFrame(self.root, text="服务控制", font=("Arial", 12))
        service_frame.pack(fill=tk.X, padx=20, pady=10)

        status_frame = tk.Frame(service_frame)
        status_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(status_frame, text="状态:", font=("Arial", 12)).pack(side=tk.LEFT)
        self.status_label = tk.Label(status_frame, text="检查中...", font=("Arial", 12, "bold"), fg="gray")
        self.status_label.pack(side=tk.LEFT, padx=10)

        btn_frame = tk.Frame(service_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        self.start_btn = tk.Button(btn_frame, text="▶ 启动", font=("Arial", 12), width=10, command=self.on_start)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(btn_frame, text="⏹ 停止", font=("Arial", 12), width=10, command=self.on_stop)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.refresh_btn = tk.Button(btn_frame, text="🔄 刷新", font=("Arial", 12), width=10, command=self.update_status)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)

        # === 触发按键设置 ===
        key_frame = tk.LabelFrame(self.root, text="触发按键", font=("Arial", 12))
        key_frame.pack(fill=tk.X, padx=20, pady=10)

        key_inner = tk.Frame(key_frame)
        key_inner.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(key_inner, text="按下此键开始录音:", font=("Arial", 11)).pack(side=tk.LEFT)

        # 找到当前选项的名称
        current_key = self.config.get("trigger_key", "cmd_r")
        current_name = "右 Command"
        for name, value in KEY_OPTIONS.items():
            if value == current_key:
                current_name = name
                break

        self.key_var = tk.StringVar(value=current_name)
        self.key_combo = ttk.Combobox(key_inner, textvariable=self.key_var, values=list(KEY_OPTIONS.keys()), state="readonly", width=15)
        self.key_combo.pack(side=tk.LEFT, padx=10)

        tk.Button(key_inner, text="保存", font=("Arial", 11), command=self.save_key).pack(side=tk.LEFT)

        # === 替换规则管理 ===
        rules_frame = tk.LabelFrame(self.root, text="替换规则（后处理）", font=("Arial", 12))
        rules_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 说明
        tk.Label(rules_frame, text="识别错误 → 正确文本", font=("Arial", 10), fg="gray").pack(anchor=tk.W, padx=10, pady=5)

        # 列表
        list_frame = tk.Frame(rules_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.rules_listbox = tk.Listbox(list_frame, font=("Arial", 12), yscrollcommand=scrollbar.set)
        self.rules_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.rules_listbox.yview)

        # 加载规则到列表
        self.refresh_rules()

        # 添加规则输入
        add_frame = tk.Frame(rules_frame)
        add_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(add_frame, text="错误:", font=("Arial", 11)).pack(side=tk.LEFT)
        self.wrong_entry = tk.Entry(add_frame, font=("Arial", 11), width=15)
        self.wrong_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(add_frame, text="→", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)

        tk.Label(add_frame, text="正确:", font=("Arial", 11)).pack(side=tk.LEFT)
        self.correct_entry = tk.Entry(add_frame, font=("Arial", 11), width=15)
        self.correct_entry.pack(side=tk.LEFT, padx=5)

        tk.Button(add_frame, text="添加", font=("Arial", 11), command=self.add_rule).pack(side=tk.LEFT, padx=10)

        # 删除按钮
        del_frame = tk.Frame(rules_frame)
        del_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Button(del_frame, text="删除选中", font=("Arial", 11), command=self.delete_rule).pack(side=tk.LEFT)
        tk.Button(del_frame, text="清空全部", font=("Arial", 11), command=self.clear_rules).pack(side=tk.LEFT, padx=10)

    def update_status(self):
        """更新服务状态"""
        if is_service_running():
            self.status_label.config(text="● 运行中", fg="green")
        else:
            self.status_label.config(text="○ 已停止", fg="red")

    def on_start(self):
        """启动服务"""
        if start_service():
            self.root.after(1000, self.update_status)

    def on_stop(self):
        """停止服务"""
        if stop_service():
            self.update_status()

    def save_key(self):
        """保存触发按键设置"""
        key_name = self.key_var.get()
        key_value = KEY_OPTIONS.get(key_name, "cmd_r")
        self.config["trigger_key"] = key_value
        save_config(self.config)
        messagebox.showinfo("成功", f"触发按键已设置为: {key_name}\n\n需要重启服务才能生效")

    def refresh_rules(self):
        """刷新规则列表"""
        self.rules_listbox.delete(0, tk.END)
        replacements = self.config.get("replacements", {})
        for wrong, correct in replacements.items():
            self.rules_listbox.insert(tk.END, f"{wrong} → {correct}")

    def add_rule(self):
        """添加替换规则"""
        wrong = self.wrong_entry.get().strip()
        correct = self.correct_entry.get().strip()

        if not wrong or not correct:
            messagebox.showwarning("警告", "请输入错误和正确的文本")
            return

        if "replacements" not in self.config:
            self.config["replacements"] = {}

        self.config["replacements"][wrong] = correct
        save_config(self.config)
        self.refresh_rules()

        self.wrong_entry.delete(0, tk.END)
        self.correct_entry.delete(0, tk.END)

        messagebox.showinfo("成功", "规则已添加\n\n需要重启服务才能生效")

    def delete_rule(self):
        """删除选中的规则"""
        selection = self.rules_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的规则")
            return

        index = selection[0]
        rule_text = self.rules_listbox.get(index)
        wrong = rule_text.split(" → ")[0]

        if wrong in self.config.get("replacements", {}):
            del self.config["replacements"][wrong]
            save_config(self.config)
            self.refresh_rules()
            messagebox.showinfo("成功", "规则已删除\n\n需要重启服务才能生效")

    def clear_rules(self):
        """清空所有规则"""
        if messagebox.askyesno("确认", "确定要清空所有替换规则吗？"):
            self.config["replacements"] = {}
            save_config(self.config)
            self.refresh_rules()


def main():
    root = tk.Tk()
    app = VoiceInputManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
