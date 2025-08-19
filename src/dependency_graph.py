#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖图管理器
负责管理Lua文件之间的依赖关系，实现拓扑排序
"""

import json
import datetime
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path
from collections import defaultdict, deque
import logging


class DependencyGraph:
    """Lua文件依赖图管理器"""
    
    def __init__(self):
        """初始化依赖图"""
        self.graph = defaultdict(set)  # 邻接表
        self.reverse_graph = defaultdict(set)  # 反向邻接表
        self.file_to_module = {}  # 文件路径到模块名的映射
        self.module_to_file = {}  # 模块名到文件路径的映射
        self.file_contents = {}  # 文件内容缓存
        # 记录暂未解析到文件的模块依赖：module_name -> set(consumer_file_path)
        self.pending_module_dependents = defaultdict(set)
        self.logger = logging.getLogger(__name__)
    
    def add_file(self, file_path: Path, module_name: str, content: str = None):
        """
        添加文件到依赖图
        
        Args:
            file_path: 文件路径
            module_name: 模块名
            content: 文件内容
        """
        file_path = Path(file_path).resolve()
        self.file_to_module[str(file_path)] = module_name
        self.module_to_file[module_name] = str(file_path)
        
        if content:
            self.file_contents[str(file_path)] = content
        
        # 初始化图节点
        if str(file_path) not in self.graph:
            self.graph[str(file_path)] = set()
        if str(file_path) not in self.reverse_graph:
            self.reverse_graph[str(file_path)] = set()

        # 将挂起依赖回填到图：已知该模块对应文件后，建立 依赖 -> 使用者 的边
        pending = self.pending_module_dependents.pop(module_name, set())
        for consumer in pending:
            # graph: dependency -> consumer
            self.graph[str(file_path)].add(consumer)
            if consumer not in self.reverse_graph:
                self.reverse_graph[consumer] = set()
            self.reverse_graph[consumer].add(str(file_path))
    
    def add_dependency(self, from_file: Path, to_module: str):
        """
        添加依赖关系
        
        Args:
            from_file: 依赖源文件
            to_module: 被依赖的模块名
        """
        from_file = Path(from_file).resolve()
        from_file_str = str(from_file)
        
        if from_file_str not in self.graph:
            self.graph[from_file_str] = set()
        
        # 如果模块已解析为文件：建立 依赖 -> 使用者 的有向边
        if to_module in self.module_to_file:
            to_file = self.module_to_file[to_module]
            if to_file not in self.graph:
                self.graph[to_file] = set()
            if from_file_str not in self.reverse_graph:
                self.reverse_graph[from_file_str] = set()
            # dependency -> consumer
            self.graph[to_file].add(from_file_str)
            self.reverse_graph[from_file_str].add(to_file)
        else:
            # 目标模块尚未解析成文件，先挂起，待 add_file 时回填
            self.pending_module_dependents[to_module].add(from_file_str)
    
    def get_dependencies(self, file_path: Path) -> Set[str]:
        """
        获取文件的直接依赖
        
        Args:
            file_path: 文件路径
            
        Returns:
            依赖的文件路径集合
        """
        file_path = Path(file_path).resolve()
        # 返回当前文件所依赖的文件集合（使用反向图）
        return self.reverse_graph.get(str(file_path), set())
    
    def get_dependents(self, file_path: Path) -> Set[str]:
        """
        获取依赖此文件的其他文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            依赖此文件的文件路径集合
        """
        file_path = Path(file_path).resolve()
        # 返回依赖此文件的其他文件（使用正向图）
        return self.graph.get(str(file_path), set())
    
    def get_all_dependencies(self, file_path: Path) -> Set[str]:
        """
        获取文件的所有依赖（包括间接依赖）
        
        Args:
            file_path: 文件路径
            
        Returns:
            所有依赖的文件路径集合
        """
        file_path = Path(file_path).resolve()
        visited = set()
        dependencies = set()
        
        def dfs(node):
            if node in visited:
                return
            visited.add(node)
            # 通过反向图获取依赖链（consumer -> dependency）
            for dep in self.reverse_graph.get(node, set()):
                dependencies.add(dep)
                dfs(dep)
        
        dfs(str(file_path))
        return dependencies
    
    def topological_sort(self) -> List[str]:
        """
        执行拓扑排序
        
        Returns:
            排序后的文件路径列表
        """
        # 计算入度
        in_degree = defaultdict(int)
        for node in self.graph:
            in_degree[node] = 0
        
        for node, deps in self.graph.items():
            for dep in deps:
                in_degree[dep] += 1
        
        # 拓扑排序
        queue = deque([node for node in self.graph if in_degree[node] == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            for dep in self.graph.get(node, set()):
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)
        
        # 检查是否有环
        if len(result) != len(self.graph):
            self.logger.warning("检测到循环依赖！")
            # 找出剩余的节点（可能形成环）
            remaining = set(self.graph.keys()) - set(result)
            self.logger.warning(f"可能形成环的节点: {remaining}")
        
        return result
    
    def detect_cycles(self) -> List[List[str]]:
        """
        检测循环依赖
        
        Returns:
            循环依赖的路径列表
        """
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node, path):
            if node in rec_stack:
                # 找到环
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for dep in self.graph.get(node, set()):
                dfs(dep, path.copy())
            
            rec_stack.remove(node)
            path.pop()
        
        for node in self.graph:
            if node not in visited:
                dfs(node, [])
        
        return cycles
    
    def get_restoration_order(self, start_file: Path) -> List[str]:
        """
        获取代码恢复的推荐顺序
        
        Args:
            start_file: 起始文件
            
        Returns:
            恢复顺序的文件路径列表
        """
        start_file = Path(start_file).resolve()
        start_file_str = str(start_file)
        
        if start_file_str not in self.graph:
            return [start_file_str]
        
        # 获取所有依赖
        all_deps = self.get_all_dependencies(start_file_str)
        
        # 构建子图
        subgraph = {}
        for dep in all_deps:
            subgraph[dep] = self.graph.get(dep, set())
        subgraph[start_file_str] = self.graph.get(start_file_str, set())
        
        # 对子图进行拓扑排序
        temp_graph = self.graph.copy()
        self.graph = subgraph
        
        try:
            result = self.topological_sort()
        finally:
            self.graph = temp_graph
        
        return result
    
    def print_graph(self):
        """打印依赖图结构"""
        print("依赖图结构:")
        print("=" * 50)
        
        for file_path, deps in self.graph.items():
            module_name = self.file_to_module.get(file_path, "未知模块")
            print(f"文件: {file_path}")
            print(f"模块: {module_name}")
            print(f"依赖: {deps}")
            print("-" * 30)
    
    def export_dot(self, output_file: str):
        """
        导出为DOT格式（用于可视化）
        
        Args:
            output_file: 输出文件路径
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("digraph Dependencies {\n")
            f.write("  rankdir=LR;\n")
            f.write("  node [shape=box];\n\n")
            
            for file_path, deps in self.graph.items():
                module_name = self.file_to_module.get(file_path, "未知")
                f.write(f'  "{file_path}" [label="{module_name}"];\n')
                
                for dep in deps:
                    f.write(f'  "{file_path}" -> "{dep}";\n')
            
            f.write("}\n")
        
        self.logger.info(f"依赖图已导出到: {output_file}")
    
    def export_json(self, output_file: str):
        """
        导出为JSON格式
        
        Args:
            output_file: 输出文件路径
        """
        dependency_data = {
            "metadata": {
                "total_files": len(self.graph),
                "total_dependencies": sum(len(deps) for deps in self.graph.values()),
                "generated_at": str(datetime.datetime.now())
            },
            "files": [],
            "dependencies": [],
            "topological_order": self.topological_sort()
        }
        
        # 添加文件信息
        for file_path, deps in self.graph.items():
            module_name = self.file_to_module.get(file_path, "未知模块")
            file_info = {
                "file_path": file_path,
                "module_name": module_name,
                "dependencies_count": len(deps),
                "dependents_count": len(self.reverse_graph.get(file_path, set()))
            }
            dependency_data["files"].append(file_info)
        
        # 添加依赖关系
        for file_path, deps in self.graph.items():
            for dep in deps:
                dependency_info = {
                    "from": file_path,
                    "to": dep,
                    "from_module": self.file_to_module.get(file_path, "未知模块"),
                    "to_module": self.file_to_module.get(dep, "未知模块")
                }
                dependency_data["dependencies"].append(dependency_info)
        
        # 写入JSON文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dependency_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"依赖关系JSON已导出到: {output_file}")
    
    def get_statistics(self) -> Dict[str, int]:
        """获取依赖图统计信息"""
        total_files = len(self.graph)
        total_deps = sum(len(deps) for deps in self.graph.values())
        max_deps = max(len(deps) for deps in self.graph.values()) if self.graph else 0
        min_deps = min(len(deps) for deps in self.graph.values()) if self.graph else 0
        
        return {
            "total_files": total_files,
            "total_dependencies": total_deps,
            "max_dependencies": max_deps,
            "min_dependencies": min_deps,
            "avg_dependencies": total_deps / total_files if total_files > 0 else 0
        }


def test_dependency_graph():
    """测试依赖图功能"""
    graph = DependencyGraph()
    
    # 添加测试文件
    graph.add_file("file1.lua", "module1")
    graph.add_file("file2.lua", "module2")
    graph.add_file("file3.lua", "module3")
    
    # 添加依赖关系
    graph.add_dependency("file1.lua", "module2")
    graph.add_dependency("file2.lua", "module3")
    graph.add_dependency("file1.lua", "module3")
    
    print("依赖图测试:")
    print("=" * 50)
    
    # 打印图结构
    graph.print_graph()
    
    # 拓扑排序
    order = graph.topological_sort()
    print(f"拓扑排序结果: {order}")
    
    # 检测循环
    cycles = graph.detect_cycles()
    if cycles:
        print(f"检测到循环依赖: {cycles}")
    else:
        print("未检测到循环依赖")
    
    # 统计信息
    stats = graph.get_statistics()
    print(f"统计信息: {stats}")


if __name__ == "__main__":
    test_dependency_graph()
