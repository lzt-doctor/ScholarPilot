# ScholarPilot：基于 Agentic RAG 的学术资料智能问答与学习规划系统

## 项目简介

ScholarPilot 是一个面向研究生申请场景的 AI 学习辅助系统。项目支持上传学术 PDF，自动解析、切分并向量化存储，用户可以基于个人资料库进行 RAG 问答，并获得带页码和原文片段的来源引用。同时系统提供学习计划生成、错题记录、错因分析和数据统计功能。

## 技术栈

Vue 3、Vite、Element Plus、Axios、ECharts、Python、FastAPI、SQLAlchemy、Pydantic、JWT、PostgreSQL、pgvector、sentence-transformers、PyMuPDF、Docker、Docker Compose。

## 个人职责

- 设计并实现前后端分离架构和 Docker 化部署方案。
- 设计 users、documents、document_chunks、chat_sessions、chat_messages、mistake_records、study_plans 等核心表。
- 实现 PDF 解析、chunk 切分、embedding 生成、pgvector 相似度检索和 RAG 问答流程。
- 设计 RetrievalAgent、StudyPlannerAgent、MistakeAnalysisAgent 三类 Agent。
- 实现 Vue 3 管理台，包括文档管理、AI 问答、学习计划、错题分析和统计图表。

## 核心功能

- JWT 登录注册与用户隔离。
- PDF 上传、解析、切分和向量化。
- 基于 pgvector 的 Top-K 语义检索。
- RAG 问答与来源引用。
- 学习计划生成。
- 错题记录、错因分析和知识点归因。
- ECharts 数据统计面板。
- Docker Compose 一键启动。

## 技术亮点

- 使用 PostgreSQL + pgvector 将结构化业务数据与向量数据统一管理。
- 通过 LLMClient 抽象支持 OpenAI、DeepSeek、Ollama 等模型接入。
- 在无真实 LLM API 时提供 mock fallback，保证项目可演示。
- Agent 职责拆分清晰，便于后续扩展为多 Agent 协作系统。
- 保留 chunk 页码和原文片段，提高 RAG 回答可追溯性。

## 简历版 3 条 bullet points

- 独立开发 ScholarPilot 学术资料智能问答系统，基于 FastAPI、Vue 3、PostgreSQL + pgvector 实现 PDF 解析、文本切分、向量化存储和 RAG 问答全流程。
- 设计 RetrievalAgent、StudyPlannerAgent、MistakeAnalysisAgent，实现资料检索、学习计划生成、错题错因分析等 Agentic AI 能力，并通过 LLMClient 支持多模型扩展与 mock 演示。
- 构建 Docker Compose 一键部署方案和 ECharts 数据看板，完成用户认证、文档管理、问答引用、学习计划、错题统计等完整 Web 产品闭环。

## 面试介绍版 1 分钟话术

ScholarPilot 是我为研究生申请展示设计的 Agentic RAG 项目，目标是把学术资料阅读、智能问答和学习规划整合到一个可运行的 Web 系统中。用户上传 PDF 后，后端会用 PyMuPDF 提取文本，按页码和段落切成 chunk，再用 sentence-transformers 生成 embedding 并存入 PostgreSQL 的 pgvector 字段。提问时系统会把问题向量化，通过余弦距离检索 Top-K 片段，拼接上下文后交给 LLMClient 生成回答，并返回文档名、页码和原文片段作为引用。项目还设计了三个 Agent：RetrievalAgent 负责检索，StudyPlannerAgent 负责学习计划，MistakeAnalysisAgent 负责错题分析。工程上我使用 FastAPI、SQLAlchemy、JWT、Vue 3、Element Plus 和 Docker Compose，实现了从数据库设计、RAG 流程到前端演示的完整闭环。

