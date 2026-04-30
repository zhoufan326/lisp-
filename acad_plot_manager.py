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

try:
    from retry_decorator import retry_on_autocad_error
except ImportError:
    def retry_on_autocad_error(*args, **kwargs):
        def decorator(f): return f
        return decorator


def _sanitize_filename(name: str) -> str:
    """过滤打印文件名中的不稳定字符，避免 PlotToFile 失败。"""
    text = str(name or "Drawing")
    for ch in '<>:"/\\|?*':
        text = text.replace(ch, "_")
    text = text.strip().rstrip(".")
    return text or "Drawing"


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


_DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "工装绘图文件")


@retry_on_autocad_error(max_attempts=5, initial_delay=2)
def plot_paper_space(doc, output_dir=None, custom_filename=None):
    """
    执行图纸空间打印。
    
    参数:
        doc: AutoCAD文档对象
        output_dir: 输出目录，默认为项目下的 "工装绘图文件" 目录
        custom_filename: 自定义文件名（不含路径和扩展名），如果提供则使用此名称命名文件
    """
    if output_dir is None:
        output_dir = _DEFAULT_OUTPUT_DIR
    try:
        # 在输出目录下创建"图纸"子目录
        output_dir = os.path.join(output_dir, "图纸")
        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 1. 切换到"A4图纸"布局并确保打印样式正确
        target_layout_name = "A4图纸"
        try:
            layout = doc.Layouts.Item(target_layout_name)
            doc.ActiveLayout = layout
            configure_print_settings(doc) # 打印前再次确保样式正确
            print(f"✓ 已切换并配置布局样式: {target_layout_name}")
        except Exception as e:
            print(f"⚠ 切换布局失败: {e}")

        # 2. 构造输出路径
        if custom_filename:
            output_file = f"{_sanitize_filename(custom_filename)}.pdf"
        else:
            doc_name = doc.Name
            base_name = os.path.splitext(doc_name)[0] if doc_name else "Drawing"
            base_name = _sanitize_filename(base_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{base_name}_{timestamp}.pdf"

        output_path = os.path.join(output_dir, output_file)

        # 3. 发送打印命令
        print(f"正在生成 PDF: {output_file} ...")
        doc.Plot.PlotToFile(output_path)
        print(f"✓ 打印任务已发送到 AutoCAD")
        return output_path

    except Exception as e:
        print(f"✗ 打印请求异常: {e}")
        raise


if __name__ == "__main__":
    print("此模块应被 autocad_controller.py 调用")
