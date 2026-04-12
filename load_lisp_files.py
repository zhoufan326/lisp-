#!/usr/bin/env python3
"""
AutoCAD LISP文件加载工具
功能：连接AutoCAD并加载当前项目文件夹中的所有LISP文件
"""

import os
import time

try:
    import win32com.client
    HAS_PYWIN32 = True
except ImportError:
    HAS_PYWIN32 = False

def is_autocad_ready(acad):
    """检查AutoCAD是否处于就绪状态"""
    try:
        return acad.GetVariable("CMDNAMES") == ""
    except:
        return False

def find_autocad():
    """查找或启动AutoCAD应用程序"""
    if not HAS_PYWIN32:
        print("错误: pywin32 未安装。请运行 'pip install pywin32'。")
        return None
    
    acad = None
    try: 
        acad = win32com.client.GetActiveObject("AutoCAD.Application") 
        print("✓ 已连接到运行中的AutoCAD") 
    except: 
        try: 
            acad = win32com.client.Dispatch("AutoCAD.Application") 
            acad.Visible = True
            print("✓ 已启动新AutoCAD实例") 
        except Exception as e: 
            print(f"✗ 无法启动AutoCAD: {e}")
            return None
            
    # 等待AutoCAD完全启动
    print("正在等待AutoCAD初始化...")
    time.sleep(3)
    return acad

def load_lisp_file(doc, lisp_file):
    """加载单个LISP文件"""
    if not doc:
        print("✗ 找不到活动文档")
        return False
    
    lisp_path = os.path.abspath(lisp_file).replace("\\", "/") 
    # 使用 vl-cmdf 函数调用 APPLOAD，尝试非交互式加载
    load_command = f'(vl-cmdf "_.appload" "{lisp_path}" "")' 
    
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # 检查AutoCAD是否就绪
            if not is_autocad_ready(doc.Application):
                print(f"尝试 {attempt+1}/{max_attempts}: AutoCAD 繁忙，等待...")
                time.sleep(2)
                continue
                
            doc.Activate() # 确保命令发往正确的文档
            doc.SendCommand(load_command + "\n") 
            print(f"✓ 已加载: {os.path.basename(lisp_file)}") 
            return True
        except Exception as e:
            print(f"尝试 {attempt+1}/{max_attempts} 失败 {os.path.basename(lisp_file)}: {e}")
            if attempt < max_attempts - 1:
                print("等待后重试...")
                time.sleep(3)
            else:
                print(f"✗ 加载失败 {os.path.basename(lisp_file)}")
                return False

def load_all_lisp_files():
    """加载当前文件夹中的所有LISP文件"""
    # 查找AutoCAD
    acad = find_autocad()
    if not acad:
        return
    
    # 获取活动文档
    try:
        doc = acad.ActiveDocument
        if not doc:
            # 如果没有活动文档，创建一个新的
            doc = acad.Documents.Add()
            print("✓ 已创建新文档")
    except Exception as e:
        print(f"✗ 无法获取文档: {e}")
        return
    
    # 遍历当前文件夹中的LISP文件
    current_dir = os.path.dirname(os.path.abspath(__file__))
    lisp_files = [f for f in os.listdir(current_dir) if f.lower().endswith('.lsp')]
    
    if not lisp_files:
        print("✗ 当前文件夹中没有LISP文件")
        return
    
    print(f"\n��在加载 {len(lisp_files)} 个LISP文件:")
    print("-" * 50)
    
    # 加载每个LISP文件
    for lisp_file in lisp_files:
        lisp_path = os.path.join(current_dir, lisp_file)
        load_lisp_file(doc, lisp_path)
        time.sleep(1) # 给AutoCAD一点处理时间
    
    print("-" * 50)
    print("\n✓ 所有LISP文件加载完成！")
    
    # 提示用户
    print("\n提示:")
    print("- 您可以在AutoCAD命令行输入LISP命令（如 (xba)）来运行")
    print("- 命令通常以 'c:' 开头，例如 'c:xba' 可以直接在命令行输入 'xba'")

if __name__ == "__main__":
    print("=" * 60)
    print("AutoCAD LISP文件加载工具")
    print("=" * 60)
    
    if not HAS_PYWIN32:
        print("请先安装pywin32:")
        print("  pip install pywin32")
        exit(1)
    
    load_all_lisp_files()
    print("\n按任意键退出...")
    input()