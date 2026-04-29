#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""套装绘制管理器"""
import os
from typing import Literal
from acad_doc_manager import find_autocad, apply_template
from lisp_loader import load_single_lisp_file
from lisp_executor import run_lisp
from Tool_calculation import SwingMachineToolingCalculator
from retry_decorator import retry_on_autocad_error
from dwg_saver import select_save_directory

class DrawerManager:
    def __init__(self, acad):
        self.acad = acad
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.template_path = os.path.join(self.project_dir, "LSP", "LISP图样.dwt")
        self.lsp_dir = os.path.join(self.project_dir, "LSP")

    # ==================== 绘制流程 ====================

    def draw_xia_bai(self, params=None):
        """绘制下摆套装"""
        if params is None:
            params = {}

        radius = params.get("radius", 0)
        blank_D = params.get("blank_D", 0)

        if radius <= 0 or blank_D <= 0:
            print("❌ 请输入有效参数")
            return

        save_path = self._resolve_save_path()
        if not save_path:
            return False

        results = SwingMachineToolingCalculator(radius, blank_D).calculate_all(
            os.path.join(self.project_dir, "口径常数.xlsx"))

        jm_r = abs(results["下摆机精磨基模R值"])
        jm_a = results["下摆机精磨基模口径"]
        pg_r = abs(results["下摆机抛光基模R值"])
        pg_a = results["下摆机抛光基模口径"]
        gs_r = abs(results["高速抛光修盘基模R值"])
        gs_a = results["高速抛光修盘基模口径"]
        jz_a = results["基准模改丸片口径"]

        is_concave = radius > 0
        xb_file: Literal['XBA_下摆凹.lsp', 'XBT_下摆凸.lsp'] = "XBA_下摆凹.lsp" if is_concave else "XBT_下摆凸.lsp"
        xb_func: Literal['xba', 'xbt'] = "xba" if is_concave else "xbt"
        b0: Literal[20, 25] = 25 if is_concave or -50 <= radius < 0 else 20
        xzt_lsp: Literal['XZT_小锥度凸.lsp', 'XZA_小锥度凹.lsp'] = "XZT_小锥度凸.lsp" if is_concave else "XZA_小锥度凹.lsp"
        xzt_func: Literal['xzt', 'xza'] = "xzt" if is_concave else "xza"

        for step_name, lsp, func, step_params in [
           # ("下摆-精磨模基模",     xb_file,   xb_func, {"r0": jm_r, "a0": jm_a, "b0": b0, "t0": 2, "tool_type":2, "save_path": save_path}),
           # ("下摆-抛光模基模",    xb_file,   xb_func, {"r0": pg_r, "a0": pg_a, "b0": b0, "t0": 2, "tool_type":1, "save_path": save_path}),
           
            ("下摆-JZM小锥度",     "JZM_锥度_基准模.lsp", "jzm2", {"r0": abs(radius), "a0": jz_a, "save_path": save_path}),
            ("高速抛光模基模修盘",  xzt_lsp,    xzt_func, {"r0": pg_r, "a0": pg_a, "tool_type":1, "save_path": save_path}),
            ("高速抛光模修盘基模",  xzt_lsp,    xzt_func, {"r0": gs_r, "a0": gs_a, "tool_type":2, "save_path": save_path}),
        ]:
            if not self._execute_lisp(step_name, lsp, func, step_params):
                return False

        print(f"绘制下摆套装完成，参数: {params}")
        return True

    def draw_mai_jun(self, params=None):
        """绘制迈均套装"""
        if params is None:
            params = {}

        radius = params.get("radius", 0)
        blank_D = params.get("blank_D", 0)

        if radius <= 0 or blank_D <= 0:
            print("❌ 请输入有效参数")
            return

        save_path = self._resolve_save_path()
        if not save_path:
            return False

        results = SwingMachineToolingCalculator(radius, blank_D).calculate_all(
            os.path.join(self.project_dir, "口径常数.xlsx"))

        jm_r = abs(results["下摆机精磨基模R值"])
        jm_a = results["下摆机精磨基模口径"]
        pg_r = abs(results["下摆机抛光基模R值"])
        pg_a = results["下摆机抛光基模口径"]
        gs_r = abs(results["高速抛光修盘基模R值"])
        gs_a = results["高速抛光修盘基模口径"]
        jz_a = results["基准模改丸片口径"]

        is_concave = radius > 0
        mj_file = "MJA_迈均凹.lsp" if is_concave else "MJT_迈均凸.lsp"
        mj_func = "mja" if is_concave else "mjt"
        dw_file: Literal['DWT_短尾凸.lsp', 'DWA_短尾凹.lsp'] = "DWT_短尾凸.lsp" if is_concave else "DWA_短尾凹.lsp"
        dw_func: Literal['dwt', 'dwa'] = "dwt" if is_concave else "dwa"

        for step_name, lsp, func, step_params in [
            ("迈均-基模",              mj_file,             mj_func, {"r0": jm_r, "a0": jm_a, "t0": 2, "save_path": save_path}),
            ("迈均-JZM短尾M24",       "JZM_短尾M24_基准模.lsp", "jzm1",   {"r0": abs(radius), "a0": jz_a, "save_path": save_path}),
            ("迈均-抛光模基模修盘",     dw_file,             dw_func, {"r0": pg_r, "a0": pg_a, "t0": 2, "tool_type": 1, "save_path": save_path}),
            ("迈均-抛光模修盘基模",     dw_file,             dw_func, {"r0": gs_r, "a0": gs_a, "t0": 2, "tool_type": 2, "save_path": save_path}),
        ]:
            if not self._execute_lisp(step_name, lsp, func, step_params):
                return False

        print(f"绘制迈均套装完成，参数: {params}")
        return True

    def draw_di_pao(self, params=None):
        """绘制低抛套装"""
        if params is None:
            params = {}

        save_path = self._resolve_save_path()
        if not save_path:
            return False

        is_concave = params.get("type", "凹") == "凹"
        dw_file = "DWA_短尾凹.lsp" if is_concave else "DWT_短尾凸.lsp"
        dw_func = "dwa" if is_concave else "dwt"

        if not self._execute_lisp("低抛", dw_file, dw_func, params):
            return False

        print(f"绘制低抛套装完成，参数: {params}")
        return True

    # ==================== 辅助函数 ====================

    @retry_on_autocad_error(max_attempts=3, initial_delay=0.5)
    def _execute_lisp(self, step_name, lsp, func, params):
        """执行LISP步骤并处理结果"""
        try:
            if not self.acad:
                self.acad = find_autocad()
                self.acad.Visible = True

            try:
                doc = apply_template(self.acad, self.template_path, None)
            except Exception:
                doc = self.acad.ActiveDocument
            doc.Activate()

            lsp_path = os.path.join(self.lsp_dir, lsp)
            if os.path.exists(lsp_path):
                load_single_lisp_file(doc, lsp_path, None)

            args = self._build_args(func, params)

            if run_lisp(self.acad, func, args, True):
                print(f"✓ {step_name} 完成")
                return True
        except Exception as e:
            print(f"❌ {step_name} 异常: {e}")

        print(f"❌ {step_name} 失败")
        return False

    def _build_args(self, func, params):
        """构建 LISP 函数参数"""
        def abs_v(k):
            default_value = 1 if k == "t0" else 0
            return str(abs(float(params.get(k, default_value))))

        args_map = {
            "xba": ["r0", "a0", "t0", "b0", lambda p: f'"{p.get("tool_type", "1")}"',
                      lambda p: p.get("tech_choice", "1"), lambda p: f'"{p.get("custom_tech_text", "")}"',
                      lambda p: f'"{p.get("save_path", "")}"'],
            "xbt": ["r0", "a0", "t0", "b0", lambda p: f'"{p.get("tool_type", "1")}"',
                      lambda p: p.get("tech_choice", "1"), lambda p: f'"{p.get("custom_tech_text", "")}"',
                      lambda p: f'"{p.get("save_path", "")}"'],
            "mja": ["r0", "a0", "t0", lambda p: f'"{p.get("save_path", "")}"'],
            "mjt": ["r0", "a0", "t0", lambda p: f'"{p.get("save_path", "")}"'],
            "dwa": ["r0", "a0", "t0", lambda p: f'"{p.get("tool_type", "1")}"', lambda p: f'"{p.get("save_path", "")}"'],
            "dwt": ["r0", "a0", "t0", lambda p: f'"{p.get("tool_type", "2")}"', lambda p: f'"{p.get("save_path", "")}"'],
            "jzm1": ["r0", "a0", "t0", lambda p: f'"{p.get("scale_str", "1:1")}"',
                      lambda p: p.get("tech_choice", "1"), lambda p: f'"{p.get("custom_tech_text", "")}"',
                      lambda p: p.get("slot_choice", "0"), lambda p: f'"{p.get("save_path", "")}"'],
            "jzm2": ["r0", "a0", "t0", lambda p: f'"{p.get("scale_str", "1:1")}"',
                      lambda p: p.get("tech_choice", "1"), lambda p: f'"{p.get("custom_tech_text", "")}"',
                      lambda p: p.get("slot_choice", "0"), lambda p: f'"{p.get("save_path", "")}"'],
            "xza": ["r0", "a0", "t0", lambda p: f'"{p.get("tool_type", "1")}"', lambda p: f'"{p.get("save_path", "")}"'],
            "xzt": ["r0", "a0", "t0", lambda p: f'"{p.get("tool_type", "2")}"', lambda p: f'"{p.get("save_path", "")}"'],
        }

        args = args_map.get(func, [])
        return [abs_v(k) if isinstance(k, str) else k(params) for k in args]

    def _resolve_save_path(self):
        """获取保存路径"""
        save_path = select_save_directory()
        if not save_path:
            print("⚠ 未获得有效的保存路径")
            return None
        return save_path
