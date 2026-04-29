#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AutoCAD LISP 智能管理系统"""

import os
import json
import tkinter as tk
import threading
import pythoncom
from tkinter import ttk, filedialog, messagebox

# 导入外部模块

try:
    from lisp_loader import LispParser, load_single_lisp_file
    from acad_doc_manager import find_autocad, apply_template, configure_print_settings
    from lisp_executor import run_lisp
    from dwg_saver import select_save_directory, get_last_save_directory, set_last_save_directory, set_material_code_provider
    from acad_plot_manager import plot_paper_space
    from filename import generate_filename
    from drawer_manager import DrawerManager
    from parameter_manager import ParameterManager
    from error_handler import ErrorHandler
except ImportError as e:
    missing_module = str(e).split()[-1]
    messagebox.showerror("导入错误", f"缺少必要模块: {missing_module}\n请确保所有依赖模块已正确安装或放置在项目目录中。")
    raise SystemExit(1)


# 配置常量
CONFIG = {
    "WINDOW_GEOMETRY": "1400x800",
    "WINDOW_TITLE": "AutoCAD LISP 智能管理 (v3.0)",
    "FONT_SIZE": 14,
    "UI_NAMES": ["DWA_短尾凹", "DWT_短尾凸", "JZM_短尾M24_基准模", "JZM_锥度_基准模", "XBA_下摆凹", "XBT_下摆凸", "MJA_迈均凹", "MJT_迈均凸", "XZA_小锥度凹", "XZT_小锥度凸"],
    "TEMPLATE_FILE": os.path.join("LSP", "LISP图样.dwt"),
    "OUTPUT_DIR": "工装绘图文件",
    "CHECK_DIR": "P:\工装绘图文件"
}

# 动态加载UI模块
HAS_UI = {name: getattr(__import__(name, fromlist=[f"{name}_UI"]), f"{name}_UI") for name in CONFIG["UI_NAMES"] if __import__(name, fromlist=[f"{name}_UI"])}


