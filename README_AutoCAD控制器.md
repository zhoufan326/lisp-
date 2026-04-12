# AutoCAD控制器使用说明

## 功能概述

这个Python脚本可以自动：
1. 打开或连接到AutoCAD
2. 应用指定的图形样板文件
3. 加载项目文件夹中的所有LISP文件
4. 运行XBA函数

## 环境要求

- Windows操作系统
- 已安装AutoCAD（支持AutoCAD 2010及以上版本）
- Python 3.6或更高版本
- pywin32库

## 安装步骤

### 1. 安装Python
确保系统已安装Python 3.6或更高版本。

### 2. 安装依赖库

在项目文件夹中打开命令提示符或PowerShell，运行：

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install pywin32
```

## 使用方法

### 方法一：直接运行

在项目文件夹中打开命令提示符或PowerShell，运行：

```bash
python autocad_controller.py
```

### 方法二：创建批处理文件

创建一个批处理文件`run_autocad.bat`，内容如下：

```batch
@echo off
cd /d "P:\AutoLISP_工装绘图项目"
python autocad_controller.py
pause
```

双击运行`run_autocad.bat`即可。

## 配置说明

脚本中的配置项位于`main()`函数中：

```python
# 配置路径
project_folder = r"P:\AutoLISP_工装绘图项目"
template_path = r"P:\AutoLISP_工装绘图项目\LISP图样.dwt"
```

如果需要修改路径，请编辑`autocad_controller.py`文件中的这些变量。

## 工作原理

1. **连接AutoCAD**: 脚本首先尝试连接已运行的AutoCAD实例，如果没有则创建新实例
2. **应用样板**: 使用AutoCAD的Documents.Add方法创建基于指定样板的新文档
3. **加载LISP**: 遍历项目文件夹中的所有`.lsp`文件，使用AutoCAD的LOAD函数加载
4. **运行函数**: 发送命令`(xba)`运行XBA函数

## 注意事项

1. **AutoCAD版本**: 确保AutoCAD版本支持COM自动化（AutoCAD 2010及以上版本）
2. **样板文件**: 确保`LISP图样.dwt`文件存在于指定路径
3. **LISP文件**: 确保项目文件夹中的LISP文件没有语法错误
4. **权限**: 确保有足够的权限运行AutoCAD和访问项目文件夹

## 故障排除

### 问题1: "无法启动AutoCAD"
- 确保AutoCAD已正确安装
- 检查AutoCAD的COM接口是否启用

### 问题2: "无法应用指定样板"
- 检查样板文件路径是否正确
- 确保样板文件存在且未损坏

### 问题3: "无法加载LISP文件"
- 检查LISP文件是否有语法错误
- 确保文件路径中没有特殊字符

### 问题4: "无法运行XBA函数"
- 确保XBA函数已正确定义在LISP文件中
- 检查函数名称是否正确（区分大小写）

## 自定义扩展

可以根据需要修改脚本以支持更多功能：

- 修改`run_lisp_function()`函数以运行其他LISP函数
- 添加参数传递功能
- 添加错误处理和日志记录
- 添加图形导出功能

## 技术支持

如有问题，请检查：
1. AutoCAD是否正确安装
2. Python环境是否正常
3. pywin32库是否正确安装
4. 文件路径是否正确
