---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: b39d940f30a0c1cf547a23c927f28498_8e4011eddc1611f1bff2525400cd780f
    ReservedCode1: D/nXma2qOQyR7JERZzjjzIqq72BZawuoPz/jcqI74Of/aMMRFnCjFyzxyvEoRgWrMocRZw5I9NnzwKEjxHP+MGx1HoJ1QDlLxrUOopT5l57xce4H9YyXlc9IK6POc/gTJWHn8jlyWdMvu8CIuJjhZQeJ7e38zry9N6kaIRHWtX/NvD1hQaRKmZGwpPg=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: b39d940f30a0c1cf547a23c927f28498_8e4011eddc1611f1bff2525400cd780f
    ReservedCode2: D/nXma2qOQyR7JERZzjjzIqq72BZawuoPz/jcqI74Of/aMMRFnCjFyzxyvEoRgWrMocRZw5I9NnzwKEjxHP+MGx1HoJ1QDlLxrUOopT5l57xce4H9YyXlc9IK6POc/gTJWHn8jlyWdMvu8CIuJjhZQeJ7e38zry9N6kaIRHWtX/NvD1hQaRKmZGwpPg=
---

# 安全说明

## 项目性质

VaultwardenManager 是一个**运行在本机的 Windows 桌面管理工具**，用于自建的 Vaultwarden 服务的日常运维：
一键部署、启动/停止、状态与地址查看、加密备份与恢复、端口管理、日志查看等。

- 本工具**不提供**任何在线服务，**不收集、不上传**任何用户数据、使用统计或诊断信息。
- 本工具**不内置**任何远端账号体系，不发起点对点的遥测请求。
- 唯一的网络访问是**你主动触发**的下载动作：一键部署时按 `config.json` 中配置的下载地址获取
  `vaultwarden.exe` 与 Web Vault 网页版压缩包；以及打开浏览器访问本机或商店页面。

## 你的密码库数据在哪里

本工具只操作本地目录，密码库本体由 Vaultwarden 自身管理：

- 部署目录（默认 `<程序目录>\vaultwarden`）下的 `data\db.sqlite3` 为密码库数据；
- `rsa_key.pem`、`ssl\key.pem` 等为服务端密钥与证书私钥；
- `.env` 内含 `ADMIN_TOKEN`（管理面板登录口令）、端口与域名配置。

这些文件的安全性取决于你的主机安全、目录权限与备份策略。请自行妥善保管，并定期验证备份可恢复。

## 严禁提交到公开仓库的内容

如果你要开源或分享本项目的副本，请务必确认以下内容**不在提交范围内**（仓库根目录的 `.gitignore`
已默认忽略，请勿使用 `git add -f` 强行加入）：

| 类别 | 具体内容 |
|---|---|
| 部署数据 | 整个 `vaultwarden\` 目录，含 `data\db.sqlite3`、`rsa_key.pem`、`web-vault\`、日志 |
| 凭据 | 部署目录 `.env` 中的 `ADMIN_TOKEN` 及任何自建的 token / 口令 |
| 证书私钥 | `ssl\key.pem`、`*.pem`、`*.key`、`*.pfx` 等 |
| 本机配置 | 任何 `config.json`（含本机绝对路径与端口），对外请使用 `config.example.json` |
| 备份文件 | `*.enc` 加密备份（即使加密，也不应公开） |
| 构建与临时产物 | `build\`、`dist\*.exe`、`*.spec`、`*.log`、`__pycache__`、虚拟环境 |

若已误提交：立即更换 `ADMIN_TOKEN`、重新生成自签证书（旧私钥视为已泄露）、清理仓库历史中的敏感文件，
并检查是否存在被推送的备份或数据库副本。

## 已知的安全设计取舍

- **自签名证书**：一键部署默认生成本机自签名证书并加入当前用户的系统信任存储，浏览器首次访问需手动
  「高级 → 继续前往」或在设置窗口点击「打开地址信任证书」。这是本地自建场景的便利性取舍，不适用于公网暴露。
- **加密备份**：密钥派生使用 PBKDF2-HMAC-SHA256（600,000 次迭代 + 随机盐），备份文件带完整性校验，
  密码错误或内容被篡改会明确失败。备份密码**不会**被写入日志或临时文件；请自行保管密码，遗忘无法找回。
- **管理面板口令**：新部署时若 `.env` 缺少 `ADMIN_TOKEN`，工具会自动生成随机口令并在界面提示显示一次，
  请立即记录保存。
- **权限模型**：工具以当前用户权限运行，不申请管理员权限、不安装系统服务、不修改防火墙规则。

## 漏洞反馈

如发现安全问题，请**不要**直接创建公开 issue。请通过以下渠道私下反馈（按你的实际情况替换占位内容）：

- 邮箱：`<在此填写你的联系邮箱>`
- 或使用代码托管平台的私密漏洞报告功能（如 GitHub Security Advisories）。

反馈时请尽量提供：受影响版本（见「关于」窗口或 `vwm/ui.py` 的 `VERSION`）、复现步骤、
操作系统版本，以及可能的实际影响。请勿附带真实密码库数据、`ADMIN_TOKEN` 或私钥内容。

本工具由个人维护，会尽力在合理时间内响应与修复，但不承诺任何形式的响应时限或商业支持。
*（内容由AI生成，仅供参考）*
