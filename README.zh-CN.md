# cli-anything-jumpserver

[English](README.md) | **简体中文**

面向 [JumpServer](https://www.jumpserver.com/) 堡垒机管理的有状态 CLI 工具(同时是一个 Claude Code Skill)。

<!-- TODO: 录制 REPL 演示后,把下面的占位图替换为真实截图/GIF。
     建议用 asciinema 或 vhs 录制 `cli-anything-jumpserver --interactive`,
     导出为 docs/repl-demo.gif 即可自动显示。 -->
<p align="center">
  <img src="docs/repl-demo.gif" alt="cli-anything-jumpserver 交互式 REPL 演示" width="720">
  <br>
  <em>交互式 REPL 模式 —— 演示占位图</em>
</p>

## 作为 Claude Code Skill 安装

```bash
npx skills add Ayasaz/jumpserver-cli -g
```

## 安装(CLI)

```bash
git clone https://github.com/Ayasaz/jumpserver-cli
cd jumpserver-cli
pip install -e .
```

## 快速开始

```bash
# 登录你的 JumpServer 实例
cli-anything-jumpserver auth login --url https://jumpserver.example.com --username admin

# 列出主机资产
cli-anything-jumpserver asset list --type host

# 搜索用户
cli-anything-jumpserver user list --search admin

# 查看活跃会话
cli-anything-jumpserver session list --active

# 启动交互式 REPL 模式
cli-anything-jumpserver --interactive
```

## 使用说明

### 认证

```bash
# 登录
cli-anything-jumpserver auth login --url <URL> --username <USER> --password <PASS>

# 查看会话状态
cli-anything-jumpserver auth status

# 切换组织(多组织场景)
cli-anything-jumpserver auth org <ORG_ID>

# 列出组织
cli-anything-jumpserver auth org --list

# 登出
cli-anything-jumpserver auth logout
```

### 资产管理

```bash
# 按类型列出资产
cli-anything-jumpserver asset list --type host
cli-anything-jumpserver asset list --type device
cli-anything-jumpserver asset list --type database

# 查看资产详情
cli-anything-jumpserver asset get <ASSET_ID> --type host

# 创建资产
cli-anything-jumpserver asset create --name "web-01" --address 192.168.1.10 --platform 1

# 更新资产
cli-anything-jumpserver asset update <ASSET_ID> --comment "Production server"

# 删除资产
cli-anything-jumpserver asset delete <ASSET_ID> --force

# 管理节点
cli-anything-jumpserver asset node list --tree
cli-anything-jumpserver asset node create --name "Production" --parent <PARENT_ID>
cli-anything-jumpserver asset node add-assets <NODE_ID> --assets "id1,id2"

# 平台
cli-anything-jumpserver asset platform list

# 网关与网域
cli-anything-jumpserver asset gateway list
cli-anything-jumpserver asset gateway test <GATEWAY_ID>
cli-anything-jumpserver asset zone list
```

### 用户管理

```bash
# 列出用户
cli-anything-jumpserver user list --search admin

# 创建用户
cli-anything-jumpserver user create --name "John Doe" --username jdoe --email jdoe@example.com

# 重置密码
cli-anything-jumpserver user reset-password <USER_ID> --password "new-password"

# 解锁用户
cli-anything-jumpserver user unblock <USER_ID>

# 当前用户资料
cli-anything-jumpserver user profile

# 我有权访问的资产
cli-anything-jumpserver user my-assets

# 用户组
cli-anything-jumpserver user group list
cli-anything-jumpserver user group create --name "DevOps Team"
cli-anything-jumpserver user group members <GROUP_ID>
```

### 授权

```bash
# 列出授权
cli-anything-jumpserver perm list

# 创建授权
cli-anything-jumpserver perm create --name "Dev access" --users "id1,id2" --assets "id1,id2"

# 查看被授权的用户/资产
cli-anything-jumpserver perm users <PERM_ID>
cli-anything-jumpserver perm assets <PERM_ID>
```

### 账号

```bash
# 列出账号
cli-anything-jumpserver account list --asset <ASSET_ID>

# 创建账号
cli-anything-jumpserver account create --asset <ASSET_ID> --username root --secret-type password

# 查看密钥(需要权限)
cli-anything-jumpserver account secret view <ACCOUNT_ID>

# 密码历史
cli-anything-jumpserver account secret history <ACCOUNT_ID>

# 账号模板
cli-anything-jumpserver account template list
```

### 会话

```bash
# 列出会话
cli-anything-jumpserver session list --active
cli-anything-jumpserver session list --protocol ssh

# 会话回放
cli-anything-jumpserver session replay <SESSION_ID>

# 终止会话
cli-anything-jumpserver session kill <SESSION_ID> --force

# 命令历史
cli-anything-jumpserver session command list --session <SESSION_ID>
cli-anything-jumpserver session command list --risk 5

# 终端状态
cli-anything-jumpserver session terminal list
cli-anything-jumpserver session terminal status <TERMINAL_ID>
```

### 审计与运维

```bash
# 登录日志
cli-anything-jumpserver audit login --status failed

# 操作日志
cli-anything-jumpserver audit operate --action delete --resource Asset

# FTP 日志
cli-anything-jumpserver audit ftp

# 改密日志
cli-anything-jumpserver audit password

# 作业
cli-anything-jumpserver ops job-list
cli-anything-jumpserver ops job-log <EXECUTION_ID>

# Playbook
cli-anything-jumpserver ops playbook-list
```

### 系统

```bash
# 系统设置
cli-anything-jumpserver system settings

# 健康检查
cli-anything-jumpserver system health

# 系统信息
cli-anything-jumpserver system info
```

### 输出格式

所有命令都支持多种输出格式:

```bash
# 表格(默认)
cli-anything-jumpserver asset list

# JSON(用于脚本/智能体)
cli-anything-jumpserver asset list --output json
cli-anything-jumpserver asset list -o json

# YAML
cli-anything-jumpserver asset list --output yaml

# 自定义列
cli-anything-jumpserver asset list --columns "name,address,platform,is_active"
```

### 预演模式(Dry Run)

所有写操作命令都支持 `--dry-run` 来预览操作而不实际执行:

```bash
cli-anything-jumpserver asset create --name test --address 10.0.0.1 --platform 1 --dry-run
cli-anything-jumpserver user delete <ID> --dry-run
```

### 环境变量

- `JUMPSERVER_URL` —— 默认 JumpServer 地址
- `JUMPSERVER_USERNAME` —— 默认用户名
- `JUMPSERVER_PASSWORD` —— 默认密码

### REPL 模式

启动交互式模式,连续执行多条命令:

```bash
cli-anything-jumpserver --interactive
# 或
cli-anything-jumpserver -i
```

在 REPL 中可使用 Tab 补全,并直接输入命令:

```
jumpserver> auth login --url https://js.example.com --username admin
✓ Login successful. Session saved.
jumpserver> asset list --type host --search web
jumpserver> session list --active
jumpserver> exit
```
