#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenRouter LLM客户端
负责与OpenRouter API通信，进行Lua代码分析和恢复
"""

import json
import time
import requests
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging


class OpenRouterClient:
    """OpenRouter API客户端"""
    
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1", model: str = "anthropic/claude-3.5-sonnet"):
        """
        初始化客户端
        
        Args:
            api_key: OpenRouter API密钥
            base_url: API基础URL
            model: 使用的模型名称
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
        
        # 设置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def analyze_lua_file(self, file_path: Path, content: str = None) -> Dict[str, Any]:
        """
        分析Lua文件，提取依赖关系
        
        Args:
            file_path: Lua文件路径
            content: 文件内容，如果为None则从文件读取
            
        Returns:
            分析结果字典
        """
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                self.logger.error(f"读取文件 {file_path} 失败: {e}")
                return {"error": str(e)}
        
        prompt = self._build_analysis_prompt(file_path, content)
        
        try:
            response = self._call_api(prompt)
            return self._parse_analysis_response(response)
        except Exception as e:
            self.logger.error(f"分析文件 {file_path} 时出错: {e}")
            return {"error": str(e)}
    
    def restore_lua_code(self, file_path: Path, content: str, dependencies: List[str]) -> str:
        """
        使用LLM恢复Lua源代码
        
        Args:
            file_path: 文件路径
            content: 原始内容（可能是unluac输出）
            dependencies: 依赖的模块列表
            
        Returns:
            恢复后的Lua源代码
        """
        prompt = self._build_restoration_prompt(file_path, content, dependencies)
        
        try:
            response = self._call_api(prompt)
            return self._extract_code_from_response(response)
        except Exception as e:
            self.logger.error(f"恢复代码时出错: {e}")
            return content  # 返回原始内容
    
    def _build_analysis_prompt(self, file_path: Path, content: str) -> str:
        """构建分析提示词"""
        return f"""你是一个Lua代码分析专家。请分析以下Lua文件，提取其中的require语句和模块依赖关系。

文件路径: {file_path}
文件内容:
```
{content}
```

请分析这个文件并返回JSON格式的结果，包含以下信息：
1. requires: 所有require语句中引用的模块名列表
2. functions: 文件中定义的函数列表
3. variables: 文件中定义的变量列表
4. classes: 文件中定义的类或表结构
5. comments: 重要的注释信息

请确保返回的是有效的JSON格式，不要包含其他文本。"""

    def _build_restoration_prompt(self, file_path: Path, content: str, dependencies: List[str]) -> str:
        """构建代码恢复提示词"""
        deps_str = "\n".join([f"- {dep}" for dep in dependencies])
        
        return f"""你是一个Lua代码恢复专家。请将以下可能是unluac反编译输出的内容恢复为可读的Lua源代码。

文件路径: {file_path}
依赖模块:
{deps_str}

原始内容:
```
{content}
```

请恢复为标准的Lua代码格式，要求：
1. 保持原有的逻辑结构
2. 添加适当的注释说明
3. 使用清晰的变量和函数命名
4. 遵循Lua代码规范
5. 保持模块的完整性

请只返回恢复后的Lua代码，不要包含其他解释文本。"""

    def _call_api(self, prompt: str) -> Dict[str, Any]:
        """调用OpenRouter API"""
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 4000,
            "temperature": 0.1
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            return result
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API调用失败: {e}")
            raise
    
    def _parse_analysis_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """解析分析响应"""
        try:
            content = response["choices"][0]["message"]["content"]
            
            # 尝试提取JSON
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            else:
                json_str = content.strip()
            
            # 移除可能的"json"标记
            if json_str.startswith("json"):
                json_str = json_str[4:].strip()
            
            return json.loads(json_str)
            
        except (KeyError, json.JSONDecodeError) as e:
            self.logger.error(f"解析响应失败: {e}")
            return {"error": f"解析失败: {e}", "raw_content": content}
    
    def _extract_code_from_response(self, response: Dict[str, Any]) -> str:
        """从响应中提取代码"""
        try:
            content = response["choices"][0]["message"]["content"]
            
            # 尝试提取代码块
            if "```lua" in content:
                code_start = content.find("```lua") + 6
                code_end = content.find("```", code_start)
                return content[code_start:code_end].strip()
            elif "```" in content:
                code_start = content.find("```") + 3
                code_end = content.find("```", code_start)
                return content[code_start:code_end].strip()
            else:
                return content.strip()
                
        except (KeyError, IndexError) as e:
            self.logger.error(f"提取代码失败: {e}")
            return ""

    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            response = self.session.get(f"{self.base_url}/models")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"连接测试失败: {e}")
            return False


def test_client():
    """测试客户端功能"""
    # 注意：需要设置有效的API密钥
    client = OpenRouterClient("your_api_key_here")
    
    if client.test_connection():
        print("API连接成功!")
    else:
        print("API连接失败!")


if __name__ == "__main__":
    test_client()
