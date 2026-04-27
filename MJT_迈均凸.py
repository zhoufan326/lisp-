import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Callable
import json
import os

class MJT_迈均凸_UI:
    def __init__(self, parent, on_execute: Callable, font_size: int = 12):
        self.parent = parent
        self.on_execute = on_execute
        self.font_size = font_size
        self.large_font_size = int(font_size * 1)
        self.inputs = {}
        self.config_dir = os.path.join(os.path.expanduser("~"), ".autolisp_mgr")
        os.makedirs(self.config_dir, exist_ok=True)
        self.param_file = os.path.join(self.config_dir, "MJT_迈均凸_params.json")
        
    def load_params(self):
        try:
            if os.path.exists(self.param_file):
                with open(self.param_file, 'r', encoding='utf-8') as f:
                    params = json.load(f)
                for key, value in params.items():
                    if key in self.inputs:
                        var = self.inputs[key]
                        if isinstance(var, (tk.StringVar, tk.IntVar, tk.BooleanVar)):
                            var.set(value)
        except Exception as e:
            print(f"加载参数失败: {e}")
            
    def save_params(self):
        try:
            params = {}
            for key, var in self.inputs.items():
                params[key] = var.get()
            with open(self.param_file, 'w', encoding='utf-8') as f:
                json.dump(params, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存参数失败: {e}")
        
    def create_ui(self, frame):
        f_large = ("Segoe UI", self.font_size, "bold")
        f_norm = ("Segoe UI", self.font_size)
        
        ttk.Label(frame, text="迈均凸模参数输入", font=f_large).pack(pady=(0, 20))
        
        param_frame = ttk.Frame(frame)
        param_frame.pack(fill=tk.X, pady=10)
        
        r0_frame = ttk.Frame(param_frame)
        r0_frame.pack(fill=tk.X, pady=10)
        ttk.Label(r0_frame, text="曲率半径(r0):", width=15, font=f_norm).pack(side=tk.LEFT)
        r0_var = tk.StringVar()
        ttk.Entry(r0_frame, textvariable=r0_var, font=f_norm).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.inputs["r0"] = r0_var
        
        a0_frame = ttk.Frame(param_frame)
        a0_frame.pack(fill=tk.X, pady=10)
        ttk.Label(a0_frame, text="口径(直径)(a0):", width=15, font=f_norm).pack(side=tk.LEFT)
        a0_var = tk.StringVar()
        ttk.Entry(a0_frame, textvariable=a0_var, font=f_norm).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.inputs["a0"] = a0_var
        
        t0_frame = ttk.Frame(param_frame)
        t0_frame.pack(fill=tk.X, pady=10)
        ttk.Label(t0_frame, text="边厚(t0):", width=15, font=f_norm).pack(side=tk.LEFT)
        t0_var = tk.StringVar()
        ttk.Entry(t0_frame, textvariable=t0_var, font=f_norm).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.inputs["t0"] = t0_var
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=20)
        ttk.Button(btn_frame, text="执行", command=self._on_run, style="Accent.TButton").pack(side=tk.RIGHT, padx=15)
        
        # 加载参数
        self.load_params()
        
    def _on_run(self):
        try:
            values = {}
            for key, var in self.inputs.items():
                values[key] = var.get()
            
            if not all([values["r0"], values["a0"], values["t0"]]):
                messagebox.showwarning("警告", "请填写所有参数！")
                return
            
            self.save_params()
            
            # 调用核心绘图函数 mjt
            self.on_execute("mjt", values)
        except Exception as e:
            messagebox.showerror("错误", str(e))