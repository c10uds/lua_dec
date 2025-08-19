#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lua模块路径解析器
负责将Lua模块名转换为对应的文件路径
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple
import platform


class LuaModuleResolver:
    """Lua模块路径解析器"""
    
    def __init__(self, base_paths: List[str] = None):
        """
        初始化解析器
        
        Args:
            base_paths: Lua模块的基础路径列表
        """
        if base_paths is None:
            # 默认路径，适配不同操作系统
            if platform.system() == "Windows":
                self.base_paths = [
                    "lua",
                    "C:\\lua",
                    "C:\\Program Files\\lua"
                ]
            elif platform.system() == "Darwin":  # macOS
                self.base_paths = [
                    "lua",
                    "/usr/local/lib/lua",
                    "/opt/lua",
                    "/usr/lib/lua"
                ]
            else:  # Linux
                self.base_paths = [
                    "lua",
                    "/usr/lib/lua",
                    "/usr/local/lib/lua",
                    "/opt/lua"
                ]
        else:
            self.base_paths = base_paths
    
    def resolve_module_to_path(self, module_name: str) -> Optional[Path]:
        """
        将Lua模块名解析为文件路径
        
        Args:
            module_name: Lua模块名，如 "luci.controller.api.xqnetwork"
            
        Returns:
            对应的文件路径，如果找不到则返回None
        """
        # 将模块名转换为路径
        path_parts = module_name.split('.')
        
        # 尝试不同的文件扩展名，优先处理 .lua.unluac 文件
        extensions = ['.lua.unluac', '.lua', '.so', '.dll', '.dylib']
        
        for base_path in self.base_paths:
            base_path_obj = Path(base_path)
            
            # 构建完整路径
            for ext in extensions:
                # 方法1: 直接拼接路径
                file_path = base_path_obj / '/'.join(path_parts) / ext.lstrip('.')
                if file_path.exists():
                    return file_path
                
                # 方法2: 使用os.path.join (更兼容)
                file_path = Path(os.path.join(base_path, *path_parts) + ext)
                if file_path.exists():
                    return file_path
        
        return None
    
    def find_module_file(self, module_name: str, search_paths: List[str] = None) -> Optional[Path]:
        """
        在指定路径中查找模块文件
        
        Args:
            module_name: 模块名
            search_paths: 搜索路径列表
            
        Returns:
            找到的文件路径
        """
        if search_paths is None:
            search_paths = self.base_paths
        
        # 将模块名转换为可能的文件名
        module_parts = module_name.split('.')
        
        # 尝试不同的文件名格式
        possible_names = [
            '.'.join(module_parts),  # luci.controller.api.xqnetwork
            module_parts[-1],        # xqnetwork
            '_'.join(module_parts),  # luci_controller_api_xqnetwork
        ]
        
        for search_path in search_paths:
            search_path_obj = Path(search_path)
            
            for name in possible_names:
                # 尝试不同的扩展名
                for ext in ['.lua', '.so', '.dll', '.dylib']:
                    file_path = search_path_obj / f"{name}{ext}"
                    if file_path.exists():
                        return file_path
                    
                    # 尝试在子目录中查找
                    for root, dirs, files in os.walk(search_path):
                        for file in files:
                            if file == f"{name}{ext}":
                                return Path(root) / file
        
        return None
    
    def get_module_dependencies(self, file_path: Path) -> List[str]:
        """
        从Lua文件中提取require语句
        
        Args:
            file_path: Lua文件路径
            
        Returns:
            require的模块名列表
        """
        dependencies = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # 简单的正则匹配require语句
            import re
            
            # 匹配 require("module.name") 或 require 'module.name'
            require_patterns = [
                r'require\s*\(\s*["\']([^"\']+)["\']\s*\)',
                r'require\s+["\']([^"\']+)["\']',
            ]
            
            for pattern in require_patterns:
                matches = re.findall(pattern, content)
                dependencies.extend(matches)
                
        except Exception as e:
            print(f"读取文件 {file_path} 时出错: {e}")
        
        return list(set(dependencies))  # 去重
    
    def add_search_path(self, path: str):
        """添加搜索路径"""
        if path not in self.base_paths:
            self.base_paths.append(path)
    
    def remove_search_path(self, path: str):
        """移除搜索路径"""
        if path in self.base_paths:
            self.base_paths.remove(path)
    
    def get_search_paths(self) -> List[str]:
        """获取所有搜索路径"""
        return self.base_paths.copy()


def test_resolver():
    """测试解析器功能"""
    resolver = LuaModuleResolver()
    
    # 测试模块解析
    test_modules = [
        "luci.controller.api.xqnetwork",
        "luci.http",
        "nixio.fs"
    ]
    
    print("测试Lua模块解析器:")
    print("=" * 50)
    
    for module in test_modules:
        path = resolver.resolve_module_to_path(module)
        print(f"模块: {module}")
        print(f"路径: {path}")
        print("-" * 30)


if __name__ == "__main__":
    test_resolver()
