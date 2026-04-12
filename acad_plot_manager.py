#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoCAD Print Manager (v3.0)
恢复默认后台打印，取消对打印结果的文件检查。
"""

import os
from datetime import datetime

try:
    import win32com.client
    HAS_PYWIN32 = True
except ImportError:
    HAS_PYWIN32 = False


def configure_print_settings(doc):
    """
    仅针对“A4图纸”布局设置 monochrome.ctb 打印样式。
    """
    if not HAS_PYWIN32:
        return False
    
    try:
        layouts = doc.Layouts
        target_layout_name = "A4图纸"
        
        try:
            layout = layouts.Item(target_layout_name)
            layout.StyleSheet = "monochrome.ctb"
            print(f"✓ 布局 '{target_layout_name}' 已应用样式: monochrome.ctb")
            return True
        except Exception:
            print(f"✗ 未找到布局 '{target_layout_name}'")
            return False
    except Exception as e:
        print(f"✗ 配置失败: {e}")
        return False


def plot_paper_space(doc, output_dir="P:\\工装绘图文件"):
    """
    执行图纸空间打印。
    恢复默认后台打印模式，不再检查文件是否生成。
    """
    try:
        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. 尝试切换到“A4图纸”布局
        target_layout_name = "A4图纸"
        try:
            doc.ActiveSpace = 1  # acPaperSpace
            doc.ActiveLayout = doc.Layouts.Item(target_layout_name)
            print(f"✓ 已切换到布局: {target_layout_name}")
        except:
            pass

        # 2. 构造输出路径
        doc_name = doc.Name
        base_name = os.path.splitext(doc_name)[0] if doc_name else "Drawing"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path_no_ext = os.path.join(output_dir, f"{base_name}_{timestamp}")
        
        # 3. 发送打印命令（使用 AutoCAD 默认后台设置）
        print(f"已向 AutoCAD 发送打印任务...")
        plot = doc.Plot
        plot.PlotToFile(output_path_no_ext, "DWG to PDF.pc3")
        
        # 4. 直接返回路径（不验证文件是否存在）
        return output_path_no_ext + ".pdf"
            
    except Exception as e:
        print(f"✗ 打印请求异常: {e}")
        return None


if __name__ == "__main__":
    print("此模块应被 autocad_controller.py 调用")
