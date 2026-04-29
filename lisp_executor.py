#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from acad_doc_manager import is_ready, force_cancel, find_autocad


def _ensure_acad(acad):
    """确保拿到可用的 AutoCAD 对象。"""
    if acad:
        try:
            acad.Visible = True
            return acad
        except Exception:
            pass
    return find_autocad()


def _ensure_document(acad):
    """确保有可执行的活动文档（全手动模式：不自动新建）。"""
    try:
        doc = acad.ActiveDocument
    except Exception:
        doc = None
    if not doc:
        raise RuntimeError("找不到活动文档，请先在 CAD 中新建或打开图形。")
    return doc


def _wait_command_complete(acad, timeout=25, poll_interval=0.1):
    """
    等待 AutoCAD 命令执行完成。
    """
    start = time.time()
    saw_busy = False
    
    # 初始快速检查，如果命令太快，可能直接就 ready 了
    time.sleep(0.2) 
    
    while time.time() - start < timeout:
        try:
            cmd_names = acad.GetVariable("CMDNAMES")
            if cmd_names:
                saw_busy = True
            else:
                # 如果曾经忙过现在闲了，或者等了 2 秒还没忙，就检查是否 ready
                if saw_busy or (time.time() - start > 2.0):
                    if is_ready(acad, 0.5):
                        return True
        except Exception:
            pass
        time.sleep(poll_interval)

    return is_ready(acad, 1.0)


def run_lisp(acad, func_name, args=None, is_param=True, wait_for_completion=True, timeout=25):
    acad = _ensure_acad(acad)
    doc = _ensure_document(acad)

    if not is_ready(acad, 5): force_cancel(acad)
    
    try:
        doc.Activate()
        time.sleep(0.3)
        
        # 重置成功标志位
        doc.SendCommand('(setvar "USERS1" "")\n')
        doc.SendCommand("\n")
        
        if is_param:
            doc.SendCommand(f"({func_name}{' ' + ' '.join(args) if args else ''})\n")
        else:
            doc.SendCommand(f"({func_name})\n")
            for arg in (args or []):
                time.sleep(0.5)
                doc.SendCommand(arg.strip('"') + "\n")

        if wait_for_completion:
            # 基础等待（等待命令行变闲）
            completed = _wait_command_complete(acad, timeout=timeout)
            
            # 核心验证：检查 USERS1 是否为 SUCCESS
            try:
                lisp_status = doc.GetVariable("USERS1")
                if lisp_status == "SUCCESS":
                    return True
            except Exception as e:
                print(f"获取 LISP 状态失败: {e}")
            
            return completed

        return True
    except Exception as e:
        print(f"执行LISP失败 {func_name}: {e}")
        raise
