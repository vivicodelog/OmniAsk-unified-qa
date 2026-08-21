# OmniAsk · 文档 + 数据统一问答平台

上传 Excel / CSV / PDF，用自然语言提问，系统自动判断该查表、该检索正文、还是该看图，然后给出带溯源的回答。

> 开发中（v0.3.0，v2 多模态链路已打通）。全程无 GPU、无梯子，模型推理走国内 API + 本地 CPU Embedding。

---

## 它解决什么

同一个问题，答案可能藏在三种地方：结构化表格里、PDF 正文里、PDF 的某张图表里。传统做法要求用户自己选"我要查数据库"还是"我要问文档"。这个项目把选择权交给系统——

```
"2024 年总销售额是多少"        → 走 NL2SQL，查表算出来
"报告里对华南市场怎么定性的"    → 走文本检索，从 PDF 正文找依据
"第 3 页那张柱状图说明什么趋势"  → 走 Qwen-VL，把图截出来喂给多模态模型
```

用户只管问，路由由一个监督者 LLM 按当前会话加载了哪些资源来决定。

---

## 整体链路

```
                    ┌─────────────┐
   上传文件 ────────▶│ FileRouter  │  MIME 检测 → 分派
                    └──────┬──────┘
              ┌────────────┴────────────┐
              ▼                         ▼
      ┌───────────────┐         ┌───────────────┐
      │ ExcelParser   │         │  PdfParser    │
      │ 列类型推断     │         │ 文本/表格/图片 │
      │ → MySQL 临时表 │         │ + bbox 坐标   │
      └───────┬───────┘         └───────┬───────┘
              │                         │
              │                 ┌───────┴────────┐
              │                 ▼                ▼
              │          ┌────────────┐   ┌────────────┐
              │          │ 向量检索    │   │  BM25      │
              │          │ bge-small  │   │ jieba 分词  │
              │          └──────┬─────┘   └─────┬──────┘
              │                 └──── RRF 融合 ──┘
              │                         │
              ▼                         ▼
        ┌─────────────────────────────────────┐
   提问 ─▶      FusionAgent（监督者 LLM）       │
        │  按资源清单动态生成可用工具，分发调用   │
        └──┬──────────────┬─────────────┬─────┘
           ▼              ▼             ▼
      sql_query    search_text    answer_image
      (NL2SQL)     (混合检索)      (Qwen-VL)
           └──────────────┴─────────────┘
                          ▼
                   结果回填 → 合成答案 + 溯源定位
```

前端拿到溯源信息后，在 PDF 上按 bbox 画高亮框，点击回答里的引用可直接跳到原文位置。

---

## 技术选型

| 组件 | 选型 | 为什么 |
|------|------|--------|
| 文本 LLM | DeepSeek API (`deepseek-chat`) | 国内直连，便宜，代码/SQL 能力好 |
| 多模态 LLM | Qwen-VL (`qwen-vl-plus`，阿里云百炼) | 国内直连，不用本地部署扛不动的视觉模型 |
| Embedding | `BAAI/bge-small-zh-v1.5` 本地 CPU | 中文效果够用，small 版无 GPU 也能跑 |
| 向量库 | ChromaDB | 本地持久化，零运维 |
| 关键词检索 | 自实现 BM25 + jieba | 补向量检索的字面匹配短板（专有名词、数字） |
| 多路融合 | RRF（倒数排名融合） | 不需要调分数权重，对两路打分尺度不敏感 |
| PDF 解析 | PyMuPDF + pdfplumber | 图片和坐标用 PyMuPDF，表格检测 pdfplumber 更强 |
| 结构化存储 | MySQL 8.0 | 上传的表格落成临时表，NL2SQL 直接查 |
| SQL 安全 | 正则白名单 + AST 校验 | 不引额外依赖，拦住写操作和多语句注入 |
| 前端 | Vue 3 + Naive UI + ECharts + vue-pdf-embed | — |

---

## 快速开始

**环境要求**：Python 3.11+（开发用 3.13）、Node 18+（开发用 20）、MySQL 8.0

### 1. 后端

```bash
git clone https://gitee.com/vivicode/omni-ask.git
cd omni-ask

python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash
# source .venv/bin/activate        # Linux / macOS
pip install -r requirements.txt
```

### 2. 配置

```bash
cp .env.example .env
```

填入 DeepSeek 和 Qwen 的 API Key，以及本机 MySQL 账号。建库：

```sql
CREATE DATABASE unified_qa CHARACTER SET utf8mb4;
```

### 3. 启动

```bash
uvicorn backend.main:app --reload        # → http://localhost:8000
```

