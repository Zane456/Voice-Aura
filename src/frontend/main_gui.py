"""Voice Aura - GUI 前端 (Glassmorphism Edition)"""

import math
import os
import random
import sys
import tkinter as tk
import tkinter.font
from tkinter import ttk, messagebox

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(SCRIPT_DIR))

from backend.config import load_config, save_config, KEY_OPTIONS, MODEL_OPTIONS
from backend.voice_service import VoiceService
from backend.permissions import check_accessibility, open_accessibility_settings, open_microphone_settings

# ===== 配色方案：Powder Blue Glassmorphism =====
C = {
    "bg": "#C8D8E8",
    "bg_panel": "#E2EEF7",
    "bg_card": "#F8FBFD",
    "border": "#B8CCDA",
    "text": "#2C5A73",
    "text_sec": "#507890",
    "text_hint": "#7A9AB0",
    "accent": "#A8CEE0",
    "accent_hover": "#8ABCD4",
    "green": "#7ECE95",
    "green_btn": "#A8D8BE",
    "green_btn_hover": "#8CC8A6",
    "red": "#D89898",
    "red_btn": "#D8A8A8",
    "red_btn_hover": "#C89090",
    "btn_text": "#2E5E74",
    "list_sel": "#C0DCE8",
    "input_border": "#C0D4E0",
    "input_focus": "#A8CEE0",
    "white": "#FFFFFF",
}


class _Orb:
    """大型背景光球 — 在面板后面缓慢漂浮，创造颜色深度"""
    COLORS = [
        (145, 195, 232), (160, 205, 238), (135, 188, 225),
        (155, 200, 235), (170, 210, 240), (140, 192, 228),
    ]

    def __init__(self, cw, ch):
        self.r = random.randint(60, 120)
        self.x = random.uniform(self.r, max(self.r + 1, cw - self.r))
        self.y = random.uniform(self.r, max(self.r + 1, ch - self.r))
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.02, 0.06)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        c = random.choice(self.COLORS)
        self.color = f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"

    def step(self, cw, ch):
        self.x += self.vx
        self.y += self.vy
        if self.x - self.r <= 0 or self.x + self.r >= cw:
            self.vx = -self.vx
        if self.y - self.r <= 0 or self.y + self.r >= ch:
            self.vy = -self.vy


class _Bubble:
    """玻璃泡泡 — 在边距区域弹跳"""
    PALETTES = [
        (90, 172, 218), (105, 180, 228), (80, 165, 210),
        (120, 192, 235), (95, 175, 220), (75, 158, 205),
        (130, 198, 240), (85, 168, 215), (140, 205, 242),
        (100, 178, 222),
    ]

    def __init__(self, cw, ch):
        self.r = random.randint(14, 38)
        self.x = random.uniform(self.r + 2, max(self.r + 3, cw - self.r - 2))
        self.y = random.uniform(self.r + 2, max(self.r + 3, ch - self.r - 2))
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.05, 0.15)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        c = random.choice(self.PALETTES)
        self.color = f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"
        hl = [min(255, v + random.randint(40, 65)) for v in c]
        self.highlight = f"#{hl[0]:02x}{hl[1]:02x}{hl[2]:02x}"
        self.rim_color = f"#{max(0,c[0]-20):02x}{max(0,c[1]-15):02x}{max(0,c[2]-10):02x}"

    def step(self, cw, ch):
        self.x += self.vx
        self.y += self.vy
        if self.x - self.r <= 0:
            self.x = self.r
            self.vx = abs(self.vx)
        elif self.x + self.r >= cw:
            self.x = cw - self.r
            self.vx = -abs(self.vx)
        if self.y - self.r <= 0:
            self.y = self.r
            self.vy = abs(self.vy)
        elif self.y + self.r >= ch:
            self.y = ch - self.r
            self.vy = -abs(self.vy)


