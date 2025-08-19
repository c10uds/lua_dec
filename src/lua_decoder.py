#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lua解码器主类
整合所有功能，实现智能Lua代码恢复
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from tqdm import tqdm
import colorama
from colorama import Fore, Style

from lua_module_resolver import LuaModuleResolver
from llm_client import OpenRouterClient
from dependency_graph import DependencyGraph


class LuaDecoder:
    """Lua解码器主类"""
    
    def __init__(self, config_file: str = "config/config.yaml"):
        """
        初始化解码器
        
        Args:
            config_file: 配置文件路径
        """
        # 初始化颜色输出
        colorama.init()
        
        # 设置日志
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # 加载配置
        self.config = self._load_config(config_file)
        
        # 初始化组件
        self.resolver = LuaModuleResolver(self.config.get('lua_paths', []))
        self.llm_client = OpenRouterClient(
            api_key=self.config['openrouter']['api_key'],
            base_url=self.config['openrouter']['base_url'],
            model=self.config['openrouter']['model']
        )
        self.dependency_graph = DependencyGraph()
        
        # 状态跟踪
        self.processed_files = set()
        self.failed_files = set()
        self.restored_files = set()
        
        self.logger.info("Lua解码器初始化完成")
    
    def _setup_logging(self):
        """设置日志系统"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "lua_decoder.log", encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 验证必要的配置
            required_keys = ['openrouter.api_key', 'openrouter.base_url', 'openrouter.model']
            for key in required_keys:
                if not self._get_nested_value(config, key):
                    raise ValueError(f"缺少必要的配置项: {key}")
            
            return config
            
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            raise
    
    def _get_nested_value(self, data: Dict, key_path: str):
        """获取嵌套字典中的值"""
        keys = key_path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def analyze_file_dependencies(self, file_path: Path) -> Dict[str, Any]:
        """
        分析文件的依赖关系
        
        Args:
            file_path: 要分析的文件路径
            
        Returns:
            分析结果字典
        """
        self.logger.info(f"开始分析文件依赖: {file_path}")
        
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 使用LLM分析依赖
            analysis_result = self.llm_client.analyze_lua_file(file_path, content)
            
            if 'error' in analysis_result:
                self.logger.error(f"分析文件 {file_path} 失败: {analysis_result['error']}")
                return analysis_result
            
            # 添加到依赖图
            module_name = self._extract_module_name(file_path)
            self.dependency_graph.add_file(file_path, module_name, content)
            
            # 处理依赖关系
            requires = analysis_result.get('requires', [])
            for req_module in requires:
                self.dependency_graph.add_dependency(file_path, req_module)
                
                # 尝试解析依赖模块的文件路径
                dep_file = self.resolver.resolve_module_to_path(req_module)
                if dep_file and dep_file.exists():
                    self.logger.info(f"找到依赖模块文件: {req_module} -> {dep_file}")
                else:
                    self.logger.warning(f"未找到依赖模块文件: {req_module}")
            
            self.processed_files.add(str(file_path))
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"分析文件 {file_path} 时出错: {e}")
            self.failed_files.add(str(file_path))
            return {"error": str(e)}
    
    def _extract_module_name(self, file_path: Path) -> str:
        """从文件路径提取模块名"""
        # 尝试从路径推断模块名
        parts = list(file_path.parts)
        
        # 查找lua目录
        try:
            lua_index = parts.index('lua')
            module_parts = parts[lua_index + 1:]
            # 移除.lua.unluac或.lua扩展名
            if module_parts and module_parts[-1].endswith('.lua.unluac'):
                module_parts[-1] = module_parts[-1][:-10]  # 移除 .lua.unluac
            elif module_parts and module_parts[-1].endswith('.lua'):
                module_parts[-1] = module_parts[-1][:-4]   # 移除 .lua
            return '.'.join(module_parts)
        except ValueError:
            # 如果没有找到lua目录，使用文件名
            filename = file_path.stem
            # 如果文件名以.lua结尾，移除它
            if filename.endswith('.lua'):
                filename = filename[:-4]
            return filename
    
    def discover_dependencies_recursively(self, start_file: Path, max_depth: int = 10):
        """
        递归发现所有依赖
        
        Args:
            start_file: 起始文件
            max_depth: 最大递归深度
        """
        self.logger.info(f"开始递归发现依赖，起始文件: {start_file}")
        
        files_to_process = [(start_file, 0)]  # (文件路径, 深度)
        processed = set()
        
        with tqdm(desc="发现依赖", unit="文件") as pbar:
            while files_to_process:
                current_file, depth = files_to_process.pop(0)
                current_file_str = str(current_file)
                
                if current_file_str in processed or depth > max_depth:
                    continue
                
                processed.add(current_file_str)
                pbar.set_description(f"分析文件: {current_file.name}")
                
                                # 分析当前文件
                analysis_result = self.analyze_file_dependencies(current_file)
                
                # 初始化requires变量
                requires = []
                if 'error' not in analysis_result:
                    # 获取依赖的模块
                    requires = analysis_result.get('requires', [])
                
                # 查找依赖文件并添加到处理队列
                for req_module in requires:
                    if depth < max_depth:
                        # 首先尝试标准路径解析
                        dep_file = self.resolver.resolve_module_to_path(req_module)
                        if dep_file and dep_file.exists() and str(dep_file) not in processed:
                            files_to_process.append((dep_file, depth + 1))
                            continue
                        
                        # 在unluac目录中查找依赖文件，优先查找 .lua.unluac 文件
                        for search_path in self.resolver.base_paths:
                            search_path_obj = Path(search_path)
                            if search_path_obj.exists():
                                # 将模块名转换为可能的文件路径，优先查找 .lua.unluac 文件
                                module_parts = req_module.split('.')
                                possible_paths = [
                                    search_path_obj / '/'.join(module_parts) / f"{module_parts[-1]}.lua.unluac",
                                    search_path_obj / '/'.join(module_parts) / f"{module_parts[-1]}.lua",
                                    search_path_obj / f"{module_parts[-1]}.lua.unluac",
                                    search_path_obj / f"{module_parts[-1]}.lua"
                                ]
                                
                                for possible_path in possible_paths:
                                    if possible_path.exists() and str(possible_path) not in processed:
                                        # 只处理 .lua.unluac 文件
                                        if possible_path.name.endswith('.lua.unluac'):
                                            self.logger.info(f"在搜索路径中找到依赖文件: {req_module} -> {possible_path}")
                                            files_to_process.append((possible_path, depth + 1))
                                            break
                                        elif possible_path.name.endswith('.lua') and not possible_path.name.endswith('.lua.unluac'):
                                            # 跳过普通的 .lua 文件，只处理 .lua.unluac
                                            continue
                                break
                
                pbar.update(1)
        
        self.logger.info(f"依赖发现完成，共处理 {len(processed)} 个文件")
    
    def restore_code_in_order(self, output_dir: str = "output"):
        """
        按依赖顺序恢复代码
        
        Args:
            output_dir: 输出目录
        """
        self.logger.info("开始按依赖顺序恢复代码")
        
        # 获取恢复顺序
        if not self.dependency_graph.graph:
            self.logger.warning("依赖图为空，无法进行代码恢复")
            return
        
        # 检测循环依赖
        cycles = self.dependency_graph.detect_cycles()
        if cycles:
            self.logger.warning(f"检测到循环依赖: {cycles}")
        
        # 获取拓扑排序结果
        restoration_order = self.dependency_graph.topological_sort()
        
        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 按顺序恢复代码
        with tqdm(restoration_order, desc="恢复代码", unit="文件") as pbar:
            for file_path in pbar:
                pbar.set_description(f"恢复: {Path(file_path).name}")
                
                try:
                    self._restore_single_file(file_path, output_path)
                    self.restored_files.add(file_path)
                except Exception as e:
                    self.logger.error(f"恢复文件 {file_path} 失败: {e}")
                    self.failed_files.add(file_path)
        
        self.logger.info(f"代码恢复完成，成功恢复 {len(self.restored_files)} 个文件")
        
        # 导出依赖图
        self.dependency_graph.export_dot(str(output_path / "dependencies.dot"))
        # 导出JSON格式的依赖关系
        self.dependency_graph.export_json(str(output_path / "dependencies.json"))
        
        # 生成报告
        self._generate_report(output_path)
    
    def _restore_single_file(self, file_path: str, output_dir: Path):
        """恢复单个文件，保持原有目录结构"""
        file_path_obj = Path(file_path)
        
        # 获取文件内容
        content = self.dependency_graph.file_contents.get(file_path, "")
        if not content:
            # 如果缓存中没有，重新读取
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                self.logger.error(f"读取文件 {file_path} 失败: {e}")
                return
        
        # 获取依赖信息
        dependencies = list(self.dependency_graph.get_dependencies(Path(file_path)))
        dep_modules = []
        for dep in dependencies:
            module_name = self.dependency_graph.file_to_module.get(dep, "")
            if module_name:
                dep_modules.append(module_name)
        
        # 使用LLM恢复代码
        restored_code = self.llm_client.restore_lua_code(
            file_path_obj, content, dep_modules
        )
        
        if not restored_code:
            self.logger.warning(f"文件 {file_path} 恢复失败，使用原始内容")
            restored_code = content
        
        # 构建输出文件路径，保持原有目录结构
        # 计算相对于当前工作目录的路径
        try:
            relative_path = file_path_obj.relative_to(Path.cwd())
        except ValueError:
            # 如果无法计算相对路径，使用文件名
            relative_path = Path(file_path_obj.name)
        
        # 处理 .lua.unluac 文件，替换为 .lua
        if relative_path.suffixes == ['.lua', '.unluac']:
            # 移除 .lua.unluac 扩展名，只保留 .lua
            # 构建新的文件名：移除最后两个扩展名，然后添加 .lua
            new_name = relative_path.stem  # 移除 .lua.unluac
            if new_name.endswith('.lua'):
                new_name = new_name[:-4]  # 再移除 .lua
            output_file = output_dir / relative_path.parent / f"{new_name}.lua"
        else:
            output_file = output_dir / relative_path
        
        # 确保输出目录存在
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存恢复后的代码
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(restored_code)
        
        self.logger.info(f"文件 {file_path} 恢复完成，保存到 {output_file}")
        self.restored_files.add(file_path)
    
    def _generate_report(self, output_dir: Path):
        """生成恢复报告"""
        report_file = output_dir / "restoration_report.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("Lua代码恢复报告\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"总文件数: {len(self.processed_files)}\n")
            f.write(f"成功恢复: {len(self.restored_files)}\n")
            f.write(f"恢复失败: {len(self.failed_files)}\n\n")
            
            if self.restored_files:
                f.write("成功恢复的文件:\n")
                for file_path in sorted(self.restored_files):
                    f.write(f"  - {file_path}\n")
                f.write("\n")
            
            if self.failed_files:
                f.write("恢复失败的文件:\n")
                for file_path in sorted(self.failed_files):
                    f.write(f"  - {file_path}\n")
                f.write("\n")
            
            # 依赖图统计
            stats = self.dependency_graph.get_statistics()
            f.write("依赖图统计:\n")
            for key, value in stats.items():
                f.write(f"  {key}: {value}\n")
        
        self.logger.info(f"恢复报告已生成: {report_file}")
    
    def run(self, start_file: str, unluac_dir: str, output_dir: str = "output"):
        """
        运行完整的解码流程
        
        Args:
            start_file: 起始文件路径
            unluac_dir: unluac文件所在目录
            output_dir: 输出目录
        """
        self.logger.info("开始运行Lua解码器")
        
        # 添加unluac目录到搜索路径
        self.resolver.add_search_path(unluac_dir)
        
        # 添加lua子目录到搜索路径
        lua_subdir = Path(unluac_dir) / "lua"
        if lua_subdir.exists():
            self.resolver.add_search_path(str(lua_subdir))
            self.logger.info(f"添加Lua子目录到搜索路径: {lua_subdir}")
        
        # 验证起始文件
        start_file_path = Path(start_file)
        if not start_file_path.exists():
            raise FileNotFoundError(f"起始文件不存在: {start_file}")
        
        # 检查起始文件是否为 .lua.unluac 文件
        if not start_file_path.name.endswith('.lua.unluac'):
            self.logger.warning(f"起始文件 {start_file} 不是 .lua.unluac 文件")
        
        print(f"{Fore.GREEN}开始分析起始文件: {start_file}{Style.RESET_ALL}")
        
        # 递归发现依赖
        self.discover_dependencies_recursively(start_file_path)
        
        print(f"{Fore.GREEN}依赖发现完成，开始代码恢复...{Style.RESET_ALL}")
        
        # 恢复代码
        self.restore_code_in_order(output_dir)
        
        print(f"{Fore.GREEN}Lua解码完成！{Style.RESET_ALL}")
        print(f"输出目录: {output_dir}")
        print(f"成功恢复: {len(self.restored_files)} 个文件")
        print(f"失败文件: {len(self.failed_files)} 个")
        
        # 显示依赖图
        if self.dependency_graph.graph:
            print(f"\n{Fore.CYAN}依赖关系图:{Style.RESET_ALL}")
            self.dependency_graph.print_graph()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Lua解码器 - 智能恢复unluac文件")
    parser.add_argument("start_file", help="起始文件路径")
    parser.add_argument("unluac_dir", help="unluac文件所在目录")
    parser.add_argument("-o", "--output", default="output", help="输出目录")
    parser.add_argument("-c", "--config", default="config/config.yaml", help="配置文件路径")
    
    args = parser.parse_args()
    
    try:
        decoder = LuaDecoder(args.config)
        decoder.run(args.start_file, args.unluac_dir, args.output)
    except Exception as e:
        print(f"{Fore.RED}错误: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
