# 笔记问答与登录交互调整实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标：** 调整登录页、问答会话生命周期和等待反馈，并移除合集入口，让问答初始化不干扰页面滚动。

**架构：** 登录页改为浅色背景；问答页只在第一次发送问题时创建会话，空会话不写入数据库。问答等待区根据后端是否返回真实思考内容选择展示真实思考打字机或简洁的“思考中 / 当前任务进展”两行提示。合集从前端导航、路由和问答侧栏移除，已有后端数据表和接口暂时保留以兼容历史数据。

**技术栈：** React、React Router、Zustand/axios、FastAPI、SQLite、Tailwind CSS。

---

### 任务 1：登录页改为白色背景

**文件：**
- 修改：`frontend/src/pages/LoginPage.jsx`

- [ ] 将页面外层背景、渐变装饰和卡片阴影改为白色/浅灰色视觉。
- [ ] 保留错误提示、提交中状态和密码输入交互。
- [ ] 构建前端确认样式类可编译。

### 任务 2：空会话不落库并移除会话初始化 loading

**文件：**
- 修改：`frontend/src/pages/RAGPage.jsx`
- 参考：`frontend/src/api/client.js`
- 修改：`src/api/note.py`
- 修改：`src/core/checkpoint.py`

- [ ] 首次加载只读取会话列表，不自动创建“新会话”；没有会话时使用本地空状态。
- [ ] 点击“新会话”只切换到本地草稿状态，不调用创建接口。
- [ ] 首次发送问题时不预先创建数据库会话；`/api/rag/ask` 在成功生成首条问答后懒创建会话并保存用户/助手消息，避免失败请求遗留空会话。
- [ ] 前端没有 `activeSessionId` 时允许发送，成功响应中的新 `session_id` 再加入会话列表并设为当前会话。
- [ ] 删除最后一个会话后回到本地空草稿，不自动创建数据库记录。
- [ ] 移除阻塞输入框和侧栏的 `sessionLoading` loading 状态；会话读取失败时允许继续输入并在发送时处理错误。

### 任务 3：统一等待反馈和初始化滚动行为

**文件：**
- 修改：`frontend/src/pages/RAGPage.jsx`

- [ ] 初始化恢复历史消息时使用 `scrollIntoView({ behavior: "auto" })` 或直接设置滚动位置。
- [ ] 用户新增问题、收到回答或打字机更新时才使用平滑滚动。
- [ ] 后端从兼容模型响应中读取可选 `reasoning_content`/`thinking` 字段并返回 `thinking`；前端若有该字段，按打字机展示真实思考。
- [ ] 没有真实思考文本时只展示两行：第一行“思考中”，第二行当前任务进展状态。
- [ ] 保留首条用户消息即时显示，并确保等待状态和回答打字机不会重复创建消息。

### 任务 4：移除合集前端功能

**文件：**
- 修改：`frontend/src/App.jsx`
- 修改：`frontend/src/components/Header.jsx`
- 修改：`frontend/src/pages/RAGPage.jsx`
- 删除：`frontend/src/pages/CollectionsPage.jsx`
- 删除：`frontend/src/hooks/useCollections.js`
- 删除：`frontend/src/stores/collectionStore.js`
- 修改：`frontend/src/api/client.js`
- 修改：`frontend/src/i18n/en.json`
- 修改：`frontend/src/i18n/zh.json`

- [ ] 删除合集导航和 `/collections` 路由。
- [ ] 删除问答侧栏中的合集筛选和相关请求。
- [ ] 删除前端合集 API、状态管理、Hook 和页面文件。
- [ ] 清理无引用的合集翻译文案。
- [ ] 保留后端合集接口和数据库表，避免已有部署启动或迁移失败。

### 任务 5：修复 403 CSRF 失效重试

**文件：**
- 修改：`frontend/src/api/client.js`
- 修改：`src/api/auth.py`
- 修改：`src/security.py`
- 修改：`tests/test_security.py`

- [ ] 确认认证状态接口能够在已登录状态下刷新 CSRF Cookie。
- [ ] 对明确的 CSRF 校验失败响应刷新令牌并只自动重试原请求一次，避免死循环和重复提交。
- [ ] 登录、登出和 GET 请求不进入重试逻辑。
- [ ] 本地未显式设置 Cookie Secure 时允许 HTTP 开发环境正常携带认证 Cookie；生产环境仍由环境变量显式启用 Secure。
- [ ] 补充令牌刷新/失效场景的回归测试或安全辅助函数测试。

### 任务 6：统一 favicon

**文件：**
- 修改：`frontend/index.html`
- 修改：`frontend/public/favicon.svg`
- 删除：`frontend/public/favicon.png`
- 删除：`frontend/public/favicon.ico`

- [ ] 只保留与页面品牌图标一致的 SVG favicon 链接。
- [ ] 删除旧 PNG/ICO 入口，避免浏览器在不同缓存或 fallback 下显示两种图标。

### 验证

- [ ] 在 `frontend` 目录运行 `npm run build`。
- [ ] 运行 `pytest -q`。
- [ ] 运行 `git diff --check`。
