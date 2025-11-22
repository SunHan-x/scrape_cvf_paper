# 论文代码仓库查找和验证系统

自动为 CVF 论文（CVPR、ICCV 等）查找官方/非官方代码实现，并验证仓库质量。

## ✨ 功能特性

### 🔍 三级代码查找策略
1. **PDF 提取** - 从论文 PDF 中提取 GitHub/GitLab 等代码链接
2. **GitHub 搜索** - 使用 GitHub API 搜索相关实现
3. **LLM 辅助** - 使用 LLM 从多个候选中选择最佳仓库

### ✅ 智能质量验证
1. **规则过滤** - 快速过滤空仓库、废弃仓库
2. **LLM 评估** - 深度分析 README、代码结构、维护状况

### 📊 数据结构
每篇论文生成 `github_links.json`：
```json
{
  "official_repo_url": "https://github.com/...",
  "unofficial_repo_urls": [],
  "selected_repo_url": "https://github.com/...",
  "repo_type": "official|unofficial|none_found",
  "quality": {
    "score": 0.85,
    "is_meaningful": true,
    "reason": "..."
  },
  "extraction_source": "pdf|github_search",
  "processed_at": "2025-11-22T10:30:00"
}
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装 Python 包
pip install -r requirements.txt

# 或使用 conda
conda create -n code_finder python=3.10
conda activate code_finder
pip install -r requirements.txt
```

### 2. 配置 API Key

编辑 `config.py`，填入你的 API Key：

```python
# Gemini API 配置
GEMINI_API_KEY = "your_actual_api_key_here"

# GitHub API Token（可选，但推荐）
GITHUB_API_TOKEN = "your_github_token_here"
```

**获取 API Key：**
- Gemini API: https://zenmux.ai/google/gemini-3-pro-preview-free
- GitHub Token: https://github.com/settings/tokens

### 3. 运行

#### 测试单篇论文
```bash
python main.py --single "CVPR/2024/3D Paintbrush Local Stylization of 3D Shapes with Cascaded Score Distillation" --limit 1
```

#### 批量处理（测试前 10 篇）
```bash
python main.py --limit 10
```

#### 批量处理所有论文
```bash
python main.py
```

## 📖 使用说明

### 命令行参数

```bash
python main.py [OPTIONS]

可选参数:
  --root-dir PATH       论文根目录 (默认: ./CVPR_PAPERS_TEST)
  --single PATH         只处理单篇论文 (如 'CVPR/2024/Paper Title')
  --limit N             限制处理数量 (用于测试)
  --no-llm              不使用 LLM (仅规则过滤，节省成本)
  --skip-pdf            跳过 PDF 提取 (只做 GitHub 搜索)
  --skip-validation     跳过仓库验证 (只查找不验证)
  --no-resume           不跳过已处理的论文 (重新处理)
```

### 使用场景

#### 场景 1: 快速测试
```bash
# 处理 5 篇论文，不使用 LLM
python main.py --limit 5 --no-llm
```

#### 场景 2: 只查找代码
```bash
# 只查找代码链接，不验证质量（节省 API 调用）
python main.py --skip-validation
```

#### 场景 3: 只做 GitHub 搜索
```bash
# PDF 已处理过，只做 GitHub 搜索补充
python main.py --skip-pdf
```

#### 场景 4: 重新验证质量
```bash
# 对已找到代码的论文重新评估质量
python main.py --skip-pdf --no-resume
```

## 📁 项目结构

```
.
├── config.py              # 配置文件（API Key、参数）
├── llm_client.py          # LLM API 客户端封装
├── utils.py               # 通用工具函数
├── pdf_extractor.py       # PDF 代码链接提取器
├── github_search.py       # GitHub 搜索器
├── repo_validator.py      # 仓库质量验证器
├── main.py                # 主流程脚本
├── requirements.txt       # Python 依赖
└── CVPR_PAPERS_TEST/      # 论文数据目录
    └── CVPR/
        └── 2024/
            └── Paper Title/
                ├── paper.pdf
                ├── paper_data.json
                └── github_links.json  # 生成的结果
```

## 🔧 模块说明

### 1. pdf_extractor.py - PDF 提取
- 从 PDF 中提取文本
- 正则匹配代码仓库 URL
- 根据上下文判断是否为官方链接
- LLM 从多个候选中选择最可能的官方仓库

### 2. github_search.py - GitHub 搜索
- 构造智能搜索查询
- 调用 GitHub API 搜索仓库
- LLM 过滤出真正实现了论文的仓库
- 按相关性排序

