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
            
            # 仅设置打印样式，其他保持样板默认
            layout.StyleSheet = "monochrome.ctb"
            
            # 更新布局显示
            layout.RefreshPlotDeviceInfo()
            
            print(f"✓ 布局 '{target_layout_name}' 已设置为 monochrome.ctb")
            return True
        except Exception as e:
            print(f"✗ 未找到布局 '{target_layout_name}' 或配置失败: {e}")
            return False
    except Exception as e:
        print(f"✗ 配置失败: {e}")
        return False


def plot_paper_space(doc, output_dir="P:\\工装绘图文件"):
    """
    执行图纸空间打印。
    """
    try:
        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. 切换到“A4图纸”布局并确保打印样式正确
        target_layout_name = "A4图纸"
        try:
            layout = doc.Layouts.Item(target_layout_name)
            doc.ActiveLayout = layout
            configure_print_settings(doc) # 打印前再次确保样式正确
            print(f"✓ 已切换并配置布局样式: {target_layout_name}")
        except Exception as e:
            print(f"⚠ 切换布局失败: {e}")

        # 2. 构造输出路径
        doc_name = doc.Name
        base_name = os.path.splitext(doc_name)[0] if doc_name else "Drawing"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{base_name}_{timestamp}.pdf"
        output_path = os.path.join(output_dir, output_file)
        
        # 3. 发送打印命令
        print(f"正在生成 PDF: {output_file} ...")
        
        plot = doc.Plot
        
        # 使用 PlotToFile，保持使用 PDF 打印机 (样板中应已预设)
        # 如果样板没设 PDF 打印机，PlotToFile 可能会报错，
        # 但用户要求“保持样板默认的打印设置”，所以我们假设样板已经配置好了。
        plot.PlotToFile(output_path)
        
        print(f"✓ 打印任务已发送到 AutoCAD")
        return output_path
            
    except Exception as e:
        print(f"✗ 打印请求异常: {e}")
        return None


if __name__ == "__main__":
    print("此模块应被 autocad_controller.py 调用")
