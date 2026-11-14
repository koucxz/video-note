# VideoNote 部署加固 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 VideoNote 在国内云服务器上以单用户或少量受邀用户模式安全运行，并控制模型 Token、CPU、内存、磁盘和上传风险。

**Architecture:** 外部请求只进入 Caddy HTTPS 反向代理；后端容器只通过 Docker 内网访问。应用层使用单租户登录和 HttpOnly 会话 Cookie，敏感配置只在服务器端读取；上传、任务和模型调用在服务端执行大小、时长、并发、频率和预算限制。频率与 Token 用量写入 SQLite 并以事务原子更新；数据继续使用 SQLite 和现有卷，但增加备份、清理和重启恢复说明。

**Tech Stack:** FastAPI、Caddy、Docker Compose、SQLite、Python requirements/constraints、pytest。

---

### Task 1: 清理和隔离凭据

**Files:**
- Modify: `config.yaml`
- Modify: `data/db/providers.json`
- Modify: `Dockerfile`
- Modify: `.gitignore`, `.env.example`, `config.yaml.example`
- Test: `tests/test_config_security.py`

- [ ] 删除仓库和运行数据中的真实 Key，统一改为环境变量占位符。
- [ ] 禁止 Dockerfile 将含凭据的 `config.yaml` 复制进镜像；改用部署时挂载的无密配置或环境变量。
- [ ] 增加密钥扫描检查，确认 Git 工作树、镜像构建上下文和 API 响应不含真实 Key。
- [ ] 对已经提交过的 Key 执行吊销和重发，并在文档中记录 Git 历史清理步骤。

### Task 2: 增加单用户/受邀用户鉴权和数据访问边界

**Files:**
- Create: `src/api/auth.py` 或等价鉴权模块
- Modify: `src/main.py`
- Modify: `src/api/*.py`
- Modify: `frontend/src/api/client.js`
- Test: `tests/test_auth.py`, `tests/test_api_access.py`

- [ ] 增加 `VIDEONOTE_AUTH_PASSWORD`、`VIDEONOTE_SESSION_SECRET`、`POST /api/auth/login`、`GET /api/auth/me` 和 `POST /api/auth/logout`；会话 Cookie 使用 HMAC 签名、7 天过期，生产环境设置 `HttpOnly + Secure + SameSite=Lax`，更换 session secret 可撤销全部会话。
- [ ] 登录成功和 `GET /api/auth/me` 设置 `videonote_csrf` 非 HttpOnly Cookie（Path=/、随机值）；前端所有写请求发送 `X-CSRF-Token`，后端常量时间比较。登录/登出豁免 CSRF，登出清理会话和 CSRF Cookie；不提供公开注册。
- [ ] 认证中间件覆盖所有 `/api/**`，仅放行健康检查和认证入口；现有 `/ws/task/{task_id}`、`/ws/all` 在握手时校验会话 Cookie 与 Origin，未认证连接立即关闭。第一阶段所有认证用户共享单租户管理员权限，不做角色区分。
- [ ] 如果支持多个账号，为任务、笔记、集合和上传文件增加 owner 标识并按用户过滤；单用户模式则明确禁止公开注册。
- [ ] 反向代理只负责入口网络控制；通过服务器防火墙限制 SSH 来源，应用访问控制由登录会话完成。需要内网模式时再增加可选 IP 白名单，不把邮箱身份交给 Nginx。

### Task 3: 消除 API Key 和服务器路径泄露

**Files:**
- Modify: `src/config/settings.py`
- Modify: `src/api/model_config.py`
- Modify: `src/api/settings.py`
- Modify: `src/api/storage.py`
- Modify: `frontend/src/pages/SettingsPage.jsx`
- Test: `tests/test_secret_redaction.py`

- [ ] 所有模型配置响应只返回 `api_key_set` 和掩码，不返回原文。
- [ ] Provider 创建、更新和查询响应不返回原始 Key；保留 Key 时使用服务器端占位语义。
- [ ] 存储接口不返回绝对服务器路径。
- [ ] 错误响应和日志过滤 Key、Authorization、Cookie 以及完整上游请求信息。

### Task 4: 控制上传、任务和 Token 成本

**Files:**
- Modify: `src/api/upload.py`
- Modify: `src/core/dedup.py`
- Modify: `src/core/engine.py`
- Modify: `src/services/ai_service.py`
- Modify: `src/api/note.py`
- Modify: `frontend/nginx.conf`
- Test: `tests/test_limits.py`, `tests/test_cost_controls.py`

