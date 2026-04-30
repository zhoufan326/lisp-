import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from dwg_saver import select_save_directory
from lisp_executor import execute_lisp

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(PROJECT_DIR, "LSP", "LISP图样.dwt")
LSP_DIR = os.path.join(PROJECT_DIR, "LSP")


TOOL_TYPES = [
    ("1", "抛光模基模修盘"),
    ("2", "抛光模修盘基模"),
    ("3", "球面低抛细磨盘"),
    ("4", "球面低抛粘盘"),
    ("5", "球面低抛抛盘")
]


def _load_params(inputs, param_file):
    try:
        if os.path.exists(param_file):
            with open(param_file, 'r', encoding='utf-8') as f:
                params = json.load(f)
            for key, value in params.items():
                if key in inputs:
                    var = inputs[key]
                    if isinstance(var, (tk.StringVar, tk.IntVar, tk.BooleanVar)):
                        var.set(value)
    except Exception as e:
        print(f"加载参数失败: {e}")


def _save_params(inputs, param_file):
    try:
        params = {key: var.get() for key, var in inputs.items()}
        with open(param_file, 'w', encoding='utf-8') as f:
            json.dump(params, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存参数失败: {e}")


def _build_args(func, params):
    def q(v):
        return f'"{v}"'
    r0 = str(abs(float(params.get("r0", 0))))
    a0 = str(float(params.get("a0", 0)))
    t0 = str(float(params.get("t0", 0)))
    tool_type = q(params.get("tool_type", "1"))
    save_path = q(params.get("save_path", ""))
    return [r0, a0, t0, tool_type, save_path]


class XZT_小锥度凸_UI:
    def __init__(self, parent, on_execute, font_size=12):
        self.parent = parent
        self.font_size = font_size
        self.inputs = {}
        config_dir = os.path.join(os.path.expanduser("~"), ".autolisp_mgr")
        os.makedirs(config_dir, exist_ok=True)
        self.param_file = os.path.join(config_dir, "XZT_小锥度凸_params.json")

    def create_ui(self, frame):
        f_large = ("Segoe UI", self.font_size, "bold")
        f_norm = ("Segoe UI", self.font_size)

        ttk.Label(frame, text="小锥度凸模参数输入", font=f_large).pack(pady=(0, 20))

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
        ttk.Label(t0_frame, text="总厚度(t0):", width=15, font=f_norm).pack(side=tk.LEFT)
        t0_var = tk.StringVar()
        ttk.Entry(t0_frame, textvariable=t0_var, font=f_norm).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.inputs["t0"] = t0_var

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=20)
        ttk.Button(btn_frame, text="执行", command=self._on_run, style="Accent.TButton").pack(side=tk.RIGHT, padx=15)

        _load_params(self.inputs, self.param_file)

    def _on_run(self):
        try:
            values = {key: var.get() for key, var in self.inputs.items()}
            if not all([values["r0"], values["a0"], values["t0"]]):
                messagebox.showwarning("警告", "请填写所有必填参数！")
                return

            save_path = select_save_directory()
            if not save_path:
                return

            _save_params(self.inputs, self.param_file)
            values["save_path"] = save_path

            execute_lisp(None, "小锥度凸模", "XZT_小锥度凸.lsp", "xzt", values, _build_args, TEMPLATE_PATH, LSP_DIR)
        except Exception as e:
            messagebox.showerror("错误", str(e))
