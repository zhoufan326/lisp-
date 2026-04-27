#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""套装绘制管理器"""
import os
from acad_doc_manager import find_autocad, apply_template, configure_print_settings
from lisp_loader import load_single_lisp_file
from lisp_executor import run_lisp
from Tool_calculation import SwingMachineToolingCalculator

class DrawerManager:
    def __init__(self, acad):
        self.acad = acad
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.template_path = os.path.join(self.project_dir, "LSP", "LISP图样.dwt")
        self.lsp_dir = os.path.join(self.project_dir, "LSP")
    
    def draw_xia_bai(self, params=None):
        """绘制下摆套装"""
        if params is None:
            params = {}
        
        # 获取参数
        radius = params.get("radius", 0)
        blank_D = params.get("blank_D", 0)
        
        # 计算工装参数
        excel_path = os.path.join(self.project_dir, "口径常数.xlsx")
        calculator = SwingMachineToolingCalculator(radius, blank_D)
        results = calculator.calculate_all(excel_path)
        
        # 步骤1: 执行下摆凹/凸.lsp
        if radius > 0:
            # 抛光模基模
            self._execute_lisp("XBA_下摆凹.lsp", "c:xba", {
                "r0": abs(results["下摆机精磨基模R值"]),
                "a0": results["下摆机精磨基模口径"],
                "b0": 25,
                "t0": 2
            })
            
            # 精磨模基模
            self._execute_lisp("XBA_下摆凹.lsp", "c:xba", {
                "r0": abs(results["下摆机抛光基模R值"]),
                "a0": results["下摆机抛光基模口径"],
                "b0": 25,
                "t0": 2
            })
        else:
            # 抛光模基模
            self._execute_lisp("XBT_下摆凸.lsp", "c:xbt", {
                "r0": abs(results["下摆机精磨基模R值"]),
                "a0": results["下摆机精磨基模口径"],
                "b0": 25,
                "t0": 2
            })
            
            # 精磨模基模
            self._execute_lisp("XBT_下摆凸.lsp", "c:xbt", {
                "r0": abs(results["下摆机抛光基模R值"]),
                "a0": results["下摆机抛光基模口径"],
                "b0": 25,
                "t0": 2
            })
        
        # 步骤2: 执行JZM小锥度
        self._execute_lisp("JZM_锥度_基准模.lsp", "c:jzm", {
            "r0": abs(radius),
            "a0": results["基准模改丸片口径"]
        })
        
        # 步骤3: 执行小锥度
        # 抛光模基模修盘
        self._execute_lisp("XZA_小锥度凹.lsp", "c:xza", {
            "r0": abs(-results["下摆机抛光基模R值"]),
            "a0": results["下摆机抛光基模口径"]
        })
        
        # 抛光模修盘基模
        self._execute_lisp("XZA_小锥度凹.lsp", "c:xza", {
            "r0": abs(results["高速抛光修盘基模R值"]),
            "a0": results["高速抛光修盘基模口径"]
        })
        
        print(f"绘制下摆套装完成，参数: {params}")
        return True
    
    def _execute_lisp(self, lsp_file, func_name, params):
        """执行单个LISP文件"""
        # 初始化CAD连接（只初始化一次）
        if not self.acad:
            self._init_cad()
        
        # 新建图形文档
        doc = apply_template(self.acad, self.template_path, None)
        doc.Activate()
        
        # 加载LISP文件
        self._load_lisp_files(lsp_file)
        
        # 构建参数
        args = self._build_args(func_name, params)
        success = run_lisp(self.acad, func_name, args, True)
        
        # 关闭图形文档（释放资源）
        doc.Close()
        
        return success
    
    def _init_cad(self):
        """初始化CAD连接"""
        if not self.acad:
            self.acad = find_autocad()
            self.acad.Visible = True
        return True
    
    def _load_lisp_files(self, *filenames):
        """加载LISP文件"""
        doc = self.acad.ActiveDocument
        for filename in filenames:
            lsp_path = os.path.join(self.lsp_dir, filename)
            if os.path.exists(lsp_path):
                load_single_lisp_file(doc, lsp_path, None)
                print(f"✓ 已加载 LISP 文件: {filename}")
    
    def _build_args(self, func_name, params):
        """构建LISP函数参数"""
        def abs_v(k): return str(abs(float(params.get(k, 0))))
        
        args_map = {
            "c:xba": ["r0", "a0", "t0", "b0", lambda p: f'"{p.get("tool_type", "1")}"', 
                      lambda p: p.get("tech_choice", "1"), lambda p: f'"{p.get("custom_tech_text", "")}"',
                      lambda p: f'"{p.get("material_code", "")}"'],
            "c:xbt": ["r0", "a0", "t0", "b0", lambda p: f'"{p.get("tool_type", "1")}"', 
                      lambda p: p.get("tech_choice", "1"), lambda p: f'"{p.get("custom_tech_text", "")}"',
                      lambda p: f'"{p.get("material_code", "")}"'],
            "c:mja": ["r0", "a0", "t0", lambda p: f'"{p.get("material_code", "")}"'],
            "c:mjt": ["r0", "a0", "t0", lambda p: f'"{p.get("material_code", "")}"'],
            "c:dwa": ["r0", "a0", "t0", lambda p: f'"{p.get("tool_type", "1")}"',
                      lambda p: f'"{p.get("material_code", "")}"'],
            "c:dwt": ["r0", "a0", "t0", lambda p: f'"{p.get("tool_type", "1")}"',
                      lambda p: f'"{p.get("material_code", "")}"'],
            "c:jzm": ["r0", "a0", "t0", lambda p: f'"{p.get("scale_str", "1:1")}"', 
                      lambda p: p.get("tech_choice", "1"), lambda p: f'"{p.get("custom_tech_text", "")}"', 
                      lambda p: p.get("slot_choice", "0"), lambda p: f'"{p.get("material_code", "")}"'],
            "c:xza": ["r0", "a0", "t0", lambda p: f'"{p.get("tool_type", "1")}"',
                      lambda p: f'"{p.get("material_code", "")}"'],
            "c:xzt": ["r0", "a0", "t0", lambda p: f'"{p.get("tool_type", "1")}"',
                      lambda p: f'"{p.get("material_code", "")}"']
        }
        
        args = args_map.get(func_name, [])
        return [abs_v(k) if isinstance(k, str) else k(params) for k in args]
    
    def draw_mai_jun(self, params=None):
        """绘制迈均套装"""
        if params is None:
            params = {}
        
        # 获取参数
        radius = params.get("radius", 0)
        blank_D = params.get("blank_D", 0)
        
        # 计算工装参数
        excel_path = os.path.join(self.project_dir, "口径常数.xlsx")
        calculator = SwingMachineToolingCalculator(radius, blank_D)
        results = calculator.calculate_all(excel_path)
        
        # 步骤1: 执行迈均凹/凸.lsp
        if radius > 0:
            # 迈均凹.lsp
            self._execute_lisp("MJA_迈均凹.lsp", "c:mja", {
                "r0": abs(results["下摆机精磨基模R值"]),
                "a0": results["下摆机精磨基模口径"]
            })
        else:
            # 迈均凸.lsp
            self._execute_lisp("MJT_迈均凸.lsp", "c:mjt", {
                "r0": abs(results["下摆机精磨基模R值"]),
                "a0": results["下摆机精磨基模口径"]
            })
        
        # 步骤2: 执行JZM短尾
        self._execute_lisp("JZM_短尾_基准模.lsp", "c:jzm", {
            "r0": abs(radius),
            "a0": results["基准模改丸片口径"]
        })
        
        # 步骤3: 执行短尾凸/凹.lsp
        if radius > 0:
            # 短尾凸.lsp - 抛光模基模修盘
            self._execute_lisp("DWT_短尾凸.lsp", "c:dwt", {
                "r0": abs(-results["下摆机抛光基模R值"]),
                "a0": results["下摆机抛光基模口径"]
            })
            
            # 短尾凸.lsp - 抛光模修盘基模
            self._execute_lisp("DWT_短尾凸.lsp", "c:dwt", {
                "r0": abs(results["高速抛光修盘基模R值"]),
                "a0": results["高速抛光修盘基模口径"]
            })
        else:
            # 短尾凹.lsp - 抛光模基模修盘
            self._execute_lisp("DWA_短尾凹.lsp", "c:dwa", {
                "r0": abs(-results["下摆机抛光基模R值"]),
                "a0": results["下摆机抛光基模口径"]
            })
            
            # 短尾凹.lsp - 抛光模修盘基模
            self._execute_lisp("DWA_短尾凹.lsp", "c:dwa", {
                "r0": abs(results["高速抛光修盘基模R值"]),
                "a0": results["高速抛光修盘基模口径"]
            })
        
        print(f"绘制迈均套装完成，参数: {params}")
        return True
    
    def draw_di_pao(self, params=None):
        """绘制低抛套装"""
        if params is None:
            params = {}
        
        # 初始化CAD连接（只初始化一次）
        if not self.acad:
            self._init_cad()
        
        # 新建图形文档
        doc = apply_template(self.acad, self.template_path, None)
        doc.Activate()
        
        # 加载LISP文件
        self._load_lisp_files("DWA_短尾凹.lsp", "DWT_短尾凸.lsp")
        
        # 调用LISP函数绘制
        func_name = "c:dwa" if params.get("type", "凹") == "凹" else "c:dwt"
        args = self._build_args(func_name, params)
        success = run_lisp(self.acad, func_name, args, True)
        
        # 关闭图形文档（释放资源）
        doc.Close()
        
        print(f"绘制低抛套装，参数: {params}")
        return success