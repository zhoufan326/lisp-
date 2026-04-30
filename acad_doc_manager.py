#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, time, win32com.client, pythoncom
from lisp_loader import LispParser, load_single_lisp_file
from retry_decorator import retry_on_autocad_error

try:
    from acad_plot_manager import configure_print_settings
    HAS_PRINT = True
except: HAS_PRINT = False

def is_ready(acad, wait=2):
    """检测 CAD 是否处于就绪状态 (无命令活动)"""
    start = time.time()
    while time.time() - start < wait:
        try:
            # 检查是否有活动命令，且 ActiveDocument 是否可用
            if acad.ActiveDocument and not acad.GetVariable("CMDNAMES"): return True
        except: pass
        time.sleep(0.1)
    return False


@retry_on_autocad_error(max_attempts=3, initial_delay=1)
def find_autocad():
    """获取或启动 AutoCAD 实例，并配置安全设置以禁用加载警告"""
    pythoncom.CoInitialize()  # 确保线程安全
    acad = None
    try: 
        # 优先获取已运行的实例，速度最快
        acad = win32com.client.GetActiveObject("AutoCAD.Application")
    except:
        try:
            # 如果没运行，则启动新实例
            acad = win32com.client.Dispatch("AutoCAD.Application")
            acad.Visible = True
        except Exception as e: 
            raise RuntimeError(f"无法启动 AutoCAD: {e}")
    
    if acad:
        configure_security_settings(acad)
    return acad

def configure_security_settings(acad):
    """
    配置 AutoCAD 安全设置以禁用加载警告：
    1. SECURELOAD = 0: 禁用安全加载警告（最直接有效）
    2. 将项目路径添加到 TRUSTEDPATHS (可选，增加一层保障)
    """
    try:
        # 1. 禁用 SECURELOAD (0 = 关闭, 1 = 开启并警告, 2 = 仅限信任路径)
        if acad.GetVariable("SECURELOAD") != 0:
            acad.SetVariable("SECURELOAD", 0)
            print("AutoCAD 安全加载警告已禁用 (SECURELOAD=0)")
        
        # 2. 尝试添加当前项目路径到 TRUSTEDPATHS (信任路径)
        curr_path = os.path.abspath(os.path.dirname(__file__))
        trusted = acad.GetVariable("TRUSTEDPATHS") or ""
        if curr_path.lower() not in trusted.lower():
            new_trusted = f"{trusted};{curr_path}" if trusted else curr_path
            acad.SetVariable("TRUSTEDPATHS", new_trusted)
            print(f"项目路径已添加到信任路径: {curr_path}")
            
    except Exception as e:
        # 系统变量可能在某些版本或特定状态下无法设置，记录但不中断
        print(f"配置 AutoCAD 安全设置时出错 (非致命): {e}")

@retry_on_autocad_error(max_attempts=3, initial_delay=1)
def apply_template(acad, primary, backup):
    """应用图形样板"""
    for p in [primary, backup]:
        if p and os.path.exists(p):
            try: return acad.Documents.Add(os.path.abspath(p))
            except: pass
    return acad.Documents.Add()

def auto_new_doc(acad, template=None, lisp=None):
    if not acad: return None
    template = template or os.path.join(os.path.dirname(__file__), "LISP图样.dwt")
    try:
        doc = apply_template(acad, template, None)
        doc.Activate()
        time.sleep(1)
        if HAS_PRINT: configure_print_settings(doc)
        if lisp and os.path.exists(lisp):
            load_single_lisp_file(doc, lisp, LispParser.parse_file(lisp))
        return doc
    except Exception as e:
        print(f"新建图形失败: {e}")
        return None
