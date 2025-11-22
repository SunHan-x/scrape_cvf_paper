# API 配置说明

## 问题诊断

当前 zenmux.ai API 返回 **500 服务器错误**，这是服务端的问题，不是你的配置问题。

## 解决方案

### 方案 1: 等待 zenmux 服务恢复
访问 https://zenmux.ai 查看服务状态

### 方案 2: 切换到其他 LLM 提供商（推荐）

我已经在 `config.py` 中添加了多个提供商支持，你可以选择：

#### 选项 A: OpenAI（最稳定，但需付费）
```python
# 在 config.py 中修改:
LLM_PROVIDER = "openai"
OPENAI_API_KEY = "sk-xxx..."  # 你的 OpenAI API Key
```
- 获取 API Key: https://platform.openai.com/api-keys
- 模型: gpt-4o-mini (便宜) 或 gpt-3.5-turbo

#### 选项 B: DeepSeek（性价比高，国内访问快）
```python
# 在 config.py 中修改:
LLM_PROVIDER = "deepseek"
DEEPSEEK_API_KEY = "sk-xxx..."  # 你的 DeepSeek API Key
```
- 获取 API Key: https://platform.deepseek.com
- 价格: 非常便宜（¥1/百万tokens）
- 模型质量: 接近 GPT-4

#### 选项 C: Moonshot/Kimi（国内服务，稳定）
```python
# 在 config.py 中修改:
LLM_PROVIDER = "moonshot"
MOONSHOT_API_KEY = "sk-xxx..."  # 你的 Moonshot API Key
```
- 获取 API Key: https://platform.moonshot.cn
- 适合国内用户

### 方案 3: 暂时不使用 LLM（免费但效果差）

运行时添加 `--no-llm` 参数：
```bash
python main.py --limit 5 --no-llm
```

这样只会使用规则过滤，不调用 LLM，完全免费但准确率较低。

## 测试新配置

配置好后，运行测试脚本：
```bash
python test_llm_api.py
```

如果看到 ✅ 就说明配置成功了！

## 推荐方案

**对于你的场景（2万多篇论文）：**

1. **首选 DeepSeek** - 性价比最高，2万篇论文大约花费 ¥10-20
2. **备选 OpenAI** - 最稳定但贵一些，约 $5-10
3. **最后 Moonshot** - 国内服务，价格中等

## 常见问题

**Q: 我必须使用 LLM 吗？**
A: 不是必须的，可以用 `--no-llm` 参数，但准确率会下降。

**Q: 成本大概多少？**
A: 以 DeepSeek 为例，2万篇论文：
- PDF 提取 + 仓库选择: ~100万 tokens ≈ ¥1
- 仓库质量评估: ~500万 tokens ≈ ¥5
- 总计: ¥6-10

**Q: 可以混用多个提供商吗？**
A: 当前版本不支持，但你可以分批处理，切换提供商。

## 当前系统状态

✅ 代码已就绪
✅ 测试脚本已创建
❌ zenmux API 暂时不可用（500错误）
⏳ 等待你配置其他 LLM 提供商

## 下一步

1. 选择一个 LLM 提供商
2. 在 `config.py` 中修改 `LLM_PROVIDER` 和对应的 API Key
3. 运行 `python test_llm_api.py` 测试
4. 测试成功后运行 `python main.py --limit 5` 处理少量论文
5. 确认无误后运行 `python main.py` 处理全部论文
