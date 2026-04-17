#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
try: from retry_decorator import retry_on_autocad_error
except: retry_on_autocad_error = lambda **kwargs: lambda f: f
from filename import generate_filename


def _sanitize_filename(name: str) -> str:
    """过滤 Windows/AutoCAD 常见不稳定字符，提升 SaveAs 成功率。"""
    text = str(name or "DRAWING")
    for ch in '<>:"/\\|?*':
        text = text.replace(ch, "_")
    text = text.strip().rstrip(".")
    return text or "DRAWING"


def _build_name(name=None, radius=None, chord_length=None, drawing_type=None):
    """优先使用 filename.py 规则生成文件名，失败时回退。"""
    if name:
        return _sanitize_filename(name)

    if radius is not None and chord_length is not None and drawing_type:
        try:
            return _sanitize_filename(generate_filename(radius, chord_length, drawing_type))
        except Exception:
            pass

    return "DRAWING"

@retry_on_autocad_error(max_attempts=5, initial_delay=2)
def save_dwg(doc, out_dir="P:\\工装绘图文件", name=None, radius=None, chord_length=None, drawing_type=None):
    try:
        os.makedirs(out_dir, exist_ok=True)
        if not any([name, radius, chord_length, drawing_type]):
            name = os.path.splitext(str(getattr(doc, "Name", "DRAWING")))[0]
        safe_name = _build_name(name, radius, chord_length, drawing_type)
        path = os.path.join(out_dir, f"{safe_name}.dwg")
        doc.SaveAs(path)
        return path
    except Exception as e:
        print(f"保存DWG失败: {e}")
        raise
