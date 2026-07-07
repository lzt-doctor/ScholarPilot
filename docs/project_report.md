# ScholarPilot 项目报告

## 1. 项目背景

研究生申请过程中，申请者通常需要阅读大量论文、课程资料、项目文档和面试题。传统资料管理方式依赖人工检索和笔记整理，难以快速定位知识点，也难以把学习过程转化为可展示的项目成果。ScholarPilot 以 Agentic RAG 为核心，将学术资料问答、学习规划、错题复盘和数据统计整合为一个完整 Web 系统。

## 2. 需求分析

系统面向计算机科学、人工智能、软件工程方向申请者，核心需求包括：

- 管理个人学术 PDF 资料。
- 对上传资料进行解析、切分和向量化。
- 基于资料内容进行可信问答，并返回引用来源。
- 根据申请目标生成阶段化学习计划。
- 记录错题，分析错因和知识点。
- 用统计图表展示资料积累和薄弱知识点。
- 支持 Docker 一键启动，方便演示和部署。

## 3. 系统设计

系统采用前后端分离架构。前端使用 Vue 3 + Element Plus 实现管理台；后端使用 FastAPI 提供 REST API；数据库使用 PostgreSQL + pgvector 存储业务数据与向量；AI 层通过可配置的 sentence-transformers 模型生成 embedding，并通过可替换 LLMClient 接入真实大模型或 mock 模式。

后端分层如下：

- routers：认证、文档、问答、学习计划、错题、统计接口。
- models：SQLAlchemy ORM 数据模型。
- schemas：Pydantic 请求与响应结构。
- services：PDF 解析、embedding、LLM 调用。
- rag：Agent 和检索逻辑。
- utils：JWT、安全和依赖注入。

## 4. 数据库设计

数据库至少包含以下核心表：

- users：保存用户身份信息和密码哈希。
- documents：保存上传文档的文件名、类型、摘要和分类。
- document_chunks：保存文档切片、页码、chunk 序号、章节标题和向量 embedding。
- chat_sessions：保存问答会话。
- chat_messages：保存用户和助手消息，以及答案引用来源。
- mistake_records：保存错题、答案、错因和知识点。
- study_plans：保存学习目标和计划内容。

其中 document_chunks.embedding 使用 pgvector 的 vector 类型，便于执行余弦距离排序检索。

## 5. 核心算法设计

系统核心算法是检索增强生成：

1. 文档解析：使用 PyMuPDF 按页抽取 PDF 文本。
2. 文本切分：按段落聚合，控制 chunk 长度，并保留页码。
3. 向量化：默认使用 `sentence-transformers/all-MiniLM-L6-v2` 生成 384 维向量，并通过 `EMBEDDING_MODEL` 支持后续切换到 `BAAI/bge-m3`、`intfloat/multilingual-e5-base` 等模型。
4. 相似度检索：将问题向量与 chunk 向量进行 cosine distance 排序。
5. 上下文构造：将 Top-K chunk 拼接为 LLM context。
6. 回答生成：调用 LLMClient 输出回答。
7. 来源引用：返回 document_name、page_number、chunk_index、chunk_text、similarity。
8. 可信度估计：根据最高 similarity 和可靠来源数量返回 high、medium 或 low。

来源引用是 ScholarPilot 区别于普通聊天机器人的关键设计。普通聊天机器人只输出答案，用户难以判断答案是否来自资料或模型想象；RAG 系统返回引用片段后，用户可以回到 PDF 页码和 chunk 原文检查依据，从而提升学术问答的可追溯性。

embedding 模型做成可配置，是为了兼顾稳定演示和后续效果提升。MVP 默认模型体积较小、启动更稳定；当项目需要更强的中文或多语言语义检索能力时，可以通过 `.env` 切换模型并重新向量化文档。由于不同模型的向量维度不同，切换模型时需要同步调整 `EMBEDDING_DIMENSION` 并重建相关向量数据。

confidence 的设计目标不是替代事实校验，而是向用户暴露检索质量。当系统找到多个相似度较高的来源时，回答更可信；当没有来源或 similarity 很低时，系统应提示 low，避免把弱依据回答包装成确定结论。

## 6. RAG 模块实现

RAG 模块位于 `backend/app/rag/agents.py` 和相关 service 中。RetrievalAgent 负责接收用户问题、生成问题向量、查询 pgvector 并返回结构化来源。Chat 路由负责创建会话、保存用户消息、调用 LLMClient、保存助手回答并返回统一响应格式。

系统同时提供 mock LLM，保证无外部 API 时仍能演示完整 RAG 流程。embedding 服务也采用降级策略：优先加载 `EMBEDDING_MODEL` 指定的 sentence-transformers 模型，本地模型不可用时使用 deterministic hash embedding 保持可运行性。

## 7. Agent 模块设计

系统设计了三个轻量 Agent：

- RetrievalAgent：面向问答场景，根据问题检索相关资料。
- StudyPlannerAgent：面向学习规划场景，根据目标、基础、周期和时间投入生成计划。
- MistakeAnalysisAgent：面向错题复盘场景，根据题目、用户答案和正确答案分析错因与知识点。

这种设计将不同智能任务拆为独立职责，后续可以扩展为多 Agent 协作、工具调用、计划执行和评估反馈。

## 8. 系统测试

建议测试路径：

1. 注册并登录用户。
2. 上传包含文字的 PDF。
3. 查看文档列表和 chunk 详情。
4. 在 AI 问答页提问，检查是否返回答案、confidence 和包含 document_name、page_number、chunk_index、chunk_text、similarity 的来源引用。
5. 生成学习计划，检查内容是否保存。
6. 录入错题，检查错因和知识点是否生成。
7. 打开统计页，检查 ECharts 图表是否展示。
8. 使用 Docker Compose 从空环境启动系统。

## 9. 项目创新点

- 将 RAG、Agent、学习规划和错题分析合并为一个可演示的申请项目。
- 保留页码、chunk 和 similarity 引用，提升问答可信度。
- 返回 confidence，让用户理解当前回答依赖的检索证据强弱。
- embedding 模型可配置，兼顾轻量演示和后续检索效果升级。
- LLMClient 可替换，支持 OpenAI、DeepSeek、Ollama 等兼容接口。
- mock fallback 让系统无需外部服务即可运行。
- 数据库设计体现结构化业务数据与向量数据的结合。

## 10. 不足与改进

当前版本是 MVP，仍有改进空间：

- 缺少正式迁移工具，后续可引入 Alembic。
- 文档解析主要处理文本型 PDF，后续可增加 OCR。
- 当前只做向量检索，后续可加入 Hybrid Search 和 Reranker。
- 文档解析和向量化仍在请求链路内，后续可使用 Redis + Celery 改为后台任务。
- LLM 回答可加入更严格的引用格式、RAG 评估面板和事实一致性评估。
- 错题分析可引入知识图谱或课程大纲映射。
- 测试体系仍较轻量，后续可补充 pytest 覆盖认证、上传、RAG 问答和 Agent 服务。

## 11. 总结

ScholarPilot 完成了从资料上传到 RAG 问答、从学习规划到错题分析、从数据存储到 Docker 部署的完整闭环。该项目能够体现申请者在 AI 应用、数据库系统、Web 全栈开发和软件工程架构方面的综合能力，并可进一步拓展为个性化学习智能体研究方向。
