"""
配置文件 - 存储API密钥和其他配置参数
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# ====================  API 配置 ====================
# 当前使用的 LLM 提供商: "aliyun" | "openai" | "deepseek" | "moonshot" | "zenmux"
LLM_PROVIDER = "aliyun"  # 使用阿里云百炼

# 阿里云百炼 (Qwen) 配置 - 推荐使用
ALIYUN_API_KEY = os.getenv("ALIYUN_API_KEY", "your_aliyun_api_key_here")
ALIYUN_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
ALIYUN_MODEL = "qwen-plus"  # 可选: qwen-plus, qwen-turbo, qwen-max

# Zenmux (Gemini) 配置
ZENMUX_API_KEY = os.getenv("ZENMUX_API_KEY", "your_zenmux_api_key_here")
ZENMUX_API_URL = "https://zenmux.ai/v1/chat/completions"
ZENMUX_MODEL = "gemini-3-pro-preview-free"

# OpenAI 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"

# DeepSeek 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your_deepseek_api_key_here")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# Moonshot (Kimi) 配置
MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY", "your_moonshot_api_key_here")
MOONSHOT_API_URL = "https://api.moonshot.cn/v1/chat/completions"
MOONSHOT_MODEL = "moonshot-v1-8k"

# 根据当前提供商设置 API 参数
if LLM_PROVIDER == "aliyun":
    GEMINI_API_KEY = ALIYUN_API_KEY
    GEMINI_API_URL = ALIYUN_API_URL
    GEMINI_MODEL = ALIYUN_MODEL
elif LLM_PROVIDER == "zenmux":
    GEMINI_API_KEY = ZENMUX_API_KEY
    GEMINI_API_URL = ZENMUX_API_URL
    GEMINI_MODEL = ZENMUX_MODEL
elif LLM_PROVIDER == "openai":
    GEMINI_API_KEY = OPENAI_API_KEY
    GEMINI_API_URL = OPENAI_API_URL
    GEMINI_MODEL = OPENAI_MODEL
elif LLM_PROVIDER == "deepseek":
    GEMINI_API_KEY = DEEPSEEK_API_KEY
    GEMINI_API_URL = DEEPSEEK_API_URL
    GEMINI_MODEL = DEEPSEEK_MODEL
elif LLM_PROVIDER == "moonshot":
    GEMINI_API_KEY = MOONSHOT_API_KEY
    GEMINI_API_URL = MOONSHOT_API_URL
    GEMINI_MODEL = MOONSHOT_MODEL
else:
    # 默认使用阿里云
    GEMINI_API_KEY = ALIYUN_API_KEY
    GEMINI_API_URL = ALIYUN_API_URL
    GEMINI_MODEL = ALIYUN_MODEL

# GitHub API 配置
GITHUB_API_TOKEN = os.getenv("GITHUB_API_TOKEN", "your_github_token_here")  # 强烈建议配置！无token每小时只能请求60次，有token可达5000次

# ==================== 路径配置 ====================
PAPERS_ROOT_DIR = "/home/sunhan/scrape_cvf/CVPR_PAPERS_TEST"

# ==================== 代码仓库搜索配置 ====================
# 支持的代码托管平台域名
CODE_HOST_DOMAINS = [
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "gitee.com",
    "gitcode.com",
]

# PDF中寻找代码链接的关键词
CODE_KEYWORDS = [
    "code",
    "github",
    "gitlab",
    "implementation",
    "source code",
    "project page",
    "repository",
]

# ==================== 仓库质量评估配置 ====================
# 规则过滤阈值
MIN_CODE_FILES = 1  # 最少代码文件数
MIN_REPO_SIZE_KB = 10  # 最小仓库大小(KB)
MAX_ABANDONED_YEARS = 3  # 最长废弃年限
MIN_STARS_FOR_OLD_REPO = 5  # 老仓库最少star数

# 代码文件扩展名
CODE_EXTENSIONS = [
    '.py', '.cu', '.cpp', '.cc', '.c', '.h', '.hpp',
    '.java', '.js', '.ts', '.go', '.rs', '.m', '.mm',
    '.ipynb', '.sh', '.yaml', '.yml'
]

# 典型实现文件名
TYPICAL_IMPL_FILES = [
    'train.py', 'main.py', 'model.py', 'models.py',
    'network.py', 'dataset.py', 'inference.py',
    'test.py', 'eval.py', 'run.py'
]

# 典型实现目录
TYPICAL_IMPL_DIRS = [
    'models', 'src', 'lib', 'scripts', 'configs',
    'train', 'test', 'inference', 'utils'
]

# 深度分析配置
MAX_DEPTH = 3  # 遍历仓库目录的最大深度
MAX_FILES_TO_ANALYZE = 20  # 分析的最大文件数
SAMPLE_FILE_LINES = 100  # 每个文件采样的行数

# ==================== LLM 调用配置 ====================
LLM_TIMEOUT = 30  # 超时时间(秒)
LLM_MAX_RETRIES = 3  # 最大重试次数
LLM_TEMPERATURE = 0.2  # 生成温度

# ==================== 并发配置 ====================
MAX_WORKERS = 5  # 最大并发数
RATE_LIMIT_DELAY = 1  # API调用间隔(秒)

# ==================== 日志配置 ====================
LOG_LEVEL = "INFO"
LOG_FILE = "code_finder.log"