class App(tk.Tk):
    """主应用程序类"""
    def __init__(self):
        super().__init__()
        self.title(CONFIG["WINDOW_TITLE"])
        self.geometry(CONFIG["WINDOW_GEOMETRY"])
        self.fs = CONFIG["FONT_SIZE"]
        
        # 配置样式
        self.style = ttk.Style()
        self.style.configure('Accent.TButton', font=('Segoe UI', 12, 'bold'), padding=10)
        
        # 初始化模块
        self.acad = None
        self.model = Model()
        self.last_save_meta = None
        self.current_func = None
        self.current_ui = None
        self.last_save_directory = None  # 记录最后保存位置
        
        self.drawer = DrawerManager(self.acad)
        self.param_manager = ParameterManager()
        self.error_handler = ErrorHandler(self)
        
        # 设置UI
        self._setup_ui()
        self._load(self.model.last_dir)
        
        # 注入物料编码供应器，使 dwg_saver 能直接从 UI 获取编码
        set_material_code_provider(lambda: self.material_code_entry.get().strip() if hasattr(self, 'material_code_entry') else "")
    
    def _setup_ui(self):
        """设置用户界面"""
        # 工具栏
        toolbar = ttk.Frame(self, padding=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        # 左侧按钮
        left_frame = ttk.Frame(toolbar)
        left_frame.pack(side=tk.LEFT)
        
        buttons = [
            ("📂 目录", self._on_dir),
            ("⚙️ 初始化", self._on_init),
            ("📂 加载", self._on_lisp),
            ("💾 保存", self._on_save_dwg),
            ("🖨️ 打印", self._on_print),
            ("🔍 检查", self._on_check_file),
            ("🔄 刷新", self._on_ref)
        ]
        
        for text, cmd in buttons:
            ttk.Button(left_frame, text=text, command=cmd, width=8).pack(side=tk.LEFT, padx=2)
        
        # 右侧参数和按钮
        right_frame = ttk.Frame(toolbar)
        right_frame.pack(side=tk.RIGHT)
        
        # 参数输入框
        param_frame = ttk.Frame(right_frame)
        param_frame.pack(side=tk.RIGHT, padx=10)
        
        self.radius_entry = self._create_labeled_entry(param_frame, "镜片半径:", 8)
        self.blank_D_entry = self._create_labeled_entry(param_frame, "口径:", 8)
        self.material_code_entry = self._create_labeled_entry(param_frame, "物料编码:", 12)
        
        # 绘制按钮
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(side=tk.RIGHT)
        
        draw_buttons = [
            ("绘制下摆工装", self._on_draw_xia_bai),
            ("绘制迈均工装", self._on_draw_mai_jun),
            ("绘制低抛工装", self._on_draw_di_pao)
        ]
        
        for text, cmd in draw_buttons:
            ttk.Button(button_frame, text=text, command=cmd, width=12, style='Accent.TButton').pack(side=tk.RIGHT, padx=2)
        
        # 状态栏
        self.status = ttk.Label(self, text="就绪", relief=tk.SUNKEN, padding=3)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 主内容区域
        paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)
        
        # 左侧文件树
        self.tree = ttk.Treeview(paned_window, show="tree", selectmode="browse")
        paned_window.add(self.tree, weight=3)
        self.tree.bind("<<TreeviewSelect>>", self._on_sel)
        
        # 右侧详情区域
        detail_frame = ttk.Frame(paned_window, padding=10)
        paned_window.add(detail_frame, weight=7)
        
        self.title_lbl = ttk.Label(detail_frame, text="选择文件", font=("Segoe UI", self.fs+3, "bold"))
        self.title_lbl.pack(anchor=tk.W)
        
        self.param_frame = ttk.Frame(detail_frame)
        self.param_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.param_inputs = {}
    
    def _create_labeled_entry(self, parent, label_text, width):
        """创建带标签的输入框"""
        ttk.Label(parent, text=label_text, font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=2)
        entry = ttk.Entry(parent, width=width, font=('Segoe UI', 10))
        entry.pack(side=tk.LEFT, padx=2)
        return entry
    
    def _update_status(self, text):
        """更新状态栏"""
        self.status.config(text=text)
    
    def _run_async(self, func, status_text="正在处理..."):
        """后台运行耗时任务"""
        def wrapper():
            pythoncom.CoInitialize()
            try:
                self.after(0, lambda: self._update_status(status_text))
                func()
            finally:
                pythoncom.CoUninitialize()
        threading.Thread(target=wrapper, daemon=True).start()
    
    def _on_dir(self):
        if directory := filedialog.askdirectory(initialdir=self.model.last_dir):
            self._load(directory)
    
    def _load(self, directory):
        def task():
            self.model.last_dir = directory
            self.model.save_cfg("last_dir", directory)
            self.model.scan(directory)
            
            def update_ui():
                self.tree.delete(*self.tree.get_children())
                for rel_path in self.model.data:
                    self.tree.insert("", tk.END, text=os.path.basename(rel_path), values=(rel_path,))
                self._update_status(f"已加载: {directory}")
            
            self.after(0, update_ui)
        
        self._run_async(task, f"正在扫描目录: {directory}...")
    
    def _on_init(self):
        def task():
            try:
                self.acad = find_autocad()
                if not self.acad:
                    self.after(0, lambda: self.error_handler.show_error("连接失败", "无法找到正在运行的AutoCAD实例，请先启动AutoCAD再尝试初始化。"))
                    return
                self.acad.Visible = True
                
                project_dir = os.path.dirname(os.path.abspath(__file__))
                template_path = os.path.join(project_dir, CONFIG["TEMPLATE_FILE"])
                
                if not os.path.exists(template_path):
                    self.after(0, lambda: self.error_handler.show_warning("警告", f"模板文件不存在: {template_path}"))
                    return
                
                doc = apply_template(self.acad, template_path, None)
                doc.Activate()
                configure_print_settings(doc)
                
                self.after(0, lambda: self._update_status("AutoCAD 初始化完成"))
                self.after(0, lambda: self.error_handler.show_info("成功", "AutoCAD 初始化完成！"))
            except Exception as e:
                self.after(0, lambda: self.error_handler.handle_exception(e, "初始化 AutoCAD"))
        
        self._run_async(task, "正在初始化 AutoCAD...")
    
    def _ensure_acad(self):
        """确保AutoCAD连接"""
        if self.acad:
            try:
                self.acad.Visible = True
                self.drawer.acad = self.acad
                return True
            except Exception:
                self.acad = None
        
        try:
            self.acad = find_autocad()
            self.acad.Visible = True
            self.drawer.acad = self.acad
            self._update_status("AutoCAD 已自动连接")
            return True
        except Exception as e:
            self.error_handler.show_error("错误", f"无法连接 AutoCAD: {e}")
            return False
    
    def _on_lisp(self):
        def task():
            if not self._ensure_acad() or not self.acad.ActiveDocument:
                self.after(0, lambda: self.error_handler.show_warning("提醒", "找不到活动文档。"))
                return
            
            count = sum(1 for _, obj in self.model.data.items() if load_single_lisp_file(self.acad.ActiveDocument, obj.path, obj.functions))
            
            self.after(0, lambda: self._update_status(f"已加载 {count} 个 LISP 文件"))
            if count > 0:
                self.after(0, lambda: self.error_handler.show_info("成功", f"已加载 {count} 个 LISP 文件。"))
        
        self._run_async(task, "正在加载 LISP 文件...")
    
    def _on_ref(self):
        self._load(self.model.last_dir)
    
    def _clear_params(self, frame=None):
        """清除参数输入"""
        target_frame = frame or self.param_frame
        for widget in target_frame.winfo_children():
            widget.destroy()
        self.param_inputs.clear()
        self.current_func = None
    
    def _on_sel(self, event):
        """文件选择事件"""
        if not (selection := self.tree.selection()):
            return
        
        rel_path = self.tree.item(selection[0], "values")[0]
        if not (obj := self.model.data.get(rel_path)):
            return
        
        self.model.curr = obj
        self.title_lbl.config(text=obj.name)
        self._clear_params(self.param_frame)
        
        name = os.path.splitext(obj.name)[0]
        if name in HAS_UI:
            self._load_custom_ui(name, rel_path)
        else:
            self._show_commands(obj)
    
    def _load_custom_ui(self, name, rel_path):
        """加载自定义UI"""
        self.current_ui = HAS_UI[name](self.param_frame, self._exec_custom, self.fs)
        self.current_ui.create_ui(self.param_frame)
        
        self.param_manager.load_params(self.current_ui)
        self.param_manager.save_params(self.current_ui)
        
        doc_frame = ttk.LabelFrame(self.param_frame, text="文档说明", padding=5)
        doc_frame.pack(fill=tk.X, pady=10)
        
        self.doc_text = tk.Text(doc_frame, height=3, font=("Segoe UI", self.fs-2))
        self.doc_text.pack(fill=tk.X, padx=5, pady=5)
        self.doc_text.insert(tk.END, self.model.get_doc(rel_path))
        self.doc_text.bind("<<Modified>>", lambda e: self._auto_save_doc(rel_path))
    
    def _show_commands(self, obj):
        """显示可用命令"""
        cmd_frame = ttk.LabelFrame(self.param_frame, text="可用命令", padding=5)
        cmd_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        for func in (obj.functions or []):
            if func.name.lower().startswith("c:"):
                row = ttk.Frame(cmd_frame)
                row.pack(fill=tk.X, pady=1)
                ttk.Label(row, text=func.name, font=("Segoe UI", self.fs)).pack(side=tk.LEFT)
                ttk.Button(row, text="🚀 执行", command=lambda f=func: self._on_exec_click(f), width=8).pack(side=tk.RIGHT)
    
    def _on_save_doc(self):
        """保存文档"""
        if self.model.curr:
            self.model.save_doc(self.model.curr.path, self.doc_text.get("1.0", tk.END).strip())
    
    def _auto_save_doc(self, rel_path):
        """自动保存文档"""
        try:
            self.doc_text.edit_modified(False)
            doc_content = self.doc_text.get("1.0", tk.END).strip()
            self.model.save_doc(rel_path, doc_content)
            self.param_manager.save_params(self.current_ui)
        except Exception:
            pass
    
    def _on_exec_click(self, func):
        """执行命令点击事件"""
        self.current_func = func
        tab_frame = self.param_frame
        
        ttk.Label(tab_frame, text=f"命令: {func.name}", font=("Segoe UI", self.fs, "bold")).pack(side=tk.LEFT)
        
        for param in func.params:
            row = ttk.Frame(tab_frame)
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=f"{param}:", width=10, font=("Segoe UI", self.fs)).pack(side=tk.LEFT)
            
            var = tk.BooleanVar() if 'flag' in param.lower() or 'is-' in param.lower() else tk.StringVar()
            if isinstance(var, tk.BooleanVar):
                ttk.Checkbutton(row, variable=var).pack(side=tk.LEFT)
            else:
                entry = ttk.Entry(row, textvariable=var, font=("Segoe UI", self.fs))
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            self.param_inputs[param] = var
            # Load saved parameter value
            saved_value = self.param_manager.get_param(param)
            if saved_value is not None:
                if isinstance(var, tk.BooleanVar):
                    var.set(saved_value)
                else:
                    var.set(str(saved_value))
        
        btn_frame = ttk.Frame(tab_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="🚀 执行", command=lambda: self._exec_generic(func, {k: v.get() for k, v in self.param_inputs.items()}), width=8).pack(side=tk.RIGHT, padx=3)
    
    def _exec_generic(self, func, params):
        """执行通用命令"""
        def task():
            try:
                if not self._ensure_acad():
                    return
                
                doc = getattr(self.acad, "ActiveDocument", None)
                if not doc:
                    self.after(0, lambda: self.error_handler.show_warning("提醒", "请先在 CAD 中新建或打开图形，再执行。"))
                    return
                
                args = []
                for key in func.params:
                    val = params.get(key)
                    if isinstance(val, bool):
                        args.append("T" if val else "nil")
                    elif str(val).replace('.', '', 1).isdigit():
                        args.append(str(val))
                    else:
                        args.append(f'"{val}"')
                
                fname = self._get_fname(func.name.replace("c:", ""), params)
                self._remember_save_meta(func.name.replace("c:", "").lower(), params, fname)
                run_lisp(self.acad, func.name, args, len(func.params) > 0)
                
                self.after(0, lambda: self._update_status(f"执行完成: {func.name}"))
            except Exception as e:
                self.after(0, lambda: self.error_handler.handle_exception(e, f"执行 {func.name}"))
        
        self._run_async(task, f"正在执行: {func.name}...")
    
    def _exec_custom(self, func_name, params):
        """执行自定义命令"""
        def task():
            try:
                if not self._ensure_acad():
                    return
                
                doc = getattr(self.acad, "ActiveDocument", None)
                if not doc:
                    self.after(0, lambda: self.error_handler.show_warning("提醒", "请先在 CAD 中新建或打开图形，再执行。"))
                    return
                
                clean_name = func_name.lower().replace("c:", "")
                args = self._build_args(clean_name, params)
                fname = self._get_fname(clean_name, params)
                self._remember_save_meta(clean_name, params, fname)
                exec_name = clean_name if func_name.lower().startswith("c:") else func_name
                
                # 将保存路径传递给LISP
                if self.last_save_directory:
                    # 设置AutoCAD系统变量保存路径
                    doc.SetVariable("SAVEFILEPATH", self.last_save_directory)
                    
                    # 如果有物料编码，路径已在 Python 侧决策并创建
                    material_code = params.get("material_code", "")
                    if material_code:
                        doc.SetVariable("MATERIALPATH", self.last_save_directory)
                
                run_lisp(self.acad, exec_name, args, True)
                
                self.after(0, lambda: self._update_status(f"执行完成: {exec_name}"))
            except Exception as e:
                self.after(0, lambda: self.error_handler.handle_exception(e, f"执行 {func_name}"))
        
        self._run_async(task, f"正在执行: {func_name}...")
    
    def _build_args(self, name, params):
        """构建命令参数"""
        def abs_val(key): return str(abs(float(params.get(key, 0))))
        def str_val(key, default=""): return f'"{params.get(key, default)}"'
        def num_val(key, default=0): return str(params.get(key, default))
        
        args_map = {
            ("dwa", "dwt", "xza", "xzt"): [abs_val("r0"), abs_val("a0"), abs_val("t0"), str_val("tool_type", "1"), str_val("material_code")],
            ("jzm1", "jzm2"): [abs_val("r0"), abs_val("a0"), abs_val("t0"), str_val("scale_str", "1:1"), num_val("tech_choice", "1"), str_val("custom_tech_text"), num_val("slot_choice", "0"), str_val("material_code")],
            ("xba", "xbt"): [abs_val("r0"), abs_val("a0"), abs_val("t0"), abs_val("b0"), str_val("tool_type", "1"), num_val("tech_choice", "1"), str_val("custom_tech_text"), str_val("material_code")],
            ("mja", "mjt"): [abs_val("r0"), abs_val("a0"), abs_val("t0"), str_val("material_code")]
        }
        
        return next(([abs_val(k) if isinstance(k, str) else k(params) for k in args] for keys, args in args_map.items() if name in keys), [])
    
    def _get_fname(self, name, params):
        """生成文件名"""
        pref = self._get_drawing_type(name, params)
        try:
            return generate_filename(float(params.get("r0", 0)), float(params.get("a0", 0)), pref or "DRAWING")
        except Exception:
            return None
    
    def _get_drawing_type(self, name, params):
        """获取绘图类型"""
        base_map = {"mja": "XPMJM", "mjt": "XPMJM", "jzm1": "JZM", "jzm2": "JZM"}
        if name in base_map: return base_map[name]
        
        tool_map = {"1": "GPMJX", "2": "GPMXJ", "3": "QX", "4": "QZ", "5": "QP"}
        special_map = {"xba": {"1": "XPMJM", "2": "XJMJM"}, "xbt": {"1": "XPMJM", "2": "XJMJM"}}
        
        tt = params.get("tool_type", "1")
        return special_map.get(name, {}).get(tt, tool_map.get(tt, "DRAWING"))
    
    def _remember_save_meta(self, func_name, params, fallback_name=None):
        """保存元数据"""
        try:
            self.last_save_meta = {"name": fallback_name, "radius": float(params.get("r0", 0)), "chord_length": float(params.get("a0", 0)), "drawing_type": self._get_drawing_type(func_name, params)}
        except Exception:
            self.last_save_meta = {"name": fallback_name}
    
    def _on_print(self):
        """打印命令"""
        def task():
            try:
                if not self._ensure_acad():
                    return
                
                doc = self.acad.ActiveDocument
                if not doc:
                    return
                
                plot_paper_space(doc)
                self.after(0, lambda: self._update_status("打印已发送"))
            except Exception as e:
                self.after(0, lambda: self.error_handler.handle_exception(e, "发送打印任务"))
        
        self._run_async(task, "正在发送打印任务...")
    
    def _on_save_dwg(self):
        """保存DWG文件"""
        # 获取物料编码
        material_code = self.material_code_entry.get().strip() if hasattr(self, 'material_code_entry') else None
        
        # 先让用户选择保存位置（如果没有物料编码）
        directory = select_save_directory(self, material_code)
        if not directory:
            self.error_handler.show_info("取消保存", "用户取消了文件保存操作。")
            return
        
        # 记录保存位置
        self.last_save_directory = directory
        set_last_save_directory(directory)
        
        def task():
            try:
                if not self._ensure_acad() or not self.acad.ActiveDocument:
                    self.after(0, lambda: self.error_handler.show_warning("提醒", "请先在 CAD 中新建或打开图形。"))
                    return
                
                doc = self.acad.ActiveDocument

                # 设置AutoCAD系统变量保存路径
                doc.SetVariable("SAVEFILEPATH", directory)

                # 直接使用 AutoCAD SaveAs
                file_stem = None
                if isinstance(self.last_save_meta, dict):
                    file_stem = self.last_save_meta.get("name")

                if not file_stem:
                    current_name = os.path.splitext(os.path.basename(getattr(doc, "Name", "DRAWING.dwg")))[0]
                    file_stem = current_name or "DRAWING"

                # 兜底：避免文件名中出现路径分隔符
                file_stem = str(file_stem).replace("/", "／").replace("\\", "／")
                save_file = os.path.join(directory, f"{file_stem}.dwg")
                doc.SaveAs(save_file)
                
                self.after(0, lambda: self._update_status(f"已保存到: {save_file}"))
                self.after(0, lambda: self.error_handler.show_info("保存成功", f"DWG 已保存到:\n{save_file}"))
                self.after(500, self._on_check_file)
            except Exception as e:
                self.after(0, lambda: self.error_handler.handle_exception(e, "保存文件"))
        
        self._run_async(task, "正在保存文件...")
    
    def _on_check_file(self):
        """检查文件"""
        if not self.last_save_meta:
            self.error_handler.show_info("检查结果", "尚未执行任何绘图操作，无法进行文件名匹配。")
            return
        
        def task():
            meta = self.last_save_meta
            expected_name = generate_filename(
                meta.get("radius", 0),
                meta.get("chord_length", 0),
                meta.get("drawing_type", "DRAWING")
            )
            expected_path = os.path.join(CONFIG["CHECK_DIR"], f"{expected_name}.dwg")
            
            if os.path.exists(expected_path):
                self.after(0, lambda: self._update_status("绘图状态: 已完成"))
                self.after(0, lambda: self.error_handler.show_info("检查成功", f"✓ 检测到文件，绘图已完成！\n文件名: {expected_name}.dwg"))
            else:
                self.after(0, lambda: self._update_status("绘图状态: 未检测到文件"))
                self.after(0, lambda: self.error_handler.show_warning("检查提醒", f"✗ 未检测到文件，绘图可能尚未保存或文件名不匹配。\n期待路径: {expected_path}"))
        
        self._run_async(task, "正在验证绘图完成状态...")
    
    def _get_draw_params(self):
        """获取绘图参数"""
        return {
            "radius": float(self.radius_entry.get()) if self.radius_entry.get() else 0,
            "blank_D": float(self.blank_D_entry.get()) if self.blank_D_entry.get() else 0,
            "material_code": self.material_code_entry.get() if self.material_code_entry.get() else ""
        }
    
    def _draw_tool(self, draw_func, status_text, success_msg):
        """通用绘图函数"""
        params = self._get_draw_params()

        def task():
            try:
                if not self._ensure_acad():
                    self.error_handler.show_warning("提醒", "无法连接 AutoCAD。")
                    return

                self.after(0, lambda: self._update_status(status_text))
                
                self.drawer.acad = self.acad
                success = draw_func(params)
                
                if success:
                    self.after(0, lambda: self._update_status(success_msg))
                    self.error_handler.show_info("成功", f"{success_msg}！")
                else:
                    self.error_handler.show_error("错误", f"{status_text}失败")
            except Exception as e:
                self.error_handler.handle_exception(e, status_text)
        
        self._run_async(task, f"{status_text}...")
    
    def _on_draw_xia_bai(self):
        """绘制下摆工装"""
        self._draw_tool(self.drawer.draw_xia_bai, "正在绘制下摆工装", "下摆工装绘制完成")
    
    def _on_draw_mai_jun(self):
        """绘制迈均工装"""
        self._draw_tool(self.drawer.draw_mai_jun, "正在绘制迈均工装", "迈均工装绘制完成")
    
    def _on_draw_di_pao(self):
        """绘制低抛工装"""
        self._draw_tool(self.drawer.draw_di_pao, "正在绘制低抛工装", "低抛工装绘制完成")


