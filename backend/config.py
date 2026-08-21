"""
集中管理所有配置：API keys、模型路径、文件限制。
通过环境变量 + .env 文件注入，不硬编码敏感信息。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- 项目根目录 ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- 敏感配置：只从环境变量读，不给兜底值 ---
# 兜底值一旦写进代码就会随仓库公开，且缺配置时会拿它去静默连接，
# 报出来的错（401 / Access denied）和真正的原因（没配 .env）对不上。
# 一律留空，交给 missing_secrets() 在启动时统一体检。
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

# --- 非敏感配置：给默认值，开箱即用 ---
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# --- 模型名称 ---
DEEPSEEK_MODEL = "deepseek-chat"          # 文本 LLM
QWEN_VL_MODEL = "qwen-vl-plus"            # 多模态 LLM（阿里云百炼）
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"           # 本地 Embedding（ModelScope 下载）

# --- 文件上传限制 ---
MAX_FILE_SIZE_MB = 50
ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".csv", ".png", ".jpg", ".jpeg"}

# --- MySQL 数据库（本机 MySQL 8.0） ---
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "qa_user"),
    "password": MYSQL_PASSWORD,
    "database": os.getenv("MYSQL_DATABASE", "unified_qa"),
    "charset": "utf8mb4",
}

# --- 配置体检 ---
# 名字 → 值。只登记敏感项；值为空说明 .env 没配或没加载到。
_SECRETS = {
    "DEEPSEEK_API_KEY": DEEPSEEK_API_KEY,
    "QWEN_API_KEY": QWEN_API_KEY,
    "MYSQL_PASSWORD": MYSQL_PASSWORD,
}


def missing_secrets() -> list[str]:
    """返回未配置的敏感项名字，供启动时提示。

    不在此处抛异常：config 被几乎所有模块 import，import 期抛错会让
    连 `--help` 都跑不起来，也会拖垮不需要这些密钥的单测。
    """
    return [name for name, value in _SECRETS.items() if not value]

# --- ChromaDB 持久化目录 ---
CHROMA_PERSIST_DIR = str(PROJECT_ROOT / "data" / "chroma_db")

# --- 文本分块 ---
CHUNK_SIZE = 800          # PDF 文本切块大小（字符）
CHUNK_OVERLAP = 100       # 相邻块重叠量
