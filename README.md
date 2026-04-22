# 货币基金折价套利监控系统

银华日利(511880)和华宝添益(511990)折价套利监控程序。

## 功能

- 实时获取基金买1/卖1价格和净值数据
- 计算卖1价格买入赎回的年化收益率
- 当年化收益率超过阈值时发送告警通知
- 提供 Web 界面实时展示监控数据
- 支持 Docker 容器化部署

## 快速开始

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置通知渠道

# 启动服务
uvicorn app.main:app --reload
```

访问 http://localhost:8000 查看 Web 界面。

### Docker 部署

```bash
# 构建镜像
docker build -t fund-monitor .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -e ALERT_THRESHOLD=3.0 \
  -e BARK_URL=https://api.day.app/YOUR_KEY \
  --name fund-monitor \
  fund-monitor
```

或使用 docker-compose：

```bash
# 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 启动服务
docker-compose up -d
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| ALERT_THRESHOLD | 告警阈值（年化收益率%） | 3.0 |
| BARK_URL | Bark 推送地址 | - |
| SERVERCHAN_KEY | Server酱 Key | - |
| EMAIL_SMTP | 邮件 SMTP 服务器 | - |
| EMAIL_USER | 邮件用户名 | - |
| EMAIL_PASSWORD | 邮件密码 | - |
| EMAIL_TO | 收件人邮箱 | - |

### 通知渠道

- **Bark**: iOS 推送工具，在 App Store 下载 Bark 获取推送地址
- **Server酱**: 微信推送服务，访问 sct.ftqq.com 获取 Key
- **邮件**: 配置 SMTP 服务器信息

## 部署到云平台

### Render

1. 连接 GitHub 仓库
2. 选择 Docker 环境
3. 设置环境变量
4. 部署

### Railway

```bash
# 安装 Railway CLI
npm install -g @railway/cli

# 登录
railway login

# 部署
railway up
```

## 年化收益率计算

```
估算净值 = 最近净值 × (1 + 1% / 365 × 天数)
折价率 = (估算净值 - 卖1价格) / 估算净值
年化收益率 = 折价率 × 365 / 占用天数
```

### 占用天数

- 周一至周四买入：T+1 到账，占用 1 天
- 周五买入：下周一到账，占用 3 天
- 长假前：按自然日计算

## 健康检查

```
GET /health
```

返回：
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00"
}
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Web 界面 |
| `/api/data` | GET | 获取实时数据 |
| `/api/config/threshold` | GET/POST | 阈值配置 |
| `/api/config/notification` | GET/POST | 通知配置 |
| `/health` | GET | 健康检查 |

## 许可证

MIT
