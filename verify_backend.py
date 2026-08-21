"""验 v2 后端链路：解析 → 建索引 → 资源清单 → fusion 调度。

不起服务、不碰 HTTP/curl，直接调 file_router，绕开 shell 编码问题。
"""
from pathlib import Path

from backend.file_router import route, get_session, build_manifest

PDF = Path.home() / "Desktop" / "2024年度销售报告.pdf"

# ① 解析 + 建索引（首次会下载 bge-small-zh 模型，等几分钟）
result, sid = route(PDF)
print(f"解析结果：{result.file_name}，共 {result.page_count} 页，"
      f"{len(result.text_blocks)} 个文本块，{len(result.images)} 张图")

ctx = get_session(sid)
assert ctx is not None

# ② 资源清单（验证 source 对齐链：清单里的名字就是后面工具的 source 参数）
manifest = build_manifest(ctx)
print("\n========== 资源清单 ==========")
print(manifest)

# ③ fusion 调度（提问①走 search_text，提问②走 answer_image）
assert ctx.fusion is not None
print("\n========== 提问① 文本检索 ==========")
print(ctx.fusion.run("2024年总销售额是多少", manifest))

print("\n========== 提问② 看图 ==========")
print(ctx.fusion.run("第3页的柱状图展示了什么趋势", manifest))