class VoiceInputManager:
    MARGIN = 50

    def __init__(self, root):
        self.root = root
        self.root.title("Voice Aura")
        self.root.configure(bg=C["bg"])
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        w, h = 960, min(1240, sh - 100)
        root.geometry(f"{w}x{h}+{(sw-w)//2}+{max(0,(sh-h)//2)}")
        root.minsize(800, 600)
        root.resizable(True, True)
        self.config = load_config()
        from frontend.recording_overlay import RecordingOverlay
        self.service = VoiceService(
            overlay=RecordingOverlay(),
            on_error=self._on_service_error,
        )
        self._setup_styles()

        # 背景画布
        self.canvas = tk.Canvas(root, bg=C["bg"], highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 大型背景光球（先画，在最底层）
        self.orbs = [_Orb(w, h) for _ in range(6)]
        self._orb_ids = []
        for orb in self.orbs:
            x, y, r = orb.x, orb.y, orb.r
            oid = self.canvas.create_oval(x-r, y-r, x+r, y+r,
                                          fill=orb.color, outline="")
            self._orb_ids.append(oid)

        # 玻璃泡泡（在光球之上）
        self.bubbles = [_Bubble(w, h) for _ in range(18)]
        self._bub_ids = []
        for b in self.bubbles:
            x, y, r = b.x, b.y, b.r
            rim = self.canvas.create_oval(x-r-2, y-r-2, x+r+2, y+r+2,
                                          fill="", outline=b.rim_color, width=1.5)
            body = self.canvas.create_oval(x-r, y-r, x+r, y+r,
                                           fill=b.color, outline="")
            shine = self.canvas.create_oval(
                x-r*0.38, y-r*0.42, x+r*0.10, y-r*0.02,
                fill=b.highlight, outline="")
            self._bub_ids.append({"rim": rim, "body": body, "shine": shine})

        # 主面板（canvas window，四周留白让泡泡可见）
        self.panel = tk.Frame(self.canvas, bg=C["bg_panel"])
        self._panel_win = self.canvas.create_window(
            self.MARGIN, self.MARGIN, window=self.panel, anchor=tk.NW)

        self.setup_ui()
        self.update_status()
        self._start_polling()
        self.canvas.bind("<Configure>", self._on_canvas_cfg)
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._animate()

    # ── 动画 ──

    def _animate(self):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10:
            cw, ch = 960, 900

        for orb, oid in zip(self.orbs, self._orb_ids):
            ox, oy = orb.x, orb.y
            orb.step(cw, ch)
            dx, dy = orb.x - ox, orb.y - oy
            self.canvas.move(oid, dx, dy)

        for b, ids in zip(self.bubbles, self._bub_ids):
            ox, oy = b.x, b.y
            b.step(cw, ch)
            dx, dy = b.x - ox, b.y - oy
            for iid in ids.values():
                self.canvas.move(iid, dx, dy)

        self._anim_id = self.root.after(55, self._animate)

    def _on_canvas_cfg(self, event):
        w = max(0, event.width - 2 * self.MARGIN)
        h = max(0, event.height - 2 * self.MARGIN)
        self.canvas.itemconfigure(self._panel_win, width=w, height=h)

    def _on_close(self):
        if hasattr(self, "_anim_id"):
            self.root.after_cancel(self._anim_id)
        if hasattr(self, "_poll_id"):
            self.root.after_cancel(self._poll_id)
        self.root.destroy()

    # ── 样式 ──

    def _setup_styles(self):
        self.root.option_add("*Font", "Helvetica 12")
        style = ttk.Style()
        try:
            style.theme_use("aqua")
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground=C["white"],
                         background=C["white"], foreground=C["text"])

    def _card(self, parent, **kw):
        return tk.Frame(parent, bg=C["bg_card"],
                        highlightbackground=C["border"],
                        highlightthickness=1, bd=0, **kw)

    def _section_title(self, parent, text):
        f = tk.Frame(parent, bg=C["bg_card"])
        f.pack(fill=tk.X, padx=16, pady=(12, 4))
        tk.Label(f, text=text, font=("Helvetica", 11, "bold"),
                 bg=C["bg_card"], fg=C["text_sec"]).pack(side=tk.LEFT)

    @staticmethod
    def _rr(canvas, x1, y1, x2, y2, r=12, **kw):
        pts = [x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,
               x2,y2-r,x2,y2,x2-r,y2,x1+r,y2,
               x1,y2,x1,y2-r,x1,y1+r,x1,y1]
        return canvas.create_polygon(pts, smooth=True, **kw)

    def _make_btn(self, parent, text, cmd, bg, fg,
                  font=("Helvetica", 13), padx=18, pady=8, r=11, hover=None):
        fo = tk.font.Font(font=font)
        tw, th = fo.measure(text), fo.metrics("ascent") + fo.metrics("descent")
        w, h = tw + padx*2, th + pady*2
        hover = hover or _adj(bg, -15)
        pbg = parent.cget("bg")
        cv = tk.Canvas(parent, width=w, height=h+3, bg=pbg, highlightthickness=0, cursor="hand2")
        self._rr(cv, 3, 5, w-1, h+2, r=r, fill=_adj(pbg, -22), outline="")
        self._rr(cv, 2, 2, w-2, h, r=r, fill=bg, outline="", tags="bg")
        cv.create_text(w//2, h//2+2, text=text, font=font, fill=fg, tags="txt")
        pressed = [False]
        def enter(e): cv.itemconfig("bg", fill=hover)
        def leave(e):
            cv.itemconfig("bg", fill=bg)
            if pressed[0]: cv.move("all", 0, -2); pressed[0] = False
        def press(e): cv.move("all", 0, 2); pressed[0] = True
        def release(e):
            if pressed[0]: cv.move("all", 0, -2); pressed[0] = False
            cmd()
        cv.bind("<Enter>", enter); cv.bind("<Leave>", leave)
        cv.bind("<ButtonPress-1>", press); cv.bind("<ButtonRelease-1>", release)
        return cv

    def _accent_btn(self, parent, text, cmd, color=None, text_color=None):
        c = color or C["accent"]
        h = C["accent_hover"] if c == C["accent"] else None
        return self._make_btn(parent, text, cmd, c, text_color or C["btn_text"], hover=h)

    def _ghost_btn(self, parent, text, cmd, fg=None):
        return self._make_btn(parent, text, cmd, C["bg_card"], fg or C["text_sec"],
                              font=("Helvetica", 12), padx=14, pady=6, r=9)

    def check_permissions(self):
        if check_accessibility():
            self.perm_label.config(text="辅助功能权限已授予", fg=C["green"])
            self.perm_btn.pack_forget()
        else:
            self.perm_label.config(text="缺少辅助功能权限 — 按键监听和文字输入将无法工作", fg=C["red"])
            self.perm_btn.config(text="打开系统设置")
            self.perm_btn.pack(side=tk.LEFT, padx=(8, 0))

    def fix_permissions(self):
        open_accessibility_settings()

    # ── UI ──

    def setup_ui(self):
        p = self.panel

        header = tk.Frame(p, bg=C["bg_panel"], height=48)
        header.pack(fill=tk.X, padx=8, pady=(10, 4))
        header.pack_propagate(False)
        tf = tk.Frame(header, bg=C["bg_panel"])
        tf.pack(side=tk.LEFT)
        tk.Label(tf, text="Voice", font=("Helvetica", 22, "bold"),
                 bg=C["bg_panel"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Label(tf, text="Aura", font=("Helvetica", 22, "bold"),
                 bg=C["bg_panel"], fg="#5AACCC").pack(side=tk.LEFT)

        # 状态卡片
        c1 = self._card(p); c1.pack(fill=tk.X, padx=8, pady=8)
        self._section_title(c1, "服务状态")
        sr = tk.Frame(c1, bg=C["bg_card"]); sr.pack(fill=tk.X, padx=16, pady=6)
        tk.Label(sr, text="状态", font=("Helvetica", 12), bg=C["bg_card"], fg=C["text_sec"]).pack(side=tk.LEFT)
        self.status_dot = tk.Label(sr, text="\u25CF", font=("Helvetica", 14), bg=C["bg_card"], fg=C["text_sec"])
        self.status_dot.pack(side=tk.LEFT, padx=(12, 4))
        self.status_label = tk.Label(sr, text="检查中...", font=("Helvetica", 12), bg=C["bg_card"], fg=C["text_sec"])
        self.status_label.pack(side=tk.LEFT)

        br = tk.Frame(c1, bg=C["bg_card"]); br.pack(fill=tk.X, padx=16, pady=(4, 14))
        self.start_btn = self._make_btn(br, "\u25B6  启动", self.on_start, C["green_btn"], C["btn_text"], hover=C["green_btn_hover"])
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.stop_btn = self._make_btn(br, "\u25A0  停止", self.on_stop, C["red_btn"], "#7A5E74", hover=C["red_btn_hover"])
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 8))
        self._ghost_btn(br, "\u21BB  刷新", self.update_status).pack(side=tk.LEFT)

        pr = tk.Frame(c1, bg=C["bg_card"]); pr.pack(fill=tk.X, padx=16, pady=(0, 10))
        self.perm_label = tk.Label(pr, text="", font=("Helvetica", 10), bg=C["bg_card"], fg=C["text_sec"], wraplength=400, justify=tk.LEFT)
        self.perm_label.pack(side=tk.LEFT)
        self.perm_btn = self._ghost_btn(pr, "打开系统设置", self.fix_permissions)
        self.perm_btn.pack(side=tk.LEFT, padx=(8, 0))

        # 设置卡片
        srow = tk.Frame(p, bg=C["bg_panel"]); srow.pack(fill=tk.X, padx=8, pady=8)
        c2 = self._card(srow); c2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        mt = tk.Frame(c2, bg=C["bg_card"]); mt.pack(fill=tk.X, padx=12, pady=(10, 2))
        tk.Label(mt, text="识别模型", font=("Helvetica", 11, "bold"), bg=C["bg_card"], fg=C["text_sec"]).pack(side=tk.LEFT)
        mi = tk.Frame(c2, bg=C["bg_card"]); mi.pack(fill=tk.X, padx=12, pady=(2, 10))
        cur_m = self.config.get("model", "Qwen/Qwen3-ASR-1.7B")
        cur_mn = "Qwen3-ASR-1.7B (精确)"
        for n, v in MODEL_OPTIONS.items():
            if v == cur_m: cur_mn = n; break
        self.model_var = tk.StringVar(value=cur_mn)
        ttk.Combobox(mi, textvariable=self.model_var, values=list(MODEL_OPTIONS.keys()), state="readonly", width=20).pack(side=tk.LEFT, padx=(0, 8))
        self._accent_btn(mi, "保存", self.save_model, text_color=C["btn_text"]).pack(side=tk.LEFT)

        c3 = self._card(srow); c3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))
        kt = tk.Frame(c3, bg=C["bg_card"]); kt.pack(fill=tk.X, padx=12, pady=(10, 2))
        tk.Label(kt, text="触发按键", font=("Helvetica", 11, "bold"), bg=C["bg_card"], fg=C["text_sec"]).pack(side=tk.LEFT)
        ki = tk.Frame(c3, bg=C["bg_card"]); ki.pack(fill=tk.X, padx=12, pady=(2, 10))
        cur_k = self.config.get("trigger_key", "cmd_r")
        cur_kn = "右 Command"
        for n, v in KEY_OPTIONS.items():
            if v == cur_k: cur_kn = n; break
        self.key_var = tk.StringVar(value=cur_kn)
        ttk.Combobox(ki, textvariable=self.key_var, values=list(KEY_OPTIONS.keys()), state="readonly", width=12).pack(side=tk.LEFT, padx=(0, 8))
        self._accent_btn(ki, "保存", self.save_key, text_color=C["btn_text"]).pack(side=tk.LEFT)

        # 替换规则
        c4 = self._card(p); c4.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self._section_title(c4, "替换规则")
        tk.Label(c4, text="语音识别的误识别词汇会自动替换为正确文本", font=("Helvetica", 10), bg=C["bg_card"], fg=C["text_hint"]).pack(anchor=tk.W, padx=16, pady=(0, 4))
        lf = tk.Frame(c4, bg=C["bg_card"]); lf.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)
        sb = tk.Scrollbar(lf, bd=0); sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.rules_listbox = tk.Listbox(lf, font=("Helvetica", 12), bd=0, bg=C["white"], fg=C["text"], selectbackground=C["list_sel"], selectforeground=C["text"], highlightthickness=0, yscrollcommand=sb.set, activestyle="none")
        self.rules_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self.rules_listbox.yview)
        self.refresh_rules()

        af = tk.Frame(c4, bg=C["bg_card"]); af.pack(fill=tk.X, padx=16, pady=(8, 4))
        tk.Label(af, text="错误", font=("Helvetica", 11), bg=C["bg_card"], fg=C["text_sec"]).pack(side=tk.LEFT)
        self.wrong_entry = tk.Entry(af, font=("Helvetica", 12), width=12, bg=C["white"], fg=C["text"], bd=0, highlightthickness=1, highlightbackground=C["input_border"], highlightcolor=C["input_focus"], insertbackground=C["text"])
        self.wrong_entry.pack(side=tk.LEFT, padx=(4, 8))
        tk.Label(af, text="\u2192", font=("Helvetica", 14), bg=C["bg_card"], fg=C["text_hint"]).pack(side=tk.LEFT)
        tk.Label(af, text="正确", font=("Helvetica", 11), bg=C["bg_card"], fg=C["text_sec"]).pack(side=tk.LEFT, padx=(8, 0))
        self.correct_entry = tk.Entry(af, font=("Helvetica", 12), width=12, bg=C["white"], fg=C["text"], bd=0, highlightthickness=1, highlightbackground=C["input_border"], highlightcolor=C["input_focus"], insertbackground=C["text"])
        self.correct_entry.pack(side=tk.LEFT, padx=(4, 8))
        self._accent_btn(af, "+ 添加", self.add_rule).pack(side=tk.LEFT)

        bf = tk.Frame(c4, bg=C["bg_card"]); bf.pack(fill=tk.X, padx=16, pady=(4, 12))
        self._ghost_btn(bf, "删除选中", self.delete_rule).pack(side=tk.LEFT)
        self._ghost_btn(bf, "清空全部", self.clear_rules).pack(side=tk.LEFT, padx=8)

    # ── 状态轮询 ──

    def _start_polling(self):
        self.update_status()
        self.check_permissions()
        self._poll_id = self.root.after(3000, self._start_polling)

    def update_status(self):
        if self.service.is_running and self.service.model is not None:
            self.status_label.config(text="运行中", fg=C["green"])
            self.status_dot.config(fg=C["green"])
        elif self.service.is_running:
            self.status_label.config(text="加载模型中...", fg="#B89828")
            self.status_dot.config(fg="#B89828")
        else:
            self.status_label.config(text="已停止", fg=C["red"])
            self.status_dot.config(fg=C["red"])

    def _on_service_error(self, message):
        self.root.after(0, lambda: messagebox.showerror("服务错误", message))

    # ── 事件处理 ──

    def on_start(self):
        if not check_accessibility():
            messagebox.showwarning("权限缺失",
                "Voice Aura 需要辅助功能权限才能监听按键和输入文字。\n\n"
                "请在系统设置中添加：\n"
                "系统设置 → 隐私与安全性 → 辅助功能")
            open_accessibility_settings()
            return
        self.service.start()
        self.root.after(2000, self.update_status)
        self.root.after(10000, self.update_status)

    def on_stop(self):
        self.service.stop()
        self.update_status()

    def save_key(self):
        kn = self.key_var.get()
        self.config["trigger_key"] = KEY_OPTIONS.get(kn, "cmd_r")
        save_config(self.config)
        if self.service.is_running:
            if messagebox.askyesno("保存成功", f"触发按键: {kn}\n是否立即重启服务以生效？"):
                self.service.stop()
                self.service.start()
                self.root.after(3000, self.update_status)
        else:
            messagebox.showinfo("保存成功", f"触发按键: {kn}")

    def save_model(self):
        mn = self.model_var.get()
        self.config["model"] = MODEL_OPTIONS.get(mn, "Qwen/Qwen3-ASR-1.7B")
        save_config(self.config)
        if self.service.is_running:
            if messagebox.askyesno("保存成功", f"模型: {mn}\n是否立即重启服务以生效？"):
                self.service.stop()
                self.service.start()
                self.root.after(10000, self.update_status)
        else:
            messagebox.showinfo("保存成功", f"模型: {mn}")

    def refresh_rules(self):
        self.rules_listbox.delete(0, tk.END)
        for w, c in self.config.get("replacements", {}).items():
            self.rules_listbox.insert(tk.END, f"  {w}  \u2192  {c}")

    def _prompt_restart(self):
        if self.service.is_running:
            if messagebox.askyesno("规则已保存",
                "替换规则已更新。\n运行中的服务需要重启才能生效。\n\n是否立即重启服务？"):
                self.service.stop()
                self.service.start()
                self.root.after(3000, self.update_status)
                self.root.after(10000, self.update_status)

    def add_rule(self):
        w = self.wrong_entry.get().strip()
        c = self.correct_entry.get().strip()
        if not w or not c:
            messagebox.showwarning("提示", "请填写错误和正确文本")
            return
        self.config.setdefault("replacements", {})[w] = c
        save_config(self.config)
        self.refresh_rules()
        self.wrong_entry.delete(0, tk.END)
        self.correct_entry.delete(0, tk.END)
        self._prompt_restart()

    def delete_rule(self):
        sel = self.rules_listbox.curselection()
        if not sel:
            return
        text = self.rules_listbox.get(sel[0]).strip()
        wrong = text.split("\u2192")[0].strip()
        self.config.get("replacements", {}).pop(wrong, None)
        save_config(self.config)
        self.refresh_rules()
        self._prompt_restart()

    def clear_rules(self):
        if messagebox.askyesno("确认", "清空全部替换规则？"):
            self.config["replacements"] = {}
            save_config(self.config)
            self.refresh_rules()
            self._prompt_restart()


def _adj(hex_color, delta):
    """调亮/调暗颜色"""
    h = hex_color.lstrip("#")
    rgb = [max(0, min(255, int(h[i:i+2], 16) + delta)) for i in (0, 2, 4)]
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def main():
    root = tk.Tk()
    VoiceInputManager(root)
    root.mainloop()
