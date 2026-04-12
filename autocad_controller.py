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

def is_autocad_ready(acad):
    """检查AutoCAD是否处于空闲状态（无正在运行的命令）"""
    try:
        # CMDNAMES 为空表示没有正在运行的命令
        return acad.GetVariable("CMDNAMES") == ""
    except:
        return False

def force_cancel_commands(acad):
    """强制发送 ESC (Ctrl+C) 序列以取消任何正在运行的命令"""
    try:
        # 0. 尝试将 AutoCAD 窗口置顶，否则 SendCommand 可能因为焦点问题失败
        acad.Visible = True
        
        doc = acad.ActiveDocument
        if doc:
            # 1. 使用 \x03 (Ctrl+C) 发送取消请求
            # 使用 SendCommand 发送控制字符在 CAD 繁忙时可能抛出 "输入无效" 错误
            # 这是因为 CAD 的 COM 队列已满或处于模态对话框状态
            try:
                # 尝试激活文档后再发送
                doc.Activate()
                doc.SendCommand("\x03\x03")
                print("i 已向 AutoCAD 发送强制取消指令 (Ctrl+C)")
                time.sleep(1)
                return True
            except Exception as e:
                # 如果 SendCommand 失败，说明 CAD 处于极度繁忙或有模态对话框
                print(f"⚠ SendCommand 发送取消指令被 CAD 拒绝: {e}")
                # 此时不抛出异常，让主程序继续尝试 Add 等操作，因为 Add 有自己的重试机制
                return False
    except Exception as e:
        print(f"⚠ 强制取消操作异常: {e}")
    return False

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
        print(f"样板不存在: {template_path}")
        return None
        
    try:
        abs_path = os.path.abspath(template_path)
        acad.Visible = True
        
        # 在执行 Add 之前，尝试确保 CAD 是“安静”的
        # 如果 CAD 弹出了对话框（如“找不到字体”），Add 可能会失败
        if not is_autocad_ready(acad):
            print("AutoCAD 正在处理其他任务，尝试强制中断...")
            force_cancel_commands(acad)
            
        # Documents.Add 始终会创建一个全新的空白图形文件
        doc = acad.Documents.Add(abs_path)
        return doc
    except Exception as e:
        print(f"创建新文档失败 ({os.path.basename(template_path)}): {e}")
        return None

def apply_template_with_fallback(acad, primary_template, backup_template): 
    """应用样板逻辑：始终尝试新建文档""" 
    if not acad: return None
    
    # 1. 尝试主样板新建
    print(f"正在创建新图形（基于主样板）: {os.path.basename(primary_template)}")
    doc = create_new_doc_from_template(acad, primary_template)
    if doc:
        print("✓ 新图形已创建")
        return doc
        
    # 2. 尝试备用样板新建
    print(f"正在创建新图形（基于备用样板）: {os.path.basename(backup_template)}")
    doc = create_new_doc_from_template(acad, backup_template)
    if doc:
        print("✓ 已使用备用样板创建新图形")
        return doc
    
    return None 

@retry_on_autocad_error(max_attempts=3, initial_delay=1) 
def load_single_lisp_file(doc, lisp_file, functions=None): 
    """加载单个LISP文件 (使用 autoload 模式)""" 
    if not doc: return False
    lisp_path = os.path.abspath(lisp_file).replace("\\", "/") 
    file_name = os.path.basename(lisp_file)
    
    # 获取该文件中的所有 c: 命令名
    cmd_list = []
    if functions:
        for f in functions:
            if f.name.lower().startswith("c:"):
                # 提取 c: 之后的部分作为命令名
                cmd_name = f.name[2:]
                cmd_list.append(cmd_name.upper())
    
    if not cmd_list:
        # 如果没找到 c: 命令，退回到普通的 load 模式
        load_command = f'(progn (vl-load-com) (load "{lisp_path}") (princ (strcat "\\n>> " "{file_name}" " 已加载。")) (princ))'
    else:
        # 构建 autoload 指令：(autoload "路径" '("CMD1" "CMD2"))
        # 注意：AutoCAD 的 autoload 要求路径中的反斜杠必须是双反斜杠或正斜杠
        cmds_str = ' '.join([f'"{c}"' for c in cmd_list])
        load_command = f'(progn (vl-load-com) (autoload "{lisp_path}" \'({cmds_str})) (princ (strcat "\\n>> " "{file_name}" " 已注册 autoload。")) (princ))'
    
    try:
        doc.Activate()
        doc.SendCommand(load_command + "\n") 
        print(f"已发送加载请求: {file_name} ({len(cmd_list)} 个命令)") 
        return True
    except Exception as e:
        print(f"加载失败: {e}")
        raise e