首次上传 PDF 时会从 ModelScope 下载 Embedding 模型（约 184MB），需等几分钟。

### 4. 前端

```bash
cd frontend
npm install
npm run dev                              # → http://localhost:5173
```

Vite 已配好把 `/api` 代理到 `localhost:8000`，直接开 5173 即可。

---

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/upload` | 上传文件，返回 `session_id` 和解析结果 |
| `GET` | `/api/file/{session_id}` | 取回该会话已上传的文件信息 |
| `POST` | `/api/chat` | 提问，返回答案 + 溯源 |

---

## 测试

```bash
pytest -q                                # 111 passed
```

测试分两层，边界划在"要不要花钱联网"：

- **纯函数 / 本地模型**：BM25 打分、RRF 融合、列类型推断、SQLGuard、图表选择、向量检索（真跑 bge + 临时 chroma 库）
- **mock 掉外部 LLM**：FusionAgent 的工具分发、VisionAgent、NL2SQL —— 锁住的是分发逻辑，不是模型输出

mock 测试覆盖不到的那一段——**真实监督者面对真实资源清单会不会选对工具**——由一个独立的真机冒烟脚本兜底：

```bash
python scripts/verify_v2_chain.py 你的报告.pdf
```

它要真 API Key、真 PDF，跑一次几十秒，所以不进 pytest 套件，演示前手动跑一遍。

---

## 项目结构

```
backend/
├── main.py                  FastAPI 入口
├── file_router.py           MIME 检测 + 分派 + 会话管理 + 资源清单
├── config.py                API keys / 模型名 / 上传限制
├── db.py                    MySQL 临时表管理
├── sql_guard.py             SQL 白名单安全校验
├── chart_selector.py        图表类型启发式选择
├── parsers/
│   ├── excel_parser.py      Excel/CSV 解析 + 列类型推断
│   └── pdf_parser.py        文本/表格/图片提取 + bbox 坐标
├── agents/
│   ├── nl2sql_agent.py      NL2SQL（含会话记忆、指代不明时反问）
│   └── vision_agent.py      Qwen-VL 看图回答
├── retrieval/
│   ├── text_retriever.py    bge + ChromaDB 向量检索
│   ├── bm25.py              BM25 + jieba 分词 + RRF 融合
│   └── fusion.py            监督者 LLM 工具调度
└── router/                  upload / chat 接口

frontend/src/
├── views/QaView.vue         主页面
├── components/
│   ├── FileUploader.vue     拖拽上传
│   ├── DataPreview.vue      数据预览表格
│   ├── ChartPanel.vue       ECharts 渲染
│   ├── PdfViewer.vue        PDF 预览 + bbox 高亮
│   └── ChatPanel.vue        对话面板
├── composables/
│   ├── useSSE.ts            SSE 流式解析
│   └── useFileUpload.ts     上传逻辑
└── api.ts

scripts/verify_v2_chain.py   真机冒烟
tests/                       pytest
docs/design.md               选型与分阶段设计
```

---

## 几个设计取舍

**动态工具菜单，而不是固定三件套**
监督者的可用工具按当前会话实际加载了什么来裁剪：没传表格就不给 `sql_query`。早期版本工具固定，结果模型看到"总销售额"这种词就往 SQL 上撞，哪怕会话里根本没有表。堵住这条路比在 prompt 里写"没有表时不要调 sql_query"可靠得多。

**BM25 和向量检索用 RRF 融合，不调权重**
两路的打分尺度完全不同（余弦相似度 vs BM25 分数），线性加权得为每个语料重调一次。RRF 只看排名不看分数，省掉这个调参环节。

**PDF 坐标不做翻转**
PyMuPDF 的 bbox 是左上原点、y 轴向下，和浏览器 CSS 坐标系一致，前端拿到直接乘缩放比例即可。这点容易踩坑——PDF 规范本身用的是左下原点。

**SQL 安全靠白名单而非黑名单**
只放行 `SELECT`，其余一律拒。黑名单永远漏（`DROP` 拦了还有 `TRUNCATE`，大小写变形、注释穿插也绕得过）。

---

## 状态

- [x] v1 数据分析：上传 → 解析 → NL2SQL → SQLGuard → 图表
- [x] v2 多模态：PDF 解析 → 混合检索 → 图文关联 → 前端高亮溯源
- [ ] 会话持久化（当前 session 在内存，服务重启即丢）
- [ ] 一次提问含多个子问题的拆解
- [ ] Embedding 切到 BGE-M3（当前 small 版，长文本效果有限）

---

## License

[Apache-2.0](LICENSE) © 2026 zhanghui
