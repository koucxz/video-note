# VideoNote 部署加固需求

## 目标

在部署到国内云服务器前，让 VideoNote 适合单用户或少量受邀用户使用，避免未授权访问、模型 Key 泄露、视频数据泄露和 Token/服务器资源被滥用。

## 当前审查结论

项目当前没有应用层鉴权；任务、笔记、上传、删除、模型配置和供应商管理接口均可直接访问。模型配置 API 会返回原始 API Key，供应商 API 也把原始 Key 保存在 JSON 并在部分响应中返回。`config.yaml` 和 Dockerfile 还可能把凭据带入镜像层。

上传接口允许最高 2GB 文件，超过 6 小时只告警不拒绝；没有请求频率限制、用户配额或 Token 预算。调用方还可以通过上传参数调整全局并发数。处理任务使用进程内 asyncio 任务，进程重启后只能标记为失败，不能由持久化队列自动恢复。

Docker Compose 当前直接发布后端 8000 端口和前端 3000 端口，健康检查依赖镜像中未明确安装的 curl。Python 依赖未锁定版本，向量服务会在首次使用时下载 embedding 模型并在本地保存索引，对低配实例有内存、磁盘和启动延迟风险。

## 约束

- 第一阶段按单用户/少量受邀用户设计，不引入复杂的多租户系统。
- 第一阶段采用单租户模式：所有通过认证的受邀用户共享一个工作区；不实现用户注册和复杂 owner 隔离。
- 鉴权采用应用内登录和 HttpOnly 会话 Cookie，密码只来自 `VIDEONOTE_AUTH_PASSWORD`；反向代理只负责网络入口和 HTTPS。
- 登录接口为 `POST /api/auth/login`，并提供 `GET /api/auth/me`、`POST /api/auth/logout`；Cookie 使用 `VIDEONOTE_SESSION_SECRET` 做 HMAC 签名，7 天过期，生产环境 `HttpOnly + Secure + SameSite=Lax`，修改 session secret 可撤销全部会话。除健康检查和认证入口外，所有 `/api/**` 均经过认证；登录成功和 `GET /api/auth/me` 设置 `videonote_csrf`（非 HttpOnly、Path=/、随机值），前端对所有写请求发送同值的 `X-CSRF-Token`，服务端常量时间比较；登录/登出不要求 CSRF，登出同时清理两个 Cookie。
- `/ws/task/{task_id}` 和 `/ws/all` 也必须校验会话 Cookie 与 Origin；未认证连接立即关闭，单租户模式下只允许已认证用户订阅任务进度。
- 第一阶段只有一个共享管理员密码，所有已认证用户拥有管理权限；不做角色区分和公开注册。
- HTTPS 采用 Caddy + ACME 自动签发和续期，域名由 `VIDEONOTE_DOMAIN` 配置，80 端口只做跳转到 443。
- Caddy 反向代理到 Docker 内部的 `frontend:80`；只映射 Caddy 的 80/443，Caddy 的 data/config 使用持久卷。部署前需将域名 A 记录指向服务器，并在云防火墙放行 80/443。
- 频率、任务和 Token 配额写入 SQLite 的持久化用量表，按默认租户和 UTC 日期统计；每次模型调用有唯一 reservation ID、task/call 类型、`reserved_tokens`、`actual_tokens`、状态和 TTL。状态仅允许 `reserved -> settled|released|expired|cancelled`；事务/锁内原子预留，成功按实际 usage 结算，失败无法取得 usage 时按预留上限结算。任务重试或自动重排队前，先在同一事务中把旧的 `reserved` reservation 标记为 `cancelled`，再创建新 reservation；启动恢复时按任务状态和 TTL 原子终结孤儿 reservation，重复回调按 reservation ID 幂等。
- 模型 Key 只允许存在于服务器端密钥存储或环境变量，浏览器响应永不返回原文。
- 公开入口只保留 HTTPS 反向代理；后端端口只在 Docker 内网可见。
- 必须保留现有 Docker 部署方式和 SQLite 数据结构的兼容性。
- 在用户确认前只输出计划，不实施代码修改。

## 验收标准

- 未登录请求不能读取、修改或删除任务、笔记、上传文件和模型配置。
- 任意 API 响应、日志和前端状态都不含完整模型 Key。
- 上传请求在流式写盘期间也受大小限制；时长、并发、单日任务数和 Token 预算有服务器端硬上限。
- 重启、健康检查、备份和恢复流程有可验证的操作说明。
- Docker 镜像构建不携带真实凭据，依赖版本可重复安装。
