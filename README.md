# Lua解码器 (Lua Decoder)

一个使用LLM智能恢复unluac文件为Lua源码的工具，支持依赖分析和拓扑排序。

## 功能特性

- 🔍 **智能依赖分析**: 使用LLM分析Lua文件的require语句和模块依赖
- 🔗 **依赖图管理**: 构建完整的依赖关系图，支持循环依赖检测
- 📊 **拓扑排序**: 按依赖顺序恢复代码，避免函数/变量冲突
- 🚀 **LLM集成**: 集成OpenRouter API，智能恢复代码结构和注释
- 🌍 **跨平台支持**: 支持Windows、Linux、macOS
- 📝 **详细报告**: 生成恢复报告和依赖关系图

## 项目结构

```
lua_decoder/
├── src/                    # 源代码
│   ├── __init__.py        # 包初始化
│   ├── lua_decoder.py     # 主解码器类
│   ├── lua_module_resolver.py  # Lua模块路径解析器
│   ├── llm_client.py      # OpenRouter LLM客户端
│   └── dependency_graph.py # 依赖图管理器
├── config/                 # 配置文件
│   └── config.yaml        # 主配置文件
├── output/                 # 输出目录
├── logs/                   # 日志目录
├── main.py                 # 主程序入口
├── requirements.txt        # Python依赖
└── README.md              # 项目说明
```

## 安装依赖

```bash
cd lua_decoder
pip install -r requirements.txt
```

## 配置

1. 复制配置文件模板：
```bash
cp config/config.yaml config/config.yaml.local
```

2. 编辑配置文件，设置OpenRouter API密钥：
```yaml
openrouter:
  api_key: "your_api_key_here"  # 替换为你的API密钥
  base_url: "https://openrouter.ai/api/v1"
  model: "anthropic/claude-3.5-sonnet"
```

## 使用方法

### 命令行使用

```bash
# 基本用法
python main.py <起始文件> <unluac目录>

# 指定输出目录
python main.py <起始文件> <unluac目录> <输出目录>

# 指定配置文件
python main.py <起始文件> <unluac目录> <输出目录> <配置文件>
```

### 示例

```bash
# 分析test.lua文件，从./unluac_files目录查找依赖
python main.py ./test.lua ./unluac_files

# 指定输出目录为./restored_code
python main.py ./test.lua ./unluac_files ./restored_code

# 使用自定义配置文件
python main.py ./test.lua ./unluac_files ./restored_code ./config/my_config.yaml
```

### 程序化使用

```python
from src.lua_decoder import LuaDecoder

# 创建解码器实例
decoder = LuaDecoder("config/config.yaml")

# 运行解码流程
decoder.run(
    start_file="./test.lua",
    unluac_dir="./unluac_files",
    output_dir="./output"
)
```

## 工作流程

1. **依赖发现**: 从起始文件开始，递归分析所有require语句
2. **路径解析**: 将Lua模块名转换为对应的文件路径
3. **依赖图构建**: 建立完整的文件依赖关系图
4. **循环检测**: 检测并报告循环依赖
5. **拓扑排序**: 按依赖顺序确定代码恢复顺序
6. **代码恢复**: 使用LLM智能恢复每个文件的源代码
7. **报告生成**: 生成恢复报告和依赖关系图

## 模块路径解析

支持多种Lua模块路径格式：

- `luci.controller.api.xqnetwork` → `lua/luci/controller/api/xqnetwork.lua`
- `luci.http` → `lua/luci/http.lua`
- `nixio.fs` → `lua/nixio/fs.lua`

## 输出文件

- **恢复的Lua代码**: 按依赖顺序恢复的源代码文件
- **依赖关系图**: DOT格式的依赖关系图（可用Graphviz可视化）
- **恢复报告**: 详细的恢复过程报告
- **日志文件**: 完整的操作日志

## 配置选项

### OpenRouter配置
- `api_key`: API密钥
- `base_url`: API基础URL
- `model`: 使用的模型名称

### Lua路径配置
- `lua_paths`: Lua模块的基础搜索路径列表

### 输出配置
- `format`: 输出格式
- `encoding`: 文件编码
- `backup`: 是否备份原文件

### LLM配置
- `max_tokens`: 最大token数
- `temperature`: 生成温度
- `timeout`: 超时时间

## 错误处理

- 自动跳过无法读取的文件
- 详细的错误日志记录
- 优雅的失败处理
- 循环依赖检测和警告

## 性能优化

- 文件内容缓存
- 智能依赖图构建
- 批量LLM API调用
- 进度条显示

## 注意事项

1. **API密钥**: 请妥善保管OpenRouter API密钥
2. **文件编码**: 建议使用UTF-8编码
3. **网络连接**: 需要稳定的网络连接访问OpenRouter API
4. **文件权限**: 确保有足够的文件读写权限
5. **循环依赖**: 工具会检测循环依赖，但建议手动检查

## 故障排除

### 常见问题

1. **API连接失败**: 检查网络连接和API密钥
2. **文件读取错误**: 检查文件路径和权限
3. **依赖解析失败**: 检查Lua模块路径配置
4. **内存不足**: 减少同时处理的文件数量

### 日志查看

```bash
# 查看最新日志
tail -f logs/lua_decoder.log

# 查看错误日志
grep "ERROR" logs/lua_decoder.log
```

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

MIT License

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基本的依赖分析和代码恢复
- 集成OpenRouter LLM API
- 实现拓扑排序和循环依赖检测
