## ADDED Requirements

### Requirement: 实时数据展示
Web 界面 SHALL 实时展示基金监控数据。

#### Scenario: 数据面板展示
- **WHEN** 用户访问 Web 界面
- **THEN** 显示银华日利和华宝添益的实时数据

### Requirement: 基金信息清晰展示
界面 SHALL 清晰展示关键数据。

#### Scenario: 数据项展示
- **WHEN** 界面加载完成
- **THEN** 显示每只基金的：基金名称、代码、买1价格、卖1价格、估算净值、占用天数、年化收益率、数据更新时间

### Requirement: 阈值配置
用户 SHALL 能通过界面配置告警阈值。

#### Scenario: 设置阈值
- **WHEN** 用户修改阈值设置
- **THEN** 保存新阈值并立即生效

### Requirement: 通知配置
用户 SHALL 能配置通知方式。

#### Scenario: 配置通知渠道
- **WHEN** 用户填写通知配置（微信推送Key、邮箱等）
- **THEN** 保存配置用于发送通知
