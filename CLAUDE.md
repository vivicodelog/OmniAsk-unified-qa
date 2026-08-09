# Unified QA — 文档+数据统一问答平台

## 项目定位
多模态、多数据源统一 AI 问答平台。上传 PDF/Excel/CSV/图片，自然语言提问，自动路由。

## 技术栈（纯国内、无 GPU、无梯子）
- **后端**：FastAPI + LangChain + ChromaDB（向量库）
- **前端**：Vue 3 + Naive UI + ECharts + vue-pdf-embed
- **文本 LLM**：DeepSeek API（国内直连）
- **多模态 LLM**：Qwen-VL API（阿里云百炼，国内直连）
- **文本 Embedding**：BGE-M3 本地 CPU
- **PDF 解析**：PyMuPDF + pdfplumber
- **模型下载**：ModelScope（魔搭社区，国内直连）

## 硬件约束
- 无 GPU，32G 内存，i7-13700H（14 核）
- Windows 11 + Git Bash
- 模型推理全部 CPU，大模型走 API

## 开发规模
- v1（数据分析助手）+ v2（多模态文档）核心链路
- 20 个工作日，目标本月底可演示

## 协作模式：拆 → 写 → 验 → 复盘

### 每个任务的标准流程
1. **拆**：AI 先拆步骤——做什么、为什么、每步产出是什么
2. **写**：AI 写代码框架，用户自己敲（不是复制粘贴），每行理解后落下去
3. **验**：写完一个模块立刻写测试，跑通才算完
4. **复盘**：每个 milestone 停下来——这段代码的设计思路、可能的面试追问

### 编码约定
- **Python**：类型注解 + Pydantic 校验 + 简短注释（解释为什么，不解释是什么）
- **Vue**：`<script setup>` + Options API 混合（用户习惯）
- **测试**：pytest，关键模块必测：parsers、SQLGuard、ChartSelector、FileRouter、FusionRetriever
- **独立项目**：不依赖 rag-project，只复用 rag_forge 的 create_llm() 思路

### 迭代节奏
- 每天一个可测试的增量，不攒到第二天
- 遇到技术卡点 15 分钟内提出来，不闷头死磕
- 每完成一个 Phase（v1 / v2 / 打通）做一次代码走读

## 面试关联
每个模块完成时，AI 提供"面试追问清单"：
- 面试官看到这段代码会问什么
- 你的回答要点是什么
- 可能的追问及应对

## 项目结构

```
unified_qa/
├── CLAUDE.md                    # 本文件 — 开窗口自动加载
├── requirements.txt
├── backend/
│   ├── main.py                  # FastAPI + SSE
│   ├── router.py                # 上传 / 对话 / 图表 API
│   ├── schemas.py               # Pydantic 模型
│   ├── file_router.py           # MIME 检测 + 链路分派
│   ├── config.py                # API keys / 模型路径
│   ├── db.py                    # SQLite 临时表管理
│   ├── chart_selector.py        # 图表类型自动选择（启发式规则）
│   ├── sql_guard.py             # SQL 白名单安全校验
│   ├── parsers/
│   │   ├── excel_parser.py      # Excel/CSV 解析 + 列类型推断
│   │   └── pdf_parser.py        # PyMuPDF 文本/表格/图片提取 + 坐标
│   ├── agents/
│   │   ├── nl2sql_agent.py      # NL2SQL Agent（DeepSeek）
│   │   └── vision_agent.py      # Qwen-VL 多模态回答
│   └── retrieval/
│       ├── text_retriever.py    # BGE-M3 文本检索
│       └── fusion.py            # 图文关联 + 检索融合
├── frontend/                    # Vue 3 新建项目
│   └── src/
│       ├── App.vue
│       ├── views/QaView.vue     # 主页面
│       ├── components/
│       │   ├── FileUploader.vue   # 拖拽上传
│       │   ├── DataPreview.vue    # 数据预览表格
│       │   ├── ChartPanel.vue     # ECharts 图表渲染
│       │   ├── PdfViewer.vue      # PDF 预览 + 区域高亮
│       │   ├── ChatPanel.vue      # 对话面板（SSE 流式）
│       │   └── SourceTrace.vue    # 引用溯源链
│       └── composables/
│           ├── useSSE.ts          # SSE 流式解析
│           └── useFileUpload.ts   # 文件上传逻辑
├── tests/
│   ├── test_excel_parser.py
│   ├── test_pdf_parser.py
│   ├── test_nl2sql_agent.py
│   ├── test_sql_guard.py
│   ├── test_chart_selector.py
│   ├── test_file_router.py
│   └── test_fusion.py
└── data/                        # 测试文件
    ├── sample_sales.xlsx
    ├── sample_report.pdf
    └── sample_mixed/
```
