#!/usr/bin/env python3
"""
热词管理器 - 图形界面
双击运行即可管理热词
"""

import tkinter as tk
from tkinter import messagebox
import os

HOTWORDS_FILE = os.path.expanduser("~/hotwords.txt")

def load_hotwords():
    """加载热词"""
    if os.path.exists(HOTWORDS_FILE):
        with open(HOTWORDS_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    return []

def save_hotwords(words):
    """保存热词"""
    with open(HOTWORDS_FILE, "w", encoding="utf-8") as f:
        for word in words:
            f.write(word + "\n")

def main():
    root = tk.Tk()
    root.title("热词管理器")
    root.geometry("400x500")
    root.resizable(True, True)

    # 标题
    title = tk.Label(root, text="🔥 热词管理器", font=("Arial", 18, "bold"))
    title.pack(pady=10)

    # 说明
    desc = tk.Label(root, text="热词会让语音识别更准确\n每行一个词，保存后自动生效", font=("Arial", 11), fg="gray")
    desc.pack(pady=5)

    # 热词列表框
    frame = tk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    listbox = tk.Listbox(frame, font=("Arial", 14), yscrollcommand=scrollbar.set)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=listbox.yview)

    # 加载现有热词
    words = load_hotwords()
    for word in words:
        listbox.insert(tk.END, word)

    # 输入框
    input_frame = tk.Frame(root)
    input_frame.pack(fill=tk.X, padx=20, pady=5)

    entry = tk.Entry(input_frame, font=("Arial", 14))
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

    def add_word():
        word = entry.get().strip()
        if word:
            listbox.insert(tk.END, word)
            entry.delete(0, tk.END)
            save_hotwords(listbox.get(0, tk.END))

    add_btn = tk.Button(input_frame, text="添加", font=("Arial", 12), command=add_word)
    add_btn.pack(side=tk.RIGHT)

    # 回车添加
    entry.bind("<Return>", lambda e: add_word())

    # 按钮区
    btn_frame = tk.Frame(root)
    btn_frame.pack(fill=tk.X, padx=20, pady=10)

    def delete_selected():
        selection = listbox.curselection()
        if selection:
            listbox.delete(selection[0])
            save_hotwords(listbox.get(0, tk.END))

    def clear_all():
        if messagebox.askyesno("确认", "确定要清空所有热词吗？"):
            listbox.delete(0, tk.END)
            save_hotwords([])

    def save_and_close():
        save_hotwords(listbox.get(0, tk.END))
        root.quit()

    del_btn = tk.Button(btn_frame, text="删除选中", font=("Arial", 11), command=delete_selected)
    del_btn.pack(side=tk.LEFT, padx=5)

    clear_btn = tk.Button(btn_frame, text="清空全部", font=("Arial", 11), command=clear_all)
    clear_btn.pack(side=tk.LEFT, padx=5)

    save_btn = tk.Button(btn_frame, text="保存并关闭", font=("Arial", 11), bg="#4CAF50", fg="white", command=save_and_close)
    save_btn.pack(side=tk.RIGHT, padx=5)

    # 关闭时保存
    def on_close():
        save_hotwords(listbox.get(0, tk.END))
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    root.mainloop()

if __name__ == "__main__":
    main()
