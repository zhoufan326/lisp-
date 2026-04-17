#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, time, win32com.client
from lisp_loader import LispParser, load_single_lisp_file

try:
    from acad_plot_manager import configure_print_settings
    HAS_PRINT = True
except: HAS_PRINT = False

def is_ready(acad, wait=2):
    start = time.time()
    while time.time() - start < wait:
        try:
            if acad.ActiveDocument and not acad.GetVariable("CMDNAMES"): return True
        except: pass
        time.sleep(0.1)
    return False

def force_cancel(acad):
    for _ in range(2):
        if is_ready(acad, 0.2): return True
        try:
            acad.ActiveDocument.SendCommand("\x03")
            time.sleep(0.3)
        except: pass
    return is_ready(acad, 0.2)

def find_autocad():
    try: return win32com.client.GetActiveObject("AutoCAD.Application")
    except:
        try:
            acad = win32com.client.Dispatch("AutoCAD.Application")
            acad.Visible = True
            return acad
        except Exception as e: raise RuntimeError(f"无法启动AutoCAD: {e}")

def apply_template(acad, primary, backup):
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
