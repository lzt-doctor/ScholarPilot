# ScholarPilot GitHub 发布指南

这份清单用于把 ScholarPilot 整理成适合公开展示的 GitHub 项目，重点是安全、可运行、可读、可用于研究生申请展示。

## 仓库信息建议

- Repository name：`ScholarPilot`
- Description：`Agentic RAG academic assistant for document QA, study planning, and mistake analysis`
- Topics：`rag`、`agentic-rag`、`fastapi`、`vue3`、`pgvector`、`sentence-transformers`、`postgresql`、`graduate-application`

## 发布前检查

- 不提交 `.env`、真实 API Key、数据库数据、上传 PDF、`node_modules`、构建产物。
- 保留 `.env.example` 和 `backend/.env.example`，让别人能按模板配置。
- 保留 `README.md`、`docs/project_report.md`、`docs/system_design.md`、`docs/resume_description.md`。
- 确认 `docker compose up --build -d` 可以启动数据库、后端和前端。
- 截图建议放在 `docs/screenshots/`，README 中再引用。

## 推荐提交命令

```bash
git add .
git commit -m "Initial ScholarPilot MVP"
```

## 通过 GitHub 网页发布

1. 登录 GitHub，创建新仓库 `ScholarPilot`。
2. 不要勾选自动生成 README、`.gitignore` 或 LICENSE，避免和本地文件冲突。
3. 在本地执行：

```bash
git branch -M main
git remote add origin https://github.com/<your-username>/ScholarPilot.git
git push -u origin main
```

## 通过 GitHub CLI 发布

如果已安装并登录 `gh`：

```bash
gh repo create ScholarPilot --public --source=. --remote=origin --push
```

如果只想作为私人作品集先打磨，可以把 `--public` 改成 `--private`。

## README 展示建议

README 首页建议优先突出：

- 一句话项目定位：Agentic RAG 学术资料问答与学习规划系统。
- 核心技术：FastAPI、Vue 3、PostgreSQL、pgvector、sentence-transformers、LLMClient。
- RAG 可信性：sources、similarity、confidence。
- Docker 一键运行方式。
- 截图：Dashboard、PDF 上传、AI 问答来源引用、学习计划、错题统计。

## 安全提醒

真实大模型 API Key 只放在本地 `.env` 中，不要写进 README、代码、截图、issue 或 commit message。
