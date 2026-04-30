#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
from acad_doc_manager import is_ready, find_autocad, apply_template
from lisp_loader import load_single_lisp_file
from retry_decorator import retry_on_autocad_error


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


def _wait_command_complete(acad, doc, timeout=20, poll_interval=0.05):
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


def _send_command_with_retry(doc, command, max_attempts=5, initial_delay=0.2):
    """发送命令到 AutoCAD，遇到 RPC_E_CALL_REJECTED 时自动重试"""
    last_exception = None
    for attempt in range(1, max_attempts + 1):
        try:
            doc.SendCommand(command)
            return
        except Exception as e:
            error_msg = str(e)
            last_exception = e
            # RPC_E_CALL_REJECTED = -2147418111，表示 CAD 正忙
            if "-2147418111" in error_msg or "拒绝接收呼叫" in error_msg:
                delay = initial_delay * (2 ** (attempt - 1))
                if attempt < max_attempts:
                    time.sleep(delay)
                    continue
            raise
    raise last_exception


def run_lisp(acad, func_name, args=None, is_param=True, wait_for_completion=True, timeout=20):
    """执行 AutoCAD LISP 函数，并通过 USERS1 系统变量判断完成状态"""
    acad = _ensure_acad(acad)
    doc = _ensure_document(acad)

    try:
        doc.Activate()
        time.sleep(0.5)

        # 清空 USERS1，供 LISP 函数后续回写完成状态
        _send_command_with_retry(doc, '(setvar "USERS1" "")\n')
        _send_command_with_retry(doc, "\n")

        if is_param:
            # 参数已拼接到函数调用中
            _send_command_with_retry(doc, f"({func_name}{' ' + ' '.join(args) if args else ''})\n")
        else:
            # 交互模式：先发送函数名，再逐行传递参数
            _send_command_with_retry(doc, f"({func_name})\n")
            for arg in (args or []):
                time.sleep(0.3)
                _send_command_with_retry(doc, arg.strip('"') + "\n")

        if wait_for_completion:
            return _wait_command_complete(acad, doc, timeout=timeout)

        return True
    except Exception as e:
        print(f"执行LISP失败 {func_name}: {e}")
        raise


def execute_lisp(acad, step_name, lsp, func, params, build_args, template_path, lsp_dir):
    """执行LISP步骤并处理结果（外部调用入口，返回 True/False）"""
    try:
        _execute_with_retry(acad, step_name, lsp, func, params, build_args, template_path, lsp_dir)
        print(f"✓ {step_name} 完成")
        return True
    except Exception as e:
        print(f"❌ {step_name} 异常: {e}")
        print(f"❌ {step_name} 失败")
        return False


@retry_on_autocad_error(max_attempts=3, initial_delay=2)
def _execute_with_retry(acad, step_name, lsp, func, params, build_args, template_path, lsp_dir):
    """执行LISP核心逻辑（可重试）"""
    if not acad:
        acad = find_autocad()
        acad.Visible = True

    try:
        doc = apply_template(acad, template_path, None)
    except Exception:
        doc = acad.ActiveDocument
    doc.Activate()

    lsp_path = os.path.join(lsp_dir, lsp)
    if os.path.exists(lsp_path):
        load_single_lisp_file(doc, lsp_path, None)

    args = build_args(func, params)
    if not run_lisp(acad, func, args, True):
        raise RuntimeError(f"{step_name} 执行失败")
