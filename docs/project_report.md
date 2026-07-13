# ScholarPilot 项目报告

## 1. 项目背景

学术资料问答的价值不只在于生成流畅文本，更在于能否定位证据、解释检索方法并重复验证结果。ScholarPilot 因此从全栈 RAG MVP 升级为面向学术 PDF 的可追溯检索系统与可复现实验平台。

## 2. 需求分析

系统保留认证、文档、问答、学习计划、错题和统计功能，同时新增运行真实性、向量版本治理、多检索基线、引用校验、实验记录和自动化测试。所有检索必须按用户隔离；任何模型失败不得被静默隐藏。

## 3. 系统设计

前端使用 Vue 3 管理业务界面和运行状态；FastAPI 提供 API 与检索编排；PostgreSQL 保存业务数据，pgvector 保存向量与 HNSW 索引；PyMuPDF 和 sentence-transformers 处理文档。PDF 解析和 embedding 通过线程池执行，正式数据库结构由 Alembic 管理。

检索逻辑实现统一 `Retriever` 接口，`RetrievalService` 负责模式选择和向量版本检查。学习计划和错题分析被准确建模为 Service，因为当前实现是单次 LLM 调用，不具备自主规划和工具循环。

## 4. 数据库设计

主要实体为用户、文档、文档 chunk、会话、消息、计划和错题。文档新增 embedding 模型、维度、版本、索引状态和安全错误码。消息保存来源、证据强度、引用校验和运行元数据。

迁移 `0001_initial` 建立基础表，`0002_research` 增加追踪字段并创建 `vector_cosine_ops` HNSW 索引。旧数据库文档被标记为 `requires_reindex`，避免猜测历史模型。

## 5. 核心检索设计

- Exact：禁用近似索引后按 cosine distance 排序，作为精确基线。
- HNSW：使用 pgvector HNSW，支持 `m`、`ef_construction` 和查询时 `ef_search`。
- BM25：jieba `HMM=False` 分词，rank-bm25 排序，缓存按用户建立并在文档变更后失效。
- Hybrid：分别取得 BM25 和向量候选，以 Reciprocal Rank Fusion 合并。

检索来源返回向量相似度、词法分数、两类 rank 和融合分数。证据低于阈值时跳过 LLM，避免在没有资料支持时生成答案。

## 6. RAG 与引用

来源按 `[1]`、`[2]` 编号加入上下文，LLM 被要求逐项引用。服务端解析回答中的编号，验证编号范围并映射到真实 chunk ID。`citation_validity` 只能说明编号存在；不能证明引文蕴含回答。

`evidence_strength` 由检索信号计算，只用于表达证据强弱。它不是答案正确率，也不是经过校准的概率。旧字段 `confidence` 仅为 API 兼容保留。

## 7. 运行真实性

sentence-transformers 加载或推理失败会返回明确错误。hash embedding 只有在 `ALLOW_EMBEDDING_FALLBACK=true` 时可用。真实 LLM 请求失败返回 `degraded` 和错误码，不会调用 mock 生成替代内容。mock 模式本身是显式可见的演示模式。

`/health/details` 和前端状态页展示 embedding backend、模型、维度、加载状态、LLM 模式、数据库和 pgvector 状态。

## 8. 系统测试

pytest 使用 SQLite 业务夹具、deterministic fake embedding 和 mock client，避免外部网络。测试覆盖 chunk、维度、fallback、模型版本、BM25、RRF、证据强度、引用、用户隔离、缓存失效、上传/重索引/删除以及 LLM 失败状态。PostgreSQL 迁移和 HNSW 路径通过 Docker/CI 验证。

## 9. 实验设计

实验平台读取 JSONL 查询与相关 chunk 标注，报告 Recall@5、Recall@10、MRR、nDCG@10 和延迟分位数。消融矩阵覆盖检索模式、chunk size、overlap、top_k 和 ef_search。每份结果保存 Git commit、时间、数据版本、配置、模型、环境与逐查询结果。

仓库 demo 是合成数据，只验证可复现链路。实际结果由 `make eval-demo` 生成，详见 `docs/research_report.md` 和 `experiments/results/demo/`。

## 10. 创新点

- 将“回答可追溯”拆为来源结构、编号引用和服务端校验。
- 将 exact、ANN、词法和融合检索置于同一可评估接口。
- 把模型身份写入文档，查询时执行兼容性检查。
- 将 mock/fallback 从隐藏实现细节改为用户可见运行状态。
- 实验保存原始查询级结果，减少只报告汇总数字的不可审计性。

## 11. 不足与改进

当前没有 OCR、reranker、引用蕴含模型、共享 BM25 缓存和持久任务队列；HNSW demo 规模过小；真实学术 benchmark 尚未建立。后续研究必须使用公开或可审计数据，避免从合成 demo 推导效果结论。

## 12. 总结

ScholarPilot 的升级重点是诚实呈现运行状态和实验条件。系统仍是研究原型，但已经具备清晰基线、失败边界、迁移方案、测试和复现入口，可用于继续研究学术文档检索与可追溯 RAG。