### 3. repo_validator.py - 质量验证
**规则过滤（快速）:**
- 检查代码文件数量
- 检查仓库大小
- 检查是否废弃/归档
- 检查更新时间和 star 数

**LLM 评估（深度）:**
- 分析 README 内容
- 分析文件结构
- 评估维护状况
- 评估代码质量
- 给出综合分数

### 4. main.py - 主流程
- 批量处理论文
- 进度跟踪和统计
- 错误处理和恢复
- 结果保存

## ⚙️ 配置说明

### config.py 重要参数

```python
# API 配置
GEMINI_API_KEY = "..."           # 必填
GITHUB_API_TOKEN = "..."         # 可选但推荐

# 路径配置
PAPERS_ROOT_DIR = "./CVPR_PAPERS_TEST"

# 搜索配置
CODE_HOST_DOMAINS = [            # 支持的代码托管平台
    "github.com",
    "gitlab.com",
    "bitbucket.org",
]

# 验证配置
MIN_CODE_FILES = 1               # 最少代码文件数
MIN_REPO_SIZE_KB = 10            # 最小仓库大小
MAX_ABANDONED_YEARS = 3          # 最长废弃年限
MIN_STARS_FOR_OLD_REPO = 5       # 老仓库最少 star 数
```

## 📊 输出结果

处理完成后，每篇论文目录下会生成 `github_links.json`：

```json
{
  "official_repo_url": "https://github.com/author/paper-impl",
  "unofficial_repo_urls": [
    "https://github.com/someone/reimplementation"
  ],
  "selected_repo_url": "https://github.com/author/paper-impl",
  "repo_type": "official",
  "quality": {
    "score": 0.85,
    "is_meaningful": true,
    "reason": "Has code files and basic structure",
    "reasons": [
      "Complete implementation with training code",
      "Well-maintained with recent commits",
      "Good documentation"
    ]
  },
  "extraction_source": "pdf",
  "processed_at": "2025-11-22T10:30:00.123456"
}
```

## 🎯 性能优化

### 成本控制
- **规则优先**: 明显无意义的仓库不调用 LLM
- **批量处理**: 支持断点续传
- **智能跳过**: 已处理的论文自动跳过

### 速度优化
- **并发控制**: 可配置并发数
- **缓存结果**: 中间结果实时保存
- **增量处理**: 支持恢复模式

## 🐛 故障排除

### 问题 1: API 调用失败
```
❌ LLM API 请求失败: 403 Forbidden
```
**解决**: 检查 `config.py` 中的 `GEMINI_API_KEY` 是否正确

### 问题 2: GitHub API 限速
```
⚠️  GitHub API 限速，等待...
```
**解决**: 
- 添加 GitHub Token 到 `config.py`
- 或等待限速解除（约 60 分钟）

### 问题 3: PDF 提取失败
```
❌ PDF 提取失败: ...
```
**解决**: 确保已安装 `pymupdf`：`pip install pymupdf`

### 问题 4: 没有找到代码
**可能原因:**
- 论文确实没有公开代码
- PDF 中没有链接 → 会自动尝试 GitHub 搜索
- GitHub 搜索没有结果 → 标记为 `none_found`

## 📝 示例输出

```
================================================================================
📝 处理论文: 3D Paintbrush Local Stylization of 3D Shapes with Cascaded Score Distillation
================================================================================
标题: 3D Paintbrush: Local Stylization of 3D Shapes with Cascaded Score Distillation
年份: 2024
  📄 从 PDF 提取代码链接...
    找到 5 个 URL
    其中 1 个是代码仓库 URL
    经上下文分析，1 个候选链接
    ✅ 找到唯一候选: https://github.com/author/3d-paintbrush
✅ 从 PDF 找到官方仓库: https://github.com/author/3d-paintbrush

────────────────────────────────────────────────────────────────────────────────
  ✅ 验证仓库: https://github.com/author/3d-paintbrush
    规则评估: Has code files and basic structure
  🤖 LLM 深度评估仓库质量...
    LLM 评估分数: 0.85
    原因: Complete implementation, Well-maintained, Good documentation
✅ 仓库有意义 (分数: 0.85)

💾 结果已保存到 .../github_links.json

进度: 1/100 | 已处理: 1 | 跳过: 0 | 错误: 0
预计剩余时间: 15.2 分钟
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可

MIT License

## 🙏 致谢

- CVF Open Access 提供论文数据
- Gemini API 提供 LLM 支持
- GitHub API 提供仓库搜索
