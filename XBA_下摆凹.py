import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Callable
import json
import os

TOOL_TYPES = [
    ("1", "抛光模基模"),
    ("2", "精磨模基模")
]
TECH_OPTIONS = [("1", "使用默认技术要求"), ("2", "自定义技术要求")]

class XBA_下摆凹_UI:
    def __init__(self, parent, on_execute: Callable, font_size: int = 12):
        self.parent = parent
        self.on_execute = on_execute
        self.font_size = font_size
        self.large_font_size = int(font_size * 1)
        self.inputs = {}
        self.config_dir = os.path.join(os.path.expanduser("~"), ".autolisp_mgr")
        os.makedirs(self.config_dir, exist_ok=True)
        self.param_file = os.path.join(self.config_dir, "XBA_下摆凹_params.json")
        
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
        f_option = ("Segoe UI", self.large_font_size)
        
        style = ttk.Style()
        style.configure("Large.TRadiobutton", font=f_option)
        
        ttk.Label(frame, text="下摆凹模参数输入", font=f_large).pack(pady=(0, 20))
        
        tool_frame = ttk.Frame(frame)
        tool_frame.pack(fill=tk.X, pady=10)
        ttk.Label(tool_frame, text="工装类型:", width=15, font=f_norm).pack(side=tk.LEFT)
        tool_var = tk.StringVar(value="1")
        self.inputs["tool_type"] = tool_var
        for val, text in TOOL_TYPES:
            ttk.Radiobutton(tool_frame, text=text, variable=tool_var, value=val).pack(side=tk.LEFT, padx=10)
        
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
        ttk.Label(t0_frame, text="平台宽度(t0):", width=15, font=f_norm).pack(side=tk.LEFT)
        t0_var = tk.StringVar()
        ttk.Entry(t0_frame, textvariable=t0_var, font=f_norm).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.inputs["t0"] = t0_var
        
        b0_frame = ttk.Frame(param_frame)
        b0_frame.pack(fill=tk.X, pady=10)
        ttk.Label(b0_frame, text="柄长(b0):", width=15, font=f_norm).pack(side=tk.LEFT)
        b0_var = tk.StringVar()
        ttk.Entry(b0_frame, textvariable=b0_var, font=f_norm).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.inputs["b0"] = b0_var
        
        tech_frame = ttk.Frame(param_frame)
        tech_frame.pack(fill=tk.X, pady=10)
        ttk.Label(tech_frame, text="技术要求:", width=15, font=f_norm).pack(side=tk.LEFT)
        tech_var = tk.StringVar(value="1")
        self.inputs["tech_choice"] = tech_var
        for val, text in TECH_OPTIONS:
            ttk.Radiobutton(tech_frame, text=text, variable=tech_var, value=val, style="Large.TRadiobutton").pack(side=tk.LEFT, padx=10)
        
        custom_tech_frame = ttk.Frame(param_frame)
        custom_tech_frame.pack(fill=tk.X, pady=10)
        ttk.Label(custom_tech_frame, text="自定义技术要求内容:", width=15, font=f_norm).pack(side=tk.LEFT)
        custom_tech_var = tk.StringVar()
        self.inputs["custom_tech_text"] = custom_tech_var
        ttk.Entry(custom_tech_frame, textvariable=custom_tech_var, font=f_norm).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
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
            
            if not all([values["r0"], values["a0"], values["t0"], values["b0"], values["tool_type"]]):
                messagebox.showwarning("警告", "请填写所有参数并选择工装类型！")
                return
            
            self.save_params()
            
            # 直接调用核心绘图函数 xba 而不是命令 c:xba，因为需要传递参数
            self.on_execute("xba", values)
        except Exception as e:
            messagebox.showerror("错误", str(e))
