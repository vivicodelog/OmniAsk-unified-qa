"""fusion run() 路由单测：mock 掉监督者 LLM 和执行器，锁死分发逻辑。

为什么能脱离真实模型/DB 测：FusionAgent 依赖注入 tool_executors，
client 也被覆盖成 MagicMock，run() 的分发是纯 Python 逻辑，可离线测。
"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from backend.retrieval.fusion import FusionAgent


def _fake_tool_call(call_id: str, name: str, arguments: dict) -> SimpleNamespace:
    """造一个 tool_call：run() 只用到 id / function.name / function.arguments。"""
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


def _fake_message(tool_calls, content=None) -> SimpleNamespace:
    """造一个 assistant message：带 model_dump（run() 回填时调它）。"""
    msg = SimpleNamespace(tool_calls=tool_calls, content=content)
    msg.model_dump = lambda exclude_none=None: {"role": "assistant", "tool_calls": tool_calls}
    return msg


def _make_agent(tool_calls, content=None, final_answer="合并答案"):
    """client 被 mock：第一次返回带 tool_calls 的 message，第二次返回 final_answer。"""
    first = MagicMock()
    first.choices[0].message = _fake_message(tool_calls, content=content)
    second = MagicMock()
    second.choices[0].message = _fake_message([], content=final_answer)
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [first, second]

    executors = {
        "search_text": MagicMock(return_value="检索到的文本"),
        "sql_query": MagicMock(return_value="SQL 查询结果"),
        "answer_image": MagicMock(return_value="图片描述"),
    }
    agent = FusionAgent(executors)
    agent.client = fake_client          # 覆盖成假的，不联网不花钱
    return agent, executors, fake_client


# ① 多个 tool_calls → 逐个分发到对的执行器（多问题的核心）
def test_run_dispatches_multiple_tool_calls():
    calls = [
        _fake_tool_call("call_1", "search_text", {"query": "结论", "source": "a.pdf"}),
        _fake_tool_call("call_2", "sql_query", {"question": "销售额", "table": "products"}),
    ]
    agent, executors, _ = _make_agent(calls)

    assert agent.run("问题", "资源清单") == "合并答案"
    executors["search_text"].assert_called_once_with({"query": "结论", "source": "a.pdf"})
    executors["sql_query"].assert_called_once_with({"question": "销售额", "table": "products"})
    executors["answer_image"].assert_not_called()


# ② 监督者不调工具 → 直接返回 content，不碰任何执行器
def test_run_returns_directly_when_no_tool_calls():
    agent, executors, _ = _make_agent([], content="直接回答")

    assert agent.run("问题", "资源清单") == "直接回答"
    for executor in executors.values():
        executor.assert_not_called()


# ③ 工具结果被回填给第二次调用（role=tool + tool_call_id 对齐）
def test_run_feeds_tool_results_back():
    calls = [_fake_tool_call("call_1", "search_text", {"query": "结论", "source": "a.pdf"})]
    agent, _, fake_client = _make_agent(calls)
    agent.run("问题", "资源清单")

    # 第二次 create 收到的 messages，应包含一条 role=tool 的回执
    second_messages = fake_client.chat.completions.create.call_args_list[1].kwargs["messages"]
    tool_messages = [m for m in second_messages if m.get("role") == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0]["tool_call_id"] == "call_1"
    assert tool_messages[0]["content"] == "检索到的文本"