class Model:
    """数据模型类"""
    def __init__(self):
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.cfg_dir = os.path.join(self.project_dir, ".autolisp_mgr")
        os.makedirs(self.cfg_dir, exist_ok=True)
        
        self.cfg_p = os.path.join(self.cfg_dir, "config.json")
        self.docs_p = os.path.join(self.cfg_dir, "docs.json")
        
        try:
            self.cfg = json.load(open(self.cfg_p))
        except Exception:
            self.cfg = {}
        
        try:
            self.docs_d = json.load(open(self.docs_p))
        except Exception:
            self.docs_d = {}
        
        self.last_dir = self.cfg.get("last_dir", ".")
        self.data = {}
        self.curr = None
    
    def save_cfg(self, key, value):
        """保存配置"""
        self.cfg[key] = value
        json.dump(self.cfg, open(self.cfg_p, 'w'))
    
    def scan(self, directory):
        """扫描目录"""
        self.data = {}
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(('.lisp', '.lsp')):
                    abs_path = os.path.abspath(os.path.join(root, file))
                    rel_path = os.path.relpath(abs_path, directory)
                    self.data[rel_path] = type('obj', (), {
                        'path': abs_path,
                        'name': file,
                        'functions': LispParser.parse_file(abs_path)
                    })
    
    def get_doc(self, path):
        """获取文档"""
        return self.docs_d.get(
            path,
            self.data[path].functions[0].docstring if self.data[path].functions else "暂无说明"
        )
    
    def save_doc(self, path, doc):
        """保存文档"""
        self.docs_d[path] = doc
        json.dump(self.docs_d, open(self.docs_p, 'w'))


if __name__ == "__main__":
    App().mainloop()
