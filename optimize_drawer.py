#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简化 drawer_manager.py 中的_execute_lisp 方法"""

with open(r'p:\AutoLISP_工装绘图项目\drawer_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 删除 _init_cad 方法
old_method = '''    def _init_cad(self):
        """初始化 CAD 连接"""
        if not self.acad:
            self.acad = find_autocad()
            self.acad.Visible = True
        return True
    
'''

content = content.replace(old_method, '')

# 简化_execute_lisp 方法
old_execute = '''    def _execute_lisp(self, lsp_file, func_name, params):
        """执行单个 LISP 文件"""
        # 初始化 CAD 连接（只初始化一次）
        if not self.acad:
            self._init_cad()'''

new_execute = '''    def _execute_lisp(self, lsp_file, func_name, params):
        """执行单个 LISP 文件（参考 MJA_迈均凹.py 的简洁写法）"""
        # 初始化 CAD 连接
        if not self.acad:
            self.acad = find_autocad()
            self.acad.Visible = True'''

content = content.replace(old_execute, new_execute)

# 删除多余的注释和代码
old_save = '''        # 自动保存文档
        if success:
            try:
                # 获取保存路径
                save_path = params.get("save_path", "")
                
                # 构建文件名'''

new_save = '''        # 自动保存文档
        if success:
            try:
                save_path = params.get("save_path", "")
                filename = f"{func_name}_{abs(float(params.get('r0', 0)))}.dwg"'''

content = content.replace(old_save, new_save)

old_filename = '''                filename = f"{func_name}_{abs(float(params.get('r0', 0)))}.dwg"
                full_path = os.path.join(save_path, filename)
                
                # 保存文档'''

new_filename = '''                full_path = os.path.join(save_path, filename)
                doc.SaveAs(full_path)'''

content = content.replace(old_filename, new_filename)

old_close = '''        # 保持文档打开，不关闭
        return success'''

new_close = '''        return success'''

content = content.replace(old_close, new_close)

with open(r'p:\AutoLISP_工装绘图项目\drawer_manager.py', 'w', encoding='utf-8') as f:
    f.write(content)
    
print('优化完成！')
