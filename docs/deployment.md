# VideoNote 生产部署

本项目的生产模式使用服务器端模型 Key。浏览器只获得模型名称和 Key 掩码，不会收到 Key 原文。

## 1. 准备环境变量

在服务器上执行：

```bash
cp .env.example .env
```

编辑 `.env`，至少填写：

```dotenv
LLM_API_KEY=你的文本模型Key
LLM_BASE_URL=https://你的模型服务/v1
LLM_MODEL=你的文本模型
VLM_API_KEY=你的视觉模型Key
VLM_BASE_URL=https://你的模型服务/v1
VLM_MODEL=你的视觉模型

VIDEONOTE_AUTH_PASSWORD=一个高强度访问密码
VIDEONOTE_SESSION_SECRET=至少32字节的随机字符串
VIDEONOTE_COOKIE_SECURE=true
VIDEONOTE_DOMAIN=note.example.com
CORS_ORIGINS=https://note.example.com

ASR_ENABLED=false
MAX_CONCURRENT_TASKS=1
MAX_UPLOAD_BYTES=536870912
MAX_VIDEO_DURATION_SECONDS=3600
ALLOW_RUNTIME_PROVIDER_KEYS=false
ALLOW_RUNTIME_PROVIDER_CONFIG=false
```

不要把 `.env` 提交到 Git。模型供应商后台还应设置额度、余额预警和单独的低额度 Key。

## 2. DNS 和云防火墙

将 `VIDEONOTE_DOMAIN` 的 A 记录指向服务器公网 IP，只放行：

- `22`：SSH，限制为自己的来源 IP
- `80`：Caddy 申请证书和跳转 HTTPS
- `443`：网页访问

不要放行 `8000` 和 `3000`。生产 Compose 会把这两个端口限制在 Docker 内部/本机。

## 3. 启动

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f backend frontend caddy
```

Caddy 会将请求转发到 `frontend:80`，前端 Nginx 再代理 `/api`、`/ws` 和 `/static` 到后端。Caddy 的证书数据保存在 `caddy_data` 卷中，不能删除。

## 4. 验证

打开 `https://你的域名`，使用 `VIDEONOTE_AUTH_PASSWORD` 登录。未登录访问任务接口应返回 401；模型设置页只能看到 Key 是否已配置和掩码，不能查看或复制原文。

```bash
curl -I https://你的域名/api/health
```

## 5. 日常维护

- 定期备份 Docker 卷中的 `data/db/videonote.db`、`data/uploads` 和 `data/output`。
- 关注模型供应商额度、服务器磁盘空间和容器日志大小。
- 升级前先执行数据库和数据目录备份。
- 试用服务器到期前确认续费或迁移，避免卷和证书数据丢失。
