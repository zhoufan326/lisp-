#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from acad_doc_manager import is_ready, force_cancel, find_autocad


def _ensure_acad(acad):
    """确保拿到可用的 AutoCAD 对象，入参失效时重新获取"""
    if acad:
        try:
            acad.Visible = True
            return acad
        except Exception:
            pass
    return find_autocad()


def _ensure_document(acad):
    """确保存在活动文档，全手动模式下由用户自行打开"""
    try:
        doc = acad.ActiveDocument
    except Exception:
        doc = None
    if not doc:
        raise RuntimeError("找不到活动文档，请先在 CAD 中新建或打开图形。")
    return doc


def _wait_command_complete(acad, doc, timeout=15, poll_interval=0.05):
    """等待 AutoCAD 命令执行完成。LISP 函数通过 (setvar "USERS1" "SUCCESS") 报告完成。"""
    start = time.time()

    while time.time() - start < timeout:
        try:
            # LISP 执行完毕后会设置 USERS1="SUCCESS"，检测到即可提前返回
            if doc.GetVariable("USERS1") == "SUCCESS":
                return True
            # 命令行空闲时确认就绪状态
            if not acad.GetVariable("CMDNAMES") and is_ready(acad, 0.3):
                return True
        except Exception:
            pass
        time.sleep(poll_interval)

    return is_ready(acad, 0.3)


def run_lisp(acad, func_name, args=None, is_param=True, wait_for_completion=True, timeout=15):
    """执行 AutoCAD LISP 函数，并通过 USERS1 系统变量判断完成状态"""
    acad = _ensure_acad(acad)
    doc = _ensure_document(acad)

    # 发送命令前确保 CAD 空闲，否则强制取消当前命令
    if not is_ready(acad, 2):
        force_cancel(acad)

    try:
        doc.Activate()
        time.sleep(0.1)

        # 清空 USERS1，供 LISP 函数后续回写完成状态
        doc.SendCommand('(setvar "USERS1" "")\n')
        doc.SendCommand("\n")

        if is_param:
            # 参数已拼接到函数调用中
            doc.SendCommand(f"({func_name}{' ' + ' '.join(args) if args else ''})\n")
        else:
            # 交互模式：先发送函数名，再逐行传递参数
            doc.SendCommand(f"({func_name})\n")
            for arg in (args or []):
                time.sleep(0.3)
                doc.SendCommand(arg.strip('"') + "\n")

        if wait_for_completion:
            return _wait_command_complete(acad, doc, timeout=timeout)

        return True
    except Exception as e:
        print(f"执行LISP失败 {func_name}: {e}")
        raise
