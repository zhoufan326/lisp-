#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工装绘图管理器 (Tooling Manager)
版本: V1.1
作者: Zhoufan
日期: 2026-04-18

功能：
1. 输入待加工镜片的R值和口径，调用Tool_calculation.py进行计算
2. 计算所得为一整套工装的R值和口径
3. 用户在GUI中选择将不同工装的R值和口径以及其他所需参数作为参数值
4. 传入不同的lisp文件的函数中，从而快速在cad中绘制一整套工装
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import Dict, Any, Callable, Optional
import json
import os
import sys
from dataclasses import dataclass, asdict
from typing import List

# 导入计算模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from Tool_calculation import SwingMachineToolingCalculator
    HAS_CALCULATOR = True
except ImportError:
    HAS_CALCULATOR = False

# 导入AutoCAD相关模块
try:
    import win32com.client
    from lisp_loader import LispParser, load_single_lisp_file
    from acad_doc_manager import find_autocad, apply_template, configure_print_settings
    from lisp_executor import run_lisp
    HAS_AUTOCAD = True
except ImportError:
    HAS_AUTOCAD = False

# ==================== 数据类定义 ====================

@dataclass
class ToolingParameters:
    """工装参数数据类"""
    name: str = ""
    r0: float = 0.0
    a0: float = 0.0
    t0: float = 0.0
    b0: float = 0.0
    tool_type: str = "1"
    tech_choice: int = 1
    custom_tech_text: str = ""
    slot_choice: int = 0
    scale_str: str = "1:1"
    lisp_function: str = ""

@dataclass
class ParameterPreset:
    """参数预设数据类"""
    preset_name: str
    toolings: List[ToolingParameters]

# ==================== 常量定义 ====================

TOOL_TYPES = {
    "dwa": [
        ("1", "抛光模基模修盘"),
        ("2", "抛光模修盘基模"),
        ("3", "球面低抛细磨盘"),
        ("4", "球面低抛粘盘"),
        ("5", "球面低抛抛盘")
    ],
    "dwt": [
        ("1", "抛光模基模修盘"),
        ("2", "抛光模修盘基模"),
        ("3", "球面低抛细磨盘"),
        ("4", "球面低抛粘盘"),
        ("5", "球面低抛抛盘")
    ],
    "xba": [
        ("1", "抛光模基模"),
        ("2", "精磨模基模")
    ],
    "xbt": [
        ("1", "抛光模基模"),
        ("2", "精磨模基模")
    ],
    "xza": [
        ("1", "抛光模基模"),
        ("2", "精磨模基模")
    ],
    "xzt": [
        ("1", "抛光模基模"),
        ("2", "精磨模基模")
    ],
    "mja": [
        ("1", "抛光模基模"),
        ("2", "精磨模基模")
    ],
    "mjt": [
        ("1", "抛光模基模"),
        ("2", "精磨模基模")
    ],
    "jzm1": [
        ("1", "基准模")
    ],
    "jzm2": [
        ("1", "基准模")
    ]
}

SLOT_CHOICES = [
    ("0", "都不开槽"),
    ("1", "凹模"),
    ("2", "凸模"),
    ("3", "都开")
]

TECH_CHOICES = [
    ("1", "使用默认技术要求"),
    ("2", "自定义技术要求")
]

LISP_FUNCTIONS = {
    "dwa": ("DWA_短尾凹.lsp", "dwa"),
    "dwt": ("DWT_短尾凸.lsp", "dwt"),
    "xba": ("XBA_下摆凹.lsp", "xba"),
    "xbt": ("XBT_下摆凸.lsp", "xbt"),
    "xza": ("XZA_小锥度凹.lsp", "xza"),
    "xzt": ("XZT_小锥度凸.lsp", "xzt"),
    "mja": ("MJA_迈均凹.lsp", "mja"),
    "mjt": ("MJT_迈均凸.lsp", "mjt"),
    "jzm1": ("JZM_短尾M24_基准模.lsp", "jzm1"),
    "jzm2": ("JZM_锥度_基准模.lsp", "jzm2")
}

