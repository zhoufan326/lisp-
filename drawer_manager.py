#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""套装绘制管理器"""
import os
from acad_doc_manager import find_autocad, apply_template, configure_print_settings
from lisp_loader import load_single_lisp_file
from lisp_executor import run_lisp
from Tool_calculation import SwingMachineToolingCalculator
from dwg_saver import get_save_path_for_material, get_last_save_directory
from retry_decorator import retry_on_autocad_error

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
        
        # 检查参数有效性
        if radius <= 0 or blank_D <= 0:
            print("❌ 请输入有效参数")
            return
         
        # 获取保存路径
        material_code = params.get("material_code", "")
        save_path = get_save_path_for_material(material_code)
        
        # 确保保存目录存在
        os.makedirs(save_path, exist_ok=True)
        
        # 计算工装参数
        excel_path = os.path.join(self.project_dir, "口径常数.xlsx")
        calculator = SwingMachineToolingCalculator(radius, blank_D)
        results = calculator.calculate_all(excel_path)
        
        # 步骤 1: 执行下摆凹/凸.lsp
        if radius > 0:
            # 抛光模基模
            self._execute_lisp("XBA_下摆凹.lsp", "xba", {
                "r0": abs(results["下摆机精磨基模R值"]),
                "a0": results["下摆机精磨基模口径"],
                "b0": 25,
                "t0": 2,
                "save_path": save_path
            })
            
            # 精磨模基模
            self._execute_lisp("XBA_下摆凹.lsp", "xba", {
                "r0": abs(results["下摆机抛光基模R值"]),
                "a0": results["下摆机抛光基模口径"],
                "b0": 25,
                "t0": 2,
                "save_path": save_path
            })
        else:
            # 抛光模基模
            self._execute_lisp("XBT_下摆凸.lsp", "xbt", {
                "r0": abs(results["下摆机精磨基模R值"]),
                "a0": results["下摆机精磨基模口径"],
                "b0": 25 if -50<=radius < 0 else 20,
                "t0": 2,
                "save_path": save_path
            })
            
            # 精磨模基模
            self._execute_lisp("XBT_下摆凸.lsp", "xbt", {
                "r0": abs(results["下摆机抛光基模R值"]),
                "a0": results["下摆机抛光基模口径"],
                "b0": 25 if -50<=radius < 0 else 20,
                "t0": 2,
                "save_path": save_path
            })
        
        # 步骤 2: 执行 JZM 小锥度
        self._execute_lisp("JZM_锥度_基准模.lsp", "jzm", {
            "r0": abs(radius),
            "a0": results["基准模改丸片口径"],
            "save_path": save_path
        })
        
        # 步骤 3: 执行小锥度
        # 抛光模基模修盘
        # 抛光模基模修盘
        self._execute_lisp("XZA_小锥度凹.lsp", "xza", {
            "r0": abs(-results["下摆机抛光基模R值"]),
            "a0": results["下摆机抛光基模口径"],
            "save_path": save_path
        })
        
        # 抛光模修盘基模
        # 精磨模修盘基模
        self._execute_lisp("XZA_小锥度凹.lsp", "xza", {
            "r0": abs(results["高速抛光修盘基模R值"]),
            "a0": results["高速抛光修盘基模口径"],
            "save_path": save_path
        })
        
        print(f"绘制下摆套装完成，参数: {params}")
        return True
    
    @retry_on_autocad_error(max_attempts=3, initial_delay=0.5)
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
        
        # 自动保存文档
        if success:
            try:
                # 获取保存路径
                save_path = params.get("save_path", "")
                
                # 构建文件名
                filename = f"{func_name}_{abs(float(params.get('r0', 0)))}.dwg"
                full_path = os.path.join(save_path, filename)
                
                # 保存文档
                doc.SaveAs(full_path)
                print(f"✓ 文档已自动保存到: {full_path}")
            except Exception as e:
                print(f"⚠ 自动保存失败: {e}")
        
        # 保持文档打开，不关闭
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
        """构建 LISP 函数参数"""
        def abs_v(k): return str(abs(float(params.get(k, 0))))
        
        args_map = {
            "xba": ["r0", "a0", "t0", "b0", lambda p: f'"{p.get("tool_type", "1")}"', 
                      lambda p: p.get("tech_choice", "1"), lambda p: f'"{p.get("custom_tech_text", "")}"',
                      lambda p: f'"{p.get("save_path", "")}"'],
            "xbt": ["r0", "a0", "t0", "b0", lambda p: f'"{p.get("tool_type", "1")}"', 
                      lambda p: p.get("tech_choice", "1"), lambda p: f'"{p.get("custom_tech_text", "")}"',
                      lambda p: f'"{p.get("save_path", "")}"'],
            "mja": ["r0", "a0", "t0", lambda p: f'"{p.get("save_path", "")}"'],
            "mjt": ["r0", "a0", "t0", lambda p: f'"{p.get("save_path", "")}"'],
            "dwa": ["r0", "a0", "t0", lambda p: f'"{p.get("save_path", "")}"'],
            "dwt": ["r0", "a0", "t0", lambda p: f'"{p.get("save_path", "")}"'],
            "jzm": ["r0", "a0", "t0", lambda p: f'"{p.get("scale_str", "1:1")}"', 
                      lambda p: p.get("tech_choice", "1"), lambda p: f'"{p.get("custom_tech_text", "")}"', 
                      lambda p: p.get("slot_choice", "0"), lambda p: f'"{p.get("save_path", "")}"'],
            "xza": ["r0", "a0", "t0", lambda p: f'"{p.get("save_path", "")}"'],
            "xzt": ["r0", "a0", "t0", lambda p: f'"{p.get("save_path", "")}"']
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
        
        # 检查参数有效性
        if radius <= 0 or blank_D <= 0:
            print("❌ 请输入有效参数")
            return
         
        # 获取保存路径
        material_code = params.get("material_code", "")
        save_path = get_save_path_for_material(material_code)
        
        # 确保保存目录存在
        os.makedirs(save_path, exist_ok=True)
        
        # 计算工装参数
        excel_path = os.path.join(self.project_dir, "口径常数.xlsx")
        calculator = SwingMachineToolingCalculator(radius, blank_D)
        results = calculator.calculate_all(excel_path)
        
        # 步骤 1: 执行迈均凹/凸.lsp
        if radius > 0:
            # 迈均凹.lsp
            self._execute_lisp("MJA_迈均凹.lsp", "mja", {
                "r0": abs(results["下摆机精磨基模 R 值"]),
                "a0": results["下摆机精磨基模口径"],
                "save_path": save_path
            })
        else:
            # 迈均凸.lsp
            self._execute_lisp("MJT_迈均凸.lsp", "mjt", {
                "r0": abs(results["下摆机精磨基模 R 值"]),
                "a0": results["下摆机精磨基模口径"],
                "save_path": save_path
            })
        
        # 步骤 2: 执行 JZM 短尾
        self._execute_lisp("JZM_短尾_基准模.lsp", "jzm", {
            "r0": abs(radius),
            "a0": results["基准模改丸片口径"],
            "save_path": save_path
        })
        
        # 步骤 3: 执行短尾凸/凹.lsp
        if radius > 0:
            # 短尾凸.lsp - 抛光模基模修盘
            self._execute_lisp("DWT_短尾凸.lsp", "dwt", {
                "r0": abs(-results["下摆机抛光基模 R 值"]),
                "a0": results["下摆机抛光基模口径"],
                "save_path": save_path
            })
            
            # 短尾凸.lsp - 抛光模修盘基模
            self._execute_lisp("DWT_短尾凸.lsp", "dwt", {
                "r0": abs(results["高速抛光修盘基模 R 值"]),
                "a0": results["高速抛光修盘基模口径"],
                "save_path": save_path
            })
        else:
            # 短尾凹.lsp - 抛光模基模修盘
            self._execute_lisp("DWA_短尾凹.lsp", "dwa", {
                "r0": abs(-results["下摆机抛光基模R值"]),
                "a0": results["下摆机抛光基模口径"],
                "save_path": save_path
            })
            
            # 短尾凹.lsp - 抛光模修盘基模
            self._execute_lisp("DWA_短尾凹.lsp", "dwa", {
                "r0": abs(results["高速抛光修盘基模 R 值"]),
                "a0": results["高速抛光修盘基模口径"],
                "save_path": save_path
            })
        
        print(f"绘制迈均套装完成，参数: {params}")
        return True
    
    def draw_di_pao(self, params=None):
        """绘制低抛套装"""
        if params is None:
            params = {}
        
        # 获取保存路径
        material_code = params.get("material_code", "")
        save_path = get_save_path_for_material(material_code)
        
        # 确保保存目录存在
        os.makedirs(save_path, exist_ok=True)
        
        # 初始化CAD连接（只初始化一次）
        if not self.acad:
            self._init_cad()
        
        # 新建图形文档
        doc = apply_template(self.acad, self.template_path, None)
        doc.Activate()
        
        # 加载LISP文件
        self._load_lisp_files("DWA_短尾凹.lsp", "DWT_短尾凸.lsp")
        
        # 调用 LISP 函数绘制
        func_name = "dwa" if params.get("type", "凹") == "凹" else "dwt"
        args = self._build_args(func_name, params)
        success = run_lisp(self.acad, func_name, args, True)
        
        # 自动保存文档
        if success:
            try:
                # 构建文件名
                filename = f"{func_name}_{abs(float(params.get('r0', 0)))}.dwg"
                full_path = os.path.join(save_path, filename)
                
                # 保存文档
                doc.SaveAs(full_path)
                print(f"✓ 文档已自动保存到: {full_path}")
            except Exception as e:
                print(f"⚠ 自动保存失败: {e}")
        
        # 保持文档打开，不关闭
        print(f"绘制低抛套装，参数: {params}")
        return success