#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""参数管理器"""

class ParameterManager:
    def __init__(self):
        self.params = {}
        self.ui_params = {}
    
    def save_params(self, ui):
        """保存UI参数"""
        if hasattr(ui, 'get_params'):
            self.ui_params = ui.get_params()
            return True
        return False
    
    def load_params(self, ui):
        """加载UI参数"""
        if self.ui_params and hasattr(ui, 'set_params'):
            ui.set_params(self.ui_params)
            return True
        return False
    
    def set_param(self, key, value):
        """设置单个参数"""
        self.params[key] = value
    
    def get_param(self, key, default=None):
        """获取单个参数"""
        return self.params.get(key, default)
    
    def clear_params(self):
        """清除所有参数"""
        self.params.clear()
        self.ui_params.clear()
    
    def get_all_params(self):
        """获取所有参数"""
        return self.params.copy()
    
    def update_params(self, new_params):
        """更新参数"""
        self.params.update(new_params)