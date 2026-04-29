#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DWG 保存路径管理模块（仅负责 Python 侧路径决策与目录创建）。"""

import os
import tkinter as tk
from tkinter import filedialog
from typing import Optional


BASE_SAVE_DIR = r"P:\AutoLISP_工装绘图项目\工装绘图文件"

# 全局变量：记录最后一次确定的保存目录
last_save_directory = BASE_SAVE_DIR
_material_code_provider = None


def set_material_code_provider(provider) -> None:
    """
    注册物料编码读取函数（通常由 UI 注入）。
    provider 应返回字符串（可为空）。
    """
    global _material_code_provider
    _material_code_provider = provider


def _resolve_material_code(material_code: str = None) -> str:
    """优先使用显式传入值，否则尝试从 UI provider 获取。"""
    code = (material_code or "").strip()
    if code:
        return code

    if callable(_material_code_provider):
        try:
            code = (_material_code_provider() or "").strip()
        except Exception:
            code = ""
    return code


def select_save_directory(parent: tk.Tk = None, material_code: str = None) -> Optional[str]:
    """
    统一确定保存目录：
    - 有物料编码：在 BASE_SAVE_DIR 下创建并返回物料目录（不弹窗）
    - 无物料编码：弹窗让用户选择目录
    """
    global last_save_directory
    
    code = _resolve_material_code(material_code)

    # 如果有物料编码，自动创建文件夹
    if code:
        material_dir = os.path.join(BASE_SAVE_DIR, code)
        os.makedirs(material_dir, exist_ok=True)
        last_save_directory = material_dir
        return material_dir
    
    # 记录当前目录
    initial_dir = last_save_directory if os.path.exists(last_save_directory) else BASE_SAVE_DIR
    
    # 弹出目录选择对话框
    directory = filedialog.askdirectory(
        title="选择DWG文件保存位置",
        initialdir=initial_dir,
        parent=parent
    )
    
    if directory:
        last_save_directory = directory
        return directory
    
    return None


def get_save_path_for_material(material_code: str) -> str:
    """获取物料编码对应的保存路径"""
    if material_code and material_code.strip():
        code = material_code.strip()
        # 如果 last_save_directory 已经是该物料目录，则直接返回，避免重复拼接
        if os.path.basename(os.path.normpath(last_save_directory)).lower() == code.lower():
            return last_save_directory
        return os.path.join(last_save_directory, code)
    return last_save_directory


def get_last_save_directory() -> str:
    """获取最后保存位置"""
    return last_save_directory


def set_last_save_directory(directory: str) -> None:
    """设置最后保存位置"""
    global last_save_directory
    last_save_directory = directory
