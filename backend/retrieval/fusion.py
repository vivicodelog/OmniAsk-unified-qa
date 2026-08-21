"""
fusion —— v2 调度中枢。

核心思路：把「多模态问题该走哪个工具」交给监督者 LLM 用 function calling 决定，
fusion 只负责执行工具、回收结果、合并回答。

三块：
  ① TOOLS：给监督者看的「能力菜单」，3 个工具的 JSON 声明
  ② build_system_prompt：监督者的 system message（规则 + 资源清单）
  ③ FusionAgent.run()：执行循环——调监督者选工具 → 执行 → 再调一次合并答案
"""

# ============================================================
# ① 工具声明：function calling 的 JSON Schema
#    description 是路由质量的关键，LLM 靠它判断「这问题该走哪个」
# ============================================================

from collections.abc import Callable
import json
from typing import cast
from openai.types.chat import ChatCompletionFunctionToolParam, ChatCompletionMessage, ChatCompletionMessageFunctionToolCall, ChatCompletionMessageParam   
from openai import OpenAI

from backend import config


TOOLS: list[ChatCompletionFunctionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "search_text",
            "description": "在 PDF 文档的文本里检索原文，用于回答'文档里写了什么、怎么规定、结论是什么、有哪些章节'这类需要查原文的问题",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要检索的关键词或完整问题"},
                    "source": {"type": "string", "description": "文档来源，从资源清单的【PDF 文本】里选，不能编造"},
                },
                "required": ["query", "source"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sql_query",
            "description": "查询结构化表格数据（Excel/CSV 导入的表），用于回答'统计、求和、对比、排名、筛选'这类需要计算或聚合的问题",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "要回答的数据问题"},
                    "table": {"type": "string", "description": "表名，从资源清单的【表格】里选，不能编造"},
                },
                "required": ["question", "table"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "answer_image",
            "description": "查看 PDF 里的图片（图表、截图、示意图），用于回答'图片里画了什么、趋势如何、布局怎样'这类需要看图片内容的问题",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "关于图片内容的问题"},
                    "source": {"type": "string", "description": "文档来源，从资源清单的【PDF 图片】里选，不能编造"},
                    "page": {"type": "integer", "description": "图片所在页码，从资源清单的图片列表里选"},
                },
                "required": ["question", "source", "page"],
            },
        },
    },
]


# ============================================================
# ② 监督者 prompt：固定规则 + 当次资源清单
# ============================================================

SUPERVISOR_RULES = """你是统一问答平台的调度员，根据用户问题判断该调用哪个工具来获取答案。

规则：
1. 先读资源清单，只调用清单里真实存在的 source / table / page，绝不编造
2. 一个问题可能涉及多个工具，此时一次性并行调用多个工具，不要拆成多次来回
3. 能用一个工具答完就只调一个，别调无关工具
4. 拿到工具结果后，用中文分条回答，每条对应一个子问题，保留关键数字和结论
5. 回答要聚焦问题：只回答用户问题直接相关的内容，检索结果里与问题无关的信息不要展开
"""


def build_system_prompt(manifest: str) -> str:
    """拼监督者的 system message：固定规则 + 当次资源清单。

    manifest 是运行时动态生成的字符串，形如：
        当前已加载的资源：
        【表格】
        - qa_xxx_0：产品名称(string)、销售额(float)
        【PDF 文本】
        - report.pdf：已索引 12 个文本块（第 1-3 页）
        【PDF 图片】
        - report.pdf：第 3 页有一张图
    """
    return f"{SUPERVISOR_RULES}\n\n{manifest}"


def build_tools(has_tables: bool, has_pdfs: bool) -> list[ChatCompletionFunctionToolParam]:
    """按当前资源动态组装工具菜单：没表格就不给 sql_query，从根上防止监督者误路由。

    TOOLS 是「能力全集」，build_tools 是「当次可用子集」——和 manifest 一样动态。
    """
    enabled: set[str] = set()
    if has_pdfs:
        enabled.update({"search_text", "answer_image"})
    if has_tables:
        enabled.add("sql_query")
    return [t for t in TOOLS if t["function"]["name"] in enabled]


class FusionAgent:
    """调度中枢。"""
    def __init__(
        self,
        tool_executors: dict[str, Callable[[dict], str]],
        tools: list[ChatCompletionFunctionToolParam] = TOOLS,
    ):
        self.client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
        )
        self.tool_executors = tool_executors
        self.tools = tools

    def run(self, question: str, manifest: str) -> str:
        messages: list[ChatCompletionMessageParam] = [              # 显式注解
            {"role": "system", "content": build_system_prompt(manifest)},
            {"role": "user", "content": question},
        ]
        resp = self.client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=messages,
            tools=self.tools,
            tool_choice="auto",
        )
        message = resp.choices[0].message
        if not message.tool_calls:
            return self._content_or_raise(message)
        
        messages.append(cast(ChatCompletionMessageParam, message.model_dump(exclude_none=True)))
        for raw_call in message.tool_calls:
            call = cast(ChatCompletionMessageFunctionToolCall, raw_call) 
            args = json.loads(call.function.arguments)
            result = self.tool_executors[call.function.name](args)
            messages.append(
                {
                    "role": "tool",            # ① 告诉 API：这是一条工具回执
                    "tool_call_id": call.id,   # ② 告诉 API：我回复的是哪次工具调用
                    "content": result,         # ③ 工具返回的结果（字符串）
                }
            )
        final = self.client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=messages,
        )
        content = final.choices[0].message.content
        if content is None:
            raise RuntimeError("监督者返回空内容")
        return content

    @staticmethod
    def _content_or_raise(msg: ChatCompletionMessage) -> str:
        content = msg.content
        if content is None:
            raise RuntimeError("监督者返回空内容")
        return content