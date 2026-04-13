#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoCAD Controller & GUI Manager (v2.7)
Robust connection logic that ensures a NEW blank drawing is created from template.
Prevents <unknown>.Add errors by checking AutoCAD's quiescent state.
"""

import os
import re
import time
import json
import glob
import functools
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

# 导入各个LISP文件对应的UI模块
try:
    from DWA_短尾凹 import DWA_短尾凹_UI
    HAS_DWA = True
except ImportError:
    HAS_DWA = False

try:
    from DWT_短尾凸 import DWT_短尾凸_UI
    HAS_DWT = True
except ImportError:
    HAS_DWT = False

try:
    from JZM_短尾M24_基准模 import JZM_短尾M24_基准模_UI
    HAS_JZM1 = True
except ImportError:
    HAS_JZM1 = False

try:
    from JZM_锥度_基准模 import JZM_锥度_基准模_UI
    HAS_JZM2 = True
except ImportError:
    HAS_JZM2 = False

try:
    from XBA_下摆凹 import XBA_下摆凹_UI
    HAS_XBA = True
except ImportError:
    HAS_XBA = False

try:
    from XZA_小锥度凹 import XZA_小锥度凹_UI
    HAS_XZA = True
except ImportError:
    HAS_XZA = False

try:
    from XZT_小锥度凸 import XZT_小锥度凸_UI
    HAS_XZT = True
except ImportError:
    HAS_XZT = False

# Try to import win32com for AutoCAD integration
try:
    import win32com.client
    HAS_PYWIN32 = True
except ImportError:
    HAS_PYWIN32 = False

# Import decorators from retry_decorator
try:
    from retry_decorator import retry_on_autocad_error, retry_with_backoff
except ImportError:
    def retry_on_autocad_error(*args, **kwargs):
        def decorator(f): return f
        return decorator

# Import print manager
try:
    from acad_plot_manager import configure_print_settings, plot_paper_space
    HAS_PRINT_MANAGER = True
except ImportError:
    HAS_PRINT_MANAGER = False

# --- AutoCAD Core Logic (Optimized for New Drawing Creation) ---

def is_autocad_ready(acad, max_wait=5):
    """
    检查AutoCAD是否处于空闲状态（无正在运行的命令）
    会持续等待直到CAD空闲或超时
    
    参数:
        acad: AutoCAD应用对象
        max_wait: 最大等待时间（秒），默认5秒
    返回:
        bool: 如果CAD空闲返回True，超时返回False
    """
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            # 首先检查CAD是否可用
            if not acad or not acad.ActiveDocument:
                time.sleep(0.2)
                continue
                
            # 检查命令名
            try:
                cmd_names = acad.GetVariable("CMDNAMES")
                if cmd_names == "" or cmd_names is None:
                    return True
            except:
                # GetVariable失败，尝试其他方法
                try:
                    # 检查ActiveDocument是否可用
                    doc = acad.ActiveDocument
                    if doc:
                        # 尝试获取模型空间
                        _ = doc.ModelSpace
                except:
                    time.sleep(0.2)
                    continue
            
            # 如果有命令在运行，等待一小段时间再检查
            time.sleep(0.2)
        except Exception as e:
            # 其他异常，等待后重试
            time.sleep(0.3)
    return False

def wait_for_autocad_ready(acad, max_wait=10):
    """
    等待AutoCAD变为空闲状态，带超时
    
    参数:
        acad: AutoCAD应用对象
        max_wait: 最大等待时间（秒），默认10秒
    返回:
        bool: 如果成功等待到空闲返回True，超时返回False
    """
    if is_autocad_ready(acad, max_wait):
        return True
    else:
        return False

def force_cancel_commands(acad, max_attempts=3):
    """
    尝试取消正在运行的AutoCAD命令
    改进版：避免在CAD极度繁忙时发送ESC导致错误
    
    参数:
        acad: AutoCAD应用对象
        max_attempts: 最大尝试次数，默认3次
    返回:
        bool: 如果CAD变为空闲返回True，否则返回False
    """
    for attempt in range(1, max_attempts + 1):
        try:
            # 首先检查是否已经空闲
            if is_autocad_ready(acad, max_wait=0.5):
                return True
            
            # 尝试将 AutoCAD 窗口置顶
            acad.Visible = True
            time.sleep(0.1)
            
            doc = acad.ActiveDocument
            if doc:
                try:
                    doc.Activate()
                    time.sleep(0.1)
                    
                    # 谨慎发送取消指令
                    try:
                        # 先尝试发送一个空行
                        doc.SendCommand("\n")
                        time.sleep(0.2)
                        
                        # 再发送ESC
                        doc.SendCommand("\x03")
                    except:
                        # 如果SendCommand失败，等待更长时间
                        pass
                    
                    # 等待更长时间让CAD处理
                    time.sleep(1 + attempt * 0.5)
                    
                    # 检查是否成功
                    if is_autocad_ready(acad, max_wait=1):
                        return True
                        
                except:
                    pass
            
            if attempt < max_attempts:
                time.sleep(1 + attempt)  # 递增等待时间
                
        except:
            if attempt < max_attempts:
                time.sleep(2)
                
    # 最后再尝试检查一次
    return is_autocad_ready(acad, max_wait=0.5)

@retry_on_autocad_error(max_attempts=5, initial_delay=2) 
def find_autocad(): 
    """查找或启动AutoCAD应用程序""" 
    if not HAS_PYWIN32:
        raise RuntimeError("pywin32 未安装。请运行 'pip install pywin32'。")
    
    acad = None
    try: 
        acad = win32com.client.GetActiveObject("AutoCAD.Application") 
        print("已连接到运行中的AutoCAD") 
    except: 
        try: 
            acad = win32com.client.Dispatch("AutoCAD.Application") 
            acad.Visible = True
            print("已启动新AutoCAD实例") 
        except Exception as e: 
            raise RuntimeError(f"无法启动AutoCAD: {e}")
            
    time.sleep(3) 
    return acad

@retry_on_autocad_error(max_attempts=3, initial_delay=2) 
def create_new_doc_from_template(acad, template_path):
    """显式创建基于样板的新文档"""
    if not os.path.exists(template_path):
        return None
        
    try:
        abs_path = os.path.abspath(template_path)
        acad.Visible = True
        
        # 在执行 Add 之前，尝试确保 CAD 是"安静"的
        # 如果 CAD 弹出了对话框（如"找不到字体"），Add 可能会失败
        if not is_autocad_ready(acad):
            force_cancel_commands(acad)
            
        # Documents.Add 始终会创建一个全新的空白图形文件
        doc = acad.Documents.Add(abs_path)
        return doc
    except Exception as e:
        return None

def apply_template_with_fallback(acad, primary_template, backup_template): 
    """应用样板逻辑：始终尝试新建文档""" 
    if not acad: return None
    
    # 1. 尝试主样板新建
    doc = create_new_doc_from_template(acad, primary_template)
    if doc:
        return doc
        
    # 2. 尝试备用样板新建
    doc = create_new_doc_from_template(acad, backup_template)
    if doc:
        return doc
    
    return None 

@retry_on_autocad_error(max_attempts=3, initial_delay=1) 
def load_single_lisp_file(doc, lisp_file, functions=None): 
    """加载单个LISP文件 (使用 autoload 模式)""" 
    if not doc: return False
    lisp_path = os.path.abspath(lisp_file).replace("\\", "/") 
    file_name = os.path.basename(lisp_file)
    
    # 获取该文件中的所有 c: 命令名
    if not functions:
        load_command = f'(progn (vl-load-com) (load "{lisp_path}") (princ (strcat "\\n>> " "{file_name}" " 已加载。")) (princ))'
    else:
        # 改进：由于 AutoCAD 内置的 (autoload) 不支持带参数的 c: 函数（它定义的桩函数是 0 参数的），
        # 我们这里通过手动定义带参数的桩函数来实现支持参数的“懒加载” (Lazy Load)。
        stubs = []
        for func in functions:
            if func.name.lower().startswith("c:"):
                # 获取参数列表，如 "r0 a0 t0"
                params_str = " ".join(func.params)
                # 定义桩函数：调用时先加载文件，然后使用 apply 转发调用
                # 注意：文件加载后，真实的函数会覆盖这个桩函数
                stub = f'(defun {func.name} ({params_str}) (load "{lisp_path}") (apply \'{func.name} (list {params_str})))'
                stubs.append(stub)
        
        if not stubs:
            load_command = f'(progn (vl-load-com) (load "{lisp_path}") (princ (strcat "\\n>> " "{file_name}" " 已加载。")) (princ))'
        else:
            stubs_code = " ".join(stubs)
            load_command = f'(progn (vl-load-com) {stubs_code} (princ (strcat "\\n>> " "{file_name}" " 已通过参数化桩函数注册。")) (princ))'
    
    try:
        doc.Activate()
        doc.SendCommand(load_command + "\n") 
        return True
    except Exception as e:
        raise e

@retry_on_autocad_error(max_attempts=5, initial_delay=2) 
def run_lisp_function(acad, function_name, args_list=None, is_parameterized=True): 
    """
    在当前活动文档运行函数
    支持直接传参 (c:FUNC arg1...) 和 模拟输入两种模式
    
    参数:
        acad: AutoCAD应用对象
        function_name: 要执行的函数名
        args_list: 参数列表
        is_parameterized: 是否使用带参调用模式。若为 False，则发送 (c:FUNC) 后模拟输入。
    返回:
        bool: 成功返回True
    """
    doc = acad.ActiveDocument 
    if not doc: 
        raise RuntimeError("找不到活动文档")
    
    # 第一步：确保AutoCAD处于空闲状态
    if not wait_for_autocad_ready(acad, max_wait=5):
        force_cancel_commands(acad, max_attempts=2)
        wait_for_autocad_ready(acad, max_wait=3)
    
    # 第二步：激活文档并发送命令
    try:
        doc.Activate()
        time.sleep(0.3)
        
        if is_parameterized:
            # 带参调用模式：(c:JZM1 90 70 8 "1:1" 1 "" 0)
            args_str = " " + " ".join(args_list) if args_list else ""
            command = f"({function_name}{args_str})"
            doc.SendCommand("\n")
            time.sleep(0.2)
            doc.SendCommand(command + "\n")
        else:
            # 模拟输入模式：发送 (c:FUNC) 然后逐个输入参数
            doc.SendCommand("\n")
            time.sleep(0.2)
            doc.SendCommand(f"({function_name})\n")
            
            if args_list:
                for arg in args_list:
                    # 模拟用户逐个回车输入参数
                    time.sleep(0.5)
                    # 去除引号（模拟输入不需要引号，除非是字符串输入）
                    clean_arg = arg.strip('"')
                    doc.SendCommand(clean_arg + "\n")
        
        time.sleep(1.0)
        return True
        
    except Exception as e:
        raise 

# --- Data Models ---

@dataclass
class LispFunction:
    name: str
    params: List[str]
    docstring: str = ""

@dataclass
class LispFile:
    path: str
    name: str
    functions: List[LispFunction] = None

class LispParser:
    DEFUN_PATTERN = re.compile(
        r'\(defun\s+([^\s\(\)]+)\s*\(([^\(\)]*)\)\s*(?:"([^"]*)"\s*)?', 
        re.IGNORECASE | re.DOTALL
    )

    @staticmethod
    def parse_file(file_path: str) -> List[LispFunction]:
        functions = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            for match in LispParser.DEFUN_PATTERN.finditer(content):
                name = match.group(1)
                if not name.lower().startswith("c:"): continue
                params_raw = match.group(2).split('/')
                params_only = params_raw[0].strip().split()
                params = [p.strip() for p in params_only if p.strip()]
                docstring = match.group(3) or ""
                functions.append(LispFunction(name, params, docstring.strip()))
        except Exception as e:
            print(f"解析错误 {file_path}: {e}")
        return functions

# --- GUI Components ---

class ExecutionDialog(tk.Toplevel):
    def __init__(self, parent, lisp_func: LispFunction, on_execute: Callable, font_size: int):
        super().__init__(parent)
        self.title(f"参数输入: {lisp_func.name}")
        self.lisp_func = lisp_func
        self.on_execute = on_execute
        self.font_size = font_size
        self.inputs = {}
        # 增加参数记忆功能
        self.config_dir = os.path.join(os.path.expanduser("~"), ".autolisp_mgr")
        os.makedirs(self.config_dir, exist_ok=True)
        self.param_file = os.path.join(self.config_dir, f"generic_{lisp_func.name}_params.json")
        
        self._setup_ui()
        self.load_params() # UI 设置好后再加载
        
        self.transient(parent)
        self.grab_set()

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
            params = {k: v.get() for k, v in self.inputs.items()}
            with open(self.param_file, 'w', encoding='utf-8') as f:
                json.dump(params, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存参数失败: {e}")

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)
        f_large = ("Segoe UI", self.font_size, "bold")
        f_norm = ("Segoe UI", self.font_size)

        ttk.Label(main_frame, text=f"命令: {self.lisp_func.name}", font=f_large).pack(pady=(0, 20))

        if not self.lisp_func.params:
            ttk.Label(main_frame, text="此命令无需参数。", font=f_norm).pack(pady=20)
        else:
            for param in self.lisp_func.params:
                frame = ttk.Frame(main_frame)
                frame.pack(fill=tk.X, pady=15)
                ttk.Label(frame, text=f"{param}:", width=12, font=f_norm).pack(side=tk.LEFT)
                if 'flag' in param.lower() or 'is-' in param.lower():
                    var = tk.BooleanVar()
                    ttk.Checkbutton(frame, variable=var).pack(side=tk.LEFT)
                    self.inputs[param] = var
                else:
                    var = tk.StringVar()
                    ttk.Entry(frame, textvariable=var, font=f_norm).pack(side=tk.LEFT, fill=tk.X, expand=True)
                    self.inputs[param] = var

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=30)
        ttk.Button(btn_frame, text="执行", command=self._on_run).pack(side=tk.RIGHT, padx=15)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT)

    def _on_run(self):
        self.save_params() # 保存参数
        values = {k: v.get() for k, v in self.inputs.items()}
        self.on_execute(self.lisp_func, values)
        self.destroy()

class AppView(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AutoCAD LISP 智能管理面板 (v2.7)")
        self.geometry("1800x1100")
        self.font_size_base = 30
        self._configure_styles()
        self._setup_ui()

    def _configure_styles(self):
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except: pass
        self.style = ttk.Style()
        self.style.theme_use('clam')
        fs = self.font_size_base
        self.style.configure("Treeview", font=("Segoe UI", fs), rowheight=int(fs * 2.2))
        self.style.configure("Treeview.Heading", font=("Segoe UI", fs, "bold"))
        self.style.configure("TFrame", background="#f5f5f7")
        self.style.configure("TLabel", background="#f5f5f7", font=("Segoe UI", fs))
        self.style.configure("TButton", font=("Segoe UI", fs))
        self.style.configure("Accent.TButton", background="#0078d4", foreground="white", font=("Segoe UI", fs, "bold"))
        self.style.configure("Save.TButton", background="#28a745", foreground="white", font=("Segoe UI", fs, "bold"))
        self.style.configure("Init.TButton", background="#ff9800", foreground="white", font=("Segoe UI", fs, "bold"))

    def _setup_ui(self):
        fs = self.font_size_base
        self.toolbar = ttk.Frame(self, padding=15)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        self.btn_load_dir = ttk.Button(self.toolbar, text="📂 加载目录")
        self.btn_load_dir.pack(side=tk.LEFT, padx=15)
        self.btn_connect_cad = ttk.Button(self.toolbar, text="🔌 连接 CAD")
        self.btn_connect_cad.pack(side=tk.LEFT, padx=15)
        self.btn_init_cad = ttk.Button(self.toolbar, text="🚀 初始化 CAD (新建图形)", style="Init.TButton")
        self.btn_init_cad.pack(side=tk.LEFT, padx=15)
        self.btn_print = ttk.Button(self.toolbar, text="🖨️ 打印")
        self.btn_print.pack(side=tk.LEFT, padx=15)
        self.btn_refresh = ttk.Button(self.toolbar, text="🔄 刷新")
        self.btn_refresh.pack(side=tk.LEFT, padx=15)
        
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=30, pady=15)
        self.nav_frame = ttk.Frame(self.paned)
        self.tree = ttk.Treeview(self.nav_frame, show="tree", selectmode="browse")
        self.tree.column("#0", width=600, minwidth=400)  # 设置列宽：600像素，最小400像素
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.paned.add(self.nav_frame, weight=1)
        
        self.details_frame = ttk.Frame(self.paned, padding=40)
        self.paned.add(self.details_frame, weight=6)
        self.lbl_file_name = ttk.Label(self.details_frame, text="请选择 LISP 文件", font=("Segoe UI", fs + 12, "bold"))
        self.lbl_file_name.pack(anchor=tk.W)
        ttk.Label(self.details_frame, text="文档说明:", font=("Segoe UI", fs, "bold")).pack(anchor=tk.W, pady=(20, 10))
        self.txt_docs = tk.Text(self.details_frame, wrap=tk.WORD, font=("Segoe UI", fs), height=5, relief=tk.SOLID, bd=1)
        self.txt_docs.pack(fill=tk.X, pady=(0, 10))
        self.btn_save_docs = ttk.Button(self.details_frame, text="💾 保存文档", style="Save.TButton")
        self.btn_save_docs.pack(anchor=tk.E, pady=(0, 20))
        ttk.Label(self.details_frame, text="可用命令 (c:):", font=("Segoe UI", fs, "bold")).pack(anchor=tk.W, pady=(20, 10))
        self.func_canvas = tk.Canvas(self.details_frame, bg="#f5f5f7", highlightthickness=0)
        self.func_scrollbar = ttk.Scrollbar(self.details_frame, orient="vertical", command=self.func_canvas.yview)
        self.func_scroll_frame = ttk.Frame(self.func_canvas)
        self.func_scroll_frame.bind("<Configure>", lambda e: self.func_canvas.configure(scrollregion=self.func_canvas.bbox("all")))
        self.func_canvas.create_window((0, 0), window=self.func_scroll_frame, anchor="nw")
        self.func_canvas.configure(yscrollcommand=self.func_scrollbar.set)
        self.func_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.func_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_bar = ttk.Frame(self, relief=tk.SUNKEN, padding=8)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_lbl = ttk.Label(self.status_bar, text="就绪", font=("Segoe UI", fs - 5))
        self.status_lbl.pack(side=tk.LEFT)

class AppController:
    def __init__(self, model: 'AppModel', view: AppView):
        self.model = model
        self.view = view
        self.acad = None
        self._bind_events()
        self._init_state()

    def _init_state(self):
        last_dir = self.model.get_config("last_dir", os.getcwd())
        self._load_directory(last_dir)

    def _bind_events(self):
        self.view.btn_load_dir.config(command=self._on_load_dir)
        self.view.btn_connect_cad.config(command=self._on_connect_cad)
        self.view.btn_init_cad.config(command=self._on_init_cad)
        self.view.btn_print.config(command=self._on_print)
        self.view.btn_refresh.config(command=self._on_refresh)
        self.view.tree.bind("<<TreeviewSelect>>", self._on_select_file)
        self.view.btn_save_docs.config(command=self._on_save_docs)

    def _on_load_dir(self):
        dir = filedialog.askdirectory(initialdir=self.model.last_dir)
        if dir: self._load_directory(dir)

    def _load_directory(self, dir: str):
        self.model.last_dir = dir
        self.model.save_config("last_dir", dir)
        self.model.scan_directory(dir)
        self._refresh_tree()
        self.view.status_lbl.config(text=f"目录已加载: {dir}")

    def _on_connect_cad(self):
        """仅连接CAD，不新建图形"""
        try:
            self.view.status_lbl.config(text="正在连接 AutoCAD...")
            self.view.update()
            
            self.acad = find_autocad()
            if not self.acad:
                raise RuntimeError("无法获取 AutoCAD 对象。")
            
            # 确保CAD窗口可见
            self.acad.Visible = True
            
            # 检查是否有活动文档
            if not self.acad.ActiveDocument:
                messagebox.showwarning("提醒", "AutoCAD 已连接，但没有活动文档。请打开或创建一个图形文件。")
                self.view.status_lbl.config(text="已连接到 AutoCAD (无活动文档)")
            else:
                self.view.status_lbl.config(text="已成功连接到 AutoCAD")
                messagebox.showinfo("成功", "已成功连接到 AutoCAD！")
        except Exception as e:
            self.view.status_lbl.config(text=f"错误: {e}")
            messagebox.showerror("连接错误", str(e))

    def _on_init_cad(self):
        """连接CAD并初始化（新建图形、加载样板、加载LISP文件）"""
        if not self.model.last_dir:
            messagebox.showwarning("提醒", "请先加载 LISP 目录。")
            return

        primary_template = filedialog.askopenfilename(
            title="选择 AutoCAD 样板 (DWT)",
            filetypes=[("AutoCAD 样板", "*.dwt")]
        )
        if not primary_template: return

        backup_template = r"C:\Users\fanzhou\AppData\Local\Autodesk\AutoCAD 2021\R24.0\chs\Template\LISP图样.dwt"

        try:
            self.view.status_lbl.config(text="正在连接 AutoCAD...")
            self.view.update()
            
            self.acad = find_autocad()
            if not self.acad: raise RuntimeError("无法获取 AutoCAD 对象。")
            
            # 始终尝试新建基于样板的图形
            self.view.status_lbl.config(text="正在创建基于样板的新图形...")
            self.view.update()
            
            doc = apply_template_with_fallback(self.acad, primary_template, backup_template)
            
            # 如果新建失败，给予明确提醒
            if not doc:
                msg = "新建图形失败。请检查 AutoCAD 是否弹出了未关闭的对话框（如字体选择），关闭后重试。"
                self.view.status_lbl.config(text="初始化失败。")
                messagebox.showerror("样板应用失败", msg)
                return
            
            # 激活新文档
            doc.Activate()
            
            # 配置打印设置（应用到当前文档的布局）
            if HAS_PRINT_MANAGER:
                try:
                    configure_print_settings(doc)
                except:
                    pass
            
            # 加载 LISP
            file_count = len(self.model.files_data)
            self.view.status_lbl.config(text=f"正在注册 {file_count} 个 LISP 文件 (autoload)...")
            self.view.update()
            
            success_count = 0
            for file_path, lisp_file_obj in self.model.files_data.items():
                try:
                    # 传入解析到的函数列表，以便构建 autoload 命令列表
                    if load_single_lisp_file(doc, file_path, functions=lisp_file_obj.functions):
                        success_count += 1
                except: continue
                time.sleep(0.3)
            
            self.view.status_lbl.config(text=f"完成！已在新图形中加载 {success_count} 个文件。")
            messagebox.showinfo("成功", f"新图形已创建并完成初始化！\n共加载 {success_count} 个 LISP 文件。")
        except Exception as e:
            self.view.status_lbl.config(text=f"错误: {e}")
            messagebox.showerror("初始化错误", str(e))

    def _on_refresh(self):
        if self.model.last_dir: self._load_directory(self.model.last_dir)

    def _refresh_tree(self):
        self.view.tree.delete(*self.view.tree.get_children())
        for path in self.model.files_data.keys():
            self.view.tree.insert("", tk.END, text=os.path.basename(path), values=(path,))

    def _on_select_file(self, event):
        sel = self.view.tree.selection()
        if not sel: return
        path = self.view.tree.item(sel[0], "values")[0]
        lfile = self.model.files_data.get(path)
        if lfile:
            self.model.current_file = lfile
            self.view.lbl_file_name.config(text=lfile.name)
            
            # 根据文件名设置文档说明
            file_name = os.path.splitext(lfile.name)[0]
            if file_name == "JZM_短尾M24_基准模":
                doc = "短尾M24基准模绘图程序\n\n参数说明：\n"
                doc += "r0: 圆弧半径\n"
                doc += "a0: 大端宽度\n"
                doc += "t0: 总厚度\n"
                doc += "scale_str: 图纸比例\n"
                doc += "tech_choice: 技术要求选择 (1: 默认, 2: 自定义)\n"
                doc += "custom_tech_text: 自定义技术要求内容\n"
                doc += "slot_choice: 开槽选项 (0: 不添加, 1: 凹模开槽, 2: 凸模开槽, 3: 都添加)"
            elif file_name == "JZM_锥度_基准模":
                doc = "锥度基准模绘图程序\n\n参数说明：\n"
                doc += "r0: 圆弧半径\n"
                doc += "a0: 大端宽度\n"
                doc += "scale_str: 图纸比例\n"
                doc += "t0: 总厚度\n"
                doc += "tech_choice: 技术要求选择 (1: 默认, 2: 自定义)\n"
                doc += "custom_tech_text: 自定义技术要求内容\n"
                doc += "slot_choice: 开槽选项 (0: 不添加, 1: 凹模开槽, 2: 凸模开槽, 3: 都添加)"
            elif file_name in ["DWA_短尾凹", "DWT_短尾凸", "XZA_小锥度凹", "XZT_小锥度凸"]:
                name_map = {
                    "DWA_短尾凹": "短尾凹模",
                    "DWT_短尾凸": "短尾凸模",
                    "XZA_小锥度凹": "小锥度凹模",
                    "XZT_小锥度凸": "小锥度凸模"
                }
                doc = f"{name_map.get(file_name)}绘图程序\n\n参数说明：\n"
                doc += "tool_type: 工装类型 (1-5)\n"
                doc += "r0: 圆弧半径\n"
                doc += "a0: 大端宽度\n"
                doc += "t0: 总厚度"
            elif file_name == "XBA_下摆凹":
                doc = "下摆凹模绘图程序\n\n参数说明：\n"
                doc += "tool_type: 工装类型 (1-2)\n"
                doc += "r0: 圆弧半径\n"
                doc += "a0: 大端宽度\n"
                doc += "t0: 总厚度\n"
                doc += "b0: 摆动半径\n"
                doc += "tech_choice: 技术要求选择 (1: 默认, 2: 自定义)\n"
                doc += "custom_tech_text: 自定义技术要求内容"
            else:
                doc = self.model.get_doc_for_file(path)
            
            self.view.txt_docs.delete("1.0", tk.END)
            self.view.txt_docs.insert(tk.END, doc)
            self._update_function_list(lfile)

    def _update_function_list(self, lfile: LispFile):
        for w in self.view.func_scroll_frame.winfo_children(): w.destroy()
        fs = self.view.font_size_base
        if not lfile.functions:
            ttk.Label(self.view.func_scroll_frame, text="未检测到 c: 命令。", font=("Segoe UI", fs)).pack(pady=20)
            return
        
        # 显示该文件中的所有 c: 函数
        for func in lfile.functions:
            if func.name.lower().startswith("c:"):
                f = ttk.Frame(self.view.func_scroll_frame, padding=10)
                f.pack(fill=tk.X, expand=True)
                sig = f"{func.name}"
                ttk.Label(f, text=sig, font=("Segoe UI", fs)).pack(side=tk.LEFT)
                btn = ttk.Button(f, text="🚀 执行", style="Accent.TButton", 
                                 command=lambda f_obj=func: self._on_execute_click(f_obj))
                btn.pack(side=tk.RIGHT, padx=20)

    def _on_save_docs(self):
        if self.model.current_file:
            doc = self.view.txt_docs.get("1.0", tk.END).strip()
            self.model.save_doc_for_file(self.model.current_file.path, doc)
            messagebox.showinfo("成功", "文档已保存！")

    def _ensure_cad_connection(self):
        """确保CAD连接，如果未连接则自动连接"""
        if not self.acad:
            try:
                self.view.status_lbl.config(text="正在连接 AutoCAD...")
                self.view.update()
                
                self.acad = find_autocad()
                if not self.acad:
                    raise RuntimeError("无法获取 AutoCAD 对象。")
                
                # 确保CAD窗口可见
                self.acad.Visible = True
                
                # 检查是否有活动文档
                if not self.acad.ActiveDocument:
                    messagebox.showwarning("提醒", "AutoCAD 已连接，但没有活动文档。请打开或创建一个图形文件。")
                    return False
                
                self.view.status_lbl.config(text="已成功连接到 AutoCAD")
                return True
            except Exception as e:
                self.view.status_lbl.config(text=f"错误: {e}")
                messagebox.showerror("连接错误", str(e))
                return False
        else:
            # 检查连接是否仍然有效
            try:
                if not self.acad.ActiveDocument:
                    messagebox.showwarning("提醒", "AutoCAD 已连接，但没有活动文档。请打开或创建一个图形文件。")
                    return False
                return True
            except:
                # 连接已失效，尝试重新连接
                return self._ensure_cad_connection()

    def _on_execute_click(self, func: LispFunction):
        # 确保CAD连接
        if not self._ensure_cad_connection():
            return
        
        # 检查当前选中的文件是否有对应的UI模块
        if self.model.current_file:
            file_name = os.path.splitext(self.model.current_file.name)[0]
            ui_module = self._get_ui_module(file_name)
            if ui_module:
                self._show_custom_ui(ui_module)
                return
        
        # 如果没有自定义UI，使用默认的参数输入对话框
        ExecutionDialog(self.view, func, self._execute_in_cad, self.view.font_size_base)

    def _get_ui_module(self, file_name: str):
        """根据文件名获取对应的UI模块"""
        ui_modules = {
            "DWA_短尾凹": (HAS_DWA, DWA_短尾凹_UI),
            "DWT_短尾凸": (HAS_DWT, DWT_短尾凸_UI),
            "JZM_短尾M24_基准模": (HAS_JZM1, JZM_短尾M24_基准模_UI),
            "JZM_锥度_基准模": (HAS_JZM2, JZM_锥度_基准模_UI),
            "XBA_下摆凹": (HAS_XBA, XBA_下摆凹_UI),
            "XZA_小锥度凹": (HAS_XZA, XZA_小锥度凹_UI),
            "XZT_小锥度凸": (HAS_XZT, XZT_小锥度凸_UI),
        }
        
        if file_name in ui_modules:
            has_module, ui_class = ui_modules[file_name]
            if has_module:
                return ui_class
        return None

    def _show_custom_ui(self, ui_class):
        """显示自定义UI对话框"""
        dialog = tk.Toplevel(self.view)
        dialog.title(f"参数输入 - {ui_class.__name__.replace('_UI', '')}")
        dialog.transient(self.view)
        dialog.grab_set()
        
        # 创建UI
        ui_instance = ui_class(dialog, self._execute_custom_function, self.view.font_size_base)
        frame = ttk.Frame(dialog, padding="30")
        frame.pack(fill=tk.BOTH, expand=True)
        ui_instance.create_ui(frame)
        
    def _execute_custom_function(self, function_name: str, params: Dict[str, Any]):
        """使用自定义UI执行LISP函数"""
        # 确保CAD连接
        if not self._ensure_cad_connection():
            return
        try:
            self.view.status_lbl.config(text=f"正在执行 {function_name}...")
            
            # 获取该函数的定义
            func_def = None
            if self.model.current_file and self.model.current_file.functions:
                for f in self.model.current_file.functions:
                    if f.name.lower() == function_name.lower():
                        func_def = f
                        break
            
            # 如果 LISP 函数定义中包含参数，则启用带参调用模式
            is_parameterized = func_def and len(func_def.params) > 0
            
            # 根据不同的函数构建参数列表
            args_list = []
            if function_name in ["c:dwa", "c:dwt", "c:xza", "c:xzt"]:
                # 这些函数的参数顺序：r0, a0, t0, tool_type
                # 注意：tool_type 在 LISP 中通过 (= tool_type "1") 这种字符串方式判断
                args_list = [
                    str(params.get("r0", "")),
                    str(params.get("a0", "")),
                    str(params.get("t0", "")),
                    f'"{params.get("tool_type", "1")}"'
                ]
            elif function_name == "c:JZM1" or function_name == "c:JZM2":
                # JZM1: r0 a0 t0 scale_str tech_choice custom_tech_text slot_choice
                # JZM2: r0 a0 scale_str t0 tech_choice custom_tech_text slot_choice
                if function_name == "c:JZM1":
                    args_list = [
                        str(params.get("r0", "")),
                        str(params.get("a0", "")),
                        str(params.get("t0", "")),
                        f'"{params.get("scale_str", "1:1")}"',
                        str(params.get("tech_choice", "1")),
                        f'"{params.get("custom_tech_text", "")}"',
                        str(params.get("slot_choice", "0"))
                    ]
                else: # c:JZM2
                    args_list = [
                        str(params.get("r0", "")),
                        str(params.get("a0", "")),
                        f'"{params.get("scale_str", "1:1")}"',
                        str(params.get("t0", "")),
                        str(params.get("tech_choice", "1")),
                        f'"{params.get("custom_tech_text", "")}"',
                        str(params.get("slot_choice", "0"))
                    ]
            elif function_name == "c:xba":
                # XBA函数的参数顺序：r0, a0, t0, b0, tool_type, tech_choice, custom_tech_text
                # 注意：tool_type 在 LISP 中通过 (= tool_type "1") 这种字符串方式判断
                args_list = [
                    str(params.get("r0", "")),
                    str(params.get("a0", "")),
                    str(params.get("t0", "")),
                    str(params.get("b0", "")),
                    f'"{params.get("tool_type", "1")}"',
                    str(params.get("tech_choice", "1")),
                    f'"{params.get("custom_tech_text", "")}"'
                ]
            
            run_lisp_function(self.acad, function_name, args_list, is_parameterized)
            args_str = " ".join(args_list)
            self.view.status_lbl.config(text=f"已发送命令: ({function_name} {args_str})")
        except Exception as e:
            messagebox.showerror("CAD 错误", str(e))

    def _execute_in_cad(self, func: LispFunction, params: Dict[str, Any]):
        # 确保CAD连接
        if not self._ensure_cad_connection():
            return
        try:
            self.view.status_lbl.config(text=f"正在执行 {func.name}...")
            args_list = []
            for p in func.params:
                v = params.get(p)
                if isinstance(v, bool): 
                    args_list.append("T" if v else "nil")
                elif isinstance(v, str) and v.replace('.','',1).isdigit(): 
                    args_list.append(str(v))
                else: 
                    args_list.append(f'"{v}"')
            
            is_parameterized = len(func.params) > 0
            run_lisp_function(self.acad, func.name, args_list, is_parameterized)
            args_str = " ".join(args_list)
            self.view.status_lbl.config(text=f"已发送命令: ({func.name} {args_str})")
        except Exception as e:
            messagebox.showerror("CAD 错误", str(e))
    
    def _on_print(self):
        """执行打印，保存PDF到P:\工装绘图文件"""
        if not self.acad:
            messagebox.showwarning("提醒", "请先连接 AutoCAD。")
            return
        
        try:
            doc = self.acad.ActiveDocument
            if not doc:
                messagebox.showwarning("提醒", "找不到活动文档。")
                return
            
            self.view.status_lbl.config(text="正在打印...")
            self.view.update()
            
            if HAS_PRINT_MANAGER:
                output_path = plot_paper_space(doc, output_dir="P:\\工装绘图文件")
                if output_path:
                    self.view.status_lbl.config(text=f"任务已发送: {os.path.basename(output_path)}")
                    messagebox.showinfo("打印任务已发送", f"AutoCAD 正在后台生成 PDF。\n文件名将为:\n{os.path.basename(output_path)}\n\n请在 P:\\工装绘图文件 文件夹中查看结果。")
                else:
                    self.view.status_lbl.config(text="发送打印任务失败")
                    messagebox.showerror("打印错误", "无法向 AutoCAD 发送打印任务。")
            else:
                messagebox.showwarning("提醒", "打印模块未加载。")
                
        except Exception as e:
            self.view.status_lbl.config(text=f"打印错误: {e}")
            messagebox.showerror("打印错误", str(e))

class AppModel:
    def __init__(self):
        self.last_dir = ""
        self.files_data: Dict[str, LispFile] = {}
        self.current_file: Optional[LispFile] = None
        self.config_dir = os.path.join(os.path.expanduser("~"), ".autolisp_mgr")
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_path = os.path.join(self.config_dir, "config.json")
        self.docs_path = os.path.join(self.config_dir, "docs.json")
        self._load_configs()
        self._load_docs_persistence()

    def _load_configs(self):
        try:
            with open(self.config_path, 'r') as f: self.config = json.load(f)
        except: self.config = {}

    def _load_docs_persistence(self):
        try:
            with open(self.docs_path, 'r') as f: self.docs_data = json.load(f)
        except: self.docs_data = {}

    def get_config(self, key, default): return self.config.get(key, default)
    def save_config(self, key, value):
        self.config[key] = value
        with open(self.config_path, 'w') as f: json.dump(self.config, f)

    def scan_directory(self, dir: str):
        self.files_data = {}
        for root, _, files in os.walk(dir):
            for file in files:
                if file.lower().endswith('.lisp') or file.lower().endswith('.lsp'):
                    path = os.path.join(root, file)
                    funcs = LispParser.parse_file(path)
                    self.files_data[path] = LispFile(path=path, name=file, functions=funcs)

    def get_doc_for_file(self, path: str) -> str:
        if path in self.docs_data: return self.docs_data[path]
        lfile = self.files_data.get(path)
        if lfile and lfile.functions: return lfile.functions[0].docstring or "暂无说明。"
        return "暂无说明。"

    def save_doc_for_file(self, path: str, doc: str):
        self.docs_data[path] = doc
        with open(self.docs_path, 'w') as f: json.dump(self.docs_data, f)

if __name__ == "__main__":
    app_view = AppView()
    app_controller = AppController(AppModel(), app_view)
    app_view.mainloop()
