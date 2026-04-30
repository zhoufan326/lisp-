#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LISP Loader Module (v3.0)
Responsible for parsing and loading LISP files into AutoCAD with autoload stubs.
"""

import os
import re
from typing import List, Dict, Set
from dataclasses import dataclass

# Try to import win32com for AutoCAD integration
try:
    import win32com.client
    HAS_PYWIN32 = True
except ImportError:
    HAS_PYWIN32 = False

# Import decorators from retry_decorator
try:
    from retry_decorator import retry_on_autocad_error
except ImportError:
    def retry_on_autocad_error(*args, **kwargs):
        def decorator(f): return f
        return decorator

@dataclass
class LispFunction:
    name: str
    params: List[str]
    docstring: str = ""

@dataclass
class LispFile:
    path: str
    name: str
    functions: List[LispFunction] = None

class LispParser:
    DEFUN_PATTERN = re.compile(
        r'\(defun\s+([^\s\(\)]+)\s*\(([^\(\)]*)\)\s*(?:"([^"]*)"\s*)?', 
        re.IGNORECASE | re.DOTALL
    )

    @staticmethod
    def parse_file(file_path: str) -> List[LispFunction]:
        functions = []
        try:
            # First try GBK (standard for AutoLISP in China)
            with open(file_path, 'r', encoding='gbk', errors='ignore') as f:
                content = f.read()
            
            for match in LispParser.DEFUN_PATTERN.finditer(content):
                name = match.group(1)
                # Parse parameters (splitting by / for local variables)
                params_raw = match.group(2).split('/')
                params_only = params_raw[0].strip().split()
                params = [p.strip() for p in params_only if p.strip()]
                docstring = match.group(3) or ""
                functions.append(LispFunction(name, params, docstring.strip()))
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
        return functions


# 文档级去重：同一文档内同一 lsp 仅注册一次桩
_DOC_STUB_REGISTRY: Dict[str, Set[str]] = {}


def _get_doc_key(doc) -> str:
    """为 AutoCAD 文档生成稳定键值。"""
    try:
        full_name = getattr(doc, "FullName", "") or ""
    except Exception:
        full_name = ""
    try:
        name = getattr(doc, "Name", "") or ""
    except Exception:
        name = ""
    # 未保存图纸通常没有 FullName，退化到 Name；都取不到时退化到 id
    return full_name or name or str(id(doc))

@retry_on_autocad_error(max_attempts=3, initial_delay=1) 
def load_single_lisp_file(doc, lisp_file, functions=None): 
    """加载单个LISP文件 (使用 autoload 模式)""" 
    if not doc: return False
    
    # 使用绝对路径（确保加载稳定性）
    lisp_path = lisp_file.replace("\\", "/") 
    file_name = os.path.basename(lisp_file)
    doc_key = _get_doc_key(doc)
    
    print(f"正在加载 LISP 文件: {lisp_path}")
    
    # 获取该文件中的所有 c: 命令名
    if not functions:
        # 如果没有预先解析函数，则直接加载整个文件
        load_command = f'(progn (vl-load-com) (load "{lisp_path}") (princ (strcat "\\n>> " "{file_name}" " 已加载。")) (princ))'
    else:
        # 小防抖：同一文档同一 lsp 的桩只注册一次
        registered = _DOC_STUB_REGISTRY.setdefault(doc_key, set())
        if lisp_path in registered:
            return True

        # 仅为“入口函数”生成桩，避免辅助函数和 *error* 造成递归/堆栈问题
        stubs = []
        processed_names = set()
        func_map = {f.name.lower(): f for f in functions}

        def add_core_stub(func_name, params):
            key = func_name.lower()
            if key in processed_names:
                return
            params_str = " ".join(params or [])
            if params_str:
                stubs.append(
                    f'(defun {func_name} ({params_str}) (load "{lisp_path}") (apply \'{func_name} (list {params_str})))'
                )
            else:
                stubs.append(f'(defun {func_name} () (load "{lisp_path}") ({func_name}))')
            processed_names.add(key)

        # 1) 先处理 c: 命令入口，并为其同名核心函数（如 xbt）生成桩
        c_entries = [f for f in functions if f.name.lower().startswith("c:")]
        for entry in c_entries:
            entry_name = entry.name
            entry_key = entry_name.lower()
            if entry_key not in processed_names:
                stubs.append(f'(defun {entry_name} () (load "{lisp_path}") ({entry_name}))')
                processed_names.add(entry_key)

            base_name = entry_name[2:]
            base_func = func_map.get(base_name.lower())
            if base_func and base_name.lower() != "*error*":
                add_core_stub(base_name, base_func.params)

        # 2) 若文件里没有 c: 入口，则仅给“核心函数”生成一个带参桩
        if not stubs:
            # 优先按文件名前缀识别核心函数，如 XBT_下摆凸.lsp -> xbt
            file_core_name = os.path.splitext(file_name)[0].split("_")[0].lower()
            core_func = None

            if file_core_name in func_map:
                f = func_map[file_core_name]
                if ":" not in f.name.lower() and f.name.lower() != "*error*":
                    core_func = f

            # 若未命中，再回退到第一个普通函数
            if not core_func:
                for func in functions:
                    name_lower = func.name.lower()
                    if ":" in name_lower or name_lower == "*error*":
                        continue
                    core_func = func
                    break

            if core_func:
                add_core_stub(core_func.name, core_func.params)

        # 3) 未找到可用入口时，直接 load 整个文件
        if not stubs:
            load_command = f'(progn (vl-load-com) (load "{lisp_path}") (princ (strcat "\\n>> " "{file_name}" " 已加载。")) (princ))'
        else:
            stubs_code = " ".join(stubs)
            load_command = f'(progn (vl-load-com) {stubs_code} (princ (strcat "\\n>> " "{file_name}" " 已注册桩函数。")) (princ))'
    
    try:
        # 动态等待文档就绪并发送加载命令
        import time
        for attempt in range(10):
            try:
                doc.Activate()
                doc.SendCommand(load_command + "\n")
                break
            except Exception as e:
                error_msg = str(e)
                if "-2147418111" in error_msg or "拒绝接收呼叫" in error_msg:
                    time.sleep(1 + attempt * 0.5)
                    continue
                raise
        
        # 等待命令执行完成
        time.sleep(2)
        
        if functions:
            _DOC_STUB_REGISTRY.setdefault(doc_key, set()).add(lisp_path)
        
        print(f"✓ LISP文件加载成功: {file_name}")
        return True
        
    except Exception as e:
        print(f"✗ LISP文件加载失败 {file_name}: {e}")
        return False
