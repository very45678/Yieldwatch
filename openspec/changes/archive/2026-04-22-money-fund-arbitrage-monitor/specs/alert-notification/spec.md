## ADDED Requirements

### Requirement: 通知窗口控制
系统 SHALL 仅在交易日 9:30-15:00 发送通知。

#### Scenario: 交易时间发送
- **WHEN** 当前时间为交易日 9:30-15:00
- **THEN** 允许发送通知

#### Scenario: 非交易时间不发送
- **WHEN** 当前时间不在交易日 9:30-15:00
- **THEN** 不发送通知

### Requirement: 定时通知
系统 SHALL 在通知窗口内每5分钟发送一次通知。

#### Scenario: 定时发送
- **WHEN** 通知窗口内到达5分钟间隔
- **THEN** 检查并发送通知

### Requirement: 阈值触发告警
系统 SHALL 在年化收益率超过设定阈值时发送告警。

#### Scenario: 收益率超过阈值
- **WHEN** 任一基金的年化收益率超过用户设定阈值
- **AND** 当前在通知窗口内
- **THEN** 发送告警通知

### Requirement: 支持多种通知渠道
系统 SHALL 支持配置多种通知渠道。

#### Scenario: 微信推送
- **WHEN** 配置了微信推送（Bark/Server酱）
- **THEN** 发送微信消息通知

#### Scenario: 邮件通知
- **WHEN** 配置了邮件通知
- **THEN** 发送邮件到指定邮箱

### Requirement: 告警内容完整
告警通知 SHALL 包含关键信息。

#### Scenario: 告警内容格式
- **WHEN** 发送告警
- **THEN** 通知包含：基金名称、年化收益率、阈值、卖1价格、估算净值、占用天数、时间
