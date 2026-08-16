"""vision_agent 测试：mock 掉 Qwen-VL 客户端，不花钱、不联网。"""
from unittest.mock import MagicMock

from backend.agents.vision_agent import VisionAgent
from backend.schemas import PdfImage


def _make_agent(answer: str) -> tuple[VisionAgent, MagicMock]:
    """造一个 client 被 mock 的 agent，返回 (agent, fake_client)。"""
    fake_client = MagicMock()
    # 关键一行：让 create 的返回值一路链到 message.content = answer
    fake_client.chat.completions.create.return_value.choices[0].message.content = answer
    agent = VisionAgent()
    agent.client = fake_client          # 覆盖成假的
    return agent, fake_client


# ① 纯函数：jpg → jpeg
def test_image_to_data_url_jpg_maps_to_jpeg():
    img = PdfImage(page=1, bbox=(0, 0, 10, 10), data=b"x", ext="jpg")
    url = VisionAgent._image_to_data_url(img)   # ← 类名直接调，不 new 对象
    assert url.startswith("data:image/jpeg;base64,")

# ② run 返回预设答案
def test_run_returns_answer():
    agent, _ = _make_agent("这是答案")
    assert agent.run("问题", [PdfImage(page=1, bbox=(0, 0, 10, 10), data=b"x", ext="jpg")]) == "这是答案"


# ③ run 真的把图片塞进请求
def test_run_sends_image_url_block():
    agent, fake_client = _make_agent("答案")
    img = PdfImage(page=1, bbox=(0, 0, 10, 10), data=b"x", ext="png")
    agent.run("看图", [img])                       # 只调一次

    # 掏出来，局部断言
    messages = fake_client.chat.completions.create.call_args.kwargs["messages"]
    content = messages[0]["content"]
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
