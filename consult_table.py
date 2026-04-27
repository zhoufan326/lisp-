import pandas as pd
import os
import sys

# 设置输出编码为UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
"""
常数查找工具模块

功能：
1. 从Excel中查找最接近的口径常数
2. 支持多组数据匹配

作者：Zhoufan
版本：V1.0
日期：2025-12-26
"""

def find_best_constant_from_excel(file_path, target_ratio):
    """
    从Excel中查找最接近的口径常数值
    
    参数:
        file_path: Excel文件路径
        target_ratio: 目标D/R系数
    
    返回:
        最接近的常数值
    """
    # 读取Excel文件
    df = pd.read_excel(file_path)
    
    # 收集所有数据
    all_data = []
    
    # 遍历三组数据
    for i in range(3):
        ratio_col = 'D/R系数' if i == 0 else f'D/R系数.{i}'
        const_col = '常数' if i == 0 else f'常数.{i}'
        
        if ratio_col in df.columns and const_col in df.columns:
            # 提取非空数据
            valid_data = df[[ratio_col, const_col]].dropna()
            
            for idx, (ratio_val, const_val) in valid_data.iterrows():
                all_data.append({
                    '组别': i+1,
                    '行号': idx+2,
                    'D/R系数': ratio_val,
                    '常数': const_val,
                    '差值': abs(ratio_val - target_ratio)
                })
    
    # 如果没有数据
    if not all_data:
        print("❌ 没有有效数据")
        return None
    
    # 查找最接近的值
    data_df = pd.DataFrame(all_data)
    closest = data_df.loc[data_df['差值'].idxmin()]
    
    # 输出结果
    if closest['差值'] == 0:
        match_type = "精确匹配"
    else:
        match_type = f"近似匹配（差值={closest['差值']:.6f}）"
    
    print(f"{match_type}:")
    print(f"  第{int(closest['组别'])}组，行{int(closest['行号'])}",f"  D/R系数: {closest['D/R系数']}",f"  常数: {closest['常数']}")

    
    return closest['常数']

if __name__ == '__main__':
# 使用示例
# 这里是测试代码，当直接运行这个文件时执行
# 但被其他文件导入时不会执行
    D_R_ratio = 1.92
    # 获取当前文件的目录，然后构建Excel文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(current_dir, "口径常数.xlsx")
    result = find_best_constant_from_excel(excel_path, D_R_ratio)

    if result is not None:
        print(f"\n📋 当 D/R系数={D_R_ratio} 时，使用常数: {result}")