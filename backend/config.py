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

# --- API Keys（优先读环境变量） ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-deepseek-key")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

QWEN_API_KEY = os.getenv("QWEN_API_KEY", "your-qwen-key")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# --- 模型名称 ---
DEEPSEEK_MODEL = "deepseek-chat"          # 文本 LLM
QWEN_VL_MODEL = "qwen-vl-plus"            # 多模态 LLM（阿里云百炼）
EMBEDDING_MODEL = "BAAI/bge-m3"           # 本地 Embedding（ModelScope 下载）

# --- 文件上传限制 ---
MAX_FILE_SIZE_MB = 50
ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".csv", ".png", ".jpg", ".jpeg"}

# --- MySQL 数据库（本机 MySQL 8.0） ---
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "qa_user"),
    "password": os.getenv("MYSQL_PASSWORD", "qa_pass_2024"),
    "database": os.getenv("MYSQL_DATABASE", "unified_qa"),
    "charset": "utf8mb4",
}

# --- ChromaDB 持久化目录 ---
CHROMA_PERSIST_DIR = str(PROJECT_ROOT / "data" / "chroma_db")

# --- 文本分块 ---
CHUNK_SIZE = 800          # PDF 文本切块大小（字符）
CHUNK_OVERLAP = 100       # 相邻块重叠量
