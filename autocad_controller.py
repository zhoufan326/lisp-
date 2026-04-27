#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, tkinter as tk, threading, pythoncom
from tkinter import ttk, filedialog, messagebox
from lisp_loader import LispParser, load_single_lisp_file
from acad_doc_manager import find_autocad, apply_template, configure_print_settings
from lisp_executor import run_lisp
from dwg_saver import save_dwg
from acad_plot_manager import plot_paper_space
from filename import generate_filename
from drawer_manager import DrawerManager
from parameter_manager import ParameterManager
from error_handler import ErrorHandler

# UI Modules Import
HAS_UI = {}
UI_NAMES = ["DWA_短尾凹", "DWT_短尾凸", "JZM_短尾M24_基准模", "JZM_锥度_基准模", 
           "XBA_下摆凹", "XBT_下摆凸", "MJA_迈均凹", "MJT_迈均凸", 
           "XZA_小锥度凹", "XZT_小锥度凸"]
for name in UI_NAMES:
    try:
        mod = __import__(name, fromlist=[f"{name}_UI"])
        HAS_UI[name] = getattr(mod, f"{name}_UI")
    except Exception: pass





class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("AutoCAD LISP 智能管理 (v3.0)"); self.geometry("1200x800"); self.fs = 14
        
        # 配置样式
        self.style = ttk.Style()
        self.style.configure('Accent.TButton', font=('Segoe UI', 12, 'bold'), padding=10)
        
        self.acad = None; self.model = Model(); self.last_save_meta = None; self.current_func = None
        self.current_ui = None  # 当前UI组件
        
        # 初始化模块
        self.drawer = DrawerManager(self.acad)
        self.param_manager = ParameterManager()
        self.error_handler = ErrorHandler(self)
        
        self._setup(); self._load(self.model.last_dir)

    def _setup(self):
        # 顶部工具栏 - 更紧凑
        t = ttk.Frame(self, padding=5); t.pack(side=tk.TOP, fill=tk.X)
        
        # 左侧按钮
        left_frame = ttk.Frame(t); left_frame.pack(side=tk.LEFT)
        for text, cmd in [("📂 目录", self._on_dir), ("⚙️ 初始化", self._on_init), ("📂 加载", self._on_lisp), ("💾 保存", self._on_save_dwg), ("🖨️打印", self._on_print), ("🔍 检查", self._on_check_file), ("🔄 刷新", self._on_ref)]:
            ttk.Button(left_frame, text=text, command=cmd, width=8).pack(side=tk.LEFT, padx=2)
        
        # 右侧功能按钮
        right_frame = ttk.Frame(t); right_frame.pack(side=tk.RIGHT)
        
        # 参数输入框
        param_frame = ttk.Frame(right_frame); param_frame.pack(side=tk.RIGHT, padx=10)
        ttk.Label(param_frame, text="镜片半径:", font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=2)
        self.radius_entry = ttk.Entry(param_frame, width=8, font=('Segoe UI', 10))
        self.radius_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(param_frame, text="口径:", font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=2)
        self.blank_D_entry = ttk.Entry(param_frame, width=8, font=('Segoe UI', 10))
        self.blank_D_entry.pack(side=tk.LEFT, padx=2)
        
        # 绘制按钮
        button_frame = ttk.Frame(right_frame); button_frame.pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="绘制下摆工装", command=self._on_draw_xia_bai, width=12, style='Accent.TButton').pack(side=tk.RIGHT, padx=2)
        ttk.Button(button_frame, text="绘制迈均工装", command=self._on_draw_mai_jun, width=12, style='Accent.TButton').pack(side=tk.RIGHT, padx=2)
        ttk.Button(button_frame, text="绘制低抛工装", command=self._on_draw_di_pao, width=12, style='Accent.TButton').pack(side=tk.RIGHT, padx=2)
        
        # 状态栏 - 更紧凑
        self.status = ttk.Label(self, text="就绪", relief=tk.SUNKEN, padding=3); self.status.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 主内容区域 - 优化布局
        p = ttk.PanedWindow(self, orient=tk.HORIZONTAL); p.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)
        
        # 左侧文件树 - 适当缩小
        self.tree = ttk.Treeview(p, show="tree", selectmode="browse"); p.add(self.tree, weight=2)
        self.tree.bind("<<TreeviewSelect>>", self._on_sel)
        
        # 右侧详情区域 - 优化布局
        df = ttk.Frame(p, padding=10); p.add(df, weight=5)
        
        # 标题 - 字体适当缩小但保持清晰
        self.title_lbl = ttk.Label(df, text="选择文件", font=("Segoe UI", self.fs+3, "bold")); self.title_lbl.pack(anchor=tk.W)
        
        # 参数输入区域
        self.param_frame = ttk.Frame(df)
        self.param_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.param_inputs = {}

    def _on_dir(self):
        d = filedialog.askdirectory(initialdir=self.model.last_dir)
        if d: self._load(d)

    def _load(self, d):
        def task():
            self.model.last_dir = d; self.model.save_cfg("last_dir", d); self.model.scan(d)
            def update_ui():
                self.tree.delete(*self.tree.get_children())
                for rel_path in self.model.data: self.tree.insert("", tk.END, text=os.path.basename(rel_path), values=(rel_path,))
                self.status.config(text=f"已加载: {d}")
            self.after(0, update_ui)
        self._run_async(task, f"正在扫描目录: {d}...")

    def _on_init(self):
        def task():
            try:
                # 连接AutoCAD
                self.acad = find_autocad(); self.acad.Visible = True
                
                # 获取项目文件夹地址
                project_dir = os.path.dirname(os.path.abspath(__file__))
                template_path = os.path.join(project_dir, "LSP", "LISP图样.dwt")
                
                # 检查模板文件是否存在
                if not os.path.exists(template_path):
                    self.after(0, lambda: messagebox.showwarning("警告", f"模板文件不存在: {template_path}"))
                    return
                
                # 根据模板新建图形
                doc = apply_template(self.acad, template_path, None)
                doc.Activate()
                configure_print_settings(doc)
                
                self.after(0, lambda: self.status.config(text="AutoCAD 初始化完成"))
                self.after(0, lambda: messagebox.showinfo("成功", "AutoCAD 初始化完成！\n已根据模板创建新图形。"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", str(e)))
        self._run_async(task, "正在初始化 AutoCAD...")

    def _ensure_acad(self):
        """确保执行前有可用 CAD 连接。"""
        if self.acad:
            try:
                self.acad.Visible = True
                return True
            except Exception:
                self.acad = None
        try:
            self.acad = find_autocad()
            self.acad.Visible = True
            self.status.config(text="AutoCAD 已自动连接")
            return True
        except Exception as e:
            messagebox.showerror("错误", f"无法连接 AutoCAD: {e}")
            return False

    def _on_new(self):
        def task():
            try:
                tmpl = filedialog.askopenfilename(filetypes=[("DWT", "*.dwt")])
                if not tmpl: return
                self.acad = find_autocad(); doc = apply_template(self.acad, tmpl, None)
                doc.Activate(); configure_print_settings(doc)
                self.after(0, lambda: self.status.config(text="新图形已创建"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", str(e)))
        self._run_async(task, "正在创建新图形...")

    def _on_lisp(self):
        def task():
            try:
                # 确保AutoCAD连接
                if not self._ensure_acad():
                    self.after(0, lambda: messagebox.showwarning("提醒", "无法连接 AutoCAD。"))
                    return
                
                doc = self.acad.ActiveDocument
                if not doc:
                    self.after(0, lambda: messagebox.showwarning("提醒", "找不到活动文档。"))
                    return
                    
                count = 0
                for _, obj in self.model.data.items():
                    if load_single_lisp_file(doc, obj.path, obj.functions): 
                        count += 1
                        print(f"✓ 已加载 LISP 文件: {obj.name}")
                
                self.after(0, lambda: self.status.config(text=f"已加载 {count} 个 LISP 文件"))
                if count > 0:
                    self.after(0, lambda: messagebox.showinfo("成功", f"LISP文件加载完成！\n共加载 {count} 个 LISP 文件。"))
                else:
                    self.after(0, lambda: messagebox.showwarning("提醒", "没有找到可加载的 LISP 文件。"))
                    
            except Exception as e:
                print(f"✗ LISP文件加载失败: {e}")
                self.after(0, lambda: messagebox.showerror("错误", f"LISP文件加载失败: {str(e)}"))
        self._run_async(task, "正在加载 LISP 文件...")

    def _on_ref(self): self._load(self.model.last_dir)

    def _clear_params(self, frame=None):
        # 销毁所有子组件
        target_frame = frame or self.param_frame
        for widget in target_frame.winfo_children():
            widget.destroy()
        self.param_inputs.clear()
        self.current_func = None



    def _on_sel(self, e):
        sel = self.tree.selection()
        if not sel: return
        rel_path = self.tree.item(sel[0], "values")[0]; obj = self.model.data.get(rel_path)
        if not obj: return
        self.model.curr = obj; self.title_lbl.config(text=obj.name)
        
        # 清除之前的UI
        self._clear_params(self.param_frame)
        
        name = os.path.splitext(obj.name)[0]
        if name in HAS_UI:
            # 创建新UI组件
            self.current_ui = HAS_UI[name](self.param_frame, self._exec_custom, self.fs)
            self.current_ui.create_ui(self.param_frame)
            
            # 恢复之前保存的参数
            self.param_manager.load_params(self.current_ui)
            
            # 自动保存参数（当UI组件创建完成后）
            self.param_manager.save_params(self.current_ui)
            
            # 添加文档说明
            doc_frame = ttk.LabelFrame(self.param_frame, text="文档说明", padding=5)
            doc_frame.pack(fill=tk.X, pady=10)
            
            # 文档说明文本框（可编辑）
            self.doc_text = tk.Text(doc_frame, height=3, font=("Segoe UI", self.fs-2))
            self.doc_text.pack(fill=tk.X, padx=5, pady=5)
            self.doc_text.insert(tk.END, self.model.get_doc(rel_path))
            
            # 绑定文本变化事件，自动保存
            self.doc_text.bind("<<Modified>>", lambda e: self._auto_save_doc(rel_path))
        else:
            # 显示可用命令
            cmd_frame = ttk.LabelFrame(self.param_frame, text="可用命令", padding=5)
            cmd_frame.pack(fill=tk.BOTH, expand=True, pady=10)
            for f in (obj.functions or []):
                if f.name.lower().startswith("c:"):
                    row = ttk.Frame(cmd_frame); row.pack(fill=tk.X, pady=1)
                    ttk.Label(row, text=f.name, font=("Segoe UI", self.fs)).pack(side=tk.LEFT)
                    ttk.Button(row, text="🚀 执行", command=lambda f_obj=f: self._on_exec_click(f_obj), width=8).pack(side=tk.RIGHT)

    def _on_save_doc(self):
        if self.model.curr: self.model.save_doc(self.model.curr.path, self.docs.get("1.0", tk.END).strip())
    
    def _auto_save_doc(self, rel_path):
        """自动保存文档说明"""
        try:
            # 取消修改标记
            self.doc_text.edit_modified(False)
            
            doc_content = self.doc_text.get("1.0", tk.END).strip()
            self.model.save_doc(rel_path, doc_content)
            # 自动保存参数
            self.param_manager.save_params(self.current_ui)
            # 不显示提示框，避免打扰用户
            # messagebox.showinfo("成功", "文档说明和参数已保存！")
        except Exception as e:
            # 不显示错误提示，避免打扰用户
            # messagebox.showerror("错误", f"保存文档说明失败: {str(e)}")
            pass

    def _on_exec_click(self, f):
        self.current_func = f
        tab_frame = self.param_frame
        
        # 通用参数输入
        row = ttk.Frame(tab_frame); row.pack(fill=tk.X, pady=3)
        ttk.Label(row, text=f"命令: {f.name}", font=("Segoe UI", self.fs, "bold")).pack(side=tk.LEFT)
        
        for p in f.params:
            row = ttk.Frame(tab_frame); row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=f"{p}:", width=10, font=("Segoe UI", self.fs)).pack(side=tk.LEFT)
            var = tk.BooleanVar() if 'flag' in p.lower() or 'is-' in p.lower() else tk.StringVar()
            if isinstance(var, tk.BooleanVar):
                ttk.Checkbutton(row, variable=var).pack(side=tk.LEFT)
            else:
                entry = ttk.Entry(row, textvariable=var, font=("Segoe UI", self.fs))
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.param_inputs[p] = var
        
        # 执行按钮
        btn_frame = ttk.Frame(tab_frame); btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="🚀 执行", command=lambda: self._exec_generic(f, {k: v.get() for k, v in self.param_inputs.items()}), width=8).pack(side=tk.RIGHT, padx=3)

    def _exec_generic(self, f, p):
        def task():
            try:
                if not self._ensure_acad(): return
                doc = getattr(self.acad, "ActiveDocument", None)
                if not doc:
                    self.after(0, lambda: messagebox.showwarning("提醒", "请先在 CAD 中新建或打开图形，再执行。"))
                    return
                args = []
                for k in f.params:
                    v = p.get(k)
                    if isinstance(v, bool): args.append("T" if v else "nil")
                    elif str(v).replace('.','',1).isdigit(): args.append(str(v))
                    else: args.append(f'"{v}"')
                fname = self._get_fname(f.name.replace("c:",""), p)
                self._remember_save_meta(f.name.replace("c:", "").lower(), p, fname)
                run_lisp(self.acad, f.name, args, len(f.params)>0)
                self.after(0, lambda: self.status.config(text=f"执行完成: {f.name}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", str(e)))
        self._run_async(task, f"正在执行: {f.name}...")

    def _exec_custom(self, f_name, p):
        def task():
            try:
                if not self._ensure_acad(): return
                doc = getattr(self.acad, "ActiveDocument", None)
                if not doc:
                    self.after(0, lambda: messagebox.showwarning("提醒", "请先在 CAD 中新建或打开图形，再执行。"))
                    return
                clean = f_name.lower().replace("c:", "")
                args = self._build_args(clean, p)
                fname = self._get_fname(clean, p)
                self._remember_save_meta(clean, p, fname)
                exec_name = clean if f_name.lower().startswith("c:") else f_name
                run_lisp(self.acad, exec_name, args, True)
                self.after(0, lambda: self.status.config(text=f"执行完成: {exec_name}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", str(e)))
        self._run_async(task, f"正在执行: {f_name}...")

    def _run_async(self, func, status_text="正在处理..."):
        """在后台线程运行耗时任务，保持 GUI 响应。"""
        def wrapper():
            pythoncom.CoInitialize()
            try:
                self.after(0, lambda: self.status.config(text=status_text))
                func()
            finally:
                pythoncom.CoUninitialize()
        threading.Thread(target=wrapper, daemon=True).start()

    def _build_args(self, name, p):
        def abs_v(k): return str(abs(float(p.get(k, 0))))
        args_map = {
            ("dwa", "dwt", "xza", "xzt"): ["r0", "a0", "t0", lambda p: f'"{p.get("tool_type", "1")}"'],
            ("jzm1", "jzm2"): ["r0", "a0", "t0", lambda p: f'"{p.get("scale_str", "1:1")}"', lambda p: p.get("tech_choice", "1"), lambda p: f'"{p.get("custom_tech_text", "")}"', lambda p: p.get("slot_choice", "0")],
            ("xba", "xbt"): ["r0", "a0", "t0", "b0", lambda p: f'"{p.get("tool_type", "1")}"', lambda p: p.get("tech_choice", "1"), lambda p: f'"{p.get("custom_tech_text", "")}"'],
            ("mja", "mjt"): ["r0", "a0", "t0"]
        }
        for keys, args in args_map.items():
            if name in keys:
                return [abs_v(k) if isinstance(k, str) else k(p) for k in args]
        return []

    def _get_fname(self, name, p):
        pref = self._get_drawing_type(name, p)
        try: return generate_filename(float(p.get("r0", 0)), float(p.get("a0", 0)), pref or "DRAWING")
        except: return None

    def _get_drawing_type(self, name, p):
        # 基础类型映射
        base_map = {"mja": "XPMJM", "mjt": "XPMJM", "jzm1": "JZM", "jzm2": "JZM"}
        if name in base_map:
            return base_map[name]
        
        # 工具类型映射
        tool_map = {
            "1": "GPMJX", "2": "GPMXJ", "3": "QX", "4": "QZ", "5": "QP"
        }
        special_map = {
            "xba": {"1": "XPMJM", "2": "XJMJM"},
            "xbt": {"1": "XPMJM", "2": "XJMJM"}
        }
        
        tt = p.get("tool_type", "1")
        if name in special_map:
            return special_map[name].get(tt, "DRAWING")
        return tool_map.get(tt, "DRAWING")

    def _remember_save_meta(self, func_name, params, fallback_name=None):
        try:
            self.last_save_meta = {
                "name": fallback_name,
                "radius": float(params.get("r0", 0)),
                "chord_length": float(params.get("a0", 0)),
                "drawing_type": self._get_drawing_type(func_name, params),
            }
        except Exception:
            self.last_save_meta = {"name": fallback_name}

    def _on_print(self):
        def task():
            try:
                if not self._ensure_acad(): return
                doc = self.acad.ActiveDocument
                if not doc: return
                plot_paper_space(doc)
                self.after(0, lambda: self.status.config(text="打印已发送"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("打印失败", str(e)))
        self._run_async(task, "正在发送打印任务...")

    def _on_save_dwg(self):
        def task():
            try:
                if not self._ensure_acad(): return
                doc = self.acad.ActiveDocument
                if not doc:
                    self.after(0, lambda: messagebox.showwarning("提醒", "请先在 CAD 中新建或打开图形。"))
                    return

                meta = self.last_save_meta or {}
                # 获取项目文件夹地址
                project_dir = os.path.dirname(os.path.abspath(__file__))
                out_dir = os.path.join(project_dir, "工装绘图文件")
                
                # 确保输出目录存在
                os.makedirs(out_dir, exist_ok=True)
                
                path = save_dwg(
                    doc,
                    out_dir=out_dir,
                    name=None,
                    radius=meta.get("radius"),
                    chord_length=meta.get("chord_length"),
                    drawing_type=meta.get("drawing_type"),
                )
                self.after(0, lambda: self.status.config(text=f"已保存: {os.path.basename(path)}"))
                self.after(0, lambda: messagebox.showinfo("保存成功", f"DWG 已保存:\n{path}"))
                # 保存后自动检查一次文件
                self.after(500, self._on_check_file)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("保存失败", str(e)))
        self._run_async(task, "正在保存文件...")

    def _on_check_file(self):
        """通过检测保存好的 DWG 文件来确认绘图是否完成。"""
        if not self.last_save_meta:
            messagebox.showinfo("检查结果", "尚未执行任何绘图操作，无法进行文件名匹配。")
            return

        def task():
            meta = self.last_save_meta
            expected_name = generate_filename(
                meta.get("radius", 0), 
                meta.get("chord_length", 0), 
                meta.get("drawing_type", "DRAWING")
            )
            out_dir = "P:\\工装绘图文件"
            expected_path = os.path.join(out_dir, f"{expected_name}.dwg")

            if os.path.exists(expected_path):
                msg = f"✓ 检测到文件，绘图已完成！\n文件名: {expected_name}.dwg"
                self.after(0, lambda: self.status.config(text="绘图状态: 已完成"))
                self.after(0, lambda: messagebox.showinfo("检查成功", msg))
            else:
                msg = f"✗ 未检测到文件，绘图可能尚未保存或文件名不匹配。\n期待路径: {expected_path}"
                self.after(0, lambda: self.status.config(text="绘图状态: 未检测到文件"))
                self.after(0, lambda: messagebox.showwarning("检查提醒", msg))
        
        self._run_async(task, "正在验证绘图完成状态...")

    def _on_draw_xia_bai(self):
        """绘制下摆工装"""
        def task():
            try:
                if not self._ensure_acad():
                    self.error_handler.show_warning("提醒", "无法连接 AutoCAD。")
                    return
                
                # 获取输入参数
                radius = float(self.radius_entry.get()) if self.radius_entry.get() else 0
                blank_D = float(self.blank_D_entry.get()) if self.blank_D_entry.get() else 0
                
                self.after(0, lambda: self.status.config(text="正在绘制下摆工装..."))
                
                # 使用DrawerManager绘制
                self.drawer.acad = self.acad
                success = self.drawer.draw_xia_bai({"radius": radius, "blank_D": blank_D})
                
                if success:
                    self.after(0, lambda: self.status.config(text="下摆工装绘制完成"))
                    self.error_handler.show_info("成功", "下摆工装绘制完成！")
                else:
                    self.error_handler.show_error("错误", "下摆工装绘制失败")
            except Exception as e:
                self.error_handler.handle_exception(e, "绘制下摆工装")
        
        self._run_async(task, "正在绘制下摆工装...")
    
    def _on_draw_mai_jun(self):
        """绘制迈均工装"""
        def task():
            try:
                if not self._ensure_acad():
                    self.error_handler.show_warning("提醒", "无法连接 AutoCAD。")
                    return
                
                # 获取输入参数
                radius = float(self.radius_entry.get()) if self.radius_entry.get() else 0
                blank_D = float(self.blank_D_entry.get()) if self.blank_D_entry.get() else 0
                
                self.after(0, lambda: self.status.config(text="正在绘制迈均工装..."))
                
                # 使用DrawerManager绘制
                self.drawer.acad = self.acad
                success = self.drawer.draw_mai_jun({"radius": radius, "blank_D": blank_D})
                
                if success:
                    self.after(0, lambda: self.status.config(text="迈均工装绘制完成"))
                    self.error_handler.show_info("成功", "迈均工装绘制完成！")
                else:
                    self.error_handler.show_error("错误", "迈均工装绘制失败")
            except Exception as e:
                self.error_handler.handle_exception(e, "绘制迈均工装")
        
        self._run_async(task, "正在绘制迈均工装...")
    
    def _on_draw_di_pao(self):
        """绘制低抛工装"""
        def task():
            try:
                if not self._ensure_acad():
                    self.error_handler.show_warning("提醒", "无法连接 AutoCAD。")
                    return
                
                # 获取输入参数
                radius = float(self.radius_entry.get()) if self.radius_entry.get() else 0
                blank_D = float(self.blank_D_entry.get()) if self.blank_D_entry.get() else 0
                
                self.after(0, lambda: self.status.config(text="正在绘制低抛工装..."))
                
                # 使用DrawerManager绘制
                self.drawer.acad = self.acad
                success = self.drawer.draw_di_pao({"radius": radius, "blank_D": blank_D})
                
                if success:
                    self.after(0, lambda: self.status.config(text="低抛工装绘制完成"))
                    self.error_handler.show_info("成功", "低抛工装绘制完成！")
                else:
                    self.error_handler.show_error("错误", "低抛工装绘制失败")
            except Exception as e:
                self.error_handler.handle_exception(e, "绘制低抛工装")
        
        self._run_async(task, "正在绘制低抛工装...")

class Model:
    def __init__(self):
        # 保存到项目根目录
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.cfg_dir = os.path.join(self.project_dir, ".autolisp_mgr"); os.makedirs(self.cfg_dir, exist_ok=True)
        self.cfg_p = os.path.join(self.cfg_dir, "config.json"); self.docs_p = os.path.join(self.cfg_dir, "docs.json")
        try: self.cfg = json.load(open(self.cfg_p))
        except: self.cfg = {}
        try: self.docs_d = json.load(open(self.docs_p))
        except: self.docs_d = {}
        self.last_dir = self.cfg.get("last_dir", "."); self.data = {}; self.curr = None

    def save_cfg(self, k, v): self.cfg[k] = v; json.dump(self.cfg, open(self.cfg_p, 'w'))
    def scan(self, d):
        self.data = {}
        for r, _, fs in os.walk(d):
            for f in fs:
                if f.lower().endswith(('.lisp', '.lsp')):
                    # 存储绝对路径，确保加载稳定性
                    abs_path = os.path.abspath(os.path.join(r, f))
                    rel_path = os.path.relpath(abs_path, d)
                    self.data[rel_path] = type('obj', (), {
                        'path': abs_path, 
                        'name': f, 
                        'functions': LispParser.parse_file(abs_path)
                    })

    def get_doc(self, p): return self.docs_d.get(p, self.data[p].functions[0].docstring if self.data[p].functions else "暂无说明")
    def save_doc(self, p, d): self.docs_d[p] = d; json.dump(self.docs_d, open(self.docs_p, 'w'))

if __name__ == "__main__": App().mainloop()
