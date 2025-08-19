#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lua解码器主程序入口
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src import LuaDecoder
import colorama
from colorama import Fore, Style

def main():
    """主函数"""
    # 初始化颜色输出
    colorama.init()
    
    print(f"{Fore.CYAN}Lua解码器 v1.0.0{Style.RESET_ALL}")
    print(f"{Fore.CYAN}智能恢复unluac文件为Lua源码{Style.RESET_ALL}")
    print("=" * 60)
    
    # 检查命令行参数
    if len(sys.argv) < 3:
        print(f"{Fore.YELLOW}用法: python main.py <起始文件> <unluac目录> [输出目录] [配置文件]{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}示例: python main.py ./test.lua ./unluac_files output config/config.yaml{Style.RESET_ALL}")
        print()
        print("参数说明:")
        print("  起始文件: 要分析的起始Lua文件路径")
        print("  unluac目录: 包含所有unluac文件的目录")
        print("  输出目录: 恢复后代码的输出目录 (可选，默认: output)")
        print("  配置文件: 配置文件路径 (可选，默认: config/config.yaml)")
        return
    
    # 解析参数
    start_file = sys.argv[1]
    unluac_dir = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "output"
    config_file = sys.argv[4] if len(sys.argv) > 4 else "config/config.yaml"
    
    # 验证文件路径
    if not os.path.exists(start_file):
        print(f"{Fore.RED}错误: 起始文件不存在: {start_file}{Style.RESET_ALL}")
        return
    
    if not os.path.exists(unluac_dir):
        print(f"{Fore.RED}错误: unluac目录不存在: {unluac_dir}{Style.RESET_ALL}")
        return
    
    if not os.path.exists(config_file):
        print(f"{Fore.RED}错误: 配置文件不存在: {config_file}{Style.RESET_ALL}")
        return
    
    try:
        # 创建解码器实例
        print(f"{Fore.GREEN}正在初始化Lua解码器...{Style.RESET_ALL}")
        decoder = LuaDecoder(config_file)
        
        # 运行解码流程
        print(f"{Fore.GREEN}开始运行解码流程...{Style.RESET_ALL}")
        decoder.run(start_file, unluac_dir, output_dir)
        
        print(f"\n{Fore.GREEN}解码完成！{Style.RESET_ALL}")
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}用户中断操作{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}发生错误: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
