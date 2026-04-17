"""
下摆机工装设计计算工具 (Swing Machine Tooling Calculator)
版本: V1.0
作者: Zhoufan
日期: 2025-12-26

功能：
1. 从Excel中查找最接近的口径常数
2. 计算下摆机精磨基模R值和口径
3. 计算下摆机抛光基模R值和口径
4. 计算高速抛光修盘基模R值和口径
5. 计算基准模口径
6. 计算抛光基模修改模

注意事项：
- 请确保Excel文件路径正确
- 函数文件D_R_ratio2K_V1.py需在同一目录下或Python路径中
"""

import pandas as pd
import math
import os
import sys
from consult_table import find_best_constant_from_excel as constant_lookup


class SwingMachineToolingCalculator:
    """下摆机工装计算器类"""
    
    def __init__(self, R, blank_D, polyurethane_thickness=0.3, 
                 diamond_pellet_thickness=3, delta_arc=3):
        """
        初始化计算器
        
        参数:
            R: 镜片R值
            blank_D: 毛坯口径
            polyurethane_thickness: 聚氨酯厚度,默认0.3
            diamond_pellet_thickness: 金刚石丸片厚度,默认3
            delta_arc: 口径扩大时弧长增加量,默认4
        """
        self.R = R
        self.blank_D = blank_D
        self.polyurethane_thickness = polyurethane_thickness
        self.diamond_pellet_thickness = diamond_pellet_thickness
        self.delta_arc = delta_arc
        
        # 计算D/R系数
        self.D_R_ratio = blank_D / R if R != 0 else 0
        
        # 其他计算属性将在需要时计算
        self.K = None
        self.grind_D = None
        self.XJMJM_R = None
        self.XJMJM_Φ = None
        self.XPMJM_R = None
        self.XPMJM_Φ = None
        self.GPMXJ_R = None
        self.GPMXJ_Φ = None
        self.JZM_Φ = None
        
    def load_constant_from_excel(self, excel_path):
        """从Excel文件加载常数K"""
        self.K = constant_lookup(excel_path, self.D_R_ratio)
        self.grind_D = self.blank_D * self.K
        return self.K
        
    def calculate_XJMJM(self):
        """计算下摆机精磨基模"""
        #如果采用总型丸片
        self.XJMJM_R = -self.R
        #如果不采用总型丸片
        if not (abs(self.R) <= 11 or self.grind_D <= 18):
           #精磨丸片厚度按4算
           diamend_JM = self.diamond_pellet_thickness+1
           self.XJMJM_R = self.XJMJM_R - diamend_JM
        self.XJMJM_Φ = abs(self.XJMJM_R) * self.grind_D / abs(self.R)
        return self.XJMJM_R, self.XJMJM_Φ
        
    def calculate_XPMJM(self):
        """计算下摆机抛光基模"""
        if self.R > 0:
            self.XPMJM_R = -self.R - self.polyurethane_thickness
        else:
            self.XPMJM_R = abs(self.R + self.polyurethane_thickness)
            
        self.XPMJM_Φ = abs(self.XPMJM_R) * self.grind_D / abs(self.R)
        return self.XPMJM_R, self.XPMJM_Φ
        
    def calculate_GPMXJ(self):
        """计算高速抛光修盘基模"""
        R = self.R
        
        if abs(R) <= 11 or self.grind_D <= 18:
            self.GPMXJ_R = R
        else:
            self.GPMXJ_R = R - self.diamond_pellet_thickness
            
        Φ = abs(self.GPMXJ_R) * self.grind_D / abs(R)
        
        if abs(R) <= 11 or self.grind_D <= 18:
            self.GPMXJ_Φ=Φ
        else:
            θ = 2 * math.asin(Φ / (2 * R))
            arc = R * θ
            self.GPMXJ_Φ = 2 * R * math.sin((arc + self.delta_arc) / (2 * R))

        return self.GPMXJ_R, self.GPMXJ_Φ
        
    def calculate_JZM(self):
        """计算基准模口径"""
        if self.GPMXJ_Φ is None or self.GPMXJ_R is None:
            self.calculate_GPMXJ()
            
        self.JZM_JAZ_Φ = abs(self.R) * self.GPMXJ_Φ / abs(self.GPMXJ_R)
        # 按照弧长增量扩大口径
        R = self.GPMXJ_R
        θ = 2 * math.asin(self.JZM_JAZ_Φ / (2 * R))
        arc = R * θ

        self.JZM_WP_Φ = 2 * R * math.sin((arc + self.delta_arc) / (2 * R))

        return self.JZM_JAZ_Φ, self.JZM_WP_Φ
        
    def calculate_all(self, excel_path):
        """计算所有工装参数"""
        print("=" * 50)
        print("下摆机工装设计计算结果")
        print("=" * 50)
        
        # 1. 加载常数
        self.load_constant_from_excel(excel_path)
        print(f"镜片R值: {self.R}")
        print(f"毛坯口径: {self.blank_D}")
        print(f"D/R系数: {self.D_R_ratio:.3f}")
        print(f"常数K: {self.K:.3f}")
        print(f"精磨口径: {self.grind_D:.3f}")
        print("-" * 30)
        
        # 2. 计算下摆机精磨基模
        XJMJM_R, XJMJM_Φ = self.calculate_XJMJM()
        print(f"下摆机精磨基模R值: {XJMJM_R}")
        print(f"下摆机精磨基模口径: {XJMJM_Φ:.3f}")
        
        # 3. 计算下摆机抛光基模
        XPMJM_R, XPMJM_Φ = self.calculate_XPMJM()
        print(f"下摆机抛光模基模R值: {XPMJM_R}")
        print(f"下摆机抛光模基模口径: {XPMJM_Φ:.3f}")
        
        # 4. 计算高速抛光修盘基模
        GPMXJ_R, GPMXJ_Φ = self.calculate_GPMXJ()
        print(f"高速抛光修盘基模R值: {GPMXJ_R}")
        print(f"高速抛光修盘基模口径: {GPMXJ_Φ:.3f}")
        
        # 5. 计算基准模
        JZM_JAZ_Φ, JZM_WP_Φ = self.calculate_JZM()
        print(f"基准模压聚氨酯R值: {self.R}")
        print(f"基准模改丸片R值: -{self.R}")
        print(f"基准模压聚氨酯口径: {JZM_JAZ_Φ:.3f}")
        print(f"基准模改丸片口径: {JZM_WP_Φ:.3f}")
        
        # 6. 计算抛光基模修改模
        print(f"高速抛光模基模修盘R值: {-XPMJM_R}")
        print(f"高速抛光模基模修盘口径: {XPMJM_Φ:.3f}")
        print("=" * 50)
        
        # 返回所有计算结果
        results = {
            '镜片R值': self.R,
            '毛坯口径': self.blank_D,
            '常数K': self.K,
            '精磨口径': self.grind_D,
            '下摆机精磨基模R值': XJMJM_R,
            '下摆机精磨基模口径': XJMJM_Φ,
            '下摆机抛光基模R值': XPMJM_R,
            '下摆机抛光基模口径': XPMJM_Φ,
            '高速抛光修盘基模R值': GPMXJ_R,
            '高速抛光修盘基模口径': GPMXJ_Φ,
            '基准模压聚氨酯口径': JZM_JAZ_Φ,
            '基准模改丸片口径': JZM_WP_Φ,
            '高速抛光基模修盘R值': -XPMJM_R,
            '高速抛光基模修盘口径': XPMJM_Φ
        }
        
        return results


def main():
    """主函数 - 用于直接运行"""
    # 示例参数
    R = 52.704           # 镜片R值
    blank_D = 22         # 毛坯口径
    # 获取当前文件的目录，然后构建Excel文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(current_dir, "口径常数.xlsx")  # Excel文件路径
    
    # 创建计算器实例
    calculator = SwingMachineToolingCalculator(
        R=R,
        blank_D=blank_D,
        polyurethane_thickness=0.3,
        diamond_pellet_thickness=3,
        delta_arc=2
    )
    
    # 执行计算
    results = calculator.calculate_all(excel_path)
    
    return results


if __name__ == "__main__":
    # 直接运行时的入口点
    main()