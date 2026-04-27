#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DWG文件保存模块 - 简化版"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional, Tuple


try:
    from retry_decorator import retry_on_autocad_error
except ImportError:
    retry_on_autocad_error = lambda **kwargs: lambda f: f


# 全局变量用于记录最后保存位置
last_save_directory = "P:工装绘图文件"


def select_save_directory(parent: tk.Tk = None, material_code: str = None) -> Optional[str]:
    """
    弹出对话框让用户选择保存位置
    如果提供了物料编码，则自动创建并使用该编码命名的文件夹
    """
    global last_save_directory
    
    # 如果有物料编码，自动创建文件夹
    if material_code and material_code.strip():
        base_dir = "P:工装绘图文件"
        material_dir = os.path.join(base_dir, material_code.strip())
        os.makedirs(material_dir, exist_ok=True)
        last_save_directory = material_dir
        return material_dir
    
    # 记录当前目录
    initial_dir = last_save_directory if os.path.exists(last_save_directory) else "P:工装绘图文件"
    
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


def get_last_save_directory() -> str:
    """获取最后保存位置"""
    return last_save_directory


def set_last_save_directory(directory: str) -> None:
    """设置最后保存位置"""
    global last_save_directory
    last_save_directory = directory


def get_save_path_for_material(material_code: str) -> str:
    """获取物料编码对应的保存路径"""
    if material_code and material_code.strip():
        return os.path.join(last_save_directory, material_code.strip())
    return last_save_directory