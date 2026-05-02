@echo off
chcp 65001 >nul
echo ==========================================
echo      AutoCAD控制器
echo ==========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请确保Python已安装并添加到系统PATH
    pause
    exit /b 1
)

echo Python已安装
echo.

REM 检查pywin32是否安装
python -c "import win32com.client" >nul 2>&1
if errorlevel 1 (
    echo 正在安装必要的依赖库...
    pip install pywin32
    if errorlevel 1 (
        echo 错误: 无法安装依赖库，请手动运行: pip install pywin32
        pause
        exit /b 1
    )
)

echo 依赖库已就绪
echo.
echo 正在启动AutoCAD控制器...
echo ==========================================
echo.

REM 运行脚本
cd /d "%~dp0"
python autocad_controller.py

echo.
echo ==========================================
pause
