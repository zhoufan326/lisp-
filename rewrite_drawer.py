#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重写 drawer_manager.py 中的_execute_lisp 方法"""

with open(r'p:\AutoLISP_工装绘图项目\drawer_manager.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到并替换_execute_lisp 方法
new_lines = []
skip_until_next_def = False
in_execute_lisp = False
execute_lisp_written = False

i = 0
while i < len(lines):
    line = lines[i]
    
    # 检测是否进入_execute_lisp 方法
    if 'def _execute_lisp(self' in line:
        in_execute_lisp = True
        # 写入新的_execute_lisp 方法
        new_lines.append('    def _execute_lisp(self, lsp_file, func_name, params):\n')
        new_lines.append('        """执行单个 LISP 文件（参考 MJA_迈均凹.py 的简洁写法）"""\n')
        new_lines.append('        # 初始化 CAD 连接\n')
        new_lines.append('        if not self.acad:\n')
        new_lines.append('            self.acad = find_autocad()\n')
        new_lines.append('            self.acad.Visible = True\n')
        new_lines.append('\n')
        new_lines.append('        # 新建图形文档\n')
        new_lines.append('        doc = apply_template(self.acad, self.template_path, None)\n')
        new_lines.append('        doc.Activate()\n')
        new_lines.append('\n')
        new_lines.append('        # 加载 LISP 文件\n')
        new_lines.append('        self._load_lisp_files(lsp_file)\n')
        new_lines.append('\n')
        new_lines.append('        # 构建参数\n')
        new_lines.append('        args = self._build_args(func_name, params)\n')
        new_lines.append('\n')
        new_lines.append('        # 直接调用 run_lisp，参考 MJA_迈均凹.py 的调用方式\n')
        new_lines.append('        success = run_lisp(self.acad, func_name, args, True)\n')
        new_lines.append('\n')
        new_lines.append('        # 自动保存文档\n')
        new_lines.append('        if success:\n')
        new_lines.append('            try:\n')
        new_lines.append('                save_path = params.get("save_path", "")\n')
        new_lines.append('                filename = f"{func_name}_{abs(float(params.get(\'r0\', 0)))}.dwg"\n')
        new_lines.append('                full_path = os.path.join(save_path, filename)\n')
        new_lines.append('                doc.SaveAs(full_path)\n')
        new_lines.append('                print(f"✓ 文档已自动保存到：{full_path}")\n')
        new_lines.append('            except Exception as e:\n')
        new_lines.append('                print(f"⚠ 自动保存失败：{e}")\n')
        new_lines.append('\n')
        new_lines.append('        return success\n')
        new_lines.append('\n')
        execute_lisp_written = True
        skip_until_next_def = True
        i += 1
        continue
    
    # 跳过旧的_execute_lisp 方法的剩余部分
    if skip_until_next_def:
        if line.strip().startswith('def ') and not line.strip().startswith('def _execute_lisp'):
            skip_until_next_def = False
            # 不跳过这个新方法的定义
        else:
            i += 1
            continue
    
    new_lines.append(line)
    i += 1

with open(r'p:\AutoLISP_工装绘图项目\drawer_manager.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('重写完成！')