FUNCTION_PARAMS = {
    "dwa": ["r0", "a0", "t0", "tool_type"],
    "dwt": ["r0", "a0", "t0", "tool_type"],
    "xba": ["r0", "a0", "t0", "b0", "tool_type", "tech_choice", "custom_tech_text"],
    "xbt": ["r0", "a0", "t0", "b0", "tool_type", "tech_choice", "custom_tech_text"],
    "xza": ["r0", "a0", "t0", "tool_type"],
    "xzt": ["r0", "a0", "t0", "tool_type"],
    "mja": ["r0", "a0", "t0"],
    "mjt": ["r0", "a0", "t0"],
    "jzm1": ["r0", "a0", "scale_str", "t0", "tech_choice", "custom_tech_text", "slot_choice"],
    "jzm2": ["r0", "a0", "scale_str", "t0", "tech_choice", "custom_tech_text", "slot_choice"]
}

# ==================== 主应用程序类 ====================

class ToolingManagerApp:
    """工装绘图管理器主应用程序"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("工装绘图管理器 V1.1")
        self.root.geometry("1400x900")
        
        # 数据初始化
        self.calculator = None
        self.calculation_results = None
        self.current_tooling = 0
        self.tooling_params_list = [ToolingParameters() for _ in range(10)]
        self.presets: List[ParameterPreset] = []
        
        # AutoCAD相关
        self.acad = None
        self.doc = None
        
        # 配置目录
        self.config_dir = os.path.join(os.path.expanduser("~"), ".tooling_manager")
        os.makedirs(self.config_dir, exist_ok=True)
        self.presets_file = os.path.join(self.config_dir, "presets.json")
        
        # 加载预设
        self.load_presets()
        
        # 创建UI
        self.create_ui()
        
    def create_ui(self):
        """创建用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Notebook
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 第一个标签页：计算输入
        self.create_calculation_tab(notebook)
        
        # 第二个标签页：参数选择
        self.create_parameter_tab(notebook)
        
        # 第三个标签页：预设管理
        self.create_preset_tab(notebook)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def create_calculation_tab(self, notebook):
        """创建计算输入标签页"""
        frame = ttk.Frame(notebook, padding="20")
        notebook.add(frame, text="计算输入")
        
        # 标题
        title_frame = ttk.Frame(frame)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        ttk.Label(title_frame, text="待加工镜片参数", font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)
        ttk.Label(title_frame, text="输入待加工镜片的R值和口径", font=("Segoe UI", 10), foreground="gray").pack(side=tk.LEFT, padx=10)
        
        # 参数输入框架
        param_frame = ttk.LabelFrame(frame, text="镜片参数", padding="15")
        param_frame.pack(fill=tk.X, pady=10)
        
        # R值输入
        r_frame = ttk.Frame(param_frame)
        r_frame.pack(fill=tk.X, pady=5)
        ttk.Label(r_frame, text="镜片R值:", width=18, font=("Segoe UI", 11)).pack(side=tk.LEFT)
        self.r_var = tk.StringVar()
        ttk.Entry(r_frame, textvariable=self.r_var, font=("Segoe UI", 11), width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(r_frame, text="mm", font=("Segoe UI", 10), foreground="gray").pack(side=tk.LEFT)
        
        # 毛坯口径输入
        d_frame = ttk.Frame(param_frame)
        d_frame.pack(fill=tk.X, pady=5)
        ttk.Label(d_frame, text="毛坯口径:", width=18, font=("Segoe UI", 11)).pack(side=tk.LEFT)
        self.d_var = tk.StringVar()
        ttk.Entry(d_frame, textvariable=self.d_var, font=("Segoe UI", 11), width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(d_frame, text="mm", font=("Segoe UI", 10), foreground="gray").pack(side=tk.LEFT)
        
        # 其他计算参数
        calc_frame = ttk.LabelFrame(frame, text="计算参数（可选）", padding="15")
        calc_frame.pack(fill=tk.X, pady=10)
        
        # 聚氨酯厚度
        pu_frame = ttk.Frame(calc_frame)
        pu_frame.pack(fill=tk.X, pady=5)
        ttk.Label(pu_frame, text="聚氨酯厚度:", width=18).pack(side=tk.LEFT)
        self.pu_var = tk.StringVar(value="0.3")
        ttk.Entry(pu_frame, textvariable=self.pu_var, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(pu_frame, text="mm", foreground="gray").pack(side=tk.LEFT)
        
        # 金刚石丸片厚度
        dia_frame = ttk.Frame(calc_frame)
        dia_frame.pack(fill=tk.X, pady=5)
        ttk.Label(dia_frame, text="金刚石丸片厚度:", width=18).pack(side=tk.LEFT)
        self.dia_var = tk.StringVar(value="3")
        ttk.Entry(dia_frame, textvariable=self.dia_var, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(dia_frame, text="mm", foreground="gray").pack(side=tk.LEFT)
        
        # 弧长增量
        arc_frame = ttk.Frame(calc_frame)
        arc_frame.pack(fill=tk.X, pady=5)
        ttk.Label(arc_frame, text="弧长增量:", width=18).pack(side=tk.LEFT)
        self.arc_var = tk.StringVar(value="2")
        ttk.Entry(arc_frame, textvariable=self.arc_var, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(arc_frame, text="mm", foreground="gray").pack(side=tk.LEFT)
        
        # Excel文件路径
        excel_frame = ttk.LabelFrame(frame, text="Excel文件", padding="15")
        excel_frame.pack(fill=tk.X, pady=10)
        
        excel_path_frame = ttk.Frame(excel_frame)
        excel_path_frame.pack(fill=tk.X, pady=5)
        ttk.Label(excel_path_frame, text="文件路径:", width=18).pack(side=tk.LEFT)
        self.excel_var = tk.StringVar(value="口径常数.xlsx")
        ttk.Entry(excel_path_frame, textvariable=self.excel_var, width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(excel_path_frame, text="浏览...", command=self.browse_excel).pack(side=tk.LEFT)
        
        # 计算按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=20)
        ttk.Button(btn_frame, text="📊 计算工装参数", command=self.calculate_tooling, 
                   style="Accent.TButton", font=("Segoe UI", 12)).pack(side=tk.RIGHT)
        
        # 计算结果显示
        result_frame = ttk.LabelFrame(frame, text="计算结果", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.result_text = tk.Text(result_frame, height=18, font=("Consolas", 10))
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
    def create_parameter_tab(self, notebook):
        """创建参数选择标签页"""
        frame = ttk.Frame(notebook, padding="20")
        notebook.add(frame, text="参数选择")
        
        # 标题
        title_frame = ttk.Frame(frame)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        ttk.Label(title_frame, text="工装参数配置", font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)
        ttk.Label(title_frame, text="选择工装并配置参数", font=("Segoe UI", 10), foreground="gray").pack(side=tk.LEFT, padx=10)
        
        # 分割为左右两部分
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：工装列表和计算结果
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        # 右侧：参数编辑
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        
        # ============== 左侧内容 ==============
        ttk.Label(left_frame, text="工装列表", font=("Segoe UI", 12, "bold")).pack(pady=(0, 10))
        
        # 工装列表框
        self.tooling_listbox = tk.Listbox(left_frame, font=("Segoe UI", 11), height=12)
        self.tooling_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.tooling_listbox.bind("<<ListboxSelect>>", self.on_tooling_select)
        
        # 填充工装列表
        self.populate_tooling_list()
        
        # 计算结果选择
        ttk.Label(left_frame, text="从计算结果中选择", font=("Segoe UI", 11, "bold")).pack(pady=(15, 5))
        
        self.result_combo = ttk.Combobox(left_frame, state="readonly", font=("Segoe UI", 10))
        self.result_combo.pack(fill=tk.X, pady=5)
        
        # 应用结果按钮
        ttk.Button(left_frame, text="✅ 应用选中结果", command=self.apply_calc_result).pack(pady=10)
        
        # ============== 右侧内容 ==============
        ttk.Label(right_frame, text="工装参数编辑", font=("Segoe UI", 12, "bold")).pack(pady=(0, 10))
        
        # 创建滚动框架
        canvas = tk.Canvas(right_frame)
        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill=tk.BOTH, expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 在滚动框架中创建参数编辑区域
        self.create_param_editor(scroll_frame)
        
        # 底部按钮
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        ttk.Button(btn_frame, text="💾 保存为预设", command=self.save_as_preset).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🚀 执行绘图", command=self.execute_drawing, 
                   style="Accent.TButton", font=("Segoe UI", 11)).pack(side=tk.RIGHT, padx=5)
        
    def create_param_editor(self, parent):
        """创建参数编辑器"""
        self.param_vars = {}
        
        # 基本信息
        info_frame = ttk.LabelFrame(parent, text="基本信息", padding="10")
        info_frame.pack(fill=tk.X, pady=5)
        
        # 工装名称
        name_frame = ttk.Frame(info_frame)
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text="工装名称:", width=15).pack(side=tk.LEFT)
        self.param_vars["name"] = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.param_vars["name"], width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # LISP函数选择
        func_frame = ttk.Frame(info_frame)
        func_frame.pack(fill=tk.X, pady=5)
        ttk.Label(func_frame, text="LISP函数:", width=15).pack(side=tk.LEFT)
        self.param_vars["lisp_function"] = tk.StringVar()
        func_combo = ttk.Combobox(func_frame, textvariable=self.param_vars["lisp_function"], 
                                   state="readonly", width=27)
        func_combo['values'] = list(LISP_FUNCTIONS.keys())
        func_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        func_combo.bind("<<ComboboxSelected>>", self.on_function_select)
        
        # 几何参数
        geo_frame = ttk.LabelFrame(parent, text="几何参数", padding="10")
        geo_frame.pack(fill=tk.X, pady=5)
        
        # R值
        r0_frame = ttk.Frame(geo_frame)
        r0_frame.pack(fill=tk.X, pady=5)
        ttk.Label(r0_frame, text="曲率半径(r0):", width=15).pack(side=tk.LEFT)
        self.param_vars["r0"] = tk.StringVar()
        ttk.Entry(r0_frame, textvariable=self.param_vars["r0"], width=20).pack(side=tk.LEFT, padx=5)
        ttk.Label(r0_frame, text="mm", foreground="gray").pack(side=tk.LEFT)
        
        # 口径
        a0_frame = ttk.Frame(geo_frame)
        a0_frame.pack(fill=tk.X, pady=5)
        ttk.Label(a0_frame, text="口径(a0):", width=15).pack(side=tk.LEFT)
        self.param_vars["a0"] = tk.StringVar()
        ttk.Entry(a0_frame, textvariable=self.param_vars["a0"], width=20).pack(side=tk.LEFT, padx=5)
        ttk.Label(a0_frame, text="mm", foreground="gray").pack(side=tk.LEFT)
        
        # 边厚
        t0_frame = ttk.Frame(geo_frame)
        t0_frame.pack(fill=tk.X, pady=5)
        ttk.Label(t0_frame, text="边厚(t0):", width=15).pack(side=tk.LEFT)
        self.param_vars["t0"] = tk.StringVar()
        ttk.Entry(t0_frame, textvariable=self.param_vars["t0"], width=20).pack(side=tk.LEFT, padx=5)
        ttk.Label(t0_frame, text="mm", foreground="gray").pack(side=tk.LEFT)
        
        # 柄长
        b0_frame = ttk.Frame(geo_frame)
        b0_frame.pack(fill=tk.X, pady=5)
        ttk.Label(b0_frame, text="柄长(b0):", width=15).pack(side=tk.LEFT)
        self.param_vars["b0"] = tk.StringVar()
        ttk.Entry(b0_frame, textvariable=self.param_vars["b0"], width=20).pack(side=tk.LEFT, padx=5)
        ttk.Label(b0_frame, text="mm", foreground="gray").pack(side=tk.LEFT)
        
        # 工装参数
        tool_frame = ttk.LabelFrame(parent, text="工装参数", padding="10")
        tool_frame.pack(fill=tk.X, pady=5)
        
        # 工装类型
        tool_type_frame = ttk.Frame(tool_frame)
        tool_type_frame.pack(fill=tk.X, pady=5)
        ttk.Label(tool_type_frame, text="工装类型:", width=15).pack(side=tk.LEFT)
        self.param_vars["tool_type"] = tk.StringVar(value="1")
        self.tool_combo = ttk.Combobox(tool_type_frame, textvariable=self.param_vars["tool_type"], 
                                        state="readonly", width=30)
        self.tool_combo['values'] = [f"{v}: {t}" for v, t in TOOL_TYPES.get("xba", [])]
        self.tool_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 比例
        scale_frame = ttk.Frame(tool_frame)
        scale_frame.pack(fill=tk.X, pady=5)
        ttk.Label(scale_frame, text="比例:", width=15).pack(side=tk.LEFT)
        self.param_vars["scale_str"] = tk.StringVar(value="1:1")
        ttk.Entry(scale_frame, textvariable=self.param_vars["scale_str"], width=20).pack(side=tk.LEFT)
        
        # 开槽方式
        slot_frame = ttk.Frame(tool_frame)
        slot_frame.pack(fill=tk.X, pady=5)
        ttk.Label(slot_frame, text="开槽方式:", width=15).pack(side=tk.LEFT)
        self.param_vars["slot_choice"] = tk.IntVar(value=0)
        self.slot_combo = ttk.Combobox(slot_frame, textvariable=self.param_vars["slot_choice"], 
                                        state="readonly", width=30)
        self.slot_combo['values'] = [f"{v}: {t}" for v, t in SLOT_CHOICES]
        self.slot_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 技术要求
        tech_frame = ttk.LabelFrame(parent, text="技术要求", padding="10")
        tech_frame.pack(fill=tk.X, pady=5)
        
        # 技术要求选择
        tech_choice_frame = ttk.Frame(tech_frame)
        tech_choice_frame.pack(fill=tk.X, pady=5)
        ttk.Label(tech_choice_frame, text="技术要求:", width=15).pack(side=tk.LEFT)
        self.param_vars["tech_choice"] = tk.IntVar(value=1)
        for val, text in TECH_CHOICES:
            ttk.Radiobutton(tech_choice_frame, text=text, variable=self.param_vars["tech_choice"], 
                            value=int(val), command=self.on_tech_select).pack(side=tk.LEFT, padx=10)
        
        # 自定义技术要求（初始隐藏）
        self.custom_tech_frame = ttk.Frame(tech_frame)
        self.custom_tech_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.custom_tech_frame, text="自定义技术要求:", width=15).pack(side=tk.LEFT)
        self.param_vars["custom_tech_text"] = tk.StringVar()
        self.custom_tech_entry = ttk.Entry(self.custom_tech_frame, textvariable=self.param_vars["custom_tech_text"], width=50)
        self.custom_tech_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.custom_tech_frame.pack_forget()  # 初始隐藏
        
    def create_preset_tab(self, notebook):
        """创建预设管理标签页"""
        frame = ttk.Frame(notebook, padding="20")
        notebook.add(frame, text="预设管理")
        
        # 标题
        title_frame = ttk.Frame(frame)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        ttk.Label(title_frame, text="参数预设管理", font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)
        ttk.Label(title_frame, text="保存和加载参数组合", font=("Segoe UI", 10), foreground="gray").pack(side=tk.LEFT, padx=10)
        
        # 预设列表
        list_frame = ttk.LabelFrame(frame, text="已保存的预设", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.preset_listbox = tk.Listbox(list_frame, font=("Segoe UI", 11), height=15)
        self.preset_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 按钮框架
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(btn_frame, text="📂 加载预设", command=self.load_preset).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ 删除预设", command=self.delete_preset).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 刷新列表", command=self.refresh_preset_list).pack(side=tk.LEFT, padx=5)
        
        # 填充预设列表
        self.refresh_preset_list()
        
    # ==================== 事件处理函数 ====================
    
    def browse_excel(self):
        """浏览Excel文件"""
        filename = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=[("Excel文件", "*.xlsx *.xls"), ("所有文件", "*.*")]
        )
        if filename:
            self.excel_var.set(filename)
            
    def calculate_tooling(self):
        """计算工装参数"""
        if not HAS_CALCULATOR:
            messagebox.showerror("错误", "无法导入计算模块！")
            return
            
        try:
            R = float(self.r_var.get())
            blank_D = float(self.d_var.get())
            pu_thickness = float(self.pu_var.get())
            dia_thickness = float(self.dia_var.get())
            delta_arc = float(self.arc_var.get())
            excel_path = self.excel_var.get()
            
            if not os.path.exists(excel_path):
                excel_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), excel_path)
            
            self.status_var.set("正在计算...")
            self.root.update()
            
            # 创建计算器实例
            self.calculator = SwingMachineToolingCalculator(
                R=R,
                blank_D=blank_D,
                polyurethane_thickness=pu_thickness,
                diamond_pellet_thickness=dia_thickness,
                delta_arc=delta_arc
            )
            
            # 执行计算
            self.calculation_results = self.calculator.calculate_all(excel_path)
            
            # 显示结果
            self.result_text.delete(1.0, tk.END)
            for key, value in self.calculation_results.items():
                self.result_text.insert(tk.END, f"{key}: {value}\n")
                
            # 更新结果选择下拉框
            self.update_result_combo()
            
            self.status_var.set("计算完成！")
            messagebox.showinfo("成功", "工装参数计算完成！")
            
        except ValueError as e:
            messagebox.showerror("错误", f"输入参数无效：{e}")
        except Exception as e:
            messagebox.showerror("错误", f"计算失败：{e}")
            
    def update_result_combo(self):
        """更新结果选择下拉框"""
        if not self.calculation_results:
            return
            
        results = []
        # 添加各种工装的R值和口径
        result_map = {
            "下摆机精磨基模": ("下摆机精磨基模R值", "下摆机精磨基模口径"),
            "下摆机抛光基模": ("下摆机抛光基模R值", "下摆机抛光基模口径"),
            "高速抛光修盘基模": ("高速抛光修盘基模R值", "高速抛光修盘基模口径"),
            "基准模压聚氨酯": ("镜片R值", "基准模压聚氨酯口径"),
            "基准模改丸片": ("镜片R值", "基准模改丸片口径"),
            "高速抛光基模修盘": ("高速抛光基模修盘R值", "高速抛光基模修盘口径")
        }
        
        for name, (r_key, d_key) in result_map.items():
            if r_key in self.calculation_results and d_key in self.calculation_results:
                r_val = self.calculation_results[r_key]
                d_val = self.calculation_results[d_key]
                results.append(f"{name} - R={r_val}, D={d_val}")
                
        self.result_combo['values'] = results
        
    def populate_tooling_list(self):
        """填充工装列表"""
        tooling_names = [
            "1. 下摆机精磨基模",
            "2. 下摆机抛光基模",
            "3. 高速抛光修盘基模",
            "4. 基准模压聚氨酯",
            "5. 基准模改丸片",
            "6. 高速抛光基模修盘",
            "7. 短尾凹模",
            "8. 短尾凸模",
            "9. 小锥度凹模",
            "10. 小锥度凸模"
        ]
        
        self.tooling_listbox.delete(0, tk.END)
        for name in tooling_names:
            self.tooling_listbox.insert(tk.END, name)
            
    def on_tooling_select(self, event):
        """工装选择事件"""
        selection = self.tooling_listbox.curselection()
        if not selection:
            return
            
        index = selection[0]
        self.current_tooling = index
        
        # 加载当前工装的参数
        params = self.tooling_params_list[index]
        for key, var in self.param_vars.items():
            if hasattr(params, key):
                value = getattr(params, key)
                if isinstance(var, tk.StringVar):
                    var.set(str(value) if value is not None else "")
                elif isinstance(var, tk.IntVar):
                    var.set(int(value) if value is not None else 0)
                    
        # 更新工装类型选项
        self.update_tool_type_options()
        
    def on_function_select(self, event):
        """函数选择事件"""
        func_name = self.param_vars["lisp_function"].get()
        if func_name in FUNCTION_PARAMS:
            self.update_tool_type_options()
            
    def update_tool_type_options(self):
        """更新工装类型选项"""
        func_name = self.param_vars["lisp_function"].get()
        if func_name in TOOL_TYPES:
            self.tool_combo['values'] = [f"{v}: {t}" for v, t in TOOL_TYPES[func_name]]
        else:
            self.tool_combo['values'] = [f"{v}: {t}" for v, t in TOOL_TYPES.get("xba", [])]
            
    def on_result_select(self, event):
        """结果选择事件"""
        pass
        
    def apply_calc_result(self):
        """应用计算结果"""
        selection = self.result_combo.get()
        if not selection or not self.calculation_results:
            return
            
        # 解析选择的结果
        # 格式: "名称 - R=xxx, D=xxx"
        try:
            parts = selection.split(" - ")
            if len(parts) != 2:
                return
                
            rd_part = parts[1]
            rd_items = rd_part.split(", ")
            
            r_val = None
            d_val = None
            
            for item in rd_items:
                if item.startswith("R="):
                    r_val = item[2:]
                elif item.startswith("D="):
                    d_val = item[2:]
                    
            if r_val:
                self.param_vars["r0"].set(r_val)
            if d_val:
                self.param_vars["a0"].set(d_val)
                
        except Exception as e:
            print(f"应用结果失败: {e}")
            
    def on_tech_select(self):
        """技术要求选择事件"""
        tech_choice = self.param_vars["tech_choice"].get()
        if tech_choice == 2:
            self.custom_tech_frame.pack(fill=tk.X, pady=5)
        else:
            self.custom_tech_frame.pack_forget()
            
    def save_current_params(self):
        """保存当前工装参数"""
        params = ToolingParameters()
        for key, var in self.param_vars.items():
            if hasattr(params, key):
                value = var.get()
                if isinstance(var, tk.StringVar):
                    setattr(params, key, value)
                elif isinstance(var, tk.IntVar):
                    setattr(params, key, value)
                    
        self.tooling_params_list[self.current_tooling] = params
        
    def save_as_preset(self):
        """保存为预设"""
        # 先保存当前参数
        self.save_current_params()
        
        # 询问预设名称
        name = simpledialog.askstring("保存预设", "请输入预设名称:")
        if not name:
            return
            
        # 创建预设
        preset = ParameterPreset(
            preset_name=name,
            toolings=list(self.tooling_params_list)
        )
        
        self.presets.append(preset)
        self.save_presets()
        self.refresh_preset_list()
        
        messagebox.showinfo("成功", f"预设 '{name}' 保存成功！")
        
    def load_preset(self):
        """加载预设"""
        selection = self.preset_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个预设！")
            return
            
        index = selection[0]
        if index >= len(self.presets):
            return
            
        preset = self.presets[index]
        self.tooling_params_list = list(preset.toolings)
        
        # 刷新工装列表
        if self.tooling_listbox.size() > 0:
            self.tooling_listbox.selection_set(0)
            self.on_tooling_select(None)
            
        messagebox.showinfo("成功", f"预设 '{preset.preset_name}' 加载成功！")
        
    def delete_preset(self):
        """删除预设"""
        selection = self.preset_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个预设！")
            return
            
        index = selection[0]
        if index >= len(self.presets):
            return
            
        preset = self.presets[index]
        if messagebox.askyesno("确认", f"确定要删除预设 '{preset.preset_name}' 吗？"):
            del self.presets[index]
            self.save_presets()
            self.refresh_preset_list()
            
    def refresh_preset_list(self):
        """刷新预设列表"""
        self.preset_listbox.delete(0, tk.END)
        for preset in self.presets:
            self.preset_listbox.insert(tk.END, preset.preset_name)
            
    def save_presets(self):
        """保存预设到文件"""
        try:
            data = []
            for preset in self.presets:
                preset_data = {
                    "preset_name": preset.preset_name,
                    "toolings": [asdict(t) for t in preset.toolings]
                }
                data.append(preset_data)
                
            with open(self.presets_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存预设失败: {e}")
            
    def load_presets(self):
        """从文件加载预设"""
        try:
            if os.path.exists(self.presets_file):
                with open(self.presets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                self.presets = []
                for preset_data in data:
                    toolings = []
                    for t_data in preset_data.get("toolings", []):
                        t = ToolingParameters()
                        for key, value in t_data.items():
                            if hasattr(t, key):
                                setattr(t, key, value)
                        toolings.append(t)
                        
                    preset = ParameterPreset(
                        preset_name=preset_data["preset_name"],
                        toolings=toolings
                    )
                    self.presets.append(preset)
                    
        except Exception as e:
            print(f"加载预设失败: {e}")
            
    def execute_drawing(self):
        """执行绘图"""
        if not HAS_AUTOCAD:
            messagebox.showerror("错误", "无法导入AutoCAD模块！")
            return
            
        # 保存当前参数
        self.save_current_params()
        
        try:
            # 连接AutoCAD
            self.status_var.set("正在连接AutoCAD...")
            self.root.update()
            
            if not self.acad:
                self.acad = find_autocad()
                self.acad.Visible = True
                
            self.doc = self.acad.ActiveDocument
            if not self.doc:
                messagebox.showwarning("警告", "请先在AutoCAD中新建或打开图形！")
                return
                
            # 获取当前工装参数
            params = self.tooling_params_list[self.current_tooling]
            func_name = params.lisp_function
            
            if not func_name or func_name not in LISP_FUNCTIONS:
                messagebox.showwarning("警告", "请先选择要执行的LISP函数！")
                return
                
            lisp_file, func = LISP_FUNCTIONS[func_name]
            lisp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LSP", lisp_file)
            
            if not os.path.exists(lisp_path):
                messagebox.showerror("错误", f"找不到LISP文件: {lisp_path}")
                return
                
            # 加载LISP文件
            self.status_var.set("正在加载LISP文件...")
            self.root.update()
            
            # 解析LISP文件
            functions = LispParser.parse_file(lisp_path)
            
            # 加载LISP文件
            if not load_single_lisp_file(self.doc, lisp_path, functions):
                messagebox.showerror("错误", "LISP文件加载失败！")
                return
                
            # 构建参数
            args = []
            param_names = FUNCTION_PARAMS.get(func_name, [])
            
            for param_name in param_names:
                value = getattr(params, param_name, None)
                if value is None:
                    continue
                    
                if param_name in ["tech_choice", "slot_choice"]:
                    args.append(str(value))
                elif param_name in ["tool_type", "custom_tech_text", "scale_str"]:
                    args.append(f'"{value}"')
                else:
                    # 数值参数
                    try:
                        float_val = float(value)
                        args.append(str(float_val))
                    except:
                        args.append(f'"{value}"')
                        
            # 执行LISP函数
            self.status_var.set("正在执行绘图...")
            self.root.update()
            
            if run_lisp(self.acad, func, args, True):
                self.status_var.set("绘图执行完成！")
                messagebox.showinfo("成功", "绘图执行完成！")
            else:
                self.status_var.set("绘图执行失败！")
                messagebox.showerror("错误", "绘图执行失败！")
                
        except Exception as e:
            self.status_var.set(f"错误: {e}")
            messagebox.showerror("错误", f"执行失败：{e}")
            
def main():
    """主函数"""
    root = tk.Tk()
    app = ToolingManagerApp(root)
    root.mainloop()
    
if __name__ == "__main__":
    main()
