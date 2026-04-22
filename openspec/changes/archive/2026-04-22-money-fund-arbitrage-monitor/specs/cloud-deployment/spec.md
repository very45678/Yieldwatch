## ADDED Requirements

### Requirement: Docker 容器化
系统 SHALL 支持 Docker 容器化部署。

#### Scenario: 构建镜像
- **WHEN** 执行 Docker 构建命令
- **THEN** 生成包含完整应用的 Docker 镜像

#### Scenario: 容器启动
- **WHEN** 启动 Docker 容器
- **THEN** 自动启动后端服务和 Web 界面

### Requirement: 配置管理
系统 SHALL 支持通过环境变量配置。

#### Scenario: 环境变量配置
- **WHEN** 设置环境变量（阈值、通知配置等）
- **THEN** 应用使用环境变量中的配置运行

### Requirement: 健康检查
系统 SHALL 提供健康检查接口。

#### Scenario: 健康状态
- **WHEN** 请求健康检查接口
- **THEN** 返回服务运行状态

### Requirement: 日志输出
系统 SHALL 输出运行日志。

#### Scenario: 标准输出日志
- **WHEN** 系统运行
- **THEN** 将日志输出到标准输出，便于容器日志收集

### Requirement: 免费云平台支持
系统 SHALL 适合免费云平台部署。

#### Scenario: 资源占用
- **WHEN** 系统正常运行
- **THEN** 内存占用保持在合理范围（如 < 256MB）