@retry_on_autocad_error(max_attempts=3, initial_delay=1) 
def run_lisp_function(acad, function_name, args_str=""): 
    """在当前活动文档运行函数""" 
    doc = acad.ActiveDocument 
    if not doc: raise RuntimeError("找不到活动文档")
    
    # 尝试中断可能正在运行的 CAD 命令
    if not is_autocad_ready(acad):
        print(f"AutoCAD 繁忙，尝试中断后运行 {function_name}...")
        force_cancel_commands(acad)
        
    doc.Activate()
    command = f"({function_name}{args_str})" 
    doc.SendCommand(command + "\n") 
    print(f"执行命令: {function_name}") 
    return True 

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
        self._setup_ui()
        self.transient(parent)
        self.grab_set()

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
        self.btn_init_cad = ttk.Button(self.toolbar, text="🚀 连接并初始化 CAD (新建图形)", style="Init.TButton")
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

    def _on_init_cad(self):
        """始终创建新图形并加载 LISP"""
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
                    print("✓ 打印配置已应用到文档")
                except Exception as e:
                    print(f"打印配置跳过 (非致命错误): {e}")
            
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
            self.view.txt_docs.delete("1.0", tk.END)
            self.view.txt_docs.insert(tk.END, self.model.get_doc_for_file(path))
            self._update_function_list(lfile)

    def _update_function_list(self, lfile: LispFile):
        for w in self.view.func_scroll_frame.winfo_children(): w.destroy()
        fs = self.view.font_size_base
        if not lfile.functions:
            ttk.Label(self.view.func_scroll_frame, text="未检测到 c: 命令。", font=("Segoe UI", fs)).pack(pady=20)
            return
        for func in lfile.functions:
            f = ttk.Frame(self.view.func_scroll_frame, padding=10)
            f.pack(fill=tk.X, expand=True)
            sig = f"{func.name} ({' '.join(func.params)})"
            ttk.Label(f, text=sig, font=("Segoe UI", fs)).pack(side=tk.LEFT)
            btn = ttk.Button(f, text="🚀 执行", style="Accent.TButton", 
                             command=lambda func=func: self._on_execute_click(func))
            btn.pack(side=tk.RIGHT, padx=20)

    def _on_save_docs(self):
        if self.model.current_file:
            doc = self.view.txt_docs.get("1.0", tk.END).strip()
            self.model.save_doc_for_file(self.model.current_file.path, doc)
            messagebox.showinfo("成功", "文档已保存！")

    def _on_execute_click(self, func: LispFunction):
        ExecutionDialog(self.view, func, self._execute_in_cad, self.view.font_size_base)

    def _execute_in_cad(self, func: LispFunction, params: Dict[str, Any]):
        if not self.acad:
            messagebox.showwarning("提醒", "请先连接 AutoCAD。")
            return
        try:
            self.view.status_lbl.config(text=f"正在执行 {func.name}...")
            args = ""
            for p in func.params:
                v = params.get(p)
                if isinstance(v, bool): args += " T " if v else " nil "
                elif isinstance(v, str) and v.replace('.','',1).isdigit(): args += f" {v} "
                else: args += f' "{v}" '
            run_lisp_function(self.acad, func.name, args)
            self.view.status_lbl.config(text=f"已发送命令: ({func.name}{args})")
        except Exception as e: messagebox.showerror("CAD 错误", str(e))
    
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
