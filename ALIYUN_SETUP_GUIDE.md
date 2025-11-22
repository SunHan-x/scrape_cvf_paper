# 阿里云百炼 (Qwen) 配置指南

## 🎯 为什么选择阿里云百炼？

✅ **免费额度**: 新用户有免费额度可用
✅ **国内访问快**: 服务器在国内，速度快
✅ **模型强大**: Qwen 系列模型质量优秀
✅ **性价比高**: 价格合理，适合大量调用

## 📝 配置步骤

### 第 1 步: 获取 API Key

1. 访问阿里云百炼控制台：
   https://bailian.console.aliyun.com

2. 如果没有账号，先注册阿里云账号

3. 在左侧菜单中找到 **"API-KEY管理"**

4. 点击 **"创建 API Key"**

5. 复制生成的 API Key（格式类似：`sk-xxx...`）

### 第 2 步: 配置到项目中

编辑 `LLM_repo_valid/config.py`：

```python
# 找到这两行，修改为：
LLM_PROVIDER = "aliyun"
ALIYUN_API_KEY = "sk-你复制的API-Key"  # 替换这里
```

### 第 3 步: 测试连接

运行测试脚本：
```bash
python test_aliyun_api.py
```

看到 ✅ 就表示配置成功！

## 🎨 模型选择

在 `config.py` 中可以选择不同的模型：

```python
ALIYUN_MODEL = "qwen-plus"  # 推荐，平衡性能和成本
# 或者：
# ALIYUN_MODEL = "qwen-turbo"  # 更快更便宜
# ALIYUN_MODEL = "qwen-max"    # 最强性能
```

**推荐配置**：
- 日常使用: `qwen-plus`
- 需要速度: `qwen-turbo`
- 追求质量: `qwen-max`

## 💰 价格参考

| 模型 | 输入价格 | 输出价格 | 适用场景 |
|------|---------|---------|---------|
| qwen-turbo | ¥0.3/百万tokens | ¥0.6/百万tokens | 快速处理 |
| qwen-plus | ¥0.8/百万tokens | ¥2/百万tokens | 推荐使用 |
| qwen-max | ¥20/百万tokens | ¥60/百万tokens | 复杂任务 |

**你的项目预估成本**（2万篇论文，使用 qwen-plus）：
- PDF 提取 + 仓库选择: ~100万 tokens ≈ ¥1
- 仓库质量评估: ~500万 tokens ≈ ¥6
- **总计: ¥7-10**

## 🚀 开始使用

配置完成后，运行：

```bash
# 测试 5 篇论文
cd LLM_repo_valid
python main.py --limit 5

# 批量处理所有论文
python main.py
```

## ❓ 常见问题

### Q: 提示 API Key 无效
A: 检查：
1. API Key 是否正确复制（不要有空格）
2. API Key 是否已激活
3. 账户余额是否充足

### Q: 请求超时
A: 
1. 检查网络连接
2. 可能是服务繁忙，稍后重试

### Q: 免费额度用完了怎么办？
A: 
1. 充值继续使用（价格很便宜）
2. 切换到其他提供商（DeepSeek 也很便宜）

### Q: 想切换回其他提供商
A: 修改 `config.py`:
```python
LLM_PROVIDER = "deepseek"  # 或 "openai" 等
```

## 📚 相关链接

- 阿里云百炼控制台: https://bailian.console.aliyun.com
- API 文档: https://help.aliyun.com/zh/model-studio/developer-reference/api-details
- 价格说明: https://help.aliyun.com/zh/model-studio/developer-reference/billing-instructions

## ✨ 优势总结

相比其他提供商：
- ✅ 比 OpenAI 便宜很多
- ✅ 比 DeepSeek 稳定性更好
- ✅ 国内访问速度快
- ✅ 有免费额度可用
- ✅ 阿里云大厂，服务稳定

**推荐指数**: ⭐⭐⭐⭐⭐

非常适合你这个项目！
