"""v2 链路真机冒烟：解析 → 建索引 → 资源清单 → fusion 真实调度。

和 tests/ 的分工：单测把 LLM 和执行器全 mock 了，锁死的是「给定 tool_calls
怎么分发」这段纯 Python 逻辑。锁不住的是**真实监督者面对真实清单会不会选对工具**
——那是概率性的（参见 fusion 误路由 sql_query 的老问题）。这个脚本专门补这一段，
顺带验 build_manifest 的真实输出、以及执行器和检索器的真实接线。

不进 pytest 的原因：要真 API key、真 PDF、首次跑还要下模型，跑一次几十秒到几分钟，
不适合放进「每次提交都跑」的套件里。演示前手动跑一遍即可。

用法：
    python scripts/verify_v2_chain.py path/to/报告.pdf
    python scripts/verify_v2_chain.py path/to/报告.pdf -q "总销售额是多少" -q "第3页图表说明什么"

前置：.env 里配好 DEEPSEEK_API_KEY 和 DASHSCOPE_API_KEY；首次运行会下载 bge-small-zh。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 允许 `python scripts/verify_v2_chain.py` 直接跑（否则 import backend 会失败）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.file_router import build_manifest, get_session, route

# 默认两问覆盖两条不同的分支：①应走 search_text ②应走 answer_image
DEFAULT_QUESTIONS = [
    "这份报告的总销售额是多少",
    "第3页的图表展示了什么趋势",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="v2 后端链路真机冒烟")
    parser.add_argument("pdf", type=Path, help="用于验证的 PDF 文件路径")
    parser.add_argument(
        "-q", "--question", action="append", dest="questions",
        help="提问（可重复；不传则用默认的两问）",
    )
    args = parser.parse_args()

    if not args.pdf.exists():
        print(f"[FAIL] 文件不存在：{args.pdf}", file=sys.stderr)
        return 1

    # ① 解析 + 建索引
    result, sid = route(args.pdf)
    print(f"[OK] 解析：{result.file_name}，{result.page_count} 页，"
          f"{len(result.text_blocks)} 个文本块，{len(result.images)} 张图")

    ctx = get_session(sid)
    if ctx is None:
        print(f"[FAIL] 会话 {sid} 建完就找不到了，check file_router._new_session", file=sys.stderr)
        return 1
    if ctx.fusion is None:
        print("[FAIL] 会话里没挂 fusion 实例，check file_router 的 PDF 分支", file=sys.stderr)
        return 1

    # ② 资源清单：清单里的名字就是后面工具的 source 参数，对不齐则工具必然查空
    manifest = build_manifest(ctx)
    print("\n========== 资源清单 ==========")
    print(manifest)

    # ③ fusion 真实调度：看监督者选的工具对不对
    for i, question in enumerate(args.questions or DEFAULT_QUESTIONS, 1):
        print(f"\n========== 提问{i}：{question} ==========")
        print(ctx.fusion.run(question, manifest))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