- [ ] 流式写盘时强制执行文件大小上限，拒绝无 Content-Length 的超限请求。
- [ ] 将最大视频时长从告警改为拒绝，并限制关键帧数量、音频时长和单任务重试次数。
- [ ] 禁止客户端修改全局并发；并发上限只来自服务器配置。
- [ ] 对上传、RAG、润色、闪卡和重试接口增加 IP/账号级频率限制和每日任务配额。
- [ ] 在 SQLite 增加 `usage_counters` 表和 `usage_reservations` 表：计数键为 `tenant_id=default + UTC date`，预留记录包含唯一 `reservation_id`、`task_id`、`call_type`、`reserved_tokens`、`actual_tokens`、状态、创建时间和 `expires_at`；状态机限定为 `reserved -> settled|released|expired|cancelled`。使用 `BEGIN IMMEDIATE` 原子预留；成功按实际 usage 结算并释放差额，失败拿不到 usage 时按预留上限结算；任务重试/自动重排队前在同一事务中取消旧 reservation 再创建新 reservation，重复回调按 reservation ID 幂等；启动时依据任务状态和 TTL 原子终结孤儿 reservation。达到上限后拒绝新调用。
- [ ] 增加单任务和每日 Token 预算；默认关闭 ASR，低配服务器默认并发为 1。
- [ ] 限制 `extra_instructions`、RAG history、批量导出 task IDs 和闪卡数量，避免输入放大和内存占用。

### Task 5: 改善任务可靠性和数据生命周期

**Files:**
- Modify: `src/core/engine.py`
- Modify: `src/core/checkpoint.py`
- Modify: `src/api/task.py`
- Modify: `docker-compose.yml`
- Create: `docs/deployment.md`
- Test: `tests/test_restart_recovery.py`, `tests/test_cleanup.py`

- [ ] 明确进程重启、重复提交和失败重试的幂等规则。
- [ ] 启动恢复或失败重试必须先处理关联的 `reserved` reservation：任务已结束则结算/释放，任务要重排队则取消旧 reservation 后再新建，确保一次模型调用只对应一条有效预留。
- [ ] 清理失败任务和超期临时文件、音频、关键帧与上传视频；清理动作不能删除正在处理的文件。
- [ ] 对 SQLite 做定期在线备份，并写出恢复和卷迁移步骤。
- [ ] 如果仍使用进程内任务，至少补充启动时自动重排队；如改用队列，选择 Redis/Celery 或轻量 SQLite 队列并保持部署复杂度可控。

### Task 6: 加固 Docker 和反向代理

**Files:**
- Modify: `Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `frontend/nginx.conf`
- Create: `docker-compose.prod.yml`
- Test: `tests/test_deployment_config.py`

- [ ] 后端只使用 `expose: 8000`，公网只发布反向代理的 80/443。
- [ ] 明确安装健康检查所需工具，或改为 Python/HTTP 健康检查；前端等待后端 healthy 后启动。
- [ ] 容器使用非 root 用户，设置 CPU、内存、临时目录和日志轮转限制。
- [ ] 新增 `Caddyfile` 和 Caddy 服务：Caddy 在 Docker 网络中 `reverse_proxy frontend:80`，仅映射宿主机 80/443；挂载持久化 `caddy_data`/`caddy_config` 卷，使用 `VIDEONOTE_DOMAIN` 配置域名，由 ACME 自动申请/续期证书并将 80 跳转 443。部署前置条件是域名 A 记录指向服务器且云防火墙放行 80/443；移除 backend:8000 和 frontend:3000 的公网映射。
- [ ] 为 Python 依赖生成可复现的锁定版本，确认 x86 国内云实例可以构建。

### Task 7: 资源评估、监控和上线检查

**Files:**
- Create: `docs/deployment-checklist.md`
- Modify: `README_CN.md`
- Test: `tests/test_smoke_deploy.py`

- [ ] 记录 2C4G/4C8G 实例的构建、首次 embedding 下载、单视频处理峰值内存和磁盘占用。
- [ ] 增加健康、磁盘、队列、任务失败率和 Token 使用量监控。
- [ ] 进行未认证访问、超限上传、并发上传、重启恢复、备份恢复和 Key 泄露回归测试。
- [ ] 上线前确认 API 供应商预算、服务器到期、备案/域名、备份和告警联系人。
