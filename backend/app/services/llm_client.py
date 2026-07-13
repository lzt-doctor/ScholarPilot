from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any

import httpx

from app.config import settings


@dataclass(frozen=True)
class LLMResult:
    content: str
    provider: str
    model: str
    mode: str
    status: str
    error_code: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status == "success"

    def runtime_metadata(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("content")
        return data


class LLMClient(ABC):
    @abstractmethod
    async def generate_answer(self, question: str, context: str) -> LLMResult:
        raise NotImplementedError

    @abstractmethod
    async def generate_study_plan(
        self, goal: str, background: str | None, weeks: int, hours_per_week: int
    ) -> LLMResult:
        raise NotImplementedError

    @abstractmethod
    async def analyze_mistake(
        self, question_text: str, user_answer: str, correct_answer: str
    ) -> LLMResult:
        raise NotImplementedError


class MockLLMClient(LLMClient):
    """Explicit demo client. Its output is always labelled as mock at runtime."""

    def _result(self, content: str) -> LLMResult:
        return LLMResult(
            content=content,
            provider="mock",
            model="deterministic-template",
            mode="mock",
            status="success",
        )

    async def generate_answer(self, question: str, context: str) -> LLMResult:
        if not context.strip():
            return self._result("知识库证据不足。请先上传包含相关内容的 PDF。")
        preview = context[:420].replace("\n", " ")
        return self._result(
            "[Mock 模式] 根据检索片段，问题"
            f"「{question}」可从以下证据中进行初步分析：{preview}... [1]"
        )

    async def generate_study_plan(
        self, goal: str, background: str | None, weeks: int, hours_per_week: int
    ) -> LLMResult:
        background_text = f"基础情况：{background}\n" if background else ""
        content = (
            "[Mock 模式：确定性模板]\n"
            f"目标：{goal}\n{background_text}"
            f"周期：{weeks} 周，每周约 {max(hours_per_week, 1)} 小时。\n\n"
            "阶段 1：资料梳理与知识地图\n- 整理核心论文、课程讲义和项目文档。\n\n"
            "阶段 2：主题精读与问答训练\n- 围绕算法、系统设计和实验方法开展资料问答。\n\n"
            "阶段 3：错题与薄弱点复盘\n- 按知识点统计高频错误并安排专项练习。\n\n"
            "阶段 4：申请展示沉淀\n- 整理项目报告、研究计划和面试介绍。"
        )
        return self._result(content)

    async def analyze_mistake(
        self, question_text: str, user_answer: str, correct_answer: str
    ) -> LLMResult:
        point = _infer_knowledge_point(question_text + " " + correct_answer)
        return self._result(
            "错因：对题目条件或关键概念理解不完整，建议复核定义和边界条件。\n"
            f"知识点：{point}"
        )


class OpenAICompatibleLLMClient(LLMClient):
    """OpenAI-compatible adapter that never silently replaces failed output."""

    async def _chat(self, messages: list[dict[str, str]]) -> str:
        if not settings.llm_api_base:
            raise ValueError("LLM_API_BASE is not configured")
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"
        payload: dict[str, Any] = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(
                settings.llm_api_base.rstrip("/") + "/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            return str(data["choices"][0]["message"]["content"]).strip()

    def _failure(self, code: str) -> LLMResult:
        return LLMResult(
            content="真实大模型当前不可用，系统未使用 mock 回答替代。",
            provider=settings.llm_provider,
            model=settings.llm_model,
            mode="degraded",
            status="error",
            error_code=code,
        )

    async def _generate(self, messages: list[dict[str, str]]) -> LLMResult:
        if not settings.llm_api_base:
            return self._failure("llm_not_configured")
        try:
            content = await self._chat(messages)
            if not content:
                return self._failure("llm_empty_response")
            return LLMResult(
                content=content,
                provider=settings.llm_provider,
                model=settings.llm_model,
                mode="real",
                status="success",
            )
        except Exception:
            return self._failure("llm_request_failed")

    async def generate_answer(self, question: str, context: str) -> LLMResult:
        return await self._generate(
            [
                {
                    "role": "system",
                    "content": (
                        "你是 ScholarPilot 的学术文档问答服务。只能依据给定来源回答；"
                        "每个事实陈述必须用 [1]、[2] 形式引用对应来源编号，不得编造来源。"
                    ),
                },
                {"role": "user", "content": f"来源：\n{context}\n\n问题：{question}"},
            ]
        )

    async def generate_study_plan(
        self, goal: str, background: str | None, weeks: int, hours_per_week: int
    ) -> LLMResult:
        return await self._generate(
            [
                {"role": "system", "content": "请输出结构化中文学习计划。"},
                {
                    "role": "user",
                    "content": (
                        f"目标：{goal}\n基础：{background or '未提供'}\n"
                        f"周期：{weeks} 周，每周 {hours_per_week} 小时"
                    ),
                },
            ]
        )

    async def analyze_mistake(
        self, question_text: str, user_answer: str, correct_answer: str
    ) -> LLMResult:
        return await self._generate(
            [
                {"role": "system", "content": "输出两行：错因：... 知识点：..."},
                {
                    "role": "user",
                    "content": (
                        f"题目：{question_text}\n学生答案：{user_answer}\n"
                        f"正确答案：{correct_answer}"
                    ),
                },
            ]
        )


def _infer_knowledge_point(text: str) -> str:
    keywords = {
        "神经网络": "深度学习",
        "transformer": "Transformer 架构",
        "attention": "注意力机制",
        "database": "数据库系统",
        "sql": "数据库系统",
        "graph": "图算法",
        "complexity": "算法复杂度",
        "操作系统": "操作系统",
        "进程": "操作系统",
        "概率": "概率统计",
    }
    lower_text = text.lower()
    for keyword, point in keywords.items():
        if keyword in lower_text:
            return point
    return "核心概念理解"


def parse_mistake_analysis(content: str) -> dict[str, str]:
    reason = ""
    point = ""
    for line in content.splitlines():
        if line.startswith(("错因：", "错因:")):
            reason = line.replace("错因：", "", 1).replace("错因:", "", 1).strip()
        if line.startswith(("知识点：", "知识点:")):
            point = line.replace("知识点：", "", 1).replace("知识点:", "", 1).strip()
    return {
        "error_reason": reason or content[:300],
        "knowledge_point": point or _infer_knowledge_point(content),
    }


def get_llm_client() -> LLMClient:
    if settings.llm_provider.lower() == "mock":
        return MockLLMClient()
    return OpenAICompatibleLLMClient()


def get_llm_runtime_status() -> dict[str, str]:
    provider = settings.llm_provider.lower()
    if provider == "mock":
        mode = "mock"
    elif settings.llm_api_base:
        mode = "real_configured"
    else:
        mode = "unavailable"
    return {
        "llm_provider": provider,
        "llm_mode": mode,
        "llm_model": "deterministic-template" if mode == "mock" else settings.llm_model,
    }
