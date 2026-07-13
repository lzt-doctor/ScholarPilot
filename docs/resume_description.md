# ScholarPilot：可追溯学术文档 RAG 检索系统与可复现实验平台

## 项目简介

面向学术 PDF 的全栈检索增强问答系统，支持文档解析、向量版本追踪、Exact/HNSW/BM25/RRF Hybrid 检索、编号引用校验、运行状态披露和可复现实验。

## 技术栈

FastAPI、SQLAlchemy、Pydantic、Alembic、PostgreSQL、pgvector、sentence-transformers、jieba、rank-bm25、PyMuPDF、Vue 3、Element Plus、ECharts、Docker Compose、pytest、GitHub Actions。

## 个人职责

- 设计用户、文档、chunk、会话和学习数据模型，使用 Alembic 管理增量迁移。
- 实现 PDF 安全校验、线程池解析、embedding 维度检查、模型版本一致性与重新索引。
- 抽象统一 Retriever，完成精确向量、HNSW、BM25 和 RRF Hybrid 检索及用户隔离。
- 设计证据阈值、编号引用解析、引用合法性校验和运行元数据。
- 建立 pytest、CI 和 JSON/CSV 实验平台，保存查询级原始结果与复现环境。

## 技术亮点

- 不静默降级：真实模型失败、显式 mock 和显式 hash fallback 在 API 与页面中可区分。
- 检索可审计：返回 similarity、lexical/vector rank、fused score、检索模式和 HNSW 参数。
- 数据可治理：文档向量模型、维度和版本不一致时拒绝查询，避免混用向量空间。
- 实验可复现：计算 Recall@5/10、MRR、nDCG@10、延迟分位数与 QPS，并保存 Git commit 和原始结果。

## 简历版 3 条 bullet points

- 基于 FastAPI、PostgreSQL/pgvector 与 Vue 3 构建可追溯学术文档 RAG 系统，实现 PDF 解析、向量版本管理、来源引用和 Docker 部署。
- 抽象 Exact、HNSW、BM25 与 RRF Hybrid 统一检索接口，强制用户数据隔离，并返回检索排名、融合分数及实际运行参数。
- 使用 Alembic、pytest 和 GitHub Actions 建立工程质量基线，开发 Recall/MRR/nDCG 与延迟消融脚本，结果包含 Git commit、配置和逐查询记录。

## 1 分钟面试介绍

ScholarPilot 是我做的一个面向学术 PDF 的可追溯 RAG 系统。它和普通聊天 Demo 的区别是把检索过程、模型版本和失败状态都暴露出来。文档上传后会通过 PyMuPDF 解析并生成向量，数据库记录模型、维度、版本和索引状态；查询支持精确余弦、pgvector HNSW、BM25 以及 RRF Hybrid，并且所有查询按用户隔离。如果模型版本不一致，系统会拒绝检索并提示重新索引。回答上下文使用编号来源，后端会校验模型引用的编号是否存在，同时明确说明 evidence strength 只表示检索证据，不是答案正确率。工程上我补了 Alembic、pytest、CI、Docker 和一套可复现实验脚本，能输出 Recall、MRR、nDCG、延迟分位数及每条查询的原始结果。当前 demo 数据只用于验证实验链路，我不会用它夸大真实检索效果。
