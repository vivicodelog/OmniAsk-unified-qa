"""fusion 工具声明 + 监督者 prompt 的测试（纯函数，不需要 API key / 模型）。"""
from backend.retrieval.fusion import TOOLS, build_system_prompt, build_tools


# ① 工具菜单：3 个工具，名字对得上（名字是 run() 里执行分发的依据）
def test_tools_names():
    names = [t["function"]["name"] for t in TOOLS]
    assert names == ["search_text", "sql_query", "answer_image"]


# ② 每个工具都声明了 required 参数（缺了，LLM 可能漏传导致工具执行报错）
def test_tools_required_params():
    required = {
        t["function"]["name"]: t["function"]["parameters"]["required"]
        for t in TOOLS
    }
    assert required["search_text"] == ["query", "source"]
    assert required["sql_query"] == ["question", "table"]
    assert required["answer_image"] == ["question", "source", "page"]


# ③ prompt = 规则 + 资源清单，二者都要进 system message
def test_build_system_prompt_contains_manifest():
    prompt = build_system_prompt("【表格】- products")
    assert "【表格】- products" in prompt
    assert "调度员" in prompt


# ④ 动态工具菜单：按加载的资源裁剪，没表格就不给 sql_query（堵住「总销售额」误路由）
def test_build_tools_filters_by_resources():
    def names(tools):
        return [t["function"]["name"] for t in tools]

    assert names(build_tools(has_tables=False, has_pdfs=True)) == ["search_text", "answer_image"]
    assert names(build_tools(has_tables=True, has_pdfs=False)) == ["sql_query"]
    assert names(build_tools(has_tables=True, has_pdfs=True)) == ["search_text", "sql_query", "answer_image"]
