#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lua解码器示例运行脚本
演示如何使用LuaDecoder类
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from lua_decoder import LuaDecoder
import colorama
from colorama import Fore, Style


def create_sample_files():
    """创建示例文件用于测试"""
    print(f"{Fore.CYAN}创建示例文件...{Style.RESET_ALL}")
    
    # 创建示例目录
    sample_dir = Path("sample_files")
    sample_dir.mkdir(exist_ok=True)
    
    # 创建示例Lua文件
    sample_files = {
        "main.lua": '''
-- 主模块文件
local http = require("luci.http")
local fs = require("nixio.fs")

local function main()
    print("Hello from main module")
    local data = http.get_data()
    fs.write_file("/tmp/test.txt", data)
end

main()
''',
        "luci/http.lua": '''
-- HTTP模块
local http = {}

function http.get_data()
    return "sample data"
end

return http
''',
        "nixio/fs.lua": '''
-- 文件系统模块
local fs = {}

function fs.write_file(path, content)
    print("Writing to: " .. path)
    print("Content: " .. content)
end

return fs
'''
    }
    
    for file_path, content in sample_files.items():
        full_path = sample_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content.strip())
        
        print(f"  创建: {full_path}")
    
    return sample_dir


def run_example():
    """运行示例"""
    print(f"{Fore.CYAN}Lua解码器示例{Style.RESET_ALL}")
    print("=" * 50)
    
    # 创建示例文件
    sample_dir = create_sample_files()
    
    # 检查配置文件
    config_file = Path("config/config.yaml")
    if not config_file.exists():
        print(f"{Fore.RED}错误: 配置文件不存在，请先配置OpenRouter API密钥{Style.RESET_ALL}")
        print(f"请编辑 {config_file} 文件，设置你的API密钥")
        return
    
    try:
        # 创建解码器实例
        print(f"\n{Fore.GREEN}初始化Lua解码器...{Style.RESET_ALL}")
        decoder = LuaDecoder(str(config_file))
        
        # 运行解码流程
        print(f"{Fore.GREEN}开始分析示例文件...{Style.RESET_ALL}")
        decoder.run(
            start_file=str(sample_dir / "main.lua"),
            unluac_dir=str(sample_dir),
            output_dir="example_output"
        )
        
        print(f"\n{Fore.GREEN}示例运行完成！{Style.RESET_ALL}")
        print(f"请查看 example_output 目录中的结果")
        
    except Exception as e:
        print(f"\n{Fore.RED}运行示例时出错: {e}{Style.RESET_ALL}")
        print(f"请检查配置文件中的API密钥设置")


def test_components():
    """测试各个组件"""
    print(f"\n{Fore.CYAN}测试各个组件...{Style.RESET_ALL}")
    
    try:
        from lua_module_resolver import LuaModuleResolver
        from dependency_graph import DependencyGraph
        
        # 测试模块解析器
        print(f"{Fore.YELLOW}测试模块解析器...{Style.RESET_ALL}")
        resolver = LuaModuleResolver()
        test_modules = ["luci.controller.api.xqnetwork", "luci.http", "nixio.fs"]
        
        for module in test_modules:
            path = resolver.resolve_module_to_path(module)
            print(f"  {module} -> {path}")
        
        # 测试依赖图
        print(f"\n{Fore.YELLOW}测试依赖图...{Style.RESET_ALL}")
        graph = DependencyGraph()
        graph.add_file("test1.lua", "module1")
        graph.add_file("test2.lua", "module2")
        graph.add_dependency("test1.lua", "module2")
        
        print("  依赖图结构:")
        graph.print_graph()
        
        print(f"\n{Fore.GREEN}组件测试完成！{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}组件测试失败: {e}{Style.RESET_ALL}")


if __name__ == "__main__":
    # 初始化颜色输出
    colorama.init()
    
    print("选择运行模式:")
    print("1. 运行完整示例")
    print("2. 测试组件")
    print("3. 退出")
    
    try:
        choice = input("\n请输入选择 (1-3): ").strip()
        
        if choice == "1":
            run_example()
        elif choice == "2":
            test_components()
        elif choice == "3":
            print("退出程序")
        else:
            print("无效选择")
            
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}用户中断{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}发生错误: {e}{Style.RESET_ALL}")
