#!/bin/bash

# Lua解码器启动脚本 (Linux/macOS)

echo "Lua解码器 v1.0.0"
echo "智能恢复unluac文件为Lua源码"
echo "=================================="

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查依赖是否安装
echo "检查依赖..."
if ! python3 -c "import requests, openai, pathlib2, colorama, tqdm, yaml" 2>/dev/null; then
    echo "安装依赖..."
    pip3 install -r requirements.txt
fi

# 检查配置文件
if [ ! -f "config/config.yaml" ]; then
    echo "错误: 配置文件不存在"
    echo "请先编辑 config/config.yaml 文件，设置OpenRouter API密钥"
    exit 1
fi

# 运行程序
echo "启动Lua解码器..."
python3 main.py "$@"
