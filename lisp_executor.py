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


def run_lisp(acad, func_name, args=None, is_param=True):
    acad = _ensure_acad(acad)
    doc = _ensure_document(acad)

    if not is_ready(acad, 5): force_cancel(acad)
    
    try:
        doc.Activate()
        time.sleep(0.3)
        doc.SendCommand("\n")
        
        if is_param:
            doc.SendCommand(f"({func_name}{' ' + ' '.join(args) if args else ''})\n")
        else:
            doc.SendCommand(f"({func_name})\n")
            for arg in (args or []):
                time.sleep(0.5)
                doc.SendCommand(arg.strip('"') + "\n")
        
        return True
    except Exception as e:
        print(f"执行LISP失败 {func_name}: {e}")
        raise
