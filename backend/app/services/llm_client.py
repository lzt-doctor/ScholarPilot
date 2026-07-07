from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.config import settings


class LLMClient(ABC):
    @abstractmethod
    async def generate_answer(self, question: str, context: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def generate_study_plan(
        self, goal: str, background: str | None, weeks: int, hours_per_week: int
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def analyze_mistake(
        self, question_text: str, user_answer: str, correct_answer: str
    ) -> dict[str, str]:
        raise NotImplementedError


class MockLLMClient(LLMClient):
    async def generate_answer(self, question: str, context: str) -> str:
        if not context.strip():
            return (
                "当前知识库中还没有检索到可引用的资料。你可以先上传 PDF，"
                "系统会解析、切分并向量化后再回答。"
            )
        preview = context[:420].replace("\n", " ")
        return (
            f"根据已上传资料，问题「{question}」可以从以下片段中得到初步回答："
            f"{preview}... 建议结合引用页码继续阅读原文，并在接入真实大模型后获得更强的推理总结。"
        )

    async def generate_study_plan(
        self, goal: str, background: str | None, weeks: int, hours_per_week: int
    ) -> str:
        background_text = f"基础情况：{background}\n" if background else ""
        weekly_hours = max(hours_per_week, 1)
        return (
            f"目标：{goal}\n"
            f"{background_text}"
            f"周期：{weeks} 周，每周约 {weekly_hours} 小时。\n\n"
            "阶段 1：资料梳理与知识地图\n"
            "- 上传核心论文、课程讲义和项目文档，建立 RAG 知识库。\n"
            "- 每周整理 3-5 个关键词，形成概念卡片。\n\n"
            "阶段 2：主题精读与问答训练\n"
            "- 围绕算法、系统设计、实验方法进行资料问答。\n"
            "- 对回答中的引用页码回看原文，补充笔记。\n\n"
            "阶段 3：错题与薄弱点攻克\n"
            "- 每周录入错题，按知识点统计高频错误。\n"
            "- 针对薄弱点安排专项练习和复盘。\n\n"
            "阶段 4：申请展示沉淀\n"
            "- 将学习记录转化为项目报告、研究计划和面试话术。\n"
            "- 准备 1 分钟项目介绍与技术追问答案。"
        )

    async def analyze_mistake(
        self, question_text: str, user_answer: str, correct_answer: str
    ) -> dict[str, str]:
        reason = (
            "对题目条件或关键概念理解不完整，导致解题路径与标准答案存在偏差。"
            "建议回到相关知识点，先复述定义，再补充边界条件和典型例题。"
        )
        point = _infer_knowledge_point(question_text + " " + correct_answer)
        return {"error_reason": reason, "knowledge_point": point}


class OpenAICompatibleLLMClient(MockLLMClient):
    """Simple adapter for OpenAI, DeepSeek, Ollama-compatible chat APIs."""

    async def _chat(self, messages: list[dict[str, str]]) -> str:
        if not settings.llm_api_base:
            return ""

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
            return data["choices"][0]["message"]["content"]

    async def generate_answer(self, question: str, context: str) -> str:
        if settings.llm_provider == "mock":
            return await super().generate_answer(question, context)
        try:
            content = await self._chat(
                [
                    {
                        "role": "system",
                        "content": "你是 ScholarPilot 的学术 RAG 助手，只能基于给定资料回答，并用中文说明依据。",
                    },
                    {
                        "role": "user",
                        "content": f"资料片段：\n{context}\n\n问题：{question}",
                    },
                ]
            )
            return content or await super().generate_answer(question, context)
        except Exception:
            return await super().generate_answer(question, context)

    async def generate_study_plan(
        self, goal: str, background: str | None, weeks: int, hours_per_week: int
    ) -> str:
        if settings.llm_provider == "mock":
            return await super().generate_study_plan(goal, background, weeks, hours_per_week)
        try:
            content = await self._chat(
                [
                    {
                        "role": "system",
                        "content": "你是研究生申请学习规划 Agent，请输出结构化中文学习计划。",
                    },
                    {
                        "role": "user",
                        "content": (
                            f"目标：{goal}\n基础：{background or '未提供'}\n"
                            f"周期：{weeks} 周，每周 {hours_per_week} 小时"
                        ),
                    },
                ]
            )
            return content or await super().generate_study_plan(
                goal, background, weeks, hours_per_week
            )
        except Exception:
            return await super().generate_study_plan(goal, background, weeks, hours_per_week)

    async def analyze_mistake(
        self, question_text: str, user_answer: str, correct_answer: str
    ) -> dict[str, str]:
        if settings.llm_provider == "mock":
            return await super().analyze_mistake(question_text, user_answer, correct_answer)
        try:
            content = await self._chat(
                [
                    {
                        "role": "system",
                        "content": "你是错题分析 Agent，输出两行：错因：... 知识点：...",
                    },
                    {
                        "role": "user",
                        "content": (
                            f"题目：{question_text}\n学生答案：{user_answer}\n"
                            f"正确答案：{correct_answer}"
                        ),
                    },
                ]
            )
            return _parse_mistake_analysis(content)
        except Exception:
            return await super().analyze_mistake(question_text, user_answer, correct_answer)


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


def _parse_mistake_analysis(content: str) -> dict[str, str]:
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
    return OpenAICompatibleLLMClient()
