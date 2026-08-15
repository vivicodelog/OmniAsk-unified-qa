import re
from openai.types.chat import ChatCompletionMessageParam

from backend.db import DBManager
from backend.sql_guard import SQLGuard
from openai import OpenAI
from backend import config

MAX_RETRIES = 3
MAX_HISTORY_TURNS = 5       # 会话历史保留最近 5 轮（连续多个"它"也能回指）
RESULT_PREVIEW_ROWS = 10    # 结果裁剪：明细查询只留前 10 行
class NL2SQLAgent:
    def __init__(self):
        self.client =OpenAI(
            api_key=config.DEEPSEEK_API_KEY,                    # 你的 key
            base_url=config.DEEPSEEK_BASE_URL, # DeepSeek 地址
        )
        self.history: list[ChatCompletionMessageParam] = []

    def _call_llm(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=config.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个 MySQL 专家，根据用户问题和表结构生成 SQL"},
                    *self.history,          # 历史对话（含反问澄清）
                    {"role": "user", "content": prompt},
                ],

                temperature=0.7,
            )
            content = response.choices[0].message.content
            if content is None:
                raise RuntimeError("LLM 返回空内容")
            return content
        except Exception as e:
            raise RuntimeError(f"LLM 调用失败: {e}")
    def run(self, question: str, schema: str, db: DBManager, guard: SQLGuard) -> dict:
        prompt = self._build_prompt(question, schema)
        errors: list[str] = []  # 记录每轮失败原因
        for _ in range(MAX_RETRIES):
            try:
                reply = self._call_llm(prompt)
            except RuntimeError as e:
                return {"success": False, "error": str(e)}

            clarify_q = self._extract_clarify(reply)
            if clarify_q:
                self._append_history(question, f"需要澄清：{clarify_q}")
                return {"success": False, "need_clarify": True, "question": clarify_q}

            sql = self._extract_sql(reply)
            ok, err = guard.validate(sql)        # 校验
            if not ok:
                errors.append(f"[guard] {err}")
                prompt = self._build_retry_prompt(question, schema, sql, err)
                continue          # ← 校验失败，下一轮重试
            # guard 通过，试着执行
            try:
                data = db.execute(sql)
                break               # ← 执行成功，退出循环
            except Exception as e:
                errors.append(f"[execute] {e}")
                prompt = self._build_retry_prompt(question, schema, sql, str(e))
                continue            # ← SQL 错误，让 LLM 修正
        else:
            return {"success": False, "error": f"SQL 生成或执行重试 {MAX_RETRIES} 次仍失败: {'; '.join(errors)}"}
      
        self._append_history(question, f"SQL: {sql}\n结果: {self._summarize(data)}")
        return {"sql": sql, "data": data, "success": True}
    
    def _build_prompt(self, question: str, schema: str) -> str:

        return f"""你是一个 MySQL 专家。根据下面的表结构，把用户问题转成可执行的 SQL。

        表结构：{schema}
    要求：
    1. 只输出一行 SQL，不要 markdown 代码块、不要解释
    2. 只能 SELECT，禁止 INSERT/UPDATE/DELETE/DROP
    3. 中文列名或表名必须用反引号包裹，如 `产品名称`
    4. 字符串值用单引号，如 WHERE name = '商品'
    5. 如果问题有歧义或指代不明（如「它」「那个」无法确定指哪个），不要生成 SQL，输出「需要澄清：<你的问题>」

        用户问题：{question}"""
        
    def _build_retry_prompt(self, question: str, schema: str, 
                         last_sql: str, error_msg: str) -> str:
        base = self._build_prompt(question, schema)
        return base + f"""

        你上一次生成的 SQL：
        {last_sql}
        校验失败原因：{error_msg}

        请修正后重新输出。"""

    @staticmethod
    def _extract_sql(text: str) -> str:
        text = text.strip()
        # 1. 先抠 markdown 代码块
        match = re.search(r"```(?:sql)?\s*(SELECT[\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            text = match.group(1).strip()
        # 2. 去掉 SELECT 前面的废话
        text = re.sub(r"^.*?(SELECT)", r"\1", text, flags=re.IGNORECASE)
        # 3. 去掉 ; 后面的尾巴
        if ";" in text:
            text = text.split(";")[0].strip() + ";"
        return text
    @staticmethod
    def _summarize(data: list[dict]) -> str:
        """结果裁剪：≤10 行全存，超过只留前 10 行 + 总数。"""
        if not data:
            return "空结果"
        if len(data) <= RESULT_PREVIEW_ROWS:
            return str(data)
        return str(data[:RESULT_PREVIEW_ROWS]) + f"\n... 共 {len(data)} 行"
    def _append_history(self, question: str, assistant_content: str) -> None:
        """记一轮对话，并裁剪到最近 MAX_HISTORY_TURNS 轮。"""
        self.history.append({"role": "user", "content": question})
        self.history.append({"role": "assistant", "content": assistant_content})
        self.history = self.history[-(MAX_HISTORY_TURNS * 2):]
    @staticmethod
    def _extract_clarify(text: str) -> str | None:
        """检测 LLM 是否在反问。是则返回澄清问题，否则返回 None。"""
        text = text.strip()
        if text.startswith("需要澄清"):
            q = text[len("需要澄清"):].lstrip("：:").strip()
            return q or "请补充说明你的问题"
        return None
