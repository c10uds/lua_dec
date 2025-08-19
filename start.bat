@echo off
REM Lua解码器启动脚本 (Windows)

echo Lua解码器 v1.0.0
echo 智能恢复unluac文件为Lua源码
echo ==================================

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python
    pause
    exit /b 1
)

REM 检查依赖是否安装
echo 检查依赖...
python -c "import requests, openai, pathlib2, colorama, tqdm, yaml" >nul 2>&1
if errorlevel 1 (
    echo 安装依赖...
    pip install -r requirements.txt
)

REM 检查配置文件
if not exist "config\config.yaml" (
    echo 错误: 配置文件不存在
    echo 请先编辑 config\config.yaml 文件，设置OpenRouter API密钥
    pause
    exit /b 1
)

REM 运行程序
echo 启动Lua解码器...
python main.py %*

pause
