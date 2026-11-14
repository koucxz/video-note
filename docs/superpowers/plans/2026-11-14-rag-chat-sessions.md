# RAG Chat Sessions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为笔记问答增加类似 Google NotebookLM 的持久化会话列表，让用户可以新建、切换、重命名、删除会话，并在刷新页面后恢复完整问答上下文。

**Architecture:** 在现有 SQLite `CheckpointManager` 中新增问答会话和消息表；RAG API 负责会话 CRUD，并通过一个显式事务方法原子化保存用户问题、助手回答、来源和 token 用量。会话保存可变的笔记范围，前端每次发送问题时同步当前范围，因此用户切换来源后后续问题立即生效；没有 `session_id` 的旧请求仍按临时会话兼容处理。

**Tech Stack:** FastAPI、SQLite/WAL、Python `CheckpointManager`、React 19、Zustand-free local state、Axios、React Markdown、现有 Sentence Transformers/Milvus RAG。

---

### Task 1: 持久化问答会话和消息

**Files:**
- Modify: `src/core/checkpoint.py`
- Modify: `tests/test_checkpoint_extended.py`

- [ ] **Step 1: Write failing tests for session and message CRUD**

覆盖以下行为：创建会话并保存 `title`、`scope`；按更新时间倒序、通过 `limit` 限制列表；追加 user/assistant 消息并按序读取；一个 exchange 在同一事务中保存两条消息并更新 `updated_at`；事务失败会回滚；重命名会话会更新 `updated_at`；删除会话会级联删除消息；查询不存在的会话返回 `None`。

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pytest tests/test_checkpoint_extended.py -k "session or chat_message" -v`

Expected: FAIL because the new `CheckpointManager` methods and tables do not exist.

- [ ] **Step 3: Add SQLite tables and manager methods**

在 `_init_db()` 增加：

```sql
qa_sessions(
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  scope TEXT NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
)
qa_messages(
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  sources TEXT NOT NULL DEFAULT '[]',
  tokens INTEGER DEFAULT 0,
  created_at TIMESTAMP NOT NULL,
  FOREIGN KEY (session_id) REFERENCES qa_sessions(id) ON DELETE CASCADE
)
```

启用 `PRAGMA foreign_keys=ON`，并添加 `idx_qa_sessions_updated`、`idx_qa_messages_session`。创建记录时由 Python 使用同一个 `datetime.now()` 写入 `created_at` 和 `updated_at`，消息写入时使用当前时间。提供 `create_qa_session`、`get_qa_session`、`list_qa_sessions(limit=50)`、`update_qa_session`、`delete_qa_session`、`get_qa_messages` 和 `save_qa_exchange` 方法；JSON 字段统一序列化/反序列化，所有写操作复用现有 `RLock`。`save_qa_exchange` 使用 `BEGIN`、`COMMIT`、`ROLLBACK`，一次写入 user/assistant 两条消息并更新会话时间，保证不会留下半条 exchange。

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: `pytest tests/test_checkpoint_extended.py -k "session or chat_message" -v`

Expected: PASS.

### Task 2: 将 RAG API 接入会话

**Files:**
- Modify: `src/api/note.py`
- Modify: `tests/test_api.py`
- Modify: `frontend/src/api/client.js`

- [ ] **Step 1: Add API tests for session lifecycle and persisted ask**

使用现有测试客户端和 mock AI/vector 服务，验证：

1. `POST /api/rag/sessions` 返回会话 ID；
2. `GET /api/rag/sessions/{id}` 返回消息；
3. `POST /api/rag/ask` 传入 `session_id` 后保存 user/assistant 两条消息；
4. 未传 `session_id` 的旧请求仍返回答案，不改变当前兼容行为；
5. 删除会话后再次读取返回 404；
6. 请求 scope 会更新会话 scope，无结果时也保存两条消息；
7. 响应包含 `session_id`、`user_message`、`assistant_message`、`sources`、`tokens`；
8. 问题/历史超限、错误类型的 `question`、`history`、`scope` 返回 422；
9. 模拟 `save_qa_exchange` 失败时确认事务回滚且没有孤立消息。

- [ ] **Step 2: Run the focused API tests and verify they fail**

Run: `pytest tests/test_api.py -k "rag_session or rag_ask" -v`

Expected: FAIL because the session routes and persistence logic do not exist.

- [ ] **Step 3: Implement session routes and request handling**

在 `/api/rag` 路由下增加：

- `GET /api/rag/sessions?limit=50`：返回最近更新的会话摘要，字段为 `id`、`title`、`scope`、`created_at`、`updated_at`、`message_count`、`preview`；`limit` 使用 Query 校验，范围为 1-100；
- `POST /api/rag/sessions`：接收 `title`、`scope`，默认标题为“新会话”；
- `GET /api/rag/sessions/{session_id}`：返回会话详情及消息；
- `PATCH /api/rag/sessions/{session_id}`：只允许更新标题；
- `DELETE /api/rag/sessions/{session_id}`：删除会话及消息。

扩展 `POST /api/rag/ask`：

- 接收可选 `session_id`；
- 有 `session_id` 时校验会话存在，并使用该会话最近 6 条消息作为历史；
- 请求带 `scope` 时先更新会话 scope，使前端当前选中的笔记范围立即生效；未带 scope 时使用会话已有 scope；
- `question` 必须是字符串且限制为 1-4000 个字符，`history` 必须是数组，最多 6 条且每条必须是包含合法 `role`/字符串 `content` 的对象、内容最多 4000 个字符，`scope` 必须是对象且 `task_ids` 必须是字符串数组；非法类型和超限统一返回 422；
- 无相关片段时也保存 user 消息和“没有可用笔记”的 assistant 消息；
- 检索和 LLM 成功或无结果 fallback 后调用 `save_qa_exchange`，一次事务写入两条消息、sources、tokens，并返回 `session_id`、`user_message`、`assistant_message`、`sources`、`tokens`；
- LLM 异常时不写入 assistant 消息，避免产生半条记录；
- 无 `session_id` 时保留现有行为。

为避免消息角色注入，历史记录只允许 `user` 和 `assistant`，内容长度和消息数量沿用现有限制。

- [ ] **Step 4: Add frontend API client functions**

在 `frontend/src/api/client.js` 添加：

```js
getRagSessions()
createRagSession(title, scope)
getRagSession(sessionId)
renameRagSession(sessionId, title)
deleteRagSession(sessionId)
```

并扩展 `ragAsk` 传递 `session_id` 和当前 `scope`。

- [ ] **Step 5: Run backend tests**

Run: `pytest tests/test_api.py -k "rag_session or rag_ask" -v`

Expected: PASS.

### Task 3: 前端增加 NotebookLM 风格会话列表

**Files:**
- Modify: `frontend/src/pages/RAGPage.jsx`
- Modify: `frontend/src/i18n/zh.json`
- Modify: `frontend/src/i18n/en.json`

- [ ] **Step 1: Add local UI behavior tests or a manual interaction checklist**

验证以下流程：首次进入自动加载会话列表；点击“新会话”后清空消息；切换会话加载历史消息和 scope；发送问题后刷新页面仍能看到完整消息；重命名和删除后列表立即更新；空会话不会阻塞创建新会话。

- [ ] **Step 2: Add session state and lifecycle to `RAGPage.jsx`**

增加 `sessions`、`activeSessionId`、`sessionLoading`、`sessionTitle` 状态：

- 页面加载调用 `getRagSessions()`；
- 没有会话时创建一个空会话；
- 选择会话调用 `getRagSession()`，恢复 `messages` 和 `selectedNotes`；
- 新会话保存当前选中的笔记 ID 作为 scope；
- 第一次发送时，如果当前会话仍是默认标题，使用问题前 30 个字符更新标题；
- 发送时传入 `session_id` 和当前 scope，成功后以服务端返回的 `user_message`、`assistant_message` 更新界面；
- 对删除当前会话的情况自动切换到最近会话或创建新会话。

左侧栏使用“会话列表 + 新建按钮 + 会话操作菜单”的布局，保留已有“知识范围”选择区域；加载合集时调用 `getCollections()`，并为每个合集调用现有 `/api/collections/{id}/notes` 获取 `noteIds`，避免依赖当前摘要接口未返回的字段；移动端将会话列表收进可折叠区域，避免挤压问答内容。

- [ ] **Step 3: Add Chinese and English translations**

增加会话相关文案：新会话、会话列表、重命名、删除会话、确认删除、暂无会话、加载会话失败等。

- [ ] **Step 4: Build the frontend**

Run: `npm run build` in `frontend/`

Expected: Vite build succeeds without React warnings that break the page.

### Task 4: 一致性、索引和回归验证

**Files:**
- Modify: `src/core/engine.py`（生成新版本后更新向量索引）
- Modify: `src/api/note.py`（编辑、润色、回滚后更新向量索引）
- Modify: `src/api/task.py`（删除笔记时移除向量索引）
- Modify: `tests/test_security.py` or `tests/test_api.py` for auth-protected routes

- [ ] **Step 1: Ensure note deletion removes stale vector entries**

删除笔记时调用 `vector.remove_note(task_id)`；新生成、编辑、润色和回滚后调用 `vector.index_note(task_id, latest_content)`，避免问答会话引用旧内容。索引更新失败不能阻塞笔记保存，记录 warning 并允许下一次重建补齐。

- [ ] **Step 2: Add authorization and input-bound tests**

验证会话 ID 不存在返回 404，标题长度限制为 1-120 个字符，问题限制为 1-4000 个字符，history 单条内容限制为 4000 个字符，认证开启时会话接口继承现有 API middleware 和 CSRF 规则。

- [ ] **Step 3: Run the full backend test suite**

Run: `pytest -q`

Expected: all existing and new tests pass.

- [ ] **Step 4: Review the final diff**

Run: `git diff --check` and `git status --short`，确认只包含会话功能相关文件。
