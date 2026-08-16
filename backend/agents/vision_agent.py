import base64

from openai import OpenAI
from openai.types.chat import ChatCompletionContentPartParam

from backend import config
from backend.schemas import PdfImage


class VisionAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=config.QWEN_API_KEY,
            base_url=config.QWEN_BASE_URL,
        )

    def run(self, question: str, images: list[PdfImage]) -> str:
        """看图问答：把问题 + 图片发给 Qwen-VL，返回答案。"""
        # ① 拼 content：先放文字块，再循环给每张图 append 一个 image_url 块
        content: list[ChatCompletionContentPartParam] = [
            {"type": "text", "text": question},
        ]
        for image in images:
            img_url = self._image_to_data_url(image)
            content.append({"type": "image_url", "image_url": {"url": img_url}})

        # ② 调 API：model 用 QWEN_VL_MODEL，messages 的 content 传【列表】
        try:
            response = self.client.chat.completions.create(
                model=config.QWEN_VL_MODEL,
                messages=[{"role": "user", "content": content}],
            )
            answer = response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Qwen-VL 调用失败: {e}")

        # ③ 返回前防一手：answer 可能为 None，None 就 raise
        if answer is None:
            raise RuntimeError("Qwen-VL 返回空内容")
        return answer

    @staticmethod
    def _image_to_data_url(image: PdfImage) -> str:
        """PdfImage → base64 data URL，给 Qwen-VL 的 image_url。"""
        # ① ext → mime：jpg 要纠正成 jpeg
        mime = "jpeg" if image.ext == "jpg" else image.ext
        # ② bytes → base64 字符串：b64encode 返回 bytes，要 decode 转回 str
        b64 = base64.b64encode(image.data).decode("ascii")
        # ③ 拼三段式 data URL
        return f"data:image/{mime};base64,{b64}"