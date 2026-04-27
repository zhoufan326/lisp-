#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""错误处理器"""
import tkinter as tk
from tkinter import messagebox
import logging
import traceback

class ErrorHandler:
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.ERROR)
        
        # 创建文件处理器
        file_handler = logging.FileHandler('autocad_error.log', encoding='utf-8')
        file_handler.setLevel(logging.ERROR)
        
        # 创建格式化器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # 添加处理器
        self.logger.addHandler(file_handler)
    
    def show_error(self, title, message):
        """显示错误消息"""
        if self.app:
            self.app.after(0, lambda: messagebox.showerror(title, message))
        else:
            messagebox.showerror(title, message)
    
    def show_warning(self, title, message):
        """显示警告消息"""
        if self.app:
            self.app.after(0, lambda: messagebox.showwarning(title, message))
        else:
            messagebox.showwarning(title, message)
    
    def show_info(self, title, message):
        """显示信息消息"""
        if self.app:
            self.app.after(0, lambda: messagebox.showinfo(title, message))
        else:
            messagebox.showinfo(title, message)
    
    def handle_exception(self, e, context=None):
        """处理异常"""
        error_msg = str(e)
        full_msg = f"错误: {error_msg}"
        
        if context:
            full_msg += f"\n上下文: {context}"
        
        # 记录日志
        self.logger.error(full_msg, exc_info=True)
        
        # 显示错误消息
        self.show_error("错误", error_msg)
    
    def log_error(self, message, exc_info=False):
        """记录错误日志"""
        self.logger.error(message, exc_info=exc_info)
    
    def log_warning(self, message):
        """记录警告日志"""
        self.logger.warning(message)
    
    def log_info(self, message):
        """记录信息日志"""
        self.logger.info(message)