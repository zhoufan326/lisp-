#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重试装饰器模块
提供带指数退避的重试机制，用于处理AutoCAD响应延迟问题
"""

import time
import functools


def retry_with_backoff(max_attempts=3, initial_delay=1, backoff_factor=1, 
                       exceptions=(Exception,), on_retry=None):
    """
    重试装饰器，支持指数退避策略
    
    参数:
        max_attempts: 最大尝试次数，默认为3
        initial_delay: 初始延迟时间（秒），默认为1
        backoff_factor: 退避因子，每次重试后延迟时间增加的量，默认为1
        exceptions: 需要捕获的异常类型元组，默认为所有Exception
        on_retry: 重试时的回调函数，接收(attempt, exception, delay)参数
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        # 最后一次尝试失败，抛出异常
                        print(f"函数 {func.__name__} 在 {max_attempts} 次尝试后仍然失败")
                        raise last_exception
                    
                    # 计算下次重试的延迟时间
                    current_delay = delay + (attempt - 1) * backoff_factor
                    
                    # 调用重试回调（如果提供）
                    if on_retry:
                        on_retry(attempt, e, current_delay)
                    else:
                        print(f"函数 {func.__name__} 第 {attempt} 次尝试失败: {e}")
                        print(f"等待 {current_delay} 秒后重试...")
                    
                    # 等待后重试
                    time.sleep(current_delay)
            
            # 理论上不会执行到这里
            raise last_exception if last_exception else RuntimeError("未知错误")
        
        return wrapper
    return decorator


def retry_on_autocad_error(max_attempts=3, initial_delay=1):
    """
    专门用于AutoCAD操作的重试装饰器
    捕获常见的AutoCAD COM错误
    
    参数:
        max_attempts: 最大尝试次数，默认为3
        initial_delay: 初始延迟时间（秒），默认为1
    """
    # AutoCAD常见的COM错误代码
    autocad_exceptions = (
        Exception,
        # Windows COM错误
        type("COMError", (Exception,), {}),
    )
    
    def on_retry(attempt, exception, delay):
        """重试时的回调函数"""
        error_msg = str(exception)
        
        # 检查是否是"被呼叫方拒绝接收呼叫"错误
        if "被呼叫方拒绝接收呼叫" in error_msg or "-2147418111" in error_msg:
            pass  # 不打印繁忙信息，静默重试
        elif "输入无效" in error_msg or "-2145386493" in error_msg:
            pass  # 不打印输入无效信息，静默重试
        elif "发生意外" in error_msg or "-2147352567" in error_msg:
            pass  # 不打印意外错误信息，静默重试
        else:
            pass  # 其他错误也不打印，静默重试
    
    return retry_with_backoff(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        backoff_factor=2,  # 每次增加2秒，给CAD更多时间恢复
        exceptions=Exception,  # 捕获所有异常
        on_retry=on_retry
    )


# 便捷装饰器，使用默认参数
retry_3_times = retry_with_backoff(max_attempts=3, initial_delay=1, backoff_factor=1)


if __name__ == "__main__":
    # 测试代码
    @retry_with_backoff(max_attempts=3, initial_delay=1, backoff_factor=1)
    def test_function():
        import random
        if random.random() < 0.7:
            raise Exception("模拟错误")
        return "成功"
    
    try:
        result = test_function()
        print(f"结果: {result}")
    except Exception as e:
        print(f"最终失败: {e}")
