---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: b39d940f30a0c1cf547a23c927f28498_8fc3d005dc1611f1a0ca525400de85a5
    ReservedCode1: LAk78AGK2Bmqv6U4xoKnZwXzFs+G9aTqHA6GxCFAyeClBnkw31SWemNVro0QqqikgscC0vXFQVvUSX+NTzwgzAqTa92JqYWuRxeYS/Aj1sZD/MjMw4qfNsEniA0e8n6OwnYtjIldKI/nYMBB7gn97eGLc24eyjszNapbReYgApM8pO8thelf9eH27gc=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: b39d940f30a0c1cf547a23c927f28498_8fc3d005dc1611f1a0ca525400de85a5
    ReservedCode2: LAk78AGK2Bmqv6U4xoKnZwXzFs+G9aTqHA6GxCFAyeClBnkw31SWemNVro0QqqikgscC0vXFQVvUSX+NTzwgzAqTa92JqYWuRxeYS/Aj1sZD/MjMw4qfNsEniA0e8n6OwnYtjIldKI/nYMBB7gn97eGLc24eyjszNapbReYgApM8pO8thelf9eH27gc=
---

---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: b39d940f30a0c1cf547a23c927f28498_7fc7f69edc1311f1a0ca525400de85a5
    ReservedCode1: v8nRqGoZ0xp4YejBuyfzYEUYvyOZUL00o7xe5Jyit7H7K3yNutHOmjvGNLQO7zXlSadfGR8oqLZIs+8fBufhyq9ivKLCY+fnf/fi3k/9dGDlSznQZWwfiIOoMH/Lj9h9UbYCoEaaRQxf9ptQ8yKDM6oxtz21Qtr5LrvJMpeL7dYCaSxttzcoaHHU5aE=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: b39d940f30a0c1cf547a23c927f28498_7fc7f69edc1311f1a0ca525400de85a5
    ReservedCode2: v8nRqGoZ0xp4YejBuyfzYEUYvyOZUL00o7xe5Jyit7H7K3yNutHOmjvGNLQO7zXlSadfGR8oqLZIs+8fBufhyq9ivKLCY+fnf/fi3k/9dGDlSznQZWwfiIOoMH/Lj9h9UbYCoEaaRQxf9ptQ8yKDM6oxtz21Qtr5LrvJMpeL7dYCaSxttzcoaHHU5aE=
---

---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: b39d940f30a0c1cf547a23c927f28498_9ac1ab68d83c11f1bff2525400cd780f
    ReservedCode1: W4QaKAhI/V1q4jtyN/liChR8dWa9nq7UjkVUQkmVzJOYpm14bfDaV6DnYnMn4WIBlrElm6GO0wK9dP6ITbhFYAgLnOj4zuGWEgTjwOMapEtWMb5XXfp6Re7jODWCD81l6wWnw+MfNdyQgrJ7M08C9qXz1pV0hzl7SJdvoabczmgbY17GYs0HvxK00Co=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: b39d940f30a0c1cf547a23c927f28498_9ac1ab68d83c11f1bff2525400cd780f
    ReservedCode2: W4QaKAhI/V1q4jtyN/liChR8dWa9nq7UjkVUQkmVzJOYpm14bfDaV6DnYnMn4WIBlrElm6GO0wK9dP6ITbhFYAgLnOj4zuGWEgTjwOMapEtWMb5XXfp6Re7jODWCD81l6wWnw+MfNdyQgrJ7M08C9qXz1pV0hzl7SJdvoabczmgbY17GYs0HvxK00Co=
---





































# Vaultwarden Manager 开发手册（DEV.md）

> 版本：v1.9.12
> 更新日期：2026-11-10
> 项目路径：`E:\yscl\vaultwarden-manager`
> 管理目标：本机 Vaultwarden 服务（部署目录随程序运行目录，便携化；端口 44444，打开地址按实际监听端口与协议动态拼接）

---

## 1. 项目概述

Vaultwarden Manager 是一个 Windows 桌面 GUI 管理工具，用于管理本机已部署的 Vaultwarden
密码管理器服务。工具采用 **Python + tkinter** 编写，**v1.8.0 起为模块式开发结构**（`vwm` 包
按职责拆分为 config/service/deploy/cert/backup/logs/network/ui/app 等模块，入口
`vaultwarden_manager.py` 为薄转发壳），PyInstaller 生成单文件 `VaultwardenManager.exe`，
无中文路径依赖，程序启动时自动创建缺失的配置文件。**v1.8.0 重构只改变代码组织，
不改变任何功能与界面行为（零回归）**。

主要功能：

| 编号 | 功能 | 说明 |
|---|---|---|
| 1 | 启动服务 | 无黑窗后台启动 `vaultwarden.exe`，工作目录固定为部署目录，保证 `.env` 生效；**v1.7.6 起**按进程真实路径判定运行，dist 残留实例不再冒充；`.env` 缺失 `ADMIN_TOKEN` 时自动生成并提示 |
| 2 | 停止服务 | 终止本用户所有 `vaultwarden.exe` 实例（**v1.8.1 起**按 Win32_Process 精确 PID 逐个 `taskkill /PID /T /F`，含非部署目录残留实例一并可靠停止，终止后轮询验证无残留） |
| 3 | 状态显示 | 轮询检测进程与端口，红/黄/绿三色醒目展示；**v1.7.6 起**检测到非部署目录同名实例时橙色提示；**v1.8.1 起**该场景返回独立状态码 `foreign`，按钮矩阵据此启用「停止服务」，打破「启动被拦截 + 停止按钮禁用」死锁 |
| 4 | 打开 Web Vault | 浏览器打开 `http(s)://localhost:<实际监听端口>`（v1.6.9 起按 cfg['port'] 动态拼接；**v1.7.0 起**先经 netstat 解析 `vaultwarden.exe` 实际监听端口、再探测实际协议 http/https，URL 与本机服务真实监听一致） |
| 5 | 打开管理面板 | 浏览器打开 `http(s)://localhost:<实际监听端口>/admin`（v1.6.9 起按 cfg['port'] + admin_path 动态拼接；**v1.7.0 起**端口/协议同「打开 Web」实际探测） |
| 6 | 查看/刷新日志 | 读取 `vaultwarden.log` 尾部（默认 300 行）；日志超过阈值（默认 10MB）自动轮转归档为 `vaultwarden.log.1`（已存在则后缀递增），读取失败给出中文提示 |
| 7 | 一键加密备份 | 将 `data` 压缩为 zip（zipfile），再加密为 `backup\data_<时间戳>_<随机段>.enc`（v1.6.2 起原「一键备份」合并入此按钮，统一承担备份入口，备份内容为完整 `data` 目录，配合「导入备份」可完整恢复）。**v1.8.8 安全加固**：密钥由 PBKDF2-HMAC-SHA256（600,000 次迭代 + 16 字节随机盐）派生，不再直接以 SHA-256(password) 作 Fernet 密钥；弱密码校验（长度 ≥8 且含字母与数字，中文提示）；备份文件带 `v2` 格式标识头与元数据（来源/工具版本/时间/zip SHA-256），完整性经 HMAC 派生密钥校验，防篡改与损坏检测；备份文件名含时间戳 + 随机段防覆盖；密码不落盘、不写入日志/临时文件 |
| 8 | 导入备份 | 选 `.enc` 文件 + 输入密码，解密为 zip 后解压恢复到 `data`；恢复前确认，现有 `data` 先改名 `data_bak_<时间戳>` 防误操作。**v1.8.8 安全加固**：导入前校验 `v2` 格式标识与元数据（来源/工具版本/备份时间），密码错误明确提示「密码错误或文件已损坏」；完整性校验（zip SHA-256 + zip 条目 CRC 全量校验）防篡改/损坏；zip-slip 加固（拒绝绝对路径/`..` 穿越/盘符/符号链接条目）+ 防压缩炸弹（条目数 ≤50000、解压总量 ≤2GiB、压缩比 ≤1000）；失败自动回滚清理临时文件，不破坏现有 `data`；v1 旧格式备份仍可导入（旧密钥派生兼容 + 明确提示旧版格式） |
| 9 | 复制地址 | 复制 `config.json` 的 domain（如 `https://localhost:44444`）到剪贴板，状态栏显示完整地址 |
| 10 | 修改端口 | 弹窗输入 1-65535 新端口，更新 config.json 的 port/domain，并同步 `.env` 的 ROCKET_PORT 与 DOMAIN（保留原内容/换行风格），提示需重启服务生效 |
| 11 | 一键部署 | 服务未运行时自动启动并轮询等待端口开放（15 秒超时），部署成功后按钮自动置灰；服务已运行则提示无需重复部署。**v1.7.2 起自动集成证书生成 + 添加系统信任**：核心文件与网页版就绪后、启动服务前，若 `ssl` 目录缺 `cert.pem`/`key.pem` 则自动调用 `generate_certificate()` 生成（无证书才生成、已有则跳过不重复生成），随后自动调用 `add_system_trust()` 添加系统信任（沿用 certutil `-addstore -user Root` 方式）；证书/信任失败**不阻塞启动**，部署结果消息附加「已自动生成自签名证书 / 证书已存在，跳过生成 / 警告：证书生成失败（原因）」「已自动添加系统信任 / 警告：添加系统信任失败（原因）」等状态提示；原「生成证书」「添加信任」两个独立按钮已移除（功能并入本按钮，见 v1.7.2 记录）。核心文件 `vaultwarden.exe` 缺失时按 config 的 `vw_download_url` 自动下载（**v1.6.4 起默认已内置官方 Windows 二进制下载地址，新用户无需手动填写**；后台线程，**界面底部显示加高进度条**：下载阶段显示已下载字节/总字节百分比，未知大小退化为不定进度并显示"部署中…"；下载/校验完成后进入启动与端口轮询阶段，进度条切换为不定进度并显示"部署中…（已等待 N 秒）"；任务结束进度条复位隐藏，完成/失败提示由消息栏展示；校验 >1MB 视为成功）；URL 被清空时则明确提示中止。**v1.6.5 起网页版自动安装**：部署目录缺少 `web-vault/index.html` 时，按 config 的 `vw_webvault_download_url` 自动下载官方 `.tar.gz` 并用 `tarfile` 解压（含 `web-vault/` 顶层目录则解到部署根、散文件则解到 `web-vault/`），校验 `index.html` 存在才算成功；下载/解压失败**不阻塞启动**，仅在部署结果消息中提示「网页版未安装，服务已启动（仅 API 可用）」；该阶段进度条复用现有回调，提示文字切换为「正在下载网页版…」，可取得 Content-Length 时按百分比推进、否则不定进度。**v1.9.4 起部署结果持久生效**：部署成功后按磁盘文件（exe>1MB + .env 有 ADMIN_TOKEN + web-vault/index.html）判定为已部署，按钮立即置灰且**重启后仍禁用**（非会话内标志）；已部署状态下点击（含重启后）只提示「已完成部署，无需重复部署；如需重新部署请先清理部署目录」不执行任何部署；缺任一项（未部署/下载不完整/缺 ADMIN_TOKEN）或仅缺网页版时按钮保持可点，可再次点击补装 |
| 12 | 部署目录便携化 | 默认部署目录 = 程序运行目录（APP_DIR）下的 `vaultwarden`（`ssl`/`backup` 为其子目录）；检测到旧固定路径配置时自动迁移（备份 config → 复制旧部署目录内容到新目录 → 更新 config 指向新路径，状态栏提示迁移结果），新目录已有数据不重复迁移 |
| 13 | 日志噪音过滤 | 读取日志时按 `log_noise_keywords`（默认 `tls handshake` / `HSTS`）过滤噪音行（如反复刷屏的 `tls handshake eof` 与 HSTS 告警），过滤后日志区顶部提示「（已过滤 N 行噪音日志）」；新增「原始日志」按钮可切换查看未过滤原始内容（按钮文案切换为「过滤日志」，切换状态显示在状态栏）；过滤仅影响展示，不影响 `vaultwarden.log` 原始落盘 |
| 14 | 操作日志落盘 | 每次按钮操作（一键部署/启动/停止/复制地址/一键加密备份/导入备份/修改端口）完成后自动追加一行 `[时间戳][操作名] 结果摘要` 到部署目录 `manager.log`，复用 `rotate_log_if_needed` 按 `log_max_mb` 阈值轮转；写入失败不影响主流程，仅在状态栏提示（v1.7.2 起「生成证书」「添加系统信任」随按钮移除不再单独落盘，证书/信任状态经一键部署结果消息体现） |
| 15 | 系统托盘（v1.6.6，v1.8.9 加固） | 关闭窗口（X）或点「退出工具」时弹出全中文确认框：选「退出程序」真正退出，选「最小化到托盘」隐藏窗口并常驻系统托盘；托盘图标单击/双击恢复主窗口，右键菜单含「显示主窗口」「退出程序」；退出时先 `icon.stop()` 清理托盘再销毁主窗口，不残留僵尸图标；托盘不可用（依赖缺失/创建失败）时关闭窗口直接退出并提示。**v1.8.9**：单实例互斥（重复启动自动激活既有窗口、托盘图标唯一）、托盘就绪等待与失败降级、回调线程安全、最小化/恢复幂等、退出清理重试兜底 |
| 16 | 设置（v1.8.5） | 主按钮矩阵之外的「设置」特殊样式按钮：打开设置窗口，可视化配置退出记忆（`quit_confirm_skip` 跳过确认开关 + `quit_default_action` 默认动作 托盘/退出 单选 + 一键恢复「每次退出都询问」）、编辑部署下载地址（`vw_download_url` / `vw_webvault_download_url` 可查看/修改）、只读展示当前端口与部署目录；保存经 `save_config` 完整写回 config.json（不破坏其他字段），取消不写盘 ；**v1.9.9 新增「浏览器插件连接」分区**（按 `port`/`domain` 动态拼接本机与局域网地址、「复制地址」写剪贴板、「打开地址信任证书」用默认浏览器打开、「获取扩展」打开 `ext_edge_url`/`ext_chrome_url`）；**v1.9.12 新增「管理员」分区**（「获取令牌」只读部署目录 `.env` 的 `ADMIN_TOKEN` 并写系统剪贴板、界面仅显示打码信息、「打开管理面板」用默认浏览器打开 `<协议>://localhost:<port>/admin`） |
| 17 | 关于（v1.8.6） | 主按钮矩阵之外的「关于」特殊样式按钮：打开关于窗口，展示软件名称 VaultwardenManager、版本（取自 ui.VERSION，随版本升级同步，当前 v1.9.12）、作者/版权（杨爽工作室）、制作人（杨爽）、制作工具（Marvis）、简要说明与「确定」按钮；**v1.8.6 起移除「部署目录」「配置文件」两行纯文本展示**，窗口高度 360→300 保持居中美观；**v1.8.7 起新增「制作人：杨爽」「制作工具：Marvis」两行展示**，窗口高度 300→330 保持居中美观；**v1.9.11 起窗口内新增「赞助支持」区**（赞助文案 + `assets\sponsor_qr.png` 收款二维码，二维码按窗口宽度自适应缩放、缺失时显示占位提示），窗口尺寸 460×330 → 460×560（内容多时按实际需求高度自适应），关于窗口成为赞助信息的唯一入口 |
| 18 | 赞助支持（v1.9.0；v1.9.11 迁入关于窗口） | 浅灰卡片（`#e9ecef` 底）：标题「赞助支持」粗体深灰居中 + 说明文字 8 号深灰居中，三段文案「一元不嫌少，十元不嫌多。/无论金额多少，都是对本软件项目的认可。/赞助属于自愿行为，不购买任何功能、不享有售后服务，仅表达您的一份善意。」+ 收款二维码（Pillow `LANCZOS` 等比缩放，最长边 ≤150px，点击可用系统看图器放大）。**v1.9.0 起位于主窗口「设置」「关于」按钮下方（left 网格 row7 columnspan=2），v1.9.11 起整体迁入关于窗口**（主窗口不再显示赞助卡片，`minsize` 由 860×690 回收为 860×640），纯展示不参与状态矩阵 |
| 19 | 获取令牌（v1.9.12） | 设置窗口「管理员」分区：一行说明文字 + 「获取令牌」「打开管理面板」两个次级按钮 + 打码状态区（`令牌：Lsbf********（43 位）`）+ 提示行。点「获取令牌」只读部署目录 `.env` 里的 `ADMIN_TOKEN`（由 `service.read_admin_token` 完成，**相对路径按 `APP_DIR` 解析、不依赖进程 CWD**），拿到值写系统剪贴板并提示「已复制到剪贴板」，界面**只显示打码信息（前 4 位 + 8 个星号 + 长度），绝不完整回显**；`.env` 不存在 / 无 `ADMIN_TOKEN` 行 / 值为空 / 值为 `$argon2` 哈希 / 读取失败（含权限不足）均有明确中文提示且不抛异常；令牌**不写入任何日志**（不经 `logs.py`，`manager.log` 无痕）；「打开管理面板」按 `port` 与 `domain` 协议打开 `<协议>://localhost:<port>/admin`，与「浏览器插件连接」分区同一套地址拼接逻辑 |

界面要求：常规桌面尺寸与配色、状态醒目，全部文本中文。

## 2. 目录结构

```
E:\yscl\vaultwarden-manager\
├── vaultwarden_manager.py   # 入口（薄转发壳：from vwm.app import main; main()）
├── vwm\                     # 核心包（v1.8.0 起模块式开发结构）
│   ├── __init__.py          # 包版本、CRYPTO_OK 探测（cryptography 可用性）
│   ├── common.py            # 共享常量/工具（CREATE_NO_WINDOW、路径安全校验等）
│   ├── config.py            # 配置管理（DEFAULT_CONFIG、load/save、update_port、迁移）
│   ├── logs.py              # 日志（rotate_log_if_needed、read_log_tail、append_manager_log）
│   ├── network.py           # 网络探测（resolve_web_url、get_listen_port、detect_scheme、get_lan_ips）
│   ├── service.py           # 服务管理（start/stop/status、ensure_admin_token、read_admin_token 只读令牌、进程路径感知）
│   ├── cert.py              # 证书（generate_certificate、add_system_trust）
│   ├── deploy.py            # 一键部署（download_file、extract_webvault_tarball、deploy_service）
│   ├── backup.py            # 加密备份/恢复（encrypt_backup、decrypt_and_restore；v1.8.8 安全加固：PBKDF2 高迭代密钥派生/弱密码校验/完整性 HMAC/防 zip-slip 与压缩炸弹/旧格式兼容）
│   ├── ui.py                # 弹窗与 UI 常量/设置·关于窗口（ask_quit_or_tray、prompt_password、prompt_port、open_settings_dialog、show_about_dialog、BTN_*、BTN_SECONDARY_*；v1.9.9 新增浏览器插件连接分区、依赖 network.get_lan_ips 与 webbrowser；v1.9.11 关于窗口内置赞助区，新增 SPONSOR_* 常量与 _sponsor_qr_file/_load_sponsor_qr/_sponsor_qr_max_w，依赖 os/PIL 加载 assets 二维码）
│   └── app.py               # GUI 主程序（VaultwardenManagerApp、_build_ui、main）
├── config.json              # 配置文件（缺失时程序启动自动创建默认配置）
├── assets\                  # 资源目录（v1.9.7 起，随包分发，路径无中文）
│   ├── app.ico              # 多尺寸 ICO（16/24/32/48/64/128/256），exe 文件图标 + 窗口图标
│   ├── app.png / app_256.png# 256×256 主图标
│   ├── app_16/24/32/48/64/128.png  # 各尺寸 PNG（小尺寸单独优化，便于界面/文档复用）
│   ├── sponsor_qr.png       # 收款二维码（v1.9.11 起由关于窗口加载；250×250 RGBA，约 33.9KB）
│   └── tray.png             # 托盘图标（64×64 RGBA，透明底）
├── tests\                   # 回归验证脚本（v1.9.9 维护起由根目录移入，13 个 verify_*.py）
├── requirements.txt         # Python 运行时依赖
├── config.example.json      # 配置示例（v1.9.11 开源化整理新增，脱敏：相对路径 + 默认端口 + 运行态字段复位）
├── .gitignore               # 版本控制忽略规则（v1.9.11 开源化整理新增：部署目录/本地配置/构建产物/缓存/临时文件）
├── LICENSE                  # MIT 协议（Copyright (c) 2026 杨爽工作室 (Yang Shuang Studio)）
├── README.md                # 开源首页（简介/功能特性/系统要求/快速开始/配置/构建/目录结构/测试/许可/免责）
├── CHANGELOG.md             # 面向用户的版本变更（Keep a Changelog 格式，v1.8.5–v1.9.12）
├── CONTRIBUTING.md          # 参与贡献（环境/依赖/运行/打包/自检/全中文约定/禁交文件）
├── SECURITY.md              # 安全说明与漏洞反馈渠道
└── DEV.md                   # 本开发手册（修改代码前必须先阅读）

# 打包产物（PyInstaller 生成，不入库）：
# dist\VaultwardenManager.exe   # 单文件可执行程序

# 管理的目标部署目录（v1.5.0 起随程序运行目录，默认 <程序目录>\vaultwarden；工具强依赖其结构）：
E:\yscl\vaultwarden-manager\vaultwarden\
├── vaultwarden.exe        # 服务主程序
├── .env                   # 服务配置（ROCKET_TLS / ROCKET_PORT 等）
├── data\                  # 数据目录（备份对象）
├── ssl\
│   ├── cert.pem           # TLS 证书
│   └── key.pem            # TLS 私钥
├── web-vault\             # Web 前端
├── vaultwarden.log        # 标准输出日志
├── vaultwarden.err.log    # 错误日志
└── manager.log            # 管家操作日志（v1.6.0：每次按钮操作落盘一行，超阈值自动轮转）
```

## 3. 技术栈与依赖

| 组件 | 说明 |
|---|---|
| Python | 3.8+（开发/运行环境） |
| tkinter | GUI 框架（标准库，无需安装） |
| cryptography | 证书生成 + Fernet 加密备份（第三方库，**运行时必需**，证书与加密备份功能使用） |
| pystray | 系统托盘图标（第三方库，**v1.6.6 运行时必需**，托盘功能使用；版本 0.19+ 支持 `run_detached()` 免手动线程） |
| Pillow | 托盘图标绘制（第三方库，**v1.6.6 运行时必需**，配合 pystray 代码绘制图标，无需额外图片文件） |
| PyInstaller | 打包工具（仅打包时需要） |

安装依赖：

```powershell
pip install cryptography pystray pillow
pip install pyinstaller   # 仅打包需要
```

## 4. 核心模块说明

### 4.0 模块结构总览（v1.8.0 新增）

**v1.8.0 将原单文件 `vaultwarden_manager.py`（v1.7.6，约 1854 行）按职责拆分为 `vwm` 包**，
入口文件仍为 `vaultwarden_manager.py`（薄转发壳：`from vwm.app import main`）。拆分只改变
代码组织，**功能与界面零回归**；模块间依赖为**单向无环**（见导入关系），避免循环依赖。

| 模块 | 职责 | 主要公开接口 |
|---|---|---|
| `vwm/__init__.py` | 包版本、cryptography 可用性探测（`CRYPTO_OK`） | `VERSION`、`CRYPTO_OK` |
| `vwm/common.py` | 共享常量/工具（无第三方依赖） | `CREATE_NO_WINDOW`、`is_safe_relative`、`path_within` 等 |
| `vwm/config.py` | 配置读写、默认值、旧路径迁移、端口同步 | `DEFAULT_CONFIG`、`CONFIG_PATH`、`load_config`、`save_config`、`update_port` |
| `vwm/logs.py` | 日志轮转、日志读取、操作日志落盘 | `rotate_log_if_needed`、`read_log_tail`、`append_manager_log`、`filter_noise_lines` |
| `vwm/network.py` | 网络探测与 URL 拼接（纯函数+子进程只读探测） | `resolve_web_url`、`get_listen_port`、`detect_scheme`、`get_lan_ips`、`is_port_open` |
| `vwm/service.py` | 服务启停/状态、.env 同步、ADMIN_TOKEN 自动生成、部署状态磁盘判定（v1.9.4）、状态探测轻量化（v1.9.5）、部署目录解析与只读令牌读取（v1.9.12） | `start_service`、`stop_service`、`get_service_status`、`ensure_admin_token`、`resolve_deploy_dir`、`read_admin_token`、`mask_token`、`ensure_env_runtime`、`is_process_running`、`find_vw_processes`、`get_deploy_state`、`_tasklist_name_hit` |
| `vwm/cert.py` | 自签名证书生成、系统信任添加 | `generate_certificate`、`add_system_trust` |
| `vwm/deploy.py` | 一键部署全链路（下载/网页版/证书/信任/启动/轮询） | `deploy_service`、`download_file`、`extract_webvault_tarball` |
| `vwm/backup.py` | 加密备份与恢复（zip+PBKDF2 派生 Fernet 加密；v1.8.8 起含完整性校验/防 zip-slip 与压缩炸弹/旧格式兼容；v1.9.5 起支持自定义保存位置与阶段回调） | `encrypt_backup`、`decrypt_and_restore`、`resolve_enc_target`、`generate_enc_filename`、`derive_fernet_key`、`derive_legacy_key`、`validate_password_strength`、`_check_zip_safety`、`_extract_zip_safely` |
| `vwm/ui.py` | 弹窗工具与 UI 配色常量、设置/关于窗口（不依赖 app；v1.8.5 起依赖 config 的 CONFIG_PATH/save_config；v1.9.9 起依赖 config 的 DEFAULT_CONFIG 与 network 的 get_lan_ips，并新增浏览器插件连接分区；v1.9.12 起依赖 service 的 read_admin_token/mask_token，新增管理员分区） | `ask_quit_or_tray`、`prompt_password`、`prompt_port`、`open_settings_dialog`、`show_about_dialog`、`BTN_BG`、`BTN_BG_ACTIVE`、`BTN_DISABLED_FG`、`BTN_SECONDARY_*` 等 |
| `vwm/app.py` | GUI 主程序（窗口/按钮矩阵/托盘/后台线程） | `VaultwardenManagerApp`、`main` |

**模块导入关系（单向无环）**：

```
vaultwarden_manager.py  →  vwm.app
vwm/app.py  →  vwm.config / vwm.service / vwm.deploy / vwm.cert / vwm.backup /
              vwm.logs / vwm.network / vwm.ui / vwm.common
vwm/deploy.py  →  vwm.service / vwm.cert / vwm.network / vwm.common
vwm/service.py  →  vwm.config / vwm.logs / vwm.network / vwm.common
vwm/cert.py  →  vwm.network / vwm.common
vwm/backup.py  →  vwm.common
vwm/logs.py  →  vwm.common
vwm/network.py  →  vwm.common
vwm/config.py  →  vwm.common
vwm/ui.py  →  vwm.common / vwm.config / vwm.network
```

- 所有模块只依赖**编号更小的兄弟模块或 common**，无反向依赖、无循环。
- `cryptography` 为可选依赖：`__init__.py` 探测可用性设 `CRYPTO_OK`，`cert.py`/`backup.py`
  仅在 `CRYPTO_OK` 为真时导入 cryptography 符号，缺失时相关功能返回「缺少 cryptography 库」提示，
  不影响 GUI 与其余功能。
- 打包：PyInstaller 从入口 `vaultwarden_manager.py` 的 `from vwm.app import main` 自动递归收集
  `vwm` 包全部模块，无需额外 hidden-import（见 §6）。

### 4.1 服务管理（启动 / 停止 / 状态）

- `start_service(cfg)`：使用 `subprocess.Popen` 后台启动 `vaultwarden.exe`。
  - **关键红线**：`cwd` 必须传部署目录（config 的 `vaultwarden_dir`，v1.5.0 起默认 = 程序运行目录下的
    `vaultwarden`），否则 `.env` 不会生效，HTTPS（ROCKET_TLS）将丢失。
  - 使用 `creationflags=CREATE_NO_WINDOW (0x08000000)` 保证无黑窗；
    `start_new_session=True` 使服务独立于管理器进程，关闭管理器不会连带退出。
  - 启动前先检测是否已在运行，避免重复拉起。
  - **v1.7.6**：运行检测按**进程真实路径**校验——`is_process_running(exe_name, deploy_dir)`
    仅当同名进程 `ExecutablePath`/`CommandLine` 属于部署目录时才视为本服务运行中；
    检测到非部署目录的同名实例（如其他目录下的测试副本残留）时**不自动结束进程**，
    直接拦截本次启动并提示「请先在任务管理器中结束该实例，再点击启动」，避免错误实例冒充。
  - **v1.7.6**：启动前调用 `ensure_admin_token(cfg)`，部署目录 `.env` 缺失/为空
    `ADMIN_TOKEN` 时自动生成强随机值（`secrets.token_urlsafe(32)`）写入（保留其他行与注释，
    已有非空值不覆盖，幂等）；新生成时成功消息附加
    「已自动生成 ADMIN_TOKEN，管理面板 https://localhost:<port>/admin 登录口令：<token>
    （请妥善保存，用于登录管理面板）」。
  - 标准输出/错误分别追加到 `vaultwarden.log` / `vaultwarden.err.log`；
    写入前调用 `rotate_log_if_needed()` 对两个日志做阈值轮转（超过 `log_max_mb` 时归档）。
- `ensure_env_runtime(cfg)`：**启动前 .env 同步（v1.7.0）**。`start_service` 发起 `Popen` 前调用，
  确保部署目录 `.env` 关键项与 config 一致（**防止 config/.env 端口漂移导致服务实际监听与打开地址不一致**）：
  - 已有证书（`ssl_dir/cert_file` + `key_file` 均存在）时写入/更新 `ROCKET_TLS`（
    `{certs="<ssl 绝对路径正斜杠>",key="<key 绝对路径正斜杠>"}`）/ `ROCKET_ADDRESS` /
    `ROCKET_PORT` / `DOMAIN`，使 HTTPS 真正生效；
  - 无证书时仅同步 `ROCKET_PORT` / `DOMAIN`（服务以 HTTP 运行，`resolve_web_url` 自动探测 http）；
  - 保留 `.env` 已有注释与其他配置，原位替换目标键；值未变化不写盘（幂等，重复调用返回空串）；
  - 有变更时返回中文提示（「已同步部署目录 .env（ROCKET_PORT/DOMAIN、ROCKET_TLS 已启用 HTTPS），重启生效」；
    **v1.7.1** 若检测到 ROCKET_PORT 旧值与 config 不一致，提示追加「，端口不一致已统一：ROCKET_PORT <旧值> → <新值>」），
    追加在 `start_service` 成功消息尾部。
- `ensure_admin_token(cfg)`：**ADMIN_TOKEN 自动生成（v1.7.6）**。读取部署目录 `.env`，
  检测 `ADMIN_TOKEN` 键缺失或值为空时，用 `secrets.token_urlsafe(32)` 生成强随机值写入：
  - 保留 `.env` 其他行、注释与原换行风格；已有非空值**绝不覆盖**（幂等，重复调用返回原值）；
  - 返回 `(token, 是否新生成)`；`.env` 不可读写时返回 `(None, False)` 且不阻塞启动；
  - `start_service` / `deploy_service` 启动前均调用；新生成时部署/启动结果消息给出
    管理面板地址与 token 值，提示妥善保存。
- **v1.9.12 只读令牌三件套（供设置窗口「获取令牌」使用，与上面的写入式 `ensure_admin_token` 严格区分）**：
  - `resolve_deploy_dir(cfg, app_dir=None)`：把 `vaultwarden_dir` 解析成绝对路径。相对路径一律
    按 **`APP_DIR`**（打包后 = exe 所在目录，源码运行 = 项目根）拼接，**禁止依赖进程当前工作目录
    （CWD）**——这是历史遗留风险点（`config.load_config` 的 `_migrate_legacy_paths()` 用
    `Path(raw).resolve()` 求值，结果会随启动目录漂移）。入参可为 `dict` / `str` / `None`，
    空值或非字典时回落 `APP_DIR/vaultwarden`，`Path()` 解析异常（`OSError` / `ValueError`）同样回落，
    绝不抛异常。
  - `mask_token(token)`：打码为「前 4 位 + 固定 8 个星号 + 长度」（`TOKEN_MASK_HEAD=4`、
    `TOKEN_MASK_STARS=8`），如 `Lsbf********（43 位）`；空值返回空串。星号数量与真实长度无关，
    仅长度信息外露，界面永不完整回显令牌。
  - `read_admin_token(cfg, app_dir=None)`：**只读**读取部署目录 `.env` 中的 `ADMIN_TOKEN`，
    返回 `dict(ok / code / token / masked / env_path / message)`，`code` 取值
    `ok`｜`no_env`｜`no_token`｜`argon2`｜`read_error`。解析规则：逐行匹配
    `^\s*ADMIN_TOKEN\s*=(.*)$`，去除首尾空白与成对引号（兼容 `ADMIN_TOKEN="xxx"`），
    **取第一个非空值**；`$argon2` 开头判定为哈希值（无法反解，提示用原始密码登录）。
    只读语义：不生成令牌、不改 `.env`、**不写任何日志文件**（不调用 `logs.py`，
    `manager.log` 与 `vaultwarden.log` 均无令牌痕迹）；所有异常（含权限不足 `OSError`）
    统一转为中文 `message` 返回，绝不向上抛出。
- `stop_service(cfg)`：**v1.8.1 起**按 `find_vw_processes(exe_name)`（Win32_Process 真实路径）精确 PID 逐个
  `taskkill /PID <pid> /T /F` 终止本用户所有同名实例（**含非部署目录残留实例，如 dist 旧部署，一并可靠停止**；
  不再依赖 tasklist 名称匹配，也不受部署目录过滤影响）；查询到进程但取不到 PID 的异常场景回退
  `taskkill /IM /T /F` 兜底；终止后轮询等待最多 6 秒并验证进程全部退出，仍有残留时列出剩余 PID/路径；
  无进程时提示「未检测到运行中的服务」而非报错。
- `get_service_status(cfg)`：结合进程检测（`tasklist` + `Win32_Process` 真实路径）与端口探测
  （`socket.create_connection`）返回状态：运行中（绿）/ 进程在但端口异常（黄）/ 已停止（红）。
  **v1.7.6**：运行判定按部署目录路径校验（`is_process_running(exe_name, deploy_dir)`）；
  检测到非部署目录同名实例（如其他目录下的测试副本残留）时状态栏橙色提示
  「检测到非部署目录的同名实例（<路径>），请先停止该实例再启动本服务」，**不自动结束进程**。
  **v1.8.1**：上述 foreign 场景返回独立状态码 `"foreign"`（不再混用 `"stopped"`），
  GUI `update_button_states` 将 foreign 视为运行侧——启用「停止服务」/「打开 Web」/「打开面板」、
  禁用「一键部署」/「启动服务」，用户可直接点击「停止服务」清理残留实例，避免
  「启动被拦截 + 停止按钮禁用」死锁。
  **v1.9.5 探测链路轻量化（输入密码卡顿根因修复）**：实测单次 `get_service_status` 原链路
  约 **4.0 秒**——`is_process_running` 与 `get_foreign_process_tip` 各起一次 PowerShell
  （`Win32_Process` 查 ExecutablePath，各约 2s），旧实现由 GUI 每 `status_check_ms`（3s）在主线程
  同步调用，主线程占用率接近 100%，表现为「弹出/输入密码框时界面卡顿」。现改为「轻量预检 + 单次
  精确查询」：新增 `_tasklist_name_hit(exe_name)`（`tasklist /FO CSV` 一次取进程名，实测约 0.1s）
  与 `_foreign_tip_from_procs(procs, deploy_dir)`（纯本地判断）；`get_service_status` 先做 tasklist
  预检，无同名进程 → 直接返回 `stopped`（不触达 PowerShell），有同名进程才调一次
  `find_vw_processes(deploy_dir=None)` 拿到全量路径后本地判定 `running` / `abnormal` / `foreign` /
  `stopped`。**四态语义、端口探测条件、foreign 提示文案与 v1.8.1 完全一致**，仅消除重复
  PowerShell 调用，单次耗时降至约 **0.13 秒**。配合 §4.5 的异步轮询，主线程占用率由 100% 降至约 4%。
- `get_deploy_state(cfg)`：**部署状态磁盘判定（v1.9.4）**。`vwm/service.py` 中的纯函数，按部署目录
  **实测文件**判断整体部署进度，返回 `(state, tip)`，`state` 三态：
  - `deployed`：`vaultwarden_dir/exe_name` 存在且 **>1MB**、`.env` 内 `ADMIN_TOKEN` 键存在且值非空、
    `web-vault/index.html` 存在——三项全满足才判已部署，tip 提示「已完成部署，无需重复部署」；
  - `partial`：核心文件与 `.env(ADMIN_TOKEN)` 就绪但缺 `web-vault/index.html`（部署部分就绪），
    允许再次点击「一键部署」补装网页版；
  - `none`：目录不存在 / 缺核心文件 / exe ≤1MB（疑似未下载完）/ 缺 `.env` 或其中无有效
    `ADMIN_TOKEN`——均为未部署，按钮保持可点。
  判定纯读磁盘、不写盘、幂等（连续调用结果一致），任何异常一律保守返回 `none`；
  **不依赖任何会话内内存标志**，因此程序重启后重新检测即可得到同样结论。
- `deploy_service(cfg, timeout=15.0, progress_cb=None, stage_cb=None)`：**一键部署**。若进程与端口均已就绪直接返回
  "服务已在运行，无需重复部署"；否则先检查核心文件 `vaultwarden.exe` 是否存在：
  - 缺失且 `vw_download_url` 为空 → 返回"核心文件缺失且未配置下载地址，请在 config.json 的
    vw_download_url 填入下载地址"并中止；
  - 缺失且已配置 URL → 调用 `download_file()`（标准库 urllib.request）在**后台线程**下载到部署目录
    （文件名 `exe_name`），下载期间通过 `progress_cb(downloaded, total)` 上报进度（界面进度条显示
    已下载字节/总字节百分比；`total=0` 表示长度未知，退化为不定进度并显示"部署中…"），
    校验文件存在且 >1MB 视为成功，失败清理半成品并给出明确错误；
  - 下载成功（或文件本就存在）后**v1.6.5 起先检查网页版**：若部署目录缺少 `web-vault/index.html`，
    则按 `vw_webvault_download_url` 调用 `download_file()` 下载官方 `.tar.gz`（文件名
    `web-vault.tar.gz`，超时 `vw_webvault_download_timeout` 默认 180），下载成功后调用
    `extract_webvault_tarball()` 解压并校验；下载/解压失败或 URL 为空**均不阻塞启动**，
    仅记录提示并在部署结果消息中附加「网页版未安装，服务已启动（仅 API 可用）」；
    下载网页版期间通过 `stage_cb("webvault")` 通知界面切换提示文字「正在下载网页版…」；
  - **v1.7.2 证书与信任自动集成**：核心文件与网页版处理就绪后、启动服务前，先检查
    `ssl_dir/cert_file` + `key_file` 是否都存在——缺失任一则调用 `generate_certificate(cfg)` 自动生成
    （已有则跳过不重复生成，通过 `stage_cb("cert")` 通知界面提示「正在生成证书…」）；
    随后调用 `add_system_trust(cfg)` 自动添加系统信任（通过 `stage_cb("trust")` 通知界面提示
    「正在添加系统信任…」）。证书生成失败 / 信任失败**均不阻塞启动**，仅附加提示到部署结果消息：
    证书成功生成时「已自动生成自签名证书」、已有时「证书已存在，跳过生成」、失败时
    「警告：证书生成失败（原因）」且跳过信任步骤；信任成功「已自动添加系统信任」、失败
    「警告：添加系统信任失败（原因）」。
  - 随后调用 `stage_cb("deploy")` 通知进入启动阶段（界面切换不定进度），
    **v1.7.6** 先调用 `ensure_admin_token(cfg)`（缺失时自动生成 ADMIN_TOKEN），
    再调用 `start_service(cfg)` 启动，并以 1 秒间隔轮询进程 + 端口直至就绪（默认 15 秒超时，
    超时后再确认一次避免临界点误报）。
  部署成功消息 **v1.7.6 起**在新生成 ADMIN_TOKEN 时附加
  「管理面板 https://localhost:<port>/admin 登录口令（ADMIN_TOKEN）：<token>，请妥善保存」。
  部署成功返回绿色提示，同时按钮矩阵会将「一键部署」置灰（服务运行中禁用）。
  **v1.9.4 起**按钮禁用不再只是「运行中临时置灰」：部署成功回调 `done()` 会立即重算
  `get_deploy_state()`，判定为 `deployed` 时「一键部署」**持久禁用**（服务停止后也不恢复可点），
  且成功消息追加「｜「一键部署」已锁定（已完成部署，如需重新部署请先清理部署目录）」。
- `extract_webvault_tarball(tgz_path, vw_dir)`：**网页版 tar.gz 解压（v1.6.5）**。用标准库
  `tarfile` 解压 Web Vault 前端：若压缩包内存在 `web-vault/` 顶层目录（`rel.split("/")[0] ==
  "web-vault"`），将包内 `web-vault/*` 直接解到部署根（保留前缀，其他根条目跳过）；若为散文件
  （无顶层 `web-vault/`），统一解到 `vw_dir/web-vault/`。每个成员先做路径净化
  （`replace("\\","/")` + `lstrip("./")`）并解析为绝对路径校验必须在目标目录内，**拒绝
  `../` 穿越与绝对路径成员**（zip-slip 防护），目录成员跳过；解压完成后校验
  `vw_dir/web-vault/index.html` 存在才算成功，返回 `(ok, 中文消息)`。
- `rotate_log_if_needed(log_path, max_mb)`：**日志轮转**。日志超过 `max_mb`（MB，默认 10）时
  将当前日志改名归档为 `log.1`（已存在则依次递增后缀），并新建空日志；未超阈值或失败返回空字符串。
- `download_file(url, dest, timeout=120.0, progress_cb=None)`：用标准库 urllib 下载文件，
  按 64KB 分块读取并节流上报进度（每 512KB 一次），下载失败清理半成品文件。
- `read_log_tail(cfg)`：读取日志尾部 `log_lines` 行；超过阈值先自动轮转（顶部标注轮转提示），
  读取失败给出明确中文提示（含文件占用原因）。
- `build_default_config()`：**运行时生成默认配置（便携化，v1.5.0）**。`vaultwarden_dir` 默认 =
  `APP_DIR/vaultwarden`（APP_DIR = 程序运行目录：开发模式为脚本目录、打包后为 exe 目录），
  `ssl_dir` 默认 = `APP_DIR/vaultwarden/ssl`，`backup_dir` 默认 = `APP_DIR/vaultwarden/backup`；
  其余字段保持原默认。config.json 缺失时按新默认自动创建。
- `_migrate_legacy_paths(cfg)`：**旧固定路径迁移（v1.5.0）**。load_config 读取 config.json 后，
  若 `vaultwarden_dir` 指向旧固定路径（≠ `APP_DIR/vaultwarden`，含空值），自动执行：
  ① 将旧 config.json 备份为 `config.json.bak-<时间戳>`；② 旧部署目录存在且新目录无数据时，
  用 `shutil.copytree` 把旧目录内容（data / ssl / .env / vaultwarden.exe / 日志等）复制到新目录
  （**保留旧目录不删除**）；③ 更新 config 的 `vaultwarden_dir` / `ssl_dir` / `backup_dir` 指向
  新路径并写回。复制期间状态栏提示「正在迁移部署目录...」，完成后提示
  「部署目录已迁移至 <新路径>，旧目录已保留，如需切换请修改 config.json」；新目录已有数据
  （二次运行）时不重复复制，仅确保 config 指向新路径。

### 4.2 证书生成

- `generate_certificate(cfg)`：基于 **cryptography** 生成 RSA-2048 自签名证书。
  - 有效期：`cert_days`（默认 3650 天 = 10 年）。
  - SAN：`localhost`（DNSName）+ `127.0.0.1` + `get_lan_ips()` 返回的本机局域网 IPv4。
    **v1.9.10 起该列表已过滤虚拟网卡（Hyper-V Default Switch、WSL、VMware/VirtualBox 等，见 §4.13），**
    证书 SAN 不再写入 `172.27.x.x` 这类仅虚拟交换机内部可达的地址，浏览器扩展用真实局域网地址连接时
    证书链可正确校验。
  - BasicConstraints `ca=True`（作为信任锚安装到根存储时需要）；
    KeyUsage 含 `key_cert_sign / crl_sign / digital_signature / key_encipherment`；
    ExtendedKeyUsage 含 `serverAuth`。
  - 写入前自动把旧 `cert.pem` / `key.pem` 备份为 `cert.pem.bak-<时间戳>` 等。
  - 生成后返回提示：**需重启服务（停止 → 启动）新证书才生效**。

> **v1.7.2**：本函数已并入「一键部署」自动链路——部署时无证书才调用生成、已有则跳过；
> 原「生成证书」独立按钮已移除（部署链路生成后立即启动服务使新证书生效，无需手动重启）；
> 证书生成失败不阻塞部署，仅附加警告提示。

- `get_lan_ips()`：UDP 连接 `8.8.8.8:80` 取默认出口 IP + 主机名解析，优先保留私网地址。

> 注意：证书功能依赖 cryptography，若 import 失败界面会提示先安装依赖。

### 4.3 系统信任

- `add_system_trust(cfg)`：执行 `certutil -addstore -user Root <cert.pem>` 安装到
  当前用户根信任库。已存在（"已存在" / "already exists"）时视为成功提示，不报错。

> **v1.7.2**：本函数已并入「一键部署」自动链路——部署时自动调用（证书存在时始终执行信任）；
> 原「添加信任」独立按钮已移除；信任失败不阻塞部署，仅附加警告提示。

### 4.4 备份（v1.6.2 起仅保留加密备份；v1.8.8 安全加固）

> **v1.8.8 备份安全设计（核心变更）**：v1.8.8 对「一键加密备份」与「导入备份」做了全面安全加固，
> 备份文件格式升级为 `v2`（新备份写入 `v2` 标识头 + 元数据 + 完整性校验，旧 `v1` 格式备份仍可导入，
> 见下「兼容策略」）。安全目标：弱密码不可用、备份不可被无密钥篡改、解压不可穿越/不可被压缩炸弹攻击、
> 密码不在任何介质残留、失败不留下半成品。

- `encrypt_backup(cfg, password, out_path=None, stage_cb=None)`：统一备份入口（原「一键备份」`backup_data` 已移除）。
  **v1.9.5 起支持自定义保存位置与阶段回调**：`out_path` 为空/空白串时沿用默认位置
  `backup_dir\data_<时间戳>_<4位随机hex>.enc`（既有命名规范不变）；传入自定义路径时按用户所选
  路径落盘（父目录不存在则自动创建，无后缀自动补 `.enc`，见 `resolve_enc_target`）。
  `stage_cb(name, text)` 在各阶段入口回调 `zip` / `check` / `kdf` / `encrypt` / `write`，
  供 GUI 状态栏显示「正在压缩 data 目录…」「正在派生密钥（PBKDF2 600000 次迭代）…」等具体进度；
  回调异常被内部捕获，**不影响加密流程**。
  流程：① **弱密码校验** `validate_password_strength(password)`——长度 ≥8 且必须同时含字母与数字，
  不满足返回中文提示「密码过弱：至少 8 位且需同时包含字母和数字」（GUI 点击备份即拦截，无需生成文件）；
  ② 将 `data` 目录**全量**压缩为 zip（标准库 zipfile，写入内存字节流）；③ 压缩包自身先过
  `_check_zip_safety` 安全红线（zip-slip/压缩炸弹自检，防止备份源目录被污染时产出危险包）；
  ④ 生成 `v2` 头部：`BACKUP_MAGIC=b"VWMBK2\n"` + 元数据 JSON（来源 `source`、工具版本 `tool_version`、
  备份时间 `created_at`、zip SHA-256 `zip_sha256`、PBKDF2 迭代数 `pbkdf2_iterations`、盐 `salt`
  base64），元数据行以 `\n` 结尾；⑤ 随机 16 字节盐 → PBKDF2-HMAC-SHA256（600,000 次迭代）派生
  32 字节 Fernet 密钥（`derive_fernet_key`），Fernet 加密"头部 + zip 字节"为载荷；⑥ 写盘
  `backup_dir\data_<YYYYMMDD_HHMMSS>_<8位随机段>.enc`（时间戳 + 随机段防覆盖），返回
  （加密文件路径、体积、文件数）。全程密码仅存于函数栈帧局部变量，**不写日志、不落临时文件**；
  密码为空或缺少 cryptography 时中止并给出中文提示。
- `decrypt_and_restore(cfg, enc_path, password)`：导入备份入口。流程：① 读取文件前 8 字节判断格式——
  **`v2`**（`BACKUP_MAGIC`）走新链路；**`v1` 旧格式**（非 `v2` 头，即 v1.8.7 及更早的裸 Fernet 载荷）
  走兼容链路 `derive_legacy_key`（SHA-256(password) 直接派生，保持旧备份可恢复），成功导入前明确提示
  「检测到旧版（v1）备份格式，已按兼容方式导入；建议重新加密备份以使用新版安全格式」；
  **两者均失败**返回「密码错误或文件已损坏」。② `v2` 链路：按头部 PBKDF2 参数（盐/迭代数）派生密钥，
  Fernet 解密载荷；**格式错误 / 解密失败（InvalidToken）** 统一提示「密码错误或文件已损坏」
  （不区分细节，防探测）；校验元数据 `zip_sha256` 与解出的 zip 字节 SHA-256 一致（**完整性/防篡改校验**），
  不一致提示「备份文件完整性校验失败：内容已被修改或文件损坏」；③ zip 全量校验：`_check_zip_safety`
  拒绝路径穿越（绝对路径、`..` 穿越、盘符、Windows 绝对路径）、符号链接条目、超限条目数
  （>50000）、超限解压总量（>2GiB）、超限压缩比（>1000，防压缩炸弹）；`ZipFile.testzip()` 校验全部
  条目 CRC；④ 恢复前 GUI 已有确认流程，现有 `data` 先改名 `data_bak_<时间戳>` 防误操作；
  `_extract_zip_safely` 逐条目解压（净化路径 + 强制 `path_within` 目标目录校验 + 累计解压字节上限），
  全部成功后**原子切换**（新 `data` 就位、`data_bak_` 保留供用户核对）；任一步失败即**回滚**：
  删除半成品新 `data`、恢复原 `data_bak_` 为 `data`，清理临时文件（TempFile 自动清理 + 显式删除），
  给出中文错误，**不破坏用户现有数据**；文件不存在时明确提示「备份文件不存在」。
- 兼容策略：**v2 为当前格式**（新备份一律 v2）；**v1 旧格式备份仍可导入**（不静默失败），
  导入时提示「旧版格式」建议重新备份；无法通过任何校验的文件统一提示
  「不是有效的备份文件」或「密码错误或文件已损坏」，不暴露内部细节。
- `resolve_enc_target(cfg, out_path=None)`：**备份保存位置解析（v1.9.5）**。纯函数，返回 `Path`：
  `out_path` 为空/空白串 → `Path(cfg["backup_dir"]) / generate_enc_filename()`（默认位置 + 既有
  `data_<YYYYMMDD_HHMMSS>_<4位随机hex>.enc` 命名，行为与 v1.9.4 完全一致）；非空 → 按用户所选路径
  规范化，无 `.enc` 后缀自动补全。**只解析不落盘**，GUI 用其生成「另存为」对话框的默认目录与默认文件名。
- **路径异常处理（v1.9.5）**：写入前校验父路径——父路径存在但不是目录 → 「备份位置无效：<路径> 不是目录。
  请更换备份位置」；目录创建失败/无权限 → 「无法创建备份目录：<路径>（原因）。请更换备份位置或检查权限」；
  目标路径本身是目录 → 「备份位置无效：<路径> 是目录。请指定文件名」。全部为中文提示、返回
  `(False, 消息)`，**不抛异常、不留半成品文件**，既有 `data` 与既有备份完全不受影响。
- 返回约定：加密备份返回 `(ok, 消息)`，成功消息含加密文件路径/体积/文件数；
  导入备份返回 `(ok, 中文消息)`，`ok=False` 时消息为上述明确中文错误，界面据此展示。

### 4.5 GUI 与线程模型

- `VaultwardenManagerApp(tk.Tk)`：主窗口，左侧 2×6 按钮矩阵（9 功能按钮 + 「原始日志/过滤日志」切换 + 「退出工具」，共 11 个；v1.6.2 起「退出工具」占最后一行整行 columnspan=2 填满矩阵；**v1.7.0 按钮文案精简**——「一键加密备份」→「加密备份」、「导入备份」不变、「添加系统信任」→「添加信任」、「打开 Web Vault」→「打开 Web」、「打开管理面板」→「打开面板」，其余不变，10 字符宽按钮全部容纳无溢出；**v1.7.2 移除「生成证书」「添加信任」两按钮**——功能并入「一键部署」，矩阵由 2×7 缩为 2×6，退出按钮改占第 6 行整行；**v1.7.3 统一按钮配色**——新增常量 `BTN_BG=#1971c2`（白字）/`BTN_BG_ACTIVE=#1864ab`，矩阵/日志切换/退出/刷新日志/弹窗全部按钮 NORMAL 态背景完全一致；**v1.7.4 提高文字对比度**——新增 `TEXT_PRIMARY=#212529`/`TEXT_SECONDARY=#343a40`/`TEXT_HINT=#495057`/`BTN_DISABLED_FG=#495057` 常量，状态标题/副标签/退出确认框提示/消息栏/取消类提示由浅灰 `#868e96`、`#495057` 改为深色高对比，按钮禁用态文字显式指定深灰，状态指示绿/橙/红加深为 `#2b8a3e`/`#d9480f`/`#c92a2a`）；**v1.7.5 按钮标题文字高对比统一**——`BTN_DISABLED_FG` 由 `#495057` 加深为 `#212529`（最深灰，与典型禁用灰底 #e9ecef 对比 13:1），密码/端口弹窗 4 按钮与刷新日志按钮补齐 `activeforeground="white"`、`disabledforeground=BTN_DISABLED_FG`（此前缺省，按压/禁用时文字可能继承系统灰），全部按钮（矩阵 11、刷新日志、退出确认框 2、弹窗 4，共 18 个）NORMAL 态统一白字、禁用态统一深色高对比，背景统一蓝 `BTN_BG` 不变），右侧日志区，底部消息栏。
- 日志区默认过滤噪音（顶部提示「（已过滤 N 行噪音日志）」）；「原始日志/过滤日志」按钮随时可切换查看
  未过滤原始内容（不修改落盘），按钮文案随状态切换，切换结果显示在状态栏。
- 耗时操作（启动/部署/停止/加密备份/导入恢复）通过 `run_task(fn, on_done, busy_text=None)` 放入后台线程执行，
  完成后经 `self.after(0, ...)` 回到主线程更新界面，期间通过 `set_busy(True)` 临时禁用全部功能按钮防止重入。
  **v1.9.5**：`busy_text` 允许业务侧自定忙碌文案（如「正在加密备份…」），不再统一覆盖为泛化的
  「正在执行，请稍候...」；工作线程回主线程统一改走 `_safe_schedule()`（带 `winfo_exists` 存活检查，
  窗口销毁后迟到回调直接丢弃，不抛 TclError）。
- **状态轮询异步化（v1.9.5，输入密码卡顿根因修复）**：新增 `refresh_status_async()` 与
  `_apply_status(res)`——前者把 `get_service_status` 放到 `vw-status-probe` 后台线程执行，
  **立即返回**（实测 < 1ms），结果经 `_safe_schedule` 回主线程由 `_apply_status` 应用
  （状态栏文字/颜色 + `_refresh_deploy_state()` + `update_button_states()`）；单飞标志
  `_status_probing` 保证探测在途时不重复发起（探测未回填前再次调用直接返回 `False`）。
  `_periodic_status` 改为调用本方法后 `after(status_check_ms)` 递归排程；`__init__` 启动时先
  `_refresh_deploy_state()` + `update_button_states()` 完成首屏渲染，再 `refresh_status_async()`
  异步回填；`_finish_task()`（任务结束）与 `on_change_port()`（改端口）同样改调异步版本。
  同步 `refresh_status()` 保留供需要即时结果的场景（如按钮矩阵内部逻辑）使用，**行为不变**。
  优化前主线程每 3 秒被约 4 秒的同步探测占满，是「弹出密码框/输入密码时卡顿」的根因；
  优化后主线程占用率约 4%，密码框弹出、键盘输入、拖动窗口全程流畅。
- **加密备份「选择备份位置」（v1.9.5）**：`on_enc_backup` 顺序为「校验 cryptography 可用 →
  `prompt_password` 输密码 → `filedialog.asksaveasfilename` 选保存位置 → 后台加密」。
  - 保存对话框默认定位 `resolve_enc_target(cfg)` 得到的既有备份目录与既有文件名
    （`initialdir=backup_dir`、`initialfile=data_<时间戳>_<hex>.enc`、`defaultextension=".enc"`、
    文件类型「加密备份 *.enc / 所有文件」），用户可改目录与文件名；
  - **取消选择**（对话框返回空串）→ 状态栏灰色提示「已取消加密备份（未选择保存位置）」，
    **不调用加密函数、不产生任何文件、不进入忙碌态**；密码框取消仍提示「已取消加密备份」；
  - 选中后状态栏立即显示「正在加密备份…」（`run_task(..., busy_text="正在加密备份…")`），
    加密线程内的阶段回调经 `_safe_schedule` 回主线程刷新具体阶段文案（压缩 / 校验 / 派生密钥 /
    加密 / 写盘），成功消息含**完整保存路径**，失败给出中文原因（路径无效、无权限等）；
  - 加密**始终在后台线程**执行，PBKDF2-HMAC-SHA256 **600,000 次迭代保持不变**（未降低安全强度）；
    加密格式仍为 `VWM_ENC_V2`，防压缩炸弹校验、v1 旧备份兼容导入逻辑完全未改，
    自选位置产生的备份与默认位置备份可互相导入。
- **一键部署进度条（v1.6.3；v1.6.7 起回归常规尺寸）**：界面底部消息栏上方新增进度区（`_progress_frame`，默认隐藏），
  含提示文字 `progress_label`（11 号粗体，全中文）与 `ttk.Progressbar`（style
  `Deploy.Horizontal.TProgressbar`，thickness=16）。执行链路：
  - 点击「一键部署」→ `on_deploy` 先 `_show_deploy_progress()` 展开进度区并复位，再 `run_task` 放后台线程；
  - 下载阶段：`deploy_service` 的工作线程每 512KB 回调 `progress_cb(downloaded, total)`，
    回调内用 `self.after(0, ...)` 切回主线程调 `_set_progress_determinate(pct, text)` 更新百分比；
    `total=0`（无 Content-Length）时退化为 `_set_progress_indeterminate("…大小未知，部署中…")` 不定进度；
  - 部署/启动阶段：下载校验完成后 `stage_cb("deploy")` 通知，回调内 `after(0)` 切主线程切换不定进度
    （`_set_progress_indeterminate`，动画间隔 15ms）并启动 `_start_deploy_poll()`——
    主线程 `after(1000)` 每 1 秒轮询 `_deploy_poll_tick()`，在 `_busy=True` 期间刷新提示文字
    「正在部署/启动服务… 部署中…（已等待 N 秒）」；`_busy=False` 时停止轮询；
  - **网页版下载阶段（v1.6.5）**：核心文件就绪后若缺 `web-vault/index.html`，`deploy_service` 先
    触发 `stage_cb("webvault")`，`on_deploy` 经 `after(0)` 切主线程把提示文字切换为「正在下载网页版…」；
    随后网页版下载回调复用同一 `progress_cb(downloaded, total)`——有 Content-Length 时
    `_set_progress_determinate` 显示百分比，`total=0` 退化为不定进度；解压阶段短暂不定进度，
    解压完成后才 `stage_cb("deploy")` 进入启动轮询阶段；
  - **证书与信任阶段（v1.7.2）**：网页版处理完成后，`deploy_service` 依次触发
    `stage_cb("cert")`（提示「正在生成证书…」，已有证书时跳过、不触发）与 `stage_cb("trust")`
    （提示「正在添加系统信任…」），`on_deploy` 经 `after(0)` 切主线程更新进度提示文字；
    两阶段为瞬时/短耗时操作，不定进度显示，完成后才 `stage_cb("deploy")` 进入启动轮询阶段；
  - 任务结束：`done` 回调在主线程调 `_finish_deploy_progress()`——取消轮询、停止动画、
    进度条复位 determinate=0、`_progress_frame` 隐藏、提示文字清空，完成/失败结果由消息栏展示；
  - 全程工作线程不触碰任何 tkinter 控件，所有 UI 更新均经 `after(0)` 回主线程，界面不冻结；
    部署期间沿用 `set_busy(True)` 保持全部功能按钮不可点。
- `update_button_states()`：**按钮状态矩阵**。每次 `refresh_status()` 轮询后按当前服务状态刷新可用性，
  并与 `_busy` 忙碌状态协调：
  - 服务运行中（含 abnormal）：禁用「一键部署 / 启动服务」，启用「停止服务」与「打开 Web / 打开面板」
    （**v1.6.9 修复**：此前运行中误将两个打开按钮禁用，服务正常运行时按钮置灰、点击无效）；
  - 服务停止时：禁用「停止服务」与「打开 Web / 打开面板」，启用「一键部署 / 启动服务」；
  - 其余按钮（复制地址 / 加密备份 / 导入备份 / 修改端口）始终可用；原始日志按钮始终可用；
  - **v1.9.4 已部署持久锁定**：`_refresh_deploy_state()` 读取 `get_deploy_state(self.cfg)` 结果存入
    `self._deploy_state`（`deployed` / `partial` / `none`），矩阵在「运行中禁用」之后、`stopped`
    恢复启用之前插入一条独立分支——`key == "deploy" and deployed` → `DISABLED`。
    因此「服务运行中」与「服务已停止」两种状态下，只要磁盘判定已部署，「一键部署」都保持禁用；
    程序重启后首次 `refresh_status()` 即重新检测，禁用状态自动保持，**不依赖会话内标志**。
    `partial`（缺网页版）仍可点击以补装，`none`（未部署/缺文件）照常可点击。
  - **v1.9.4 点击拦截双保险**：即使通过其它路径触发 `on_deploy`，入口处先调 `get_deploy_state()`，
    已部署则**直接返回**（刷新状态、置灰按钮、状态栏橙字提示「已完成部署，无需重复部署；
    如需重新部署请先清理部署目录 <部署目录>」），不启动任何部署线程，点击禁用按钮无任何副作用。
  - **v1.9.4 状态栏提示**：状态栏副标签实时显示部署进度语义——「已部署（一键部署已锁定）」/
    「部署部分就绪（可点击一键部署补装网页版）」/「未部署（可点击一键部署）」，
    迁移提示存在时优先级更高，覆盖显示迁移提示。
  - 操作进行中（`_busy=True`）：全部功能按钮临时禁用，「退出工具」保持可用；
    操作结束后 `set_busy(False)` 按上述状态矩阵恢复。
  - **v1.8.5**：矩阵之外新增「设置」「关于」两个特殊样式按钮（白底蓝字描边，
    `BTN_SECONDARY_*`，位于矩阵下方第 7 行左/右两列），**不参与状态矩阵**——任何服务状态
    （running/abnormal/foreign/stopped）与 `_busy` 忙碌期间均保持可用；矩阵 11 个主按钮的状态
    规则完全不变。
- **打开地址动态拼接（v1.6.9；v1.7.0 扩展）**：`resolve_web_url(cfg)` 纯函数动态拼接打开地址，
  不再写死 8000、不依赖可能与实际端口不同步的 `cfg['domain']`；`on_web` 用该地址打开 Web Vault，
  `on_admin` 用该地址 + `cfg['admin_path']`（默认 `/admin`）打开管理面板；「修改端口」同步
  `cfg['port']` 后两个按钮自动跟随新端口。回调内 `webbrowser.open` 抛异常时
  状态栏提示「打开浏览器失败：<原因>」而非静默失败。
  - **v1.6.9**：按 `cfg['port']` 拼接 `https://localhost:<port>`；
  - **v1.7.0 实际监听端口 + 协议探测**：新增 `get_listen_port(exe_name)`（`tasklist` 建 PID→进程名映射
    + `netstat -ano -p tcp` 过滤 LISTENING，解析 `vaultwarden.exe` 监听端口，排序去重）与
    `detect_scheme(host, port)`（TLS 握手探测：成功返回 `https`、失败返回 `http`、端口未开返回空串）；
    `resolve_web_url` 执行顺序：① 若 `get_listen_port` 命中实际监听端口且 ≠ cfg['port']，以实际端口为准
    （config/.env 与运行时漂移时打开地址仍正确）；② `detect_scheme("127.0.0.1", 端口)` 探测实际协议——
    服务未启用 TLS（无 `.env` ROCKET_TLS，如当前 HTTP 运行）时拼 `http://`，不再因 HTTPS 握手失败报网络链接错误；
    ③ 服务未运行/探测失败回退 `https://localhost:<cfg['port']>`。
- 状态每 `status_check_ms`（默认 3000ms）自动轮询刷新。

### 4.6 端口修改与地址复制

- `prompt_port(parent, current_port)`：模态弹窗输入新端口（1-65535），回车/确定提交，
  Esc/取消关闭；非法输入弹错误提示不关闭。
- `update_port(cfg, new_port)`：同步更新 `config.json` 的 `port` 与 `domain`
  （`https://localhost:<新端口>`），并同步部署目录 `.env` 的 `ROCKET_PORT` 与 `DOMAIN`（v1.7.0）：
  - `.env` 已存在 `ROCKET_PORT=` / `DOMAIN=` 时原位替换值，保留原注释与换行风格；
  - 不存在时在文件末尾追加对应键值对（末尾无换行先补换行）；
  - 完成后提示**需重启服务（停止 → 启动）后生效**。
- **v1.8.2 端口单一配置源**：config.json 的 `port` 为权威，`.env` 的 ROCKET_PORT/DOMAIN 由
  `update_port` / `ensure_env_runtime` 自动同步（不手工改 .env）；默认端口字面量仅存在于
  `config.build_default_config` 一处（`default_port`），domain 由 port 派生；UI/URL 拼接/
  探测/部署全链路读取 `cfg['port']`，无任何硬编码端口残留。
- `on_copy_addr`：复制 `cfg["domain"]`（Web Vault 访问地址）到剪贴板并在状态栏显示。
- 按钮矩阵为 2×7：新增「一键部署」（置顶，青色）与「修改端口」「复制地址」。

### 4.7 系统托盘与退出确认（v1.6.6）

- **确认框 `ask_quit_or_tray(parent, remember_default=False)`**：点击主窗口右上角关闭（X）或「退出工具」按钮时弹出的全中文
  模态对话框（440×260，`grab_set` 模态 + `wait_window` 阻塞至选择）：标题「要退出 Vaultwarden 管家吗？」，
  副文案提示「退出程序将先停止 Vaultwarden 服务再退出；最小化到托盘不会停止服务，可从系统托盘图标恢复窗口」,
  常规尺寸按钮（10 号粗体、10 字符宽 × 1 行高）：「退出程序」「最小化到托盘」两按钮
  NORMAL 态背景统一为 `BTN_BG=#1971c2`（白字，按压 `BTN_BG_ACTIVE=#1864ab`）。
  **v1.8.3 返回结构改为 dict `{"action": "quit"/"tray"/None, "remember": bool}`**（此前返回字符串
  `"quit"`/`"tray"`/`None`）：按钮下方新增勾选框「记住我的选择，下次不再询问」（Checkbutton，
  白底勾选块、与弹窗底色一致、手型光标）；`action` 为选择动作，`remember=True` 表示勾选了记忆；
  直接关闭对话框返回 `{"action": None}`（取消，窗口保持原状态）。
  **v1.6.8 弹出位置**：创建时经 `_centered_geometry(parent, 440, 260)` 计算 geometry——优先按主窗口
  `winfo_x/y/width/height` 相对主窗口正中间居中（先 `update_idletasks()` 取准确几何，`x/y` 与主窗口边缘
  截断保护取非负）；主窗口几何不可用（已最小化/隐藏时 width/height 为 1、或查询抛 `TclError`）时退化为
  屏幕居中，避免弹到屏幕外；尺寸 440×260（v1.8.3 增高容纳勾选框，按钮、文字、功能不变）。
- **托盘创建 `_create_tray_icon()`**：`__init__` 末尾调用。优先 **pystray**（`Icon.run_detached()`，
  pystray ≥0.19 免手动线程，旧版回退 `threading.Thread(target=icon.run, daemon=True)`）；
  图标用 **Pillow 代码绘制**（64×64 RGBA：蓝底圆角方块 + 白色 V 形，无额外图片文件依赖）；
  tooltip「Vaultwarden 管家」；托盘回调运行在独立线程，**统一经 `self.after(0, ...)` 回主线程**
  操作 tkinter 控件（与 `run_task` 工作线程同一模式）；右键菜单含「显示主窗口」（`default=True`，
  单击/双击也触发）与「退出程序」。依赖缺失（`import pystray/PIL` 失败）或创建失败时
  `_tray_active=False` 降级：关闭窗口直接退出并在状态栏提示，不残留僵尸托盘。
- **关闭/退出统一入口 `on_close_request()`**：绑定 `WM_DELETE_WINDOW`，同时「退出工具」`on_exit`
  改调它，行为一致——托盘可用时按退出记忆逻辑处理；`"quit"` → `_quit_app()`，
  `"tray"` → `_minimize_to_tray()`（`root.withdraw()` 隐藏窗口）；托盘不可用时直接 `_quit_app()`。
  **v1.8.3 退出记忆逻辑**：① `cfg.quit_confirm_skip=True` 且未按住 Shift → 不再弹框，按
  `cfg.quit_default_action`（`"tray"`/`"quit"`）直接执行记忆动作；② 弹框时勾选「记住我的选择」→
  `config.apply_quit_memory(cfg, action)` 持久化（`quit_confirm_skip=True` + `quit_default_action=action`
  写回 config.json），状态栏绿色提示「已记住退出方式为「最小化到托盘/退出程序」，下次退出不再询问」
  并写 manager.log；③ 未勾选 → 仅本次生效、下次仍询问（不写盘）；④ 未勾选但原本已记忆（Shift 强制
  询问场景）→ `config.clear_quit_memory(cfg)` 清除记忆，恢复每次询问并提示。
  **恢复询问入口（v1.8.3，二选一）**：界面内**按住 Shift 再点关闭（X）/「退出工具」**——主窗口
  `bind_all` 监听 `<KeyPress/KeyRelease-Shift_L/Shift_R>` 维护 `_shift_held` 标志，Shift 按住时
  `on_close_request` 强制弹框（勾选框默认不勾选，确认后若未勾选即清除记忆恢复询问）；或直接修改
  config.json 的 `quit_confirm_skip` 为 `false`。
- **恢复 `_show_from_tray()`**（托盘回调经 `after(0)` 进主线程）：`deiconify()` + `lift()` +
  `focus_force()` 显示并置顶窗口，状态栏提示「已从系统托盘恢复」。
- **退出清理 `_quit_app()`**：**v1.8.4 退出前先停止服务**——所有「退出程序」路径（确认框选
  「退出程序」、记忆 `quit_default_action="quit"` 直接退出、Shift 强制询问后选退出、托盘菜单
  「退出程序」等）统一先进本方法：检测到服务在运行则状态栏/日志提示「正在停止服务…」，复用
  `service.stop_service` 停止全部实例并轮询确认；停止失败（超时仍有残留）或异常时弹全中文确认框
  `ui.ask_stop_failed_quit`（「仍退出」/「取消退出」），绝不静默放弃；无服务在运行则直接退出。
  取消退出分支保留主窗口与托盘图标、不执行清理。最小化到托盘（`_minimize_to_tray`）不经过本
  方法、不停止服务。真正退出时先 `icon.stop()` 通知托盘线程退出、清理托盘图标，再 `destroy()`
  销毁主窗口结束 `mainloop`，保证不残留僵尸托盘图标。v1.8.3 勾选持久化、Shift 恢复询问、按钮
  矩阵等既有行为不变。
- **v1.8.9 托盘整体加固**：① **单实例互斥**——新增 `_acquire_single_instance()`（`CreateMutexW`
  固定名 `Global\VaultwardenManager_SingleInstance`），`main()` 启动前获取；重复启动时
  `_activate_existing_instance()` 通过 `FindWindowW` 找到既有主窗口并 `ShowWindow(SW_RESTORE)`
  + `SetForegroundWindow` 激活，第二实例立即退出，**从源头保证托盘图标唯一**、杜绝重复启动在
  任务栏堆积多个图标；② **托盘异步就绪**——`_create_tray_icon()` 创建 `run_detached()` 后轮询
  等待 `icon._running` 就绪（最多 3 秒，每次 `time.sleep(0.2)`），就绪后才置 `_tray_active=True`；
  期间若检测到窗口关闭请求先走最小化到托盘（`_minimize_to_tray`）则稍后重试，避免「窗口已隐藏但
  托盘图标尚未就绪」导致窗口丢失；创建失败/依赖缺失降级为直接退出并提示；③ **回调线程安全**——
  新增 `_safe_schedule(cb)`：先 `winfo_exists()` 校验窗口仍存活，再 `after(0, cb)` 调度；所有托盘
  回调（显示/退出）统一改走 `_safe_schedule`，杜绝「主窗口已销毁后托盘线程迟到回调」导致的
  `TclError` 崩溃；④ **幂等与状态复位**——`_minimize_to_tray()`/`_show_from_tray()` 增加
  `_tray_active` + 窗口 `state()` 双条件幂等判断（已隐藏不再重复 withdraw、已显示不再重复
  deiconify）；`_quit_app()` 退出清理托盘：`icon.stop()` 失败时追加重试兜底（间隔 0.5s 最多
  3 次），成功后显式置 `_tray_icon=None`、`_tray_active=False`，保证状态一致、图标唯一清理；
  ⑤ **存量 Bug 修复**——`append_manager_log` 定义签名 `(cfg, action, summary)`，app.py 中
  6 处调用（退出记忆×2、退出停服务×3、设置保存×1）缺少 cfg/action/summary 参数会抛
  `TypeError`（影响退出/设置操作日志落盘），v1.8.9 全部补齐为
  `append_manager_log(self.cfg, 操作名, 摘要)`；托盘/退出/设置/关于/按钮矩阵零回归。
- **v1.9.1 退出链路非阻塞化（退出卡顿优化）**：根因——`_quit_app` 在主线程**同步**执行「检测服务（`find_vw_processes` 起 PowerShell/Win32_Process，实测约 2s）+ `stop_service`（内部再次 find + taskkill + 轮询确认，每轮轮询又起 PowerShell，实测约 4.3s）」，点击退出后界面假死最坏 6.4 秒。优化：① **停止服务改后台线程**——`_quit_app` 置 `_quitting` 防重入，主线程先刷新「正在退出…（停止服务中）」提示并 `update_idletasks()` 立即响应，`threading.Thread(daemon=True)` 执行「检测→stop_service」，结果经 `_safe_schedule` 回主线程 `_on_stop_result()` 统一处理：成功 → `_final_cleanup()`（托盘 `icon.stop()` 重试兜底 + `destroy()`）；失败 → `ask_stop_failed_quit`（「仍退出」→ `_final_cleanup`，「取消退出」→ 复位 `_quitting`、保留主窗口与托盘，与 v1.8.4 一致）；等待期间重复退出请求因 `_quitting` 直接忽略，不重复启动线程；② **轮询确认轻量化**——`service.stop_service` 新增 `_tasklist_pids()`（`tasklist /FO CSV` 一次取全 PID，不起 PowerShell），轮询固定 6s 时间预算、间隔 0.2s 按 PID 存活判定，替代原先每轮 `find_vw_processes`（每轮约 2s 空耗）；取不到 PID 罕见场景回退 find 轮询。**功能行为零变化**：退出前仍确保停止服务、manager.log 落盘、取消保留窗口托盘、托盘清理兜底。
- **v1.9.2 进程被强杀后托盘 ghost 图标清理（启动广播托盘刷新 + 图标重注册兜底）**：根因——正常退出路径 `_final_cleanup` 已执行 `icon.stop()`（内部 `Shell_NotifyIcon(NIM_DELETE)`）+ 重试兜底，托盘图标随进程正常注销；但进程被**强杀**（`taskkill /F` / 任务管理器结束）时进程来不及执行 NIM_DELETE，explorer 通知区仍保存该图标条目，形成「ghost 图标」长期残留且无进程可响应点击。方案：① **启动广播清 ghost**——新增 `app._refresh_tray_icons()`：`ctypes.windll.user32.PostMessageW(HWND_BROADCAST=0xFFFF, WM_TIMECHANGE=0x001A, 0, 0)` 向所有顶层窗口广播系统时间变更消息，explorer 收到后重读通知区、自动清理失效（进程已死）图标条目；WM_TIMECHANGE 是通知区公认安全刷新手法，只触发刷新、不删除其它应用正常注册的图标，不误伤系统托盘；**实测关键约束**：广播必须**前置到自身托盘图标注册之前**——若在图标注册后再广播，explorer 重建通知区时会丢掉刚注册的 pystray 图标（Win11 新版通知区下 pystray 的 WM_TASKBARCREATED 重注册不生效），故 `main()` 顺序为：单实例互斥 → `_refresh_tray_icons()` → `time.sleep(2.5)`（等 explorer 完成通知区重建）→ 创建 `VaultwardenManagerApp`（内部注册托盘图标）→ `mainloop()`；② **图标重注册兜底**——新增 `app._resend_taskbar_created()`：`_create_tray_icon()` 置 `_tray_active=True` 后 `self.after(2000, ...)` 延迟调用，向自身 pystray 图标窗口（`icon._hwnd`）`PostMessageW(RegisterWindowMessage("TaskbarCreated"))`，触发 pystray 重新 `Shell_NotifyIcon(NIM_ADD)`；实测发现进程被强杀后 explorer 通知区可能处于异常状态、首次 NIM_ADD 注册不被显示，补发 TaskbarCreated 可稳定恢复显示；同一 hWnd+hID 的 NIM_ADD 只更新不新增，不产生重复图标、不影响其它应用；③ ctypes/user32 异常时静默跳过（降级为不刷新，功能零回归）。配合 v1.8.9 既有防线：单实例互斥（`CreateMutexW`）保证重复启动不堆积图标；`_create_tray_icon` 就绪轮询保证图标可用；`_final_cleanup` 退出清理兜底保证正常退出无残留——**强杀残留由启动广播兜底清理，异常通知区由重注册兜底恢复**。验证：`tests\verify_ghost_v192.py` 20/20 PASS（py_compile app/ui、广播参数断言 `(0xFFFF, 0x001A, 0, 0)`、ctypes 异常静默兜底、main 接线断言、v1.8.9 单实例互斥与退出清理保留、`SetLastError(0)` 前置与 183 双条件、无实例时首次 `True`/同进程二次 `False`、`_nim_delete_icon` 接线且位于 `icon.stop()` 之后、`Shell_NotifyIconW(2)`、TaskbarCreated 重注册接线、VERSION=v1.9.2）；真机冒烟（源码 + dist 两环境）——① 干净启动（含广播）托盘图标正常显示、无空白槽位；② `taskkill /F` 强杀后进程无残留、图标消失、无 ghost 占位；③ 强杀后重新启动，广播清理 + 重注册兜底生效，图标稳定恢复显示、其余应用托盘图标排列不变（不误伤）；④ 单实例互斥生效（第二实例自动退出）；⑤ 正常退出路径托盘图标正常消失（v1.9.1 回归 verify_quit_v191 11 项全 PASS）。

- **v1.9.2 补充修复（「启动后约 6~12 秒自动退出」根因 + 退出显式 NIM_DELETE 兜底）**：① **自动退出真根因**——`_acquire_single_instance()` 原实现调用 `CreateMutexW` 后**未清零 `GetLastError()`**，同线程残留的错误码（183 `ERROR_ALREADY_EXISTS`）被后续判定读到，导致**互斥创建成功却被误判为「已有实例」**，进而走「激活已有窗口并退出」分支：程序启动 → 创建托盘约 2~3s → 误判触发 `_quit_app` → 窗口与托盘图标自动消失（表现为「约 12 秒后进程自己退出/图标没了」）；explorer 重启只是让该误判更早暴露，并非根因。修复：`kernel32.SetLastError(0)` 前置 + 显式声明 `CreateMutexW` 的 `restype/argtypes`，仅按「返回值非空 且 `GetLastError()==ERROR_ALREADY_EXISTS`」双重条件判定，第二实例才走激活退出；实测确认历史残留旧源码进程占用同一 `Local\VaultwardenManager_SingleInstance` 时也会触发该误判，结束旧进程后 `_acquire_single_instance()` 返回 `True`、进程稳定存活。② **退出显式 NIM_DELETE 兜底**——新增 `VaultwardenManagerApp._nim_delete_icon(hwnd, hid)`：`_final_cleanup` 在 `icon.stop()`（pystray 内部 `_hide()` → `NIM_DELETE`）之后，用事先记录的 `icon._hwnd` 与 `id(icon)`（与 pystray 注册标识 `hID=id(self)` 严格一致）再显式调用一次 `Shell_NotifyIconW(NIM_DELETE=2, ...)`，覆盖 pystray 线程停止超时/内部 `_hide()` 未执行等异常路径，确保通知区条目被物理删除；图标未就绪或 hwnd 无效时静默跳过，无副作用。③ 验证：`tests\verify_ghost_v192.py` 20/20 PASS（A1-A2 编译、B1-B5 广播参数/顺序/ctypes 静默、C0-C4 互斥无实例首次 `True` 与同进程二次 `False`、D1-D5 `_nim_delete_icon` 接线与 `Shell_NotifyIconW(2)` 及 pystray 标识一致、E1-E2 TaskbarCreated 重注册、F1 VERSION）；退出回归 `verify_v192_all.py` 19 项 + `verify_reentry.py` 2 项全 PASS（tasklist 含当前 PID、取消退出保留窗口/托盘并复位 `_quitting`、「仍退出」销毁、成功停止销毁、`_quitting` 防重入不新建线程、退出仍调用 NIM_DELETE 与 `icon.stop()`）；源码真机实测：启动后 12s/30s 均存活（修复前约 12s 自动退出），强杀后重启 15s/30s 均存活。④ **终验补充（onefile 双进程与「进程已结束但托盘图标不退出」的真实成因）**——PyInstaller `-F` 产出的 exe 运行时为**父子双进程结构**（父 `runw.exe` bootloader + 子 GUI 进程，`tasklist` 可见同映像名两条记录）；实测 `taskkill /F /PID <父>` 只结束后仅剩 GUI 子进程（`pids=[子]`），主窗口句柄（`FindWindowW("TkTopLevel","Vaultwarden 管理工具")`）与托盘图标**仍存活并响应**——用户从任务管理器「结束任务」若只命中父引导进程，就会看到「进程已结束、托盘图标点不掉」的假象，且残留子进程持有 `Local\VaultwardenManager_SingleInstance` 互斥，使再次启动被判定为「已有实例」而「启动即退出」（表现为程序打不开）。因此：**结束进程必须结束进程树**（任务管理器「详细信息」中结束全部 `VaultwardenManager.exe`，或 `taskkill /F /T /IM VaultwardenManager.exe`）；`_activate_existing_instance()` 据此加固——`FindWindowW` 改为 6×0.5s 重试（覆盖新实例启动早期「广播 2.5s + 托盘就绪轮询」窗口尚未创建的正常情况），重试后仍找不到主窗口则判定为强杀遗留的孤儿残留进程，弹框明确提示用户结束全部 `VaultwardenManager.exe` 进程后重启，不再让用户面对「无窗口无图标却启动失败」的黑箱。⑤ **通知区条目实测（硬指标）**——用 `HKCU\Control Panel\NotifyIconSettings` 中 `ExecutablePath` 命中 `VaultwardenManager.exe` 的条目数度量 ghost 堆积：运行中 =1、`taskkill /F /T` 强杀后 =1（Win11 持久化设置项保留，含幽灵条目）、强杀后重启（广播刷新 + 重注册）=1，全程**始终为 1、无堆积**，证明启动广播 + 同一 `hWnd+hID` 重注册不会新增重复条目；托盘区像素采样（蓝色图标簇面积 169px）在启动后 3s~51s 连续 16 次采样均稳定存在，无「约 12 秒后图标消失」现象，验证 `SetLastError(0)` 修复有效。⑥ **退出回归独立脚本**——新增 `tests\verify_quit_v192.py` 11/11 PASS（`tasklist_pids` 含当前 PID / 取消退出保留窗口与托盘并复位 `_quitting` / 「仍退出」销毁窗口 / 成功停止销毁窗口 / `_quitting` 防重入不新建线程且保持退出中 / 退出调用 `_nim_delete_icon` 兜底 / 退出仍 `icon.stop()` / `_final_cleanup` 清空托盘状态），脚本末尾 `os._exit()` 收尾规避 tkinter `Tcl_AsyncDelete` 噪声，退出链路零回归。

- **v1.9.3 第二实例弹提示（单实例互斥交互完善）**：v1.9.2 及以前检测到已有实例时仅「激活既有窗口后静默退出」，用户无任何可见反馈（尤其孤儿残留场景表现为「双击无反应/打不开」）。v1.9.3 在既有互斥基础上补齐提示交互：① **弹窗防重复 `_acquire_notice_lock()`**——新增第二把互斥 `Local\VaultwardenManager_NoticeLock`（`SetLastError(0)` 前置 + `ERROR_ALREADY_EXISTS` 双条件，与主互斥判定方式一致），只有抢到该锁的第二实例才弹提示，同一时刻只弹一次；同进程二次调用返回 `False`（进程内 `_notice_lock_acquired` 标志复位保护），快速连点/连开多个第二实例不会叠加弹窗、不出错；② **`_activate_existing_instance()` 重写为「提示 + 激活」**——先经 `ctypes.windll.user32.MessageBoxW` 弹**中文置顶提示框**，标题固定 `VaultwardenManager`，flags `0x50040`（`MB_TOPMOST|MB_SETFOREGROUND|MB_ICONINFORMATION`，无父窗口也强制置顶可见、设前台、带信息图标、只有「确定」按钮）；文案按场景区分：找到主窗口 → 「程序已在运行中，请勿重复打开。\n\n可从任务栏窗口或系统托盘图标打开已有窗口。」；6×0.5s `FindWindowW` 重试后仍无主窗口（强杀遗留孤儿残留进程）→ 「程序已在运行中，但未找到它的主窗口（可能是上次被强制结束后遗留的残留进程）。\n\n请打开任务管理器→详细信息，结束所有 VaultwardenManager.exe 进程后重新启动；也可在命令行执行：taskkill /F /T /IM VaultwardenManager.exe」；③ **提示后激活、激活失败不影响退出**——`MessageBoxW` 返回后（用户点确定）再尝试 `ShowWindow(SW_RESTORE)` + `SetForegroundWindow` 激活既有窗口，`ctypes`/窗口句柄异常时静默容错，不阻塞既有实例、不影响第二实例自身退出；④ **自行退出不残留**——`app.main()` 接线为 `if not _acquire_single_instance(): if _acquire_notice_lock(): _activate_existing_instance(); return`，提示结束即 `return` 结束进程（未创建 Tk 窗口与托盘，无 GUI 残留）；⑤ `vwm/ui.py` `VERSION` → v1.9.3（关于窗口版本号同步）。⑥ **置顶加固 `_keep_dialog_topmost()`**——实测本机 Windows 11 Build 26200 上 `MB_TOPMOST` 并不落到对话框的 `WS_EX_TOPMOST` 样式位（`GetWindowLongW(h,-20)` 恒为 `0x00010101`，手工 `SetWindowPos(HWND_TOPMOST)` 亦不改变该位），且 MessageBox 未必抢到前台（后台启动场景），仅靠 flags 无法保证「置顶可见」。为彻底满足要求，新增 `_keep_dialog_topmost(user32, title)`：弹框前启动**守护线程**，以 `FindWindowW("#32770", "VaultwardenManager")` 轮询（最多 60×0.05s）命中后调用 `SetWindowPos(h, HWND_TOPMOST, 0,0,0,0, SWP_NOSIZE|SWP_NOMOVE|SWP_NOACTIVATE)` 显式置顶（`argtypes/restype` 显式声明，避免 64 位下 `HWND(-1)` 被按 32 位 int 截断），置顶后线程自然结束；线程异常、窗口未出现、`ctypes` 不可用均静默跳过，不阻塞 MessageBox 调用方，也不影响第二实例提示后的退出。⑦ **验证（收尾复测）**——静态断言 `tests\verify_single_instance_v193.py` **38/38 PASS**（原 35 项 + 新增 H1 `_keep_dialog_topmost` 定义/守护线程、H2 `SetWindowPos(HWND_TOPMOST)` 参数、H3 弹框前置顶顺序）；exe 真机 `verify_si_dist_v193.py` **15/15 PASS**（A1-A2 第一实例建窗存活、B1 第二实例 1.0s 内弹出标题为 `VaultwardenManager` 的提示框、B2 提示框可见且中心点 `WindowFromPoint` 命中自身即**未被遮挡**、B3-B5 正常场景文案含「程序已在运行中」与任务栏/托盘引导且不含孤儿文案、B6 点确定后 0.5s 内退出码 0、B7 无残留进程、B8 第一实例不受影响、C1-C4 连开 3 个只弹 1 次且全部退出、D1 收尾零残留）；`tests\verify_si_live.py`（exe 模式）实测提示 1.01s、退出码 0、无残留、连开 3 个同时仅 1 个提示框；`tests\verify_si_orphan.py`（源码）模拟孤儿互斥持有者，3.21s 弹出孤儿专用文案并退出码 0；既有回归 `tests\verify_quit_v192.py` **11/11**、`tests\verify_ghost_v192.py` **20/20**（F1 版本判据改为「VERSION ≥ v1.9.2」语义比较，适配版本升级后不再硬编码旧版本串）。

### 4.8 设置与关于窗口（v1.8.5；v1.9.9 新增浏览器插件连接分区与卡片滚动；v1.9.10 局域网 IP 探测修正；v1.9.11 关于窗口内置赞助支持区；v1.9.12 设置窗口新增管理员分区）

- **按钮与样式**：主按钮矩阵（2×6，11 键）之外新增「设置」「关于」两个特殊样式按钮，位于
  矩阵下方第 7 行左/右两列（`grid(row=6, column=0/1)`，padx/pady 与矩阵一致）。样式明显区别于
  主按钮：白底 `BTN_SECONDARY_BG=#ffffff` + 蓝字 `BTN_SECONDARY_FG=#1971c2`（与主按钮蓝系协调）
  + 按压态浅蓝 `BTN_SECONDARY_ACTIVE_BG=#e7f5ff` + `relief="solid"` 描边
  （`highlightbackground=#1971c2`、`highlightthickness=1`），`activeforeground=#1971c2`、
  `disabledforeground=BTN_DISABLED_FG`。两按钮**不参与状态矩阵**，任何服务状态与 `_busy` 期间
  始终可用；矩阵布局与 `update_button_states` 主逻辑零改动。
- **设置窗口 `open_settings_dialog(parent, cfg, on_status=None)`**：`tk.Toplevel`，经
  `_centered_geometry` 相对主窗口居中（560×690），全中文、与主界面风格一致。
  **v1.9.9 布局变更**：卡片区由直接 `pack` 到窗口改为放入 `Canvas + 垂直 Scrollbar`
  （`inner` 框架 + `create_window` 随窗口宽度自适应 + `<Configure>` 同步 `scrollregion` +
  窗口级 `<MouseWheel>` 滚动），分区增多后窗口高度有限也能访问全部分区；卡片自身间距
  （`padx=16`、`pady=(14,4)/(4)`）、字号、配色保持不变；底部「保存设置」「取消」仍
  `pack(side="bottom")` 固定不滚动，关闭/保存逻辑零改动。包含：
  ① **退出记忆设置**——`quit_confirm_skip` 开关（Checkbutton「跳过退出确认（记住退出方式后退出不再询问）」，
  与 `quit_confirm_skip` 变量双向绑定）+ `quit_default_action` 单选（「退出程序（先停止服务再退出）」
  /「最小化到托盘」）+ 「一键恢复「每次退出都询问」」按钮（直接 `cfg["quit_confirm_skip"]=False`
  并写盘，状态栏提示）+ **自动恢复开关**（v1.9.8 Checkbutton
  「退出后下次启动自动恢复服务（退出时服务在运行则下次启动自动启动）」，绑定
  `auto_restore_service`，关闭时保存会同时把 `last_exit_service_running` 置 `false`）；
  ② **部署相关下载地址**——`vw_download_url`、`vw_webvault_download_url` 两个输入框可查看/编辑；
  ③ **浏览器插件连接（v1.9.9）**——见下方独立条目；
  ④ **管理员（v1.9.12）**——「获取令牌」只读 `.env` 的 `ADMIN_TOKEN` 并写剪贴板、「打开管理面板」，
  见下方独立条目；
  ⑤ **只读信息**——当前端口（`cfg["port"]`）与部署目录（`cfg["vaultwarden_dir"]`）只读展示；
  ⑥ 底部「保存设置」「取消」两按钮——保存时用 `config.save_config(cfg)` 完整写回 config.json
  （只更新本窗口涉及的字段，不破坏其他字段），成功后提示「设置已保存」；取消不写盘。
  调用方 `app.on_settings` 在窗口关闭后同步 `self.cfg`（重新 load_config）并刷新状态栏提示；
  **v1.9.9 起额外把 `self.set_msg` 作为 `on_status` 传入**，使设置窗口内的操作结果
  （如「复制地址」成功/失败）同步回显主窗口状态栏；不传 `on_status` 时仅在窗口内提示行显示，
  保持对旧调用方式兼容。
- **浏览器插件连接分区（v1.9.9）**：白色卡片 `card_ext`（`tk.Frame(inner, bg="#ffffff")`、
  `pack(fill="x", padx=16, pady=4)`）+ 标题「浏览器插件连接」（`("Microsoft YaHei UI", 11, "bold")`、
  `TEXT_PRIMARY`），分区位于「下载地址」与「只读信息」之间，控件如下：
  - **地址行（只读 Entry）**：两个 `tk.Entry(state="readonly", readonlybackground="#f8f9fa")`，
    行标签宽 15（「本机地址」/「局域网地址」），字号 9、`TEXT_SECONDARY`。
    地址**全部按 config 动态拼接，无任何硬编码端口**：
    `plugin_port = cfg.get("port") or DEFAULT_CONFIG.get("port")`，本机地址
    `f"{scheme}://localhost:{port}"`、局域网地址 `f"{scheme}://{ip}:{port}"`；`scheme` 由
    `cfg["domain"]` 是否以 `http://` 开头决定（默认 `https`）。局域网 IP 由
    `network.get_lan_ip_info()` 提供（v1.9.10 起），`win.after(60, _load_lan_ip)` 触发的
    `_load_lan_ip()` 在**后台 daemon 线程**执行探测（`ipconfig` 子进程不占用主线程），完成后
    `win.after(0, _apply_lan_info)` 回主线程回填地址，**打开窗口零卡顿**；无网卡/IP 时显示
    「未检测到局域网 IP（请检查网络连接）」并不抛异常；候选多于 1 个时提示行追加「另有 N 个
    可用地址，已选用首选」，单候选沿用原「已检测到局域网 IP：…」文案（探测策略见 §4.13）。
  - **「复制地址」按钮**：把当前选中地址写入系统剪贴板（`clipboard_clear` +
    `clipboard_append` + `update_idletasks`，窗口关闭后仍保留）；点击哪个地址行即选中哪个
    （`<Button-1>` / `<FocusIn>` 事件切换），检测到局域网 IP 后默认复制局域网地址
    （手机/其它电脑可用）；窗口内提示行与主状态栏同步提示「已复制地址：<url>」
    （成功绿 `#2b8a3e`，剪贴板不可用时红 `#c92a2a`）。
  - **「打开地址信任证书」按钮**：`webbrowser.open(选中地址)` 用默认浏览器打开该地址，
    并提示「若提示『您的连接不是私密连接』，请点『高级』→『继续前往』信任自签证书，
    之后扩展才能连接」——**未信任自签证书时浏览器扩展会报无法连接**，必须先访问信任一次。
  - **「获取扩展（Edge）」「获取扩展（Chrome）」按钮**：`webbrowser.open` 打开配置键
    `ext_edge_url` / `ext_chrome_url`，缺键时用 `DEFAULT_CONFIG` 默认值兜底（见 §5）。
  - **说明文字（两段）**：顶部（`font=("Microsoft YaHei UI", 9)`、`TEXT_HINT`、`wraplength=460`、
    `justify/anchor="w"`）——「安装 Bitwarden 浏览器扩展后，在扩展登录页点「设置」把
    「服务器地址」填成下面的地址，再用账号登录即可同步。」；底部（同款样式，字号 8）——
    「说明：地址需与服务端口一致；若扩展里曾填错服务器地址，请先到扩展设置页清除（或退出登录）
    后重新填写，否则会一直提示无法连接。服务未启动时地址无法访问，请先在主界面启动服务。」
  - **提示行**：`plugin_tip_var` 绑定的 `tk.Label`（字号 8、`TEXT_HINT`、`wraplength=460`），
    承载「已复制地址：…」「已检测到局域网 IP：…」「未检测到局域网 IP…」
    「已用默认浏览器打开…」等操作结果；`on_status` 可用时同步写主状态栏。
  - 四个操作按钮沿用次级按钮样式（白底 `#ffffff`、蓝字 `BTN_SECONDARY_FG`、
    `activebackground=BTN_SECONDARY_ACTIVE_BG`、`relief=tk.SOLID`、`bd=1`、
    `highlightthickness=1`、`cursor="hand2"`），分两行 `pack(side="left")`
    （复制 / 信任证书一行，Edge / Chrome 一行），字号、间距、配色与其它分区一致；
    新增控件不改动主窗口按钮矩阵与状态禁用逻辑。
- **管理员分区（v1.9.12，获取令牌）**：白色卡片 `card_admin`（`tk.Frame(inner, bg="#ffffff")`、
  `pack(fill="x", padx=16, pady=4)`）+ 标题「管理员」（`("Microsoft YaHei UI", 11, "bold")`、
  `TEXT_PRIMARY`），位于「浏览器插件连接」与「当前信息（只读）」之间（分区顺序：
  退出记忆 → 下载地址 → 浏览器插件连接 → **管理员** → 当前信息），在原有 Canvas + Scrollbar
  滚动区内，窗口 560×690 与滚动区域自适应，不破坏既有分区与按钮矩阵。控件自上而下：
  - **说明文字（字号 9、`TEXT_HINT`、`wraplength=460`、`justify/anchor="w"`）**：
    「进入 Vaultwarden 管理面板需使用部署目录 .env 中的管理员令牌（ADMIN_TOKEN）。点「获取令牌」
    会把令牌复制到系统剪贴板，粘贴到管理面板登录框即可。」
  - **打码状态区**：`admin_mask_var`（`tk.StringVar`，初值「令牌：尚未获取」）绑定的只读
    `tk.Label`（`#f8f9fa` 底、`TEXT_PRIMARY` 粗体、字号 9、`relief=tk.SOLID`、`bd=1`、
    `padx/pady=8/4`、`fill="x"`），成功时显示 `令牌：<前 4 位>********（<N> 位）`，
    失败时显示「令牌：未获取到」——**界面唯一展示令牌的位置，且永不完整回显**。
  - **按钮行**：「获取令牌」`get_admin_token` + 「打开管理面板」`open_admin_panel`，
    均为次级按钮样式 `ext_btn_cfg`（白底 `#ffffff`、蓝字 `BTN_SECONDARY_FG`、
    `activebackground=BTN_SECONDARY_ACTIVE_BG`、`relief=tk.SOLID`、`bd=1`、
    `highlightthickness=1`、`cursor="hand2"`），`pack(side="left")` 一行排列（间距 `padx=(8,0)`）。
  - **`get_admin_token()` 行为**：`info = service.read_admin_token(cfg)`（相对路径按 `APP_DIR`
    解析，不依赖 CWD，详见 §4.1）→ 成功时 `win.clipboard_clear()` + `clipboard_append(token)` +
    `win.update_idletasks()`（窗口关闭后剪贴板仍保留），`admin_mask_var` 仅写入 `masked` 打码串，
    提示行「已复制到剪贴板（<打码>）」，`on_status` 同步主状态栏（绿 `#2b8a3e`）；
    `tk.TclError`（剪贴板不可用）时提示「已读取令牌但复制失败：系统剪贴板不可用（<打码>）」；
    失败分支直接展示 `info["message"]` 中文提示（红 `#c92a2a`）：`.env` 不存在 →
    「未找到 .env 文件（<路径>），请先在主界面完成「一键部署」」；无 `ADMIN_TOKEN` 行或值为空 →
    「该配置未设置管理员令牌（.env 中没有 ADMIN_TOKEN 或值为空），可在主界面重新「一键部署」自动生成」；
    值为 `$argon2` 哈希 → 「该 ADMIN_TOKEN 是 argon2 哈希值，无法反解出原始令牌；请使用设置该哈希时
    对应的原始密码登录管理面板」；读取失败/权限不足 → 「读取 .env 失败：<原因>（请检查文件权限）」。
    `read_admin_token` 外再包一层 `try/except` 兜底（异常转「读取管理员令牌失败：<原因>」），
    **任何情况都不向 UI 线程抛异常，也不写任何日志**。
  - **`open_admin_panel()` 行为**：`admin_url` 与「浏览器插件连接」分区**同一套拼接逻辑**——
    `plugin_scheme` 由 `cfg["domain"]` 是否以 `http://` 开头决定，端口取
    `cfg.get("port") or DEFAULT_CONFIG.get("port")`，路径取 `admin_path`（缺省 `/admin`，
    缺前导 `/` 自动补齐），拼成 `<协议>://localhost:<port>/admin` 后 `webbrowser.open()`，
    提示「已用默认浏览器打开管理面板：<url>」；`webbrowser` 异常时提示「打开浏览器失败，
    请手动访问：<url>」，`on_status` 同步主状态栏。
  - **底部说明（字号 8、`TEXT_HINT`、`wraplength=460`）**：「说明：界面只显示打码信息（前 4 位 +
    长度），不会完整回显令牌；令牌仅写入剪贴板，不写入任何日志文件。若提示 argon2 哈希，说明 .env 里
    配置的是哈希值，只能用原始密码登录。」提示行 `admin_tip_var` 绑定的 `tk.Label` 承载上述操作结果。
  - **安全边界**：本分区**不调用 `logs.append_manager_log`**、不写 `manager.log`/`vaultwarden.log`，
    也不修改 `.env`（与 §4.1 的写入式 `ensure_admin_token` 严格分离），令牌仅在内存与系统剪贴板中出现。
- **关于窗口 `show_about_dialog(parent, cfg)`**：`tk.Toplevel` 居中展示软件名称
  （VaultwardenManager）、版本（取自 `ui.VERSION`，当前 v1.9.12）、作者/版权（杨爽工作室）、
  制作人（杨爽）、制作工具（Marvis）、简要说明（Vaultwarden 密码管理器的本机管理工具）、
  **赞助支持区**与「确定」按钮；
  **v1.8.6 移除「部署目录」（`cfg["vaultwarden_dir"]`）与「配置文件」（`config.CONFIG_PATH`）
  两行纯文本展示**，窗口尺寸由 460×360 调整为 460×300；**v1.8.7 新增「制作人：杨爽」
  与「制作工具：Marvis」两行展示**，窗口尺寸由 460×300 调整为 460×330；
  **v1.9.11 新增赞助支持区（详见 §4.9）**，窗口尺寸 460×330 → **460×560**，
  `win.update_idletasks()` 后按 `winfo_reqheight()` 取 `max(560, 需求高度)` 二次居中
  （内容多时不裁剪，尺寸不变时不做多余 `geometry` 调用），
  经 `_centered_geometry` 相对主窗口居中保持美观。
- **v1.9.11 关于窗口控件清单（自上而下）**：① 白卡片 `card`（`#ffffff`、`pack(fill="x", padx=16, pady=(16,4))`）内：
  软件名 `("Microsoft YaHei UI", 15, "bold")` + `#1971c2`；「版本：…」「作者 / 版权：杨爽工作室」
  「制作人：杨爽」「制作工具：Marvis」四行（字号 10、`TEXT_SECONDARY`）；两行功能说明
  （字号 9、`TEXT_HINT`、`wraplength=400`、居中）；② 赞助区浅灰卡片 `sp_card`（`#e9ecef`、
  `padx/pady=6`、`pack(fill="x", padx=16, pady=(0,4))`）——标题「赞助支持」、三段文案、二维码、
  扫码提示行；③ 底部「确定」按钮（`BTN_BG` 蓝底白字、`width=10`、`cursor="hand2"`），
  `pack(pady=(8,16))`。窗口 `resizable(False, False)` + `transient(parent)` + `grab_set()`，
  `WM_DELETE_WINDOW` 绑 `win.destroy`，末尾 `parent.wait_window(win)`。

### 4.9 赞助支持区（v1.9.0 主窗口卡片；v1.9.11 迁入关于窗口）

- **当前位置（v1.9.11 起）**：赞助信息**只在关于窗口内展示**，主窗口与设置窗口均不再有赞助分区。
  关于窗口内 `sp_card` 为浅灰卡片（`C_SP_CARD=#e9ecef`、`padx/pady=6`、`pack(fill="x", padx=16,
  pady=(0,4))`），位于白色信息卡片与底部「确定」按钮之间，自上而下依次为：
  标题「赞助支持」→ 三段赞助文案 → 收款二维码 → 扫码提示行；460×560 窗口内完整可见，
  不滚动、不裁剪、不挤压「确定」按钮。
- **文案与配色**：`vwm/ui.py` 模块级常量 `SPONSOR_TITLE="赞助支持"`、`SPONSOR_TEXT`（原三段文案：
  「一元不嫌少，十元不嫌多。/无论金额多少，都是对本软件项目的认可。/赞助属于自愿行为，
  不购买任何功能、不享有售后服务，仅表达您的一份善意。」）、`SPONSOR_QR_HINT="手机扫码即可 ·
  点击二维码可用系统看图器放大"`；配色常量 `C_SP_CARD="#e9ecef"`、`C_SP_TITLE`/`C_SP_TEXT`/
  `C_SP_HINT` 分别复用 `TEXT_PRIMARY`/`TEXT_SECONDARY`/`TEXT_HINT`（与本项目蓝白配色一致）。
  标题 `("Microsoft YaHei UI", 10, "bold")`；正文 `("Microsoft YaHei UI", 8)`、`justify/anchor
  ="center"`、`wraplength=400` 自动换行；提示行 8 号 `C_SP_HINT` 居中。
- **二维码资源**：`assets\sponsor_qr.png`（250×250 RGBA，34664 字节），**随包分发**
  （PyInstaller `--add-data "assets;assets"`），**v1.9.11 起不再写死绝对路径**
  （v1.9.6 的 `SPONSOR_QR_PATH` 常量与 `_attach_sponsor_qr` 方法已从 `vwm/app.py` 移除）。
  - **路径解析 `_sponsor_qr_file()`（三通道）**：① `sys._MEIPASS/assets/sponsor_qr.png`
    （单文件 exe 解包目录）→ ② exe 同级 `assets/sponsor_qr.png`（便于外部替换图片）→
    ③ 项目根 `assets/sponsor_qr.png`（源码直接运行）；全部缺失返回空串。
  - **加载 `_load_sponsor_qr(max_w=SPONSOR_QR_MAX_W)`（双通道）**：① 首选 Pillow
    `Image.open` + `convert("RGBA")` + `Image.LANCZOS` **等比缩放**（最长边 ≤`max_w`）+
    `ImageTk.PhotoImage` 上屏（LANCZOS 保证二维码边缘清晰可扫）；② Pillow / ImageTk 不可用
    时退回 `tk.PhotoImage(file=path)` + `subsample(factor)` 整数降采样（`factor =
    ceil(最长边 / max_w)`）；两通道均失败返回 `(None, path, 原因)`，**不抛异常**。
  - **宽度自适应 `_sponsor_qr_max_w(container)`**：取容器 `winfo_width() - 60px`（左右留白），
    夹在 `[SPONSOR_QR_MIN_W=96, SPONSOR_QR_MAX_W=150]` 区间；窗口未完成布局（宽度 ≤1）时
    退化为 150，避免出现 1px 图或超大图；当前 460 宽窗口下实际显示 150×150。
  - **交互**：二维码 `tk.Label(image=..., cursor="hand2")` 绑定 `<Button-1>` → `os.startfile(path)`
    交系统看图器放大（异常静默吞掉，不影响窗口）；提示行文案说明该行为。
  - **防 GC 空白**：图片对象与路径分别挂到窗口对象 `win._sponsor_qr_photo` /
    `win._sponsor_qr_path`（不再挂在主窗口 `self` 上）。
  - **容错（不崩不塌）**：图片缺失 / 内容损坏 / 两通道均失败时，二维码位置改显示
    「二维码暂不可用\n（请检查 assets/sponsor_qr.png）」占位（9 号 `C_SP_HINT`、
    `width=18`、`height=3`），**不弹窗、不抛异常**，卡片布局不塌陷，提示行照常展示。
- **主窗口变化（v1.9.11）**：`vwm/app.py` 删除 `_build_ui` 中 `sponsor` 容器（left 网格 row7
  的赞助卡片代码块）、`_attach_sponsor_qr(self, parent)` 方法、顶部 `SPONSOR_QR_PATH` /
  `SPONSOR_QR_MAX_W` 常量与 `__init__` 中 `self._sponsor_qr_photo = None`；主窗口
  `minsize` 由 `860×690` **回收为 `860×640`**（默认 `960×700`、`geometry("960x700")` 不变），
  按钮矩阵（row0-5）、设置/关于（row6）、退出（row5 columnspan2）与状态栏布局零改动。
- **设置窗口核对**：设置窗口自 v1.8.5 起即未包含赞助分区（赞助区一直在主窗口 left 网格），
  v1.9.11 复核确认四个分区（退出记忆 / 下载地址 / 浏览器插件连接 / 只读信息）无任何赞助残留
  控件与文案；`vwm/config.py` 无赞助专用配置键，旧 `config.json` 无需迁移、不报错。
- **验证（v1.9.11）**：`tests\verify_about_sponsor_v1911.py` **59/59 PASS**——A 常量与二维码资源
  （存在性/尺寸/深色像素）、B 加载缩放与容错自适应（缺图/坏图/宽度夹取）、C 源码断言
  （主窗口已无赞助卡片、设置窗口无残留）、D 真机关于窗口（弹出、二维码控件已映射、
  像素非空白）、E 真机主窗口（13 键矩阵完好、无浅灰赞助卡片、版本号 v1.9.11）、
  F 真机设置窗口（四分区正常、无赞助控件）；`tests\verify_tray_smoke_v1911.py` **13/13 PASS**
  （托盘真实创建、菜单结构、退出清理、无残留线程）。
- **历史沿革**：v1.9.0 主窗口 left 网格 `row7 columnspan=2` 浅灰赞助卡片（标题 9 号粗体 +
  三段文案 8 号、`wraplength=172`，纯展示不响应点击）；v1.9.6 卡片内新增收款二维码
  （写死绝对路径 `E:\yscl\shuage-coin-helper\website\ewm\ewmsk.png`、`minsize` 640→690）；
  v1.9.11 整体迁入关于窗口、二维码改用 `assets` 随包资源、主窗口 `minsize` 回收为 640。


### 4.10 图标资源与加载（v1.9.7）

**设计**：按参考设计图统一为「盾牌安全」风格——主体为蓝色盾牌（扁平 + 微渐变，主色 `#2196F3`，
下缘渐深至 `#1565C0`），盾内有粗描边钥匙孔符号，盾顶有银蓝小挂锁，整体深色/浅色背景下均可辨识。
图标由 `temp\make_icon_v197.py`（Pillow 程序化绘制）生成，**不做位图缩放凑尺寸**：≤32px 走
「近满画布盾牌 + 加粗钥匙孔」简化形态（去挂锁/去描边细节），避免小尺寸细节糊成一团；
≥48px 用完整形态（白底板 + 钥匙/点阵 + 挂锁）。

**资源清单**（全部落 `E:\yscl\vaultwarden-manager\assets\`，无中文路径）：

| 文件 | 尺寸 | 用途 |
|---|---|---|
| `app.ico` | 16/24/32/48/64/128/256 多尺寸 | exe 文件图标（PyInstaller `--icon`）+ 窗口图标 |
| `app_16.png` / `app_24.png` / `app_32.png` / `app_48.png` / `app_64.png` / `app_128.png` | 对应尺寸 | 小尺寸/界面/文档复用 |
| `app.png`、`app_256.png` | 256×256 | 主图标（高清） |
| `tray.png` | 64×64 RGBA 透明底 | 系统托盘图标（pystray） |

**加载方式**：`app._asset_path(name)` 统一解析资源路径——依次尝试
① `sys._MEIPASS`（PyInstaller 单文件解包目录，打包后首选）
② exe 同级目录 `assets\`（免打包绿色分发时使用）
③ 项目根目录 `assets\`（源码运行）；
返回首个存在文件的绝对路径，全部不存在返回 `None`。调用方**必须容错**：

1. **exe 文件图标**：打包参数 `--icon=assets\app.ico`（见 §6），运行时无需处理。
2. **主窗口图标**：`_apply_window_icon()` 双通道——先 `iconbitmap(ico_path)`（`default=` 同时作用于
   后续 Toplevel/弹窗），失败再 `iconphoto(True, PhotoImage(file=png))`（Pillow 通道）；
   **注**：tk 的 `wm_iconbitmap()` 查询在部分 Windows 版本返回空串（图标挂在窗口类而非实例），
   验证应改用 Win32 `GetClassLongPtrW(hwnd, GCLP_HICON)` 取真实 HICON 像素。
3. **系统托盘图标**：`_create_tray_icon()` 优先读 `tray.png`（RGBA 透明底），读取失败**回退**到
   v1.6.6 的 Pillow 代码绘制 64×64 蓝底白 V 图标；`_hwnd`、`_resend_taskbar_created()`
   （TaskbarCreated 重注册）、`_nim_delete_icon(id(icon))` 等 v1.9.2 ghost 清理机制**完全不改**。
4. **容错红线**：任一图标加载失败**不得抛异常、不得弹窗、不得影响主流程**——窗口图标失败则跳过
   （窗口用系统默认图标），托盘图标失败则回退代码绘制；仅在 `manager.log` 记一条
   `append_manager_log(cfg, "图标", ...)` 警告。

**验证**：`tests\verify_icon_v197.py` **44/44 全绿**——I1 资源清单（10 个文件存在、非空、PNG/ICO 尺寸正确）、
I2 ICO 多尺寸（含 256）、I3 `_asset_path` 三档兜底与不存在的返回 `None`、I4 源码接线
（`_apply_window_icon` 调用点、`tray.png` 优先、回退分支存在）、I5 ghost 机制保留
（`_hwnd`/`_nim_delete_icon`/`_resend_taskbar_created` 均在）、I6 真机窗口图标像素校验
（Win32 取 HICON，白底 + 蓝盾占比判定为新图标）。

### 4.11 端口占用自动切换（v1.9.8）

**目标**：避免「一键部署」「启动服务」因配置端口被其它程序占用而启动失败，改为自动改用可用随机端口后继续。

- **探测函数（`vwm/network.py` 新增）**
  - `is_port_in_use(port)`：**连接 + 绑定双判定**——先尝试 `connect_ex`（能连上说明已有监听者），再尝试本地绑定（绑定失败多为 TIME_WAIT / 已占用），任一命中即判占用，避免单一路径误判。
  - `is_port_bindable(port)`：纯绑定校验（用于挑选端口时快速验证可用性）。
  - `pick_free_port(min_port=20000, max_port=65000, tries=30)`：在高位区间随机挑端口并校验可绑定，最多重试 30 次；仍失败返回 `None`。
- **切换封装（`vwm/service.py` 新增）**
  - `PORT_FALLBACK_MIN/MAX`（20000/65000）为随机端口区间常量。
  - `_own_service_holds_port(cfg)`：**排除自身已运行的 vaultwarden 实例占用端口的正常情况**——若占用者正是本工具管理的服务进程，则不视为冲突、不切换（防止把正常运行的服务误判为端口被占）。
  - `_apply_port_change(cfg, new_port)`：一次性落盘 `config.json` 的 `port` 与 `domain`（`https://localhost:<新端口>`），并同步部署目录 `.env` 的 `ROCKET_PORT` / `DOMAIN` / `ROCKET_TLS`；返回同步说明文本。
  - `ensure_port_available(cfg) -> (ok, msg, switched)`：三态返回。端口空闲 → `(True, "", False)`，**不弹任何多余提示**；被他人占用 → 自动挑选随机端口、落盘、刷新界面地址，返回 `(True, "端口 X 被占用，已自动切换到 Y…", True)`；极端情况（挑不到可用端口）返回 `(False, 中文原因, False)`。
- **接线**
  - 一键部署：`vwm/deploy.py` 的 `deploy_service` 在**动作开始前**调用 `ensure_port_available`，切换说明并入成功消息末尾（部署结果回调亦刷新部署状态与界面地址）。
  - 启动服务：`vwm/app.py` 的 `on_start` 改为**先 `ensure_port_available` 再 `start_service`**，切换提示与启动结果合并展示。
  - **不漂移红线**：单次启动流程内至多切换一次端口；切换后仍启动失败时给出中文错误（沿用既有 `start_service` 失败文案）。
  - 切换后 `cfg["domain"]` 已更新，故状态栏地址、「复制地址」`on_copy_addr`、「打开 Web」`on_web`/`on_admin`（经 `resolve_web_url`）**自动跟随新端口**，无需额外改动。
  - 既有「修改端口」按钮逻辑、证书信任主机名（`resolve_web_url` / 证书 CN）不受影响。

### 4.12 服务运行状态记忆与自动恢复（v1.9.8）

**目标**：退出程序前服务是运行状态时，下次启动程序自动把服务拉起来，减少手动点击。

- **持久化字段**（`vwm/config.py` 默认值，旧配置自动补齐）：`last_exit_service_running`（默认 `false`）、`auto_restore_service`（默认 `true`）。
- **退出记录（`vwm/app.py`）**
  - 新增 `_record_exit_state(running)`：写内存 `cfg` 并 `save_config` 落盘。
  - `_quit_app` 的 worker 中**先记录再停服务**（顺序不可颠倒）：`find_vw_processes` 判定当前是否有服务在跑 → `_record_exit_state(True/False)` → `stop_service`。**v1.8.4「退出前先停服务」行为完整保留**。
  - `_on_stop_result`：停止失败但用户仍选择退出时，同样标记 `True`（下次启动仍会尝试恢复）。
  - 用户主动点「停止服务」后再退出，因退出时进程已不存在，自然记录 `false`。
- **启动恢复（`_maybe_auto_restore`）**
  - 时机：`__init__` 末尾 `after(1200)` 调度（等界面就绪后执行），不阻塞启动。
  - 判定链：`auto_restore_service` 开启 **且** `last_exit_service_running` 为真 **且** `get_deploy_state(cfg) == "deployed"` **且** 当前未在运行 → 才执行自动启动；启动前同样过 `ensure_port_available`，走既有 `start_service`，忙碌提示「正在自动恢复服务（上次退出时服务在运行）…」，成功后写 `append_manager_log(cfg, "自动恢复", ...)`。
  - 清标志规则：启动成功、已在运行、未部署（提示「已跳过自动启动」）、开关关闭 —— 均清除标志，**避免重复自动启动**；仅**启动失败时保留标志**（下次再试，并留中文失败日志）。
  - 与用户手动操作互斥：`run_task` 后台线程 + 按钮态刷新复用既有机制，不额外加锁。
- **设置开关（`vwm/ui.py`）**：设置对话框新增勾选项「退出后下次启动自动恢复服务」（绑定 `cfg["auto_restore_service"]`，默认勾选）；保存时写回开关，**取消勾选时立即清除 `last_exit_service_running`**，此后不再自动启动。窗口 `minsize` 由 540 调至 590 容纳新控件。

### 4.13 局域网 IP 探测策略（v1.9.10）

**背景（P1 缺陷）**：v1.9.9 及以前 `network.get_lan_ips()` 只做「UDP 出口地址 + 主机名解析」两路收集
后按字典序 `sorted()`，真机得到 `['192.0.2.1', '198.51.100.10']`，**192.0.2.1（Hyper-V Default Switch
虚拟网卡）** 因字典序靠前被当作局域网地址显示在设置窗口「浏览器插件连接」，手机/其它电脑根本连不上
（该网段仅在 Hyper-V 内部可达）。

**v1.9.10 探测链路（`vwm/network.py`）**：

1. **真实出口地址优先**——`_udp_outbound_ips()` 依次对 `8.8.8.8:80` / `114.114.114.114:80` /
   `223.5.5.5:80` 建 `SOCK_DGRAM connect`（**不实际发包**，仅由系统选路）取 `getsockname()[0]`，
   得到即默认路由出口地址；与之相同的候选额外 +60 分。
2. **网卡枚举**——`_parse_ipconfig()` 解析 `ipconfig` 输出（`CREATE_NO_WINDOW` 子进程、8 秒超时、
   `mbcs`→`utf-8`→`gbk` 逐级解码，中英文系统通用）：顶格行为适配器标题、缩进行为字段，提取网卡名、
   描述、IPv4、默认网关；网关字段跨行时（IPv6 网关在前、IPv4 网关续行）由续行规则补齐。
3. **虚拟网卡过滤**（`_virtual_reason`）
   - **硬排除**（名称/描述命中任一关键词）：`virtualbox`、`vmware`、`vmnet`、`wsl`、`docker`、
     `loopback`、`npcap`、`tap-windows`、`tap adapter`、`openvpn`、`wireguard`、`tailscale`、
     `zerotier`、`teredo`、`bluetooth`（含「Bluetooth 网络连接」）、`vpn`、`pseudo`、`wan miniport`、
     `wi-fi direct`。
   - **软判定**（`hyper-v` / `vethernet` / `虚拟` / `virtual ethernet`）：**仅在没有默认网关时排除**；
     有默认网关则保留为候选并 **−25 分**。原因：Hyper-V「外部虚拟交换机」是桥接物理网卡的交换机，
     其 IPv4 往往就是本机真实局域网地址（**本机唯一可用地址 198.51.100.10 正位于
     `vEthernet (外部虚拟交换机)`**），按关键词一刀切会把唯一正确地址也过滤掉；而 `Default Switch`、
     `内部虚拟交换机`、WSL/Docker 适配器均无默认网关，仍会被可靠排除。
   - **地址层硬排除**：`127.*`（回环）、`169.254.*`（APIPA，未取到 DHCP 的自动私有地址）。
4. **排序打分**（`_ip_rank` + 加权）：私网段 `192.168.x`（+30）> `10.x`（+20）> `172.16–31.x`（+10）
   > `100.64/10`（+5）> 其它（0）；**有默认网关 +100**；与 UDP 出口地址一致 +60；
   Hyper-V/vEthernet 桥接 −25；同分按 IP 稳定排序。
5. **多候选全量返回**——`get_lan_ip_info(refresh=False)` 返回 `primary`（首选）、`candidates`
   （全部非虚拟候选，已排序）、`details`（候选的网卡名/描述/网关/评分/是否桥接）、`excluded`
   （被排除地址 + 中文原因）、`udp_probe`（UDP 原始探测值）、`source`（`udp` / `adapter` / `none`）、
   `cached`。`get_lan_ips(refresh=False)` **保持原签名与语义**（返回 `candidates` 列表，供
   `cert.py` 证书 SAN 使用），新参数均有默认值，既有调用零改动。
6. **缓存与不阻塞界面**——结果写入模块级 `_LAN_CACHE`（TTL 30 秒，`refresh=True` 强制刷新）；
   设置窗口 `_load_lan_ip()` 改为后台 daemon 线程探测 + `win.after(0, _apply_lan_info)` 回主线程
   回填（窗口已销毁则静默放弃），主线程不再执行 `ipconfig`。
7. **界面展示**——局域网地址行显示首选地址；提示行在候选 >1 时追加「另有 N 个可用地址，已选用首选」，
   单候选沿用「已检测到局域网 IP：…」，无候选显示「未检测到局域网 IP（请检查网络连接）」，均不抛异常。

**真机实测（2026-11-09，DESKTOP-IHABM60）**：

- 选中：`198.51.100.10`（`vEthernet (外部虚拟交换机)`，默认网关 `198.51.100.1`，评分 165，与 UDP 出口一致）；
- 排除：`192.0.2.1`（`vEthernet (Default Switch)`，无默认网关）、`169.254.10.20`
  （`vEthernet (内部虚拟交换机)`，APIPA）；
- 单次探测 0.043 s（含 `ipconfig` 子进程），缓存命中 0.0000 s。

## 5. 配置说明

配置文件 `config.json` 位于程序所在目录（开发模式为脚本目录，打包后为 exe 目录）。
**程序启动时若文件缺失或损坏，会自动重建默认配置**，不会报错。
**v1.5.0 起默认部署目录动态化**：vaultwarden_dir / ssl_dir / backup_dir 的默认值随程序运行目录生成
（`<程序目录>\vaultwarden` 及其子目录）；若读取到旧固定路径配置，启动时自动迁移（见 §4.1）。

| 字段 | 默认值 | 说明 |
|---|---|---|
| vaultwarden_dir | `<程序目录>\vaultwarden` | Vaultwarden 部署目录（含 exe 与 .env；v1.5.0 起随运行目录） |
| exe_name | `vaultwarden.exe` | 服务主程序名 |
| port | `44444` | 服务端口（**v1.8.2 起为唯一权威配置源**：默认字面量仅存在于 `build_default_config` 一处，运行时全链路动态读取，禁止在 UI/URL 拼接/探测/部署逻辑中写死；与 .env ROCKET_PORT/DOMAIN 一致，「修改端口」与启动前 `ensure_env_runtime` 会同步更新 .env） |
| ssl_dir | `E:\yscl\vaultwarden\ssl` | 证书目录 |
| cert_file / key_file | `cert.pem` / `key.pem` | 证书/私钥文件名 |
| backup_dir | `<程序目录>\vaultwarden\backup` | 备份根目录 |
| log_file / err_log_file | `vaultwarden.log` / `vaultwarden.err.log` | 日志文件名（位于部署目录） |
| log_lines | `300` | 日志区显示尾部行数 |
| log_max_mb | `10` | 日志轮转阈值（MB）；查看日志/启动服务/写 manager.log 时超过该值自动归档为 `.1`（已存在后缀递增）并新建空日志 |
| log_noise_keywords | `["tls handshake", "HSTS"]` | 日志噪音过滤关键词列表（v1.6.0）；日志区按此过滤噪音行（大小写不敏感），可追加自定义关键词 |
| vw_download_url | `https://github.com/nextyancc/Vaultwarden-Windows-Binary/releases/download/1.37.5-windows/vaultwarden-1.37.5-windows-x64.exe` | 核心文件 `vaultwarden.exe` 缺失时的自动下载地址（v1.6.4 起内置官方 Windows 二进制下载链接，新用户无需手动填写即可一键部署；为空则一键部署明确提示中止；**已有 config.json 时保留用户已填值，仅新建配置使用默认值**） |
| vw_download_timeout | `120` | 自动下载超时（秒） |
| vw_webvault_download_url | `https://github.com/dani-garcia/bw_web_builds/releases/download/v2026.10.1/bw_web_v2026.10.1.tar.gz` | Web Vault 网页版 `.tar.gz` 自动下载地址（v1.6.5；部署目录缺 `web-vault/index.html` 时一键部署自动下载；为空则跳过网页版安装，服务仍正常启动；**已有 config.json 时保留用户已填值，缺失字段自动补齐默认值**） |
| vw_webvault_download_timeout | `180` | 网页版自动下载超时（秒） |
| status_check_ms | `3000` | 状态轮询间隔（毫秒） |
| cert_days | `3650` | 证书有效期（天） |
| domain | `https://localhost:44444` | Web Vault 地址（「复制地址」复制此值；「修改端口」后同步更新为 `https://localhost:<新端口>`；v1.8.2 起默认值由 port 派生，不再独立写死端口） |
| admin_path | `/admin` | 管理面板路径 |
| quit_confirm_skip | `false` | v1.8.3：是否跳过退出确认——确认框勾选「记住我的选择，下次不再询问」后置 `true`，此后退出直接执行记忆动作不再弹框；旧 config 缺省为 `false`（仍弹框询问）；改回 `false` 或按住 Shift 退出可恢复询问 |
| quit_default_action | `tray` | v1.8.3：记忆的退出动作——`tray`=最小化到托盘 / `quit`=退出程序；仅在 `quit_confirm_skip=true` 时生效 |
| last_exit_service_running | `false` | v1.9.8：退出时服务是否在运行的状态记忆。仅当退出前服务在跑（`_quit_app` / 停止失败仍退出）时置 `true`；用户先手动停服再退出则为 `false`；旧配置缺省自动补齐为 `false` |
| auto_restore_service | `true` | v1.9.8：下次启动是否自动恢复服务的开关（设置对话框「退出后下次启动自动恢复服务」）。`true` 且 `last_exit_service_running=true` 且已部署、当前未运行 → 启动后自动拉起服务；置 `false` 时不再自动启动并清除记忆标志 |
| ext_edge_url | `https://microsoftedge.microsoft.com/addons/search/bitwarden` | v1.9.9：设置窗口「浏览器插件连接」分区「获取扩展（Edge）」按钮打开的地址（`webbrowser.open`）；旧 config 缺键时由 `load_config` 自动补齐，界面读取时另有 `DEFAULT_CONFIG` 兜底，缺失不会报错 |
| ext_chrome_url | `https://chromewebstore.google.com/search/bitwarden` | v1.9.9：同上，「获取扩展（Chrome）」按钮打开的地址；旧 config 缺键自动补齐默认值 |

## 6. PyInstaller 打包方法

在项目目录执行（**v1.9.10 起以此命令为准，`--exclude-module` 列表必须带全**）：

```powershell
cd E:\yscl\vaultwarden-manager
pip install pyinstaller cryptography
python -m PyInstaller -F -w --noconfirm --clean --icon=assets\app.ico --add-data "assets;assets" --exclude-module numpy --exclude-module numpy.libs --exclude-module yaml --exclude-module bcrypt --exclude-module scipy --exclude-module pandas --exclude-module matplotlib --exclude-module PyQt5 --exclude-module PySide6 --name VaultwardenManager vaultwarden_manager.py
```

- `-F`（=`--onefile`）：打包为单文件；`-w`（=`--noconsole`）：GUI 程序不弹控制台窗口；
  `--clean`：清 PyInstaller 缓存，避免旧 TOC 夹带已排除模块。
- **v1.9.10 起体积瘦身（必须带这段 excludes）**：`--exclude-module numpy numpy.libs yaml bcrypt
  scipy pandas matplotlib PyQt5 PySide6`。这些模块**项目代码零引用**（`requirements.txt` 仅
  `cryptography` / `pystray` / `pillow`），此前由 site-packages 环境的 PyInstaller hook 连带收集：
  `numpy.libs\libscipy_openblas64_*.dll` 单文件 19.47 MB，连带 `numpy` 2.17 MB / `numpy.libs` 6.31 MB /
  `PIL._avif` 之外的 yaml 0.11 MB、bcrypt 0.13 MB 等。加 excludes 后**exe 由 35,610,012 字节（33.96 MB）
  降至 23,527,895 字节（22.44 MB），减少 12,082,117 字节（−33.9%）**，归档条目 1072 → 1025。
- **必须保留的依赖（勿加 excludes）**：`cryptography`（备份加密 `cryptography.fernet` + 证书生成，
  归档内 3.37 MB）、`pystray`（托盘，PYZ 内 13 个模块）、`PIL`（托盘/二维码/截图，归档内 6.41 MB）、
  `tkinter`（GUI）。加 excludes 后每次构建**必须做功能回归**（见下方清单），任一项失败即去掉 excludes 重建。
- **构建日志与临时产物**：日志重定向到项目根之外（会话中间产物目录）的 `build_<ver>_<时间戳>.log`，
  构建完成后删除项目根的 `build\` 与 `VaultwardenManager.spec`，不污染项目根。
- **v1.9.7 起必须带 `--icon=assets\app.ico`**（exe 文件图标，多尺寸 ICO，含 256px）与
  `--add-data "assets;assets"`（把图标资源打进单文件，运行时经 `sys._MEIPASS\assets\` 读取）。
  漏掉 `--add-data` 时窗口/托盘图标会因找不到资源而回退（窗口用系统默认图标、托盘回退代码绘制），
  **不报错但不符合统一图标要求**。
- **v1.8.0 起入口仍为 `vaultwarden_manager.py`**（薄转发壳 `from vwm.app import main`），
  PyInstaller 会从该 import 自动递归收集 `vwm` 包全部模块，无需额外 `--hidden-import`。
- 产物：`dist\VaultwardenManager.exe`。
- 若打包后报 cryptography 缺失，追加参数：`--collect-all cryptography`。
- **部署注意（v1.5.0 便携化）**：exe 放哪，`vaultwarden` 就部署到哪——首次运行在 exe 所在目录
  自动创建 `config.json`，部署目录默认即 `<exe 目录>\vaultwarden`。若 exe 目录下的 config.json 仍指向
  旧固定路径（如 `E:\yscl\vaultwarden`），启动时会自动迁移：备份 config → 复制旧部署目录内容到新目录
  → 更新 config 指向新目录（旧目录保留，确认无误后可手动删除）；如需切换部署位置，修改 config.json 的
  `vaultwarden_dir` / `ssl_dir` / `backup_dir` 三个字段即可。
- **打包后功能回归清单（v1.9.10 起每次构建必做，任一失败即回退不含 excludes 的构建）**：
  1. **启动两次**：分别 `Start-Process dist\VaultwardenManager.exe`（工作目录设为 `dist`），
     每次主窗口「Vaultwarden 管理工具」在 30 s 内出现（onefile 解包，实测 4.1–4.2 s），2 s 后仍存活；
  2. **主窗口**：976×739，按钮矩阵完整，状态栏与日志区渲染正常；
  3. **设置窗口**：真实点击「设置」（客户端坐标约 (58,350)），Toplevel「设置」576×729 弹出；
     「退出记忆设置 / 部署相关下载地址 / 浏览器插件连接 / 当前信息（只读）」四个分区随滚动逐帧渲染正常，
     「浏览器插件连接」显示 `https://localhost:<port>` 与 `https://<首选局域网IP>:<port>`，无文字重叠/错位/缺字；
  4. **备份加密/解密**：在**临时目录**构造假 `data`，调用 `backup.encrypt_backup` → `decrypt_and_restore`
     往返成功、正文明文一致、内容还原、错误密码被拒、弱密码被拒（不动真实部署数据）；
  5. **托盘**：`pystray.Icon` 对象可生成、`assets\tray.png` 可加载（64×64 RGBA），exe 启动后
     `HKCU\Control Panel\NotifyIconSettings` 有本程序通知区条目；
  6. **归档审计**：`PYZ` 内 `cryptography`/`pystray`/`PIL`/`vwm`/`tkinter` 均在，`numpy`/`yaml`/`bcrypt`/
     `scipy`/`pandas`/`matplotlib`/`PyQt5`/`PySide6` 均为 0；`assets\` 12 个文件全部在归档内；
  7. **进程清理**：`taskkill /F /T /IM VaultwardenManager.exe` 后 `tasklist` 零残留。
- 路径红线：项目与部署目录均须为**无中文路径**（当前满足：`E:\yscl\...`）。

## 7. 修改规范（强制约定）

1. **修改代码前，必须先阅读本手册**，掌握目录结构、模块职责与红线（尤其 §4.1 启动
   工作目录、§5 配置自动创建机制）。
2. **修改完成后，必须更新本手册**：
   - 若功能新增/变更/删除 → 同步更新 §1 功能表、§2 目录结构、§4 核心模块说明；
   - 若配置字段变更 → 同步更新 §5 配置表；
   - 若打包方式变更 → 同步更新 §6；
   - **每次修改（无论大小）必须在 §8 版本记录追加一条**：日期、版本、修改人、变更摘要。
3. 版本号规则：功能新增 +0.1（如 1.0.0 → 1.1.0）；修复缺陷 +0.0.1（如 1.0.0 → 1.0.1）；
   重大重构/不兼容变更 +1.0（如 1.0.0 → 2.0.0）。
4. 本项目的三条红线，改动时不得破坏：
   - 启动服务 `cwd` 必须为部署目录（保证 .env 生效）；
   - 项目路径不得出现中文（打包与运行兼容）；
   - 配置文件缺失时程序必须自动创建默认值，不得抛异常。
5. 修改涉及第三方依赖时，同步更新 `requirements.txt` 与 §3 依赖表。

## 8. 版本记录

| 版本 | 日期 | 修改人 | 变更摘要 |
|---|---|---|---|
| v1.0.0 | 2026-11-02 | Marvis file-agent | 初始版本：创建工具（启动/停止/证书/信任/状态/打开链接/日志/备份）+ 本手册 |
| v1.1.0 | 2026-11-02 | Marvis file-agent | 新增「加密备份」（zip+Fernet .enc）、「导入备份」（解密恢复，data 先改名 data_bak_ 防误操作，含 zip-slip 防护）、「复制IP」；按钮矩阵扩为 2×6；更新 §1/§2/§3/§4/§5 说明并重新打包 |
| v1.2.0 | 2026-11-02 | Marvis file-agent | 「复制IP」改为「复制地址」（复制 config 的 domain，状态栏显示完整地址）；新增「修改端口」（弹窗校验 1-65535，同步更新 config.json 的 port/domain 与 .env 的 ROCKET_PORT，保留原内容/换行风格，提示需重启服务生效）；按钮矩阵保持 2×6；更新 §1/§4/§5 并重新打包 |
| v1.3.0 | 2026-11-03 | Marvis file-agent | 新增「一键部署」（服务未运行则启动并轮询等待端口开放，15 秒超时，部署成功后按钮置灰，已运行则提示无需重复部署）；新增 `update_button_states()` 按钮状态矩阵，按服务运行/停止状态自动禁用/启用「一键部署/启动/停止/Web Vault/管理面板」，与 `_busy` 忙碌状态协调（操作中全部功能按钮临时禁用、退出保持可用）；按钮矩阵扩为 2×7，窗口加大至 980×880；更新 §1/§4/§6 并重新打包 |
| v1.4.0 | 2026-11-03 | Marvis file-agent | 日志加固 + 一键部署自动下载：新增日志轮转（查看日志或启动服务时超过 `log_max_mb` 默认 10MB 自动归档 `vaultwarden.log.1`/递增后缀并新建空日志，读取失败给中文提示）；「一键部署」核心文件缺失时按 `vw_download_url` 用标准库 urllib 后台下载（进度百分比+大小，校验 >1MB，失败清理半成品并明确提示），URL 为空则提示填地址中止；config 新增 `log_max_mb` / `vw_download_url` / `vw_download_timeout`（自动补默认字段）；更新 §1/§4/§5 并重新打包 |
| v1.5.0 | 2026-11-03 | Marvis file-agent | 部署目录便携化：DEFAULT_CONFIG 改为运行时生成（`build_default_config()`），`vaultwarden_dir` 默认 = APP_DIR/vaultwarden、`ssl_dir` = APP_DIR/vaultwarden/ssl、`backup_dir` = APP_DIR/vaultwarden/backup（APP_DIR = 程序运行目录），config 缺失时按新默认创建；`load_config` 新增旧固定路径自动迁移（`_migrate_legacy_paths`：备份旧 config 为 config.json.bak-<时间戳> → 旧部署目录存在且新目录无数据时用 copytree 复制旧目录内容到新目录、旧目录保留 → 更新 config 指向新路径并写回；复制期间状态栏提示「正在迁移部署目录...」，完成后提示迁移结果；新目录已有数据不重复迁移），GUI 启动时在状态栏显示迁移提示；更新 §1/§2/§4/§5/§6 并重新打包 |
| v1.6.0 | 2026-11-03 | Marvis file-agent | 日志加固（噪音过滤）+ 日志落地（操作日志）：config 新增 `log_noise_keywords`（默认 `["tls handshake", "HSTS"]`，自动补默认字段）；新增 `filter_noise_lines()`，`read_log_tail` 改为支持 `filter_noise` 参数并返回 `(内容, 被过滤行数)`，日志区过滤噪音行且顶部提示「（已过滤 N 行噪音日志）」；新增「原始日志」按钮切换查看未过滤原始内容（按钮文案切换为「过滤日志」，切换状态显示在状态栏），过滤不影响 vaultwarden.log 原始落盘；新增 `append_manager_log()` 把每次按钮操作（一键部署/启动/停止/生成证书/添加系统信任/复制地址/一键备份/加密备份/导入备份/修改端口）落盘到部署目录 `manager.log`（格式 `[时间戳][操作名] 结果摘要`，复用 `rotate_log_if_needed` 按 `log_max_mb` 轮转，写入失败不影响主流程仅在状态栏提示）；按钮矩阵扩为 2×7 填满（12 功能 + 日志切换 + 退出）；更新 §1/§2/§4/§5 并重新打包 |
| v1.6.1 | 2026-11-03 | Marvis file-agent | 修复启动崩溃（AttributeError: '_tkinter.tkapp' object has no attribute '_raw_log'）：`__init__` 中 `_build_ui()` 之后、首次 `refresh_log()` 之前初始化 `self._raw_log = False`（默认过滤模式，与 UI 一致）；`refresh_log` 内部改读 `getattr(self, "_raw_log", False)` 兜底，防止未来初始化顺序问题再次触发；核对「原始日志/过滤日志」切换逻辑（`on_toggle_raw` 更新 `_raw_log` → 改按钮文案 → 刷新日志区 → 状态栏提示）无需改动；mock tkinter 冒烟测试通过后重新打包 |
| v1.6.2 | 2026-11-03 | Marvis file-agent | 「一键备份」与「加密备份」合并为「一键加密备份」：删除原非加密完整备份入口（按钮 `("backup", "一键备份")`、回调 `on_backup`、函数 `backup_data`），统一由 `on_enc_backup` → `encrypt_backup(cfg, password)` 承担全部备份（选密码 → data 全量 zip 打包 → Fernet 加密 .enc，具备完整可恢复能力，配合「导入备份」解密恢复）；按钮矩阵由 14 个减为 13 个，「退出工具」占最后一行整行（columnspan=2）填满 2×7；`update_button_states` 为通用遍历无需改动；config 的 `backup_dir` 等备份字段保持不变；同步更新 §1/§4 说明并重新打包 |
| v1.6.3 | 2026-11-03 | Marvis file-agent | 「一键部署」增加进度条显示：新增 `from tkinter import ttk`；`_build_ui` 底部消息栏上方新增部署进度区（隐藏的 `_progress_frame`：13 号粗体中文提示文字 `progress_label` + 加高 `ttk.Progressbar`（style `Deploy.Horizontal.TProgressbar`，thickness=22））；`deploy_service` 新增 `stage_cb` 参数，下载/校验完成后、调用 `start_service` 前触发 `stage_cb("deploy")`；`on_deploy` 重写为四阶段：①点击即 `_show_deploy_progress()` 展开进度区复位；②下载阶段由工作线程回调 `progress_cb(downloaded, total)`，经 `after(0)` 切主线程 `_set_progress_determinate` 显示百分比，`total=0`（无 Content-Length）退化为 `_set_progress_indeterminate` 不定进度并显示"部署中…"；③`stage_cb("deploy")` 触发后切换不定进度并启动主线程 `after(1000)` 轮询 `_deploy_poll_tick`，`_busy` 期间每秒刷新「正在部署/启动服务… 部署中…（已等待 N 秒）」；④`done` 回调 `_finish_deploy_progress()` 取消轮询、停止动画、进度条复位 determinate=0、隐藏进度区，结果由消息栏展示；全程工作线程不触碰 tkinter 控件，所有 UI 更新经 `after(0)`/`after(1000)` 回主线程，界面不冻结；部署期间沿用 `set_busy` 保持按钮不可点；mock tkinter 冒烟测试（进度区构建/状态切换/stage 顺序/复位）全部通过后重新打包 |
| v1.6.5 | 2026-11-03 | Marvis file-agent | 「一键部署」集成 Web Vault 网页版自动安装（不新增按钮）：`deploy_service` 在核心文件就绪后、启动服务前检测部署目录 `web-vault/index.html`，缺失时按新增配置字段 `vw_webvault_download_url`（默认 `https://github.com/dani-garcia/bw_web_builds/releases/download/v2026.10.1/bw_web_v2026.10.1.tar.gz`）与 `vw_webvault_download_timeout`（默认 180）下载官方 `.tar.gz` 到部署目录 `web-vault.tar.gz`，再用新增 `extract_webvault_tarball()` 解压（标准库 tarfile；含 `web-vault/` 顶层目录则解到部署根并保留前缀、其他根条目跳过，散文件则解到 `web-vault/`；每个成员路径净化 + 绝对路径校验拒绝 `../` 穿越；目录成员跳过；校验 `web-vault/index.html` 存在才算成功）；下载/解压失败或 URL 为空均**不阻塞启动**，部署结果消息附加「网页版未安装，服务已启动（仅 API 可用）」；进度条复用：新增 `stage_cb("webvault")` 阶段，提示文字切换「正在下载网页版…」，下载回调复用 `progress_cb` 有 Content-Length 显示百分比、否则不定进度，解压期间不定进度，解压完成后才 `stage_cb("deploy")` 进入启动轮询；`build_default_config()` 增补两个新字段，`load_config` 的 merged 机制保证已有 config 用户值保留、缺失字段自动补齐；同步更新本机 `config.json` 增补两字段；更新 §1/§4/§5 并重新打包 |
| v1.6.6 | 2026-11-03 | Marvis file-agent | 新增**系统托盘**与**关闭确认**：点击主窗口右上角 X 或「退出工具」不再直接退出，改为弹出全中文模态确认框 `ask_quit_or_tray`（600×320，红「退出程序」/蓝「最小化到托盘」，按钮 14 号粗体宽 12 高 2；关闭对话框=取消）；托盘方案采用 **pystray**（0.19.5，`Icon.run_detached()` 免手动线程，旧版回退 daemon 线程）+ **Pillow** 代码绘制 64×64 蓝底白 V 图标（无额外图片文件），tooltip「Vaultwarden 管家」，单击/双击恢复主窗口，右键菜单含「显示主窗口」「退出程序」；`__init__` 绑定 `WM_DELETE_WINDOW` → `on_close_request()`，`on_exit` 改调同一入口保持一致；托盘回调在独立线程经 `after(0)` 回主线程操作 tkinter（与 `run_task` 同模式）；`_minimize_to_tray` 用 `withdraw()` 隐藏、`_show_from_tray` 用 `deiconify()+lift()+focus_force()` 恢复；真正退出 `_quit_app()` 先 `icon.stop()` 清理托盘再 `destroy()`，不残留僵尸图标；依赖缺失/创建失败时 `_tray_active=False` 降级为关闭直接退出并提示；新增依赖 pystray/Pillow（requirements.txt 同步）；更新 §1/§3/§4.7/§8 并重新打包 |
| v1.6.7 | 2026-11-03 | Marvis file-agent | **界面视觉回归常规桌面**：移除「适合脚操作」特化——按钮尺寸回归常规（主按钮矩阵 10 号粗体、10 字符宽 × 1 行高、RAISED 细边框，间距收紧 padx/pady 4；退出确认框 `ask_quit_or_tray` 缩为 440×230、标题 13 号、副文案 9 号、按钮 10 号粗体宽 10 高 1；主窗口默认 960×700、最小 860×640；顶部状态标签 14 号粗体、副标签 9 号；日志区标题 10 号粗体、日志字体 Consolas 9、刷新按钮 9 号；消息栏 10 号；部署进度提示 11 号粗体、进度条 thickness=16 常规厚度）；配色统一（#f0f2f5 主背景、白色日志头、深色日志区、红/蓝/青按钮色不变）；全部功能、托盘、日志、备份、部署逻辑零改动；同步更新 §1/§4.5/§4.7 描述并重新打包 |
| v1.6.8 | 2026-11-03 | Marvis file-agent | **退出确认框相对主窗口居中弹出**：新增 `_centered_geometry(parent, w, h)` 纯函数计算 geometry 字符串——优先用主窗口 `winfo_x/y/width/height`（先 `update_idletasks()` 取准确几何）计算相对主窗口正中间的 `440x230+x+y` 坐标，`x/y` 截断保护取非负；主窗口几何不可用（已最小化/隐藏时 width/height 为 1、或查询抛 `TclError`）时退化为屏幕居中，屏幕信息再异常则兜底 1920×1080 计算；`ask_quit_or_tray` 创建确认框时 `dlg.geometry("440x230")` 改为 `dlg.geometry(_centered_geometry(parent, 440, 230))`，尺寸、标题、按钮、文字、功能全部保持不变；mock tkinter 冒烟测试（几何可用居中/左移截断/最小化退化/几何异常退化/屏幕异常兜底/调用接线/尺寸不变）全部通过后重新打包；同步更新 §4.7 描述并重新打包 |
| v1.6.9 | 2026-11-03 | Marvis file-agent | **修复「打开 Web Vault」「打开管理面板」点击无效 + 打开地址动态化**：根因为 `update_button_states()` 按钮状态矩阵逻辑写反——服务运行中（running/abnormal）误将两个打开按钮 `DISABLED`，服务正常运行时按钮置灰、点击无响应；修复为运行中启用「打开 Web Vault/打开管理面板」+「停止服务」、禁用「一键部署/启动服务」，停止时反向（部署/启动可用、打开按钮禁用）。URL 来源同步改为动态拼接：新增 `resolve_web_url(cfg)` 纯函数按 `cfg['port']` 运行时生成 `https://localhost:<port>`，`on_web` 打开该地址、`on_admin` 打开该地址 + `cfg['admin_path']`（默认 `/admin`），不再写死 8000、不依赖可能与实际端口不同步的 `cfg['domain']`；`webbrowser.open` 抛异常时状态栏提示「打开浏览器失败：<原因>」替代静默失败；界面按钮文案与全中文不变。排查佐证：本机实际服务（PID 21476）监听 127.0.0.1:8000，与 cfg['port']=8000 一致，domain 未漂移，故 URL 本身正确、点击无效确系按钮被禁用所致；另发现 E:\yscl\vaultwarden-manager\vaultwarden\.env 的 ROCKET_PORT=44444 与 config 的 port=8000 不一致（配置漂移风险），修复后打开地址一律跟随 cfg['port']，不再受该漂移影响。mock tkinter 冒烟测试（resolve_web_url 拼接 8000/44444/str、admin 拼接、running/abnormal/stopped/unknown/busy 五态按钮矩阵、回调异常保护、成功路径 URL 断言）26 项全部通过后重新打包；同步更新 §1/§4.5 并重新打包 |
| v1.7.0 | 2026-11-03 | Marvis file-agent | **修复「打开 Web」浏览器报网络链接错误（HTTP/HTTPS 协议错配）+ 按钮文案溢出 + 端口漂移根治**：① 问题2根因：服务实际以 **HTTP** 运行（部署目录 .env 无 `ROCKET_TLS`，v1.6.9 起 `resolve_web_url` 固定拼 `https://`），浏览器对纯 HTTP 端口发起 TLS 握手必然失败报网络链接错误；且 config/.env 端口漂移时 URL 端口可能偏离实际监听。修复：新增 `get_listen_port(exe_name)`（tasklist+netstat 解析 `vaultwarden.exe` 实际监听端口，排序去重）与 `detect_scheme(host, port)`（TLS 握手探测 https/http），`resolve_web_url` 升级为先取实际监听端口（漂移时以实际为准）、再探测实际协议（无 TLS 时拼 `http://`），服务未运行回退 `https://localhost:<cfg['port']>`；`on_web`/`on_admin` 打开地址随之修正。② 「修改端口」原已同步 .env ROCKET_PORT，v1.7.0 补同步 **DOMAIN**（避免改端口后 .env 仍指向旧域名端口）；新增 `ensure_env_runtime(cfg)`，`start_service` 启动前自动同步 .env 关键项（有证书时写 ROCKET_TLS/ROCKET_ADDRESS/ROCKET_PORT/DOMAIN 使 HTTPS 生效、无证书仅同步 ROCKET_PORT/DOMAIN；保留注释、值不变不写盘、幂等）。③ 问题1：按钮矩阵部分中文文案过长（如「一键加密备份」「添加系统信任」）10 字符宽显示溢出，v1.7.0 精简为「加密备份」「添加信任」「打开 Web」「打开面板」（其余不变），真实 tkinter 测量 text 61px < 按钮需求宽 88px，全部无溢出。验证：隔离 mock 冒烟（get_listen_port 解析=8000、resolve_web_url=http://localhost:8000 与实际监听一致、停止回退、update_port 同步 ROCKET_PORT+DOMAIN 且保留注释、ensure_env_runtime 有/无证书两场景+幂等、13 按钮宽度测量）全部通过；同步更新 §1/§4/§5/§8 并重新打包 |
| v1.7.1 | 2026-11-03 | Marvis file-agent | **端口统一与漂移加固（v1.7.1）**：config.json（dev 与 dist）port/domain 统一为 44444（`port=44444`、`domain=https://localhost:44444`），部署目录 .env 的 ROCKET_PORT 保持 44444、DOMAIN 同步修正为 https://localhost:44444，三者与实际监听（HTTPS 44444）一致；`build_default_config()` 默认端口 8000 → 44444（防全新部署新建配置漂移回 8000）；`ensure_env_runtime` 增强：同步时记录 .env ROCKET_PORT 旧值，若与 config 不一致，提示追加「端口不一致已统一：ROCKET_PORT <旧值> → <新值>」（原「修改端口」同步 ROCKET_PORT+DOMAIN、启动前 ensure_env_runtime 以 config 为准统一 .env 且不触碰 ADMIN_TOKEN 等键的链路保持不变）；新增 verify_v171.py 冒烟验证 27 项全部通过；同步更新 §1/§4/§5/§8 并重新打包 |
| v1.7.2 | 2026-11-03 | Marvis file-agent | **「生成证书」「添加信任」合并入「一键部署」**：`deploy_service` 在核心文件与网页版处理就绪后、启动服务前新增两段自动链路——① 证书：检查 `ssl_dir/cert_file`+`key_file` 是否都存在，缺失任一则调用 `generate_certificate(cfg)` 自动生成（无证书才生成、已有则跳过不重复生成），失败不阻塞启动；② 信任：调用 `add_system_trust(cfg)` 自动添加系统信任（沿用 `certutil -addstore -user Root` 现有实现），失败不阻塞启动；部署结果消息按实际状态附加「已自动生成自签名证书 / 证书已存在，跳过生成 / 警告：证书生成失败（原因）」「已自动添加系统信任 / 警告：添加系统信任失败（原因）」，证书缺失时跳过信任并提示；`stage_cb` 新增 `"cert"`/`"trust"` 两阶段，进度提示依次为「正在生成证书…」「正在添加系统信任…」（已有证书时 cert 阶段不触发）；移除按钮矩阵 `("cert","生成证书")`、`("trust","添加信任")` 两项与 `on_cert`/`on_trust` 回调（按钮矩阵 2×7 缩为 2×6：9 功能按钮 + 原始日志切换 + 退出，共 11 个，退出按钮改占第 6 行整行）；`update_button_states` 注释同步去掉两按钮；部署/启动/停止等其余按钮、`ensure_env_runtime` 端口链路、备份导入、托盘全部不变；新增 verify_v172.py 冒烟验证 27 项（无证书自动生成+信任触发、有证书跳过生成、信任失败不阻塞、证书失败不阻塞且跳过信任、按钮无残留引用、2×6 布局）全部通过；同步更新 §1 功能表（删除两功能行并重编号、一键部署行增 v1.7.2 说明、操作日志落盘操作列表去两按钮）/§4.1/§4.2/§4.3/§4.5/§8 并重新打包 |
| v1.7.3 | 2026-11-03 | Marvis file-agent | **统一所有按钮背景色（NORMAL 态完全一致）**：源码新增统一按钮配色常量 `BTN_BG=#1971c2`（协调蓝，白字）/`BTN_BG_ACTIVE=#1864ab`（按压态深蓝）；此前功能按钮矩阵 11 个按钮各带独立色（一键部署 #099268、启动 #2f9e44、停止 #d64545、打开 Web #f08c00、打开面板 #e8590c、加密备份 #9c36b5、导入备份 #d6336c、修改端口 #f59f00、复制地址 #339af0、原始日志 #5c7cfa、退出 #868e96），「刷新日志」浅灰 #dee2e6，退出确认框红 #d64545/蓝 #1971c2，密码弹窗确定 #1971c2、端口弹窗确定 #f59f00，且各弹窗「取消」未设 bg——现全部统一为 `BTN_BG`；改动点：① 主按钮矩阵 rows 颜色字段全部改为 `BTN_BG`，创建处 `activebackground` 改 `BTN_BG_ACTIVE`；② 「刷新日志」按钮 bg/fg/activebackground 统一；③ 退出确认框「退出程序」「最小化到托盘」两按钮统一；④ 密码/端口弹窗「确定」「取消」4 按钮统一（取消补 fg 白字）；状态文本/消息栏指示色（绿/橙/红/蓝）不受影响保留；新增 verify_v173.py 冒烟验证 10 项（AST 静态：常量值、8 处按钮创建处均带 bg、所有 bg/activebackground 一致、矩阵 rows 颜色全统一、按钮创建处无残留旧色值）全部通过；同步更新 §4.5/§4.7/§8 并重新打包 |
| v1.7.4 | 2026-11-03 | Marvis file-agent | **修复界面灰色看不清问题（提高文字与元素对比度）**：新增文字配色常量 `TEXT_PRIMARY=#212529`（主文字/状态标题/消息栏，白底对比 >12:1）/`TEXT_SECONDARY=#343a40`（次级/状态副标签，>7:1）/`TEXT_HINT=#495057`（提示文字，浅底 >5:1）/`BTN_DISABLED_FG=#495057`（按钮禁用态文字）；排查并修复 9 处低对比元素——① 顶部状态标题 `status_label` fg `#868e96`→`TEXT_PRIMARY`；② 状态副标签 `status_sub` fg `#868e96`→`TEXT_SECONDARY`；③ 退出确认框提示文字 fg `#868e96`→`TEXT_HINT`；④ 消息栏 `msg_label` fg `#495057`→`TEXT_PRIMARY`；⑤ `set_msg` 默认色 `#495057`→`TEXT_PRIMARY`；⑥ 5 处「已取消…」取消类提示 `#868e96`→`TEXT_HINT`（加密备份/导入备份×2/恢复/修改端口）；⑦ 两处 `btn_cfg`（功能矩阵+退出确认框）新增 `disabledforeground=BTN_DISABLED_FG`，禁用态文字由系统浅灰改为深灰可读；⑧ 状态指示色加深：绿 `#2f9e44`→`#2b8a3e`、橙 `#f08c00`→`#d9480f`、红 `#d64545`→`#c92a2a`（含 check_status 三态与全部 set_msg 调用）；⑨ 上轮 v1.7.3 引入的浅灰排查：确认「刷新日志」浅灰已统一为蓝、矩阵按钮无残留浅灰，仅发现上述说明文字/取消提示仍浅灰，本轮一并修正；按钮 NORMAL 态保持统一 `BTN_BG=#1971c2` 白字（v1.7.3 红线不破坏）；日志区深底浅字（bg `#111418`/fg `#c9d1d9`）对比度本就充足、保留；新增 verify_v174.py 冒烟验证 20 项（AST 静态：6 个配色常量、所有 Label/Button 的 fg 无低对比浅灰、源码无 `#868e96` 实际使用、关键控件抽查、按钮禁用文字配置、全部按钮 bg 仍统一、所有 set_msg 颜色无低对比、状态三色加深、模拟渲染 fg 集合）全部通过；同步更新 §4.5/§8 并重新打包 |
| v1.7.5 | 2026-11-03 | Marvis file-agent | **按钮标题（文字）颜色统一高对比修复（v1.7.5）**：逐项排查全部 18 个按钮标题 fg 与 disabledforeground——功能矩阵 11 个、刷新日志、退出确认框 2 个、密码/端口弹窗确定取消 4 个；修复：① 禁用态文字常量 `BTN_DISABLED_FG` 由 `#495057` 加深为 `#212529`（最深灰，与典型禁用灰底 #e9ecef 对比度 13.01:1，禁用时标题清晰可读）；② 密码/端口弹窗 4 按钮与刷新日志按钮补齐 `activeforeground="white"` 与 `disabledforeground=BTN_DISABLED_FG`（此前缺省，按压/禁用时标题可能继承系统灰）；③ 全部按钮 NORMAL 态 `fg="white"`、按压态 `activeforeground="white"`、禁用态 `disabledforeground=BTN_DISABLED_FG`，背景保持统一蓝 `BTN_BG=#1971c2`/`BTN_BG_ACTIVE=#1864ab`（v1.7.3 红线不破坏）；验证：新增 verify_v175.py AST 静态验证 9 项全 PASS（常量值、8 处按钮创建调用、矩阵 11 按钮 rows 颜色全 BTN_BG、所有按钮 fg/activeforeground=white 且 bg/activebackground 统一、全部按钮显式 disabledforeground、无灰色系 fg 字面量残留、禁用文字对比度 13.01:1、NORMAL 白字对比度 5.02:1）；同步更新 §4.5/§8 并重新打包 |
| v1.7.6 | 2026-11-03 | Marvis file-agent | **修复新环境部署后管理面板必现 ADMIN_TOKEN 未配置 + 进程检测加固**：① 新增 `ensure_admin_token(cfg)`——部署/启动链路检测部署目录 `.env` 的 `ADMIN_TOKEN` 缺失或为空时，用 `secrets.token_urlsafe(32)` 自动生成强随机值写入（保留其他行/注释/换行风格，已有非空值不覆盖，幂等；`.env` 不可读写返回 `(None, False)` 不阻塞启动）；`start_service` 与 `deploy_service` 启动前均调用，新生成时启动/部署成功消息附加「已自动生成 ADMIN_TOKEN，管理面板 https://localhost:<port>/admin 登录口令：<token>（请妥善保存，用于登录管理面板）」（部署成功消息格式「管理面板 https://localhost:<port>/admin 登录口令（ADMIN_TOKEN）：<token>，请妥善保存」）；② `is_process_running` 增加 `deploy_dir` 参数（默认空串=按进程名兼容）：经 `Win32_Process` 取 `ExecutablePath`/`CommandLine`，仅路径属于部署目录才视为本服务运行中；新增 `find_vw_processes`/`_in_deploy_dir`/`get_foreign_process_tip` 辅助函数；`start_service` 检测到非部署目录同名实例（如 dist 残留）时拦截并提示「请先在任务管理器中结束该实例，再点击启动」，不自动杀进程；`get_service_status` 状态栏对非部署目录同名实例橙色提示（状态码保持 stopped，按钮矩阵不变）；③ 验证：verify_v176.py AST+运行时隔离冒烟 37 项全 PASS（缺失生成/已有不覆盖/空值原位替换/幂等/注释保留/路径正反例/dist 不冒充/foreign 提示/状态集成）；开发过程踩坑：并行编辑同一文件竞态丢失两处修改（deploy_service 的 ensure_admin_token 调用、get_service_status 路径校验），已串行补齐；`ensure_admin_token` 空值替换因 `\s*` 贪婪吃掉行尾换行致 token 落到下一行，改为先剥离行尾换行再替换；同步更新 §1/§4.1/§8 并重新打包 |
| v1.8.0 | 2026-11-03 | Marvis file-agent | **模块式重构（单文件 → vwm 包，功能与界面零回归）**：将 v1.7.6 单文件 `vaultwarden_manager.py`（约 1854 行）按职责拆分为 `vwm` 包——`common`（共享常量/工具）、`config`（配置读写/默认值/旧路径迁移/update_port）、`logs`（轮转/读取/操作日志落盘）、`network`（resolve_web_url/get_listen_port/detect_scheme/get_lan_ips）、`service`（启停/状态/ensure_admin_token/ensure_env_runtime/进程路径感知）、`cert`（证书生成/系统信任）、`deploy`（一键部署全链路/download_file/extract_webvault_tarball）、`backup`（加密备份/恢复/zip-slip 防护）、`ui`（弹窗与 UI 配色常量）、`app`（GUI 主程序 VaultwardenManagerApp/main）；入口 `vaultwarden_manager.py` 改为薄转发壳 `from vwm.app import main`；`__init__.py` 提供 `CRYPTO_OK` 可选依赖探测，cert/backup 仅在可用时导入 cryptography 符号；模块导入关系单向无环（各模块仅依赖 common 与编号更小的兄弟模块）。**行为零改动**：按钮矩阵 2×6（11 按钮）、托盘 pystray+Pillow、确认框相对主窗口居中、resolve_web_url 动态端口/协议、证书信任并入部署、ADMIN_TOKEN 自动生成、进程真实路径校验、日志轮转/噪音过滤、备份加密恢复、config 便携化迁移全部保留。修复切块遗漏 import：`config.py` 补 `re`（update_port 用）、`cert.py`/`backup.py` 补 cryptography 条件导入。验证：py_compile 12 文件 OK；AST 全模块未定义全局名扫描（排除函数内局部变量）无真实遗漏；stub-tkinter + 真实 cryptography 冒烟 7 组全 PASS（GUI 实例化+按钮矩阵 11+行为、ensure_admin_token 首次生成+幂等+保留注释、resolve_web_url 返回 https://localhost:44444、update_port 同步 config/.env、generate_certificate 真实生成 cert.pem/key.pem、备份加密→解密恢复往返、模块职责断言+无循环导入）；更新 §1/§2/§4.0（新增模块结构总览与导入关系）/§6/§8 并重新打包 |
| v1.8.1 | 2026-11-03 | Marvis file-agent | **修复「停止服务」无法停止（含非部署目录残留实例）+ foreign 独立状态码**：根因——v1.7.6 路径感知让 `get_service_status` 在检测到非部署目录同名实例（dist exe 视角下 E:\yscl\vaultwarden-manager\vaultwarden\vaultwarden.exe）时返回 `"stopped"`，`update_button_states` 对 stopped 态禁用「停止服务」按钮；同时 `start_service` 又拦截启动提示先停止实例，形成「启动被拦 + 停止按钮禁用」死锁，用户只能手动到任务管理器结束。修复：① `get_service_status` foreign 场景返回独立状态码 `"foreign"`（橙色提示不变）；② `app.update_button_states` 将 `"foreign"` 纳入运行侧（running/abnormal/foreign）——启用「停止服务」/「打开 Web」/「打开面板」、禁用「一键部署」/「启动服务」，用户可直接点击停止清理残留；③ `stop_service` 增强可靠停止：改按 `find_vw_processes`（Win32_Process）精确 PID 逐个 `taskkill /PID /T /F`，不再依赖 tasklist 名称匹配、不受部署目录过滤影响（**含非部署目录残留实例一并停**），终止后轮询最多 6 秒验证进程全部退出，取不到 PID 时回退 `taskkill /IM /T /F` 兜底，无进程提示「未检测到运行中的服务」。验证：只读冒烟 verify_v181.py 全 PASS（AST 语法 + dist cfg→`foreign`、dev cfg→`running`、stop_service 无进程提示、app 矩阵含 foreign）；真机验证——实际实例 PID 24340（E:\yscl\vaultwarden-manager\vaultwarden\vaultwarden.exe）经新 stop_service 停止成功，`find_vw_processes` 无残留、端口 44444 不再监听；同步更新 §1 功能表/§4.1/§8 并重新打包 |
| v1.8.2 | 2026-11-03 | Marvis file-agent | **端口不写死、单一配置源动态读取（v1.8.2）**：全量扫描 vwm 包与入口/DEV.md/config/.env 硬编码端口——Python 源码端口字面量收敛至 `config.py` `build_default_config` 一处（`default_port=44444` 为唯一权威默认值，`domain` 改由 `f"https://localhost:{port}"` 派生，不再独立写死 44444）；运行时 URL 拼接/实际监听探测/部署/UI/复制地址/.env 同步全链路读取 `cfg['port']`（沿用 `resolve_web_url`/`get_listen_port`/`detect_scheme`/`ensure_env_runtime`/`update_port` 动态机制并确认无残留）；DEV.md §5 配置表 port 默认值 `8000` 纠错为 `44444`（v1.7.1 代码已改、文档漏改）；新增 verify_v182_port_dynamic.py 冒烟 26 项全 PASS（默认派生/已有 config 兼容/改 55555 全链路跟随/ensure_env_runtime 幂等/复原 44444/AST 审计无端口字面量）；同步更新 §1 管理目标/§4.6/§5/§8 并重新打包 |
| v1.8.3 | 2026-11-03 | Marvis file-agent | **退出确认改为「勾选框 + 持久化记忆」（退出不再询问）**：确认框 `ask_quit_or_tray` 新增勾选框「记住我的选择，下次不再询问」（Checkbutton，白底勾选块、弹窗同底色、手型光标；窗口 440×230 → 440×260 居中容纳）；返回结构由字符串改为 dict `{"action": "quit"/"tray"/None, "remember": bool}`（`action=None` 表示取消）；config.json 新增两字段 `quit_confirm_skip`（默认 `false`）与 `quit_default_action`（默认 `"tray"`），并入 `build_default_config` 默认值，`load_config` 的 merged 机制保证**旧 config 无字段自动补齐默认、仍弹窗询问**；新增 `config.save_config(cfg)`（完整写回 config.json，供运行时字段持久化）与 `config.apply_quit_memory(cfg, action)`/`config.clear_quit_memory(cfg)`（返回更新后 cfg + 中文提示，写盘失败提示不持久化但不抛异常）；`app.on_close_request` 记忆逻辑——`quit_confirm_skip=true` 且未按住 Shift → 不弹框直接按 `quit_default_action` 执行；弹框勾选 → `apply_quit_memory` 持久化 + 状态栏绿字提示「已记住退出方式为…下次退出不再询问」+ 写 manager.log；未勾选 → 仅本次生效不写盘；未勾选但原本已记忆 → `clear_quit_memory` 清除记忆恢复询问；**恢复询问入口**：按住 Shift 点关闭（X）/「退出工具」强制弹框（主窗口 `bind_all` 监听 `<KeyPress/KeyRelease-Shift_L/Shift_R>` 维护 `_shift_held`，勾选框默认不勾选、确认后未勾选即清除记忆），或直接改 config.json 的 `quit_confirm_skip=false`；托盘不可用降级直接退出、托盘/居中/按钮矩阵/配色全部不变；新增 verify_v183 冒烟 22 项全 PASS（默认字段/旧 config 兼容补齐/apply tray+quit 写盘/clear 恢复/决策矩阵 skip+Shift/勾选/未勾选/取消/ui 签名/三文件编译）；同步更新 §4.7/§5/§8 并重新打包 |
| v1.8.4 | 2026-11-03 | Marvis file-agent | **退出前先停止服务（所有「退出程序」路径统一）**：`app._quit_app()` 改造——检测到服务在运行则状态栏/日志提示「正在停止服务…」，复用 `service.stop_service`（v1.8.1 的精确 PID + 轮询确认）停止全部实例并轮询确认；停止失败（超时仍有残留）或异常时弹全中文确认框 `ui.ask_stop_failed_quit`（新增，440×250 居中，「仍退出」/「取消退出」两按钮，关闭弹窗=取消退出），**绝不静默放弃**；无服务在运行直接退出；任何取消退出分支保留主窗口与托盘图标不执行清理。覆盖全部退出路径：确认框选「退出程序」本次生效、记忆 `quit_default_action="quit"` 直接退出、Shift 强制询问后选退出、托盘菜单「退出程序」（托盘不可用降级直接退出）——均先进 `_quit_app` 先停后退；「最小化到托盘」路径（确认框选托盘 / 记忆 tray / Shift 恢复）不停止服务。确认框 `ask_quit_or_tray` 副文案更新为「退出程序将先停止 Vaultwarden 服务再退出；最小化到托盘不会停止服务，可从系统托盘图标恢复窗口。」；v1.8.3 勾选持久化、Shift 恢复询问、按钮矩阵、托盘/配色全部不变。新增 verify_v184 冒烟 39 项全 PASS（运行+停止成功先提示再退出/无服务直接退出/停止失败仍退出/停止失败取消退出保留窗口托盘/stop_service 异常兜底取消/记忆 quit 直接退出先停后退/记忆 tray 不停止/确认框 quit 先停后退/确认框 tray 不停止/ui 文案与接线源码断言/四文件编译）；真实环境导入校验 OK（find_vw_processes/ask_stop_failed_quit 可用、当前无服务时 stop_service 返回未检测到）；同步更新 §4.7/§5/§8 并重新打包 |
| v1.8.5 | 2026-11-03 | Marvis file-agent | **新增「设置」「关于」按钮（特殊样式）+ 退出记忆可视化配置与下载地址编辑**：主按钮矩阵（2×6，11 键）之外新增「设置」「关于」两个特殊样式按钮——白底 `BTN_SECONDARY_BG=#ffffff` + 蓝字 `BTN_SECONDARY_FG=#1971c2`（与主按钮 #1971c2 蓝系协调）+ 按压态浅蓝 `BTN_SECONDARY_ACTIVE_BG=#e7f5ff` + `relief="solid"` 描边（`highlightbackground=#1971c2`），位于矩阵下方第 7 行左/右两列（grid row6 col0/col1），**不参与状态矩阵**（任何服务状态 running/abnormal/foreign/stopped 与 _busy 忙碌期间均可用），主按钮矩阵布局与状态矩阵逻辑零改动；「设置」窗口 `ui.open_settings_dialog(parent, cfg)`（相对主窗口居中、全中文、主风格一致）——退出记忆区（`quit_confirm_skip` 跳过确认开关 + `quit_default_action` 默认动作 托盘/退出 单选 + 一键恢复「每次退出都询问」按钮直接置 skip=false 并写盘）、下载地址区（`vw_download_url` / `vw_webvault_download_url` 可查看/编辑）、只读展示当前端口与部署目录；保存经 `config.save_config` 完整写回（只更新本窗口字段、不破坏其他字段），取消不写盘；「关于」窗口 `ui.show_about_dialog(parent, cfg)` 展示软件名 VaultwardenManager、版本 v1.8.5、作者/版权 杨爽工作室、部署目录、配置文件路径、简要说明；app.py 新增 `on_settings`（保存后重新 load_config 同步 self.cfg + 状态栏提示）/`on_about` 回调，ui.py 顶部新增 `from .config import CONFIG_PATH, save_config`（ui 依赖 config，仍单向无环）；新增 verify_v185 冒烟 47 项全 PASS（三文件编译/ui VERSION 与次级样式常量/两窗口函数存在/保存走 save_config/一键恢复清 skip/app 按钮接线+import/按钮总数 13+主按钮键完整/设置关于白底蓝字描边+row6 位置/退出按钮仍 row5 columnspan2/主按钮仍蓝底白字/状态矩阵 running·busy 设置关于常开+主按钮零回归/设置窗口开关·单选·2 输入框·保存写盘字段一致·其他字段未破坏·一键恢复写盘·取消不写盘/关于窗口五项信息）；同步更新 §1 功能表（16 设置/17 关于）/§2/§4.0（ui 依赖 config）/§4.5/§4.8（新增）/§8 并重新打包 |
| v1.8.6 | 2026-11-03 | Marvis file-agent | **关于窗口精简（移除「部署目录」「配置文件」两行展示）**：`vwm/ui.py` `show_about_dialog` 删除「部署目录」（`cfg["vaultwarden_dir"]`）与「配置文件」（`config.CONFIG_PATH`）两行 `tk.Label` 纯文本展示，保留软件名称 VaultwardenManager、版本 v1.8.6、作者/版权（杨爽工作室）、简要说明与「确定」按钮；窗口尺寸 `_centered_geometry(parent, 460, 360)` → `460×300`，仍相对主窗口居中保持美观；函数 docstring 同步更新为 v1.8.6 说明；其余窗口（设置窗口、退出确认框、按钮矩阵、状态矩阵）零改动；新增 verify_v186 冒烟 25 项全 PASS（三文件编译/关于函数源码无两行 Label/保留软件名·版本·作者·说明·确定按钮/窗口尺寸 460x300/app 设置·关于接线与主按钮矩阵零回归/关于窗口 stub 实例化无两行文字且其余项齐全/设置窗口退出记忆·下载地址·只读信息·保存取消按钮零回归）；同步更新 §1 功能表（17 关于）/§4.8/§8 并重新打包 |
| v1.8.7 | 2026-11-03 | Marvis file-agent | **关于窗口新增「制作人」「制作工具」两行**：`vwm/ui.py` `show_about_dialog` 在作者/版权行后新增两行 `tk.Label` 纯文本展示——「制作人：杨爽」「制作工具：Marvis」（与作者/版权行同字号同配色），保留软件名称 VaultwardenManager、版本 v1.8.7、作者/版权（杨爽工作室）、简要说明与「确定」按钮；`VERSION` 常量 v1.8.5 → v1.8.7；窗口尺寸 `_centered_geometry(parent, 460, 300)` → `460×330` 容纳新增两行，仍相对主窗口居中保持美观；函数 docstring 同步更新为 v1.8.7 说明；其余窗口（设置窗口、退出确认框、按钮矩阵、状态矩阵）零改动；冒烟验证通过（py_compile/import/关于窗口 stub 实例化含两行文字且其余项齐全/窗口尺寸 460x330/VERSION=v1.8.7）；同步更新 §1 功能表（17 关于）/§4.8/§8 并重新打包 |
| v1.8.8 | 2026-11-03 | Marvis file-agent | **「加密备份」「导入备份」全面安全加固（备份安全设计）**：`vwm/backup.py` 备份格式升级 `v2`（`BACKUP_MAGIC=b"VWMBK2\n"` + 元数据 JSON：source/tool_version/created_at/zip_sha256/pbkdf2_iterations/salt），密钥派生由 SHA-256(password) 直派升级为 **PBKDF2-HMAC-SHA256（600,000 次迭代 + 16 字节随机盐）**（`derive_fernet_key`，旧 `derive_legacy_key` 保留作 v1 兼容）；新增 `validate_password_strength`（长度 ≥8 且含字母与数字，弱密码中文拦截「密码过弱：至少 8 位且需同时包含字母和数字」）；**完整性/防篡改**：元数据 `zip_sha256` 与解密后 zip 字节 SHA-256 比对 + `ZipFile.testzip()` 全条目 CRC 校验，篡改/损坏明确提示「备份文件完整性校验失败：内容已被修改或文件损坏」；**zip-slip 复核强化**：`_check_zip_safety` 拒绝绝对路径（含盘符/Windows 绝对路径）/`..` 穿越/空段穿越/符号链接条目（修复目录条目尾部斜杠误拒，标准目录条目放行）；**防压缩炸弹**：条目数 ≤50000、解压总量 ≤2GiB、压缩比 ≤1000，`_extract_zip_safely` 逐条目净化 + 强制目标目录校验 + 累计字节上限；**导入前格式与元数据校验**：按文件头 8 字节区分 v2/v1，v2 走新链路、v1 旧格式走兼容链路并明确提示「检测到旧版（v1）备份格式…建议重新加密备份」，格式错误/解密失败统一「密码错误或文件已损坏」（防探测），文件不存在明确提示；**密码不落痕**：密码仅存函数栈帧局部变量，不写日志/临时文件；**失败清理**：导入失败回滚（删半成品新 data → 恢复 data_bak_ → 清理临时文件），备份文件名 `data_<时间戳>_<随机段>.enc` 防覆盖；冒烟验证 `backup_smoke_test.py` **30/30 PASS**（正常往返/错误密码/篡改载荷·元数据/dotdot·absolute·drive·symlink 拒绝/条目数·压缩比·总量超限拒绝/弱密码拒绝/旧格式导入成功+错误密码拒绝/非备份文件拒绝/data 原样保留/文件不存在提示）；同步更新 §1 功能表（7/8/17）/§2/§4.0/§4.4/§8 并重新打包 |
| v1.8.9 | 2026-11-03 | Marvis file-agent | **托盘功能整体排查加固（根因：托盘异步就绪竞态 + 存量日志调用缺参）**：用户反馈「点击关闭/最小化到托盘有点问题」——基线主链路（关闭→托盘→恢复→再关闭→菜单退出→清理）冒烟全部通过，异常点锁定在未覆盖边界：① 托盘 `run_detached()` 异步创建，`__init__` 立即返回时 `_tray_active=True` 但托盘线程可能尚未就绪，此时关闭请求走 `_minimize_to_tray` 隐藏窗口，托盘图标尚未创建导致「窗口消失且无图标可恢复」；② 重复启动无互斥，任务栏可堆积多个图标；③ 主窗口销毁后托盘线程迟到回调直接 `after(0)` 可能抛 `TclError`；④ 存量 Bug：app.py 6 处 `append_manager_log` 调用缺参（定义签名为 `(cfg, action, summary)`，调用缺 cfg/action/summary 会抛 TypeError，波及退出记忆×2/退出停服务×3/设置保存×1 的操作日志落盘）。加固：① 新增 `_acquire_single_instance()`（`CreateMutexW` 固定名 `Global\VaultwardenManager_SingleInstance`）+ `_activate_existing_instance()`（`FindWindowW` + `ShowWindow(SW_RESTORE)` + `SetForegroundWindow`），`main()` 启动前检查，重复启动激活既有窗口后立即退出，**托盘图标从源头唯一**；② `_create_tray_icon()` 创建后轮询等待 `icon._running` 就绪（最多 3 秒×0.2s），就绪才置 `_tray_active=True`，未就绪时关闭请求稍后重试最小化，创建失败/依赖缺失降级直接退出；③ 新增 `_safe_schedule(cb)`（`winfo_exists()` 存活校验 + `after(0)`），全部托盘回调改走它，杜绝迟到回调崩溃；④ `_minimize_to_tray`/`_show_from_tray` 幂等化（`_tray_active` + 窗口 `state()` 双条件），`_quit_app` 清理托盘 `icon.stop()` 失败重试兜底（0.5s×3 次）并置 `_tray_icon=None`/`_tray_active=False`；⑤ 修复 6 处 `append_manager_log` 缺参调用为 `append_manager_log(self.cfg, 操作名, 摘要)`；ui.py VERSION → v1.8.9。验证：tray_smoke.py 主链路全 PASS（托盘创建/隐藏/幂等/恢复/菜单项）+ quit_cleanup.py 退出清理断言（`icon._running=False`/`_tray_icon=None`/`_tray_active=False`）+ first_instance/mutex_test.py 单实例互斥（第二实例 acquire=False 且激活既有窗口 hwnd）+ btn_matrix.py 暴露并修复日志缺参 Bug + regression.py 综合回归 ALL PASS（托盘链路+设置保存/取消+关于+关闭进托盘+恢复+再隐藏+manager.log 落盘断言）；py_compile 四文件通过；同步更新 §1 功能表（15/17）/§4.7/§4.8/§8 并重新打包 |
| v1.9.0 | 2026-11-04 | Marvis file-agent | **新增「赞助支持」卡片（界面左侧设置/关于下方）**：`vwm/app.py` `_build_ui` 在「设置」「关于」按钮（grid row6）正下方新增 `sponsor` 容器——`tk.Frame(left, bg="#e9ecef", padx=6, pady=6)` `grid(row=7, column=0, columnspan=2, sticky="ew", padx=4, pady=(8, 0))`，内部标题「赞助支持」（Microsoft YaHei UI 9 bold、TEXT_PRIMARY 深灰、居中）与三段说明文字（Microsoft YaHei UI 8、TEXT_SECONDARY、justify/anchor=center、wraplength=172 自动换行）：「一元不嫌少，十元不嫌多。/无论金额多少，都是对本软件项目的认可。/赞助属于自愿行为，不购买任何功能、不享有售后服务，仅表达您的一份善意。」，与图1文案一致、样式同为浅灰居中；纯展示 Label 不响应点击，不参与状态矩阵与 `_busy` 禁用，按钮矩阵/设置/关于/退出（row5 columnspan2）/状态栏布局零改动，主窗口默认高度 700 内无挤压溢出；`vwm/ui.py` VERSION → v1.9.0；冒烟验证通过（py_compile app.py/ui.py、stub-tkinter 下 FakeApp._build_ui 构建成功、13 键按钮矩阵完整、赞助卡片源码断言含标题/三段文案/row=7）；同步更新 §1 功能表（18）/§4.8 后新增 §4.9/§8 并重新打包 |
| v1.9.1 | 2026-11-04 | Marvis file-agent | **退出链路非阻塞化（退出卡顿优化）**：根因——`_quit_app` 主线程**同步**执行 find_vw_processes（Win32_Process 起 PowerShell，实测每次约 2s）+ stop_service（内部再次 find + taskkill + 每轮 find 轮询约 4.3s），点击退出后界面假死最坏 6.4 秒（实测 stopped 2.07s / run 6.43s 全程冻结）。方案：① `_quit_app` 停止服务改**后台 daemon 线程**——主线程先刷新「正在退出…（停止服务中）」提示并 `update_idletasks()` 立即返回，线程执行「检测→stop_service」，结果经 `_safe_schedule` 回主线程 `_on_stop_result`（成功→`_final_cleanup`：托盘 `icon.stop()` 重试兜底 + `destroy()`；失败→`ask_stop_failed_quit` 仍退出/取消退出，取消复位 `_quitting`、保留窗口托盘），新增 `_quitting` 防重入（等待期间重复退出直接忽略）；② `service.stop_service` 轮询确认**轻量化**——新增 `_tasklist_pids()`（`tasklist /FO CSV` 一次取全 PID、不起 PowerShell），轮询固定 6s 时间预算、0.2s 间隔按 PID 存活判定，替代每轮 find_vw_processes 约 2s 空耗，取不到 PID 罕见场景回退 find 轮询。**功能行为零变化**：退出前仍确保停止服务、manager.log 落盘、取消保留窗口托盘、托盘清理兜底。验证：优化前后对比——**主线程冻结时间 stopped 2.07s→0.017s、run 6.43s→0.013s**（UI 立即响应，窗口销毁总时长中其余为后台停止耗时、期间界面可操作有状态提示）；回归 verify_quit_v191.py 11 项全 PASS（取消保留窗口托盘+_quitting 复位/仍退出销毁/成功销毁/防重入不重复启动线程/tasklist_pids 含当前 PID/真实服务启动→停止 2.7s 无残留）；manager.log 退出记录落盘正常；py_compile 三文件通过；ui.py VERSION → v1.9.1；同步更新 §1 功能表（15/17）/§4.7/§8 并重新打包 |
| v1.9.2 | 2026-11-04 | Marvis file-agent | **进程被强杀后托盘 ghost 图标清理（启动广播托盘刷新 + 图标重注册兜底）**：根因——正常退出路径 `_final_cleanup` 已执行 `icon.stop()`（内部 `Shell_NotifyIcon(NIM_DELETE)`）+ 重试兜底，托盘图标随进程正常注销；但进程被**强杀**（`taskkill /F` / 任务管理器结束）时进程来不及执行 NIM_DELETE，explorer 通知区仍保存该图标条目，形成「ghost 图标」长期残留且无进程可响应点击。方案：① **启动广播清 ghost**——新增 `app._refresh_tray_icons()`：`ctypes.windll.user32.PostMessageW(HWND_BROADCAST=0xFFFF, WM_TIMECHANGE=0x001A, 0, 0)` 向所有顶层窗口广播系统时间变更消息，explorer 收到后重读通知区、自动清理失效（进程已死）图标条目；WM_TIMECHANGE 是通知区公认安全刷新手法，只触发刷新、不删除其它应用正常注册的图标，不误伤系统托盘；**实测关键约束**：广播必须**前置到自身托盘图标注册之前**——若在图标注册后再广播，explorer 重建通知区时会丢掉刚注册的 pystray 图标（Win11 新版通知区下 pystray 的 WM_TASKBARCREATED 重注册不生效），故 `main()` 顺序为：单实例互斥 → `_refresh_tray_icons()` → `time.sleep(2.5)`（等 explorer 完成通知区重建）→ 创建 `VaultwardenManagerApp`（内部注册托盘图标）→ `mainloop()`；② **图标重注册兜底**——新增 `app._resend_taskbar_created()`：`_create_tray_icon()` 置 `_tray_active=True` 后 `self.after(2000, ...)` 延迟调用，向自身 pystray 图标窗口（`icon._hwnd`）`PostMessageW(RegisterWindowMessage("TaskbarCreated"))`，触发 pystray 重新 `Shell_NotifyIcon(NIM_ADD)`；实测发现进程被强杀后 explorer 通知区可能处于异常状态、首次 NIM_ADD 注册不被显示，补发 TaskbarCreated 可稳定恢复显示；同一 hWnd+hID 的 NIM_ADD 只更新不新增，不产生重复图标、不影响其它应用；③ ctypes/user32 异常时静默跳过（降级为不刷新，功能零回归）。配合 v1.8.9 既有防线：单实例互斥（`CreateMutexW`）保证重复启动不堆积图标；`_create_tray_icon` 就绪轮询保证图标可用；`_final_cleanup` 退出清理兜底保证正常退出无残留——**强杀残留由启动广播兜底清理，异常通知区由重注册兜底恢复**。验证：`tests\verify_ghost_v192.py` 20/20 PASS（py_compile app/ui、广播参数断言 `(0xFFFF, 0x001A, 0, 0)`、ctypes 异常静默兜底、main 接线断言、v1.8.9 单实例互斥与退出清理保留、`SetLastError(0)` 前置与 183 双条件、无实例时首次 `True`/同进程二次 `False`、`_nim_delete_icon` 接线且位于 `icon.stop()` 之后、`Shell_NotifyIconW(2)`、TaskbarCreated 重注册接线、VERSION=v1.9.2）；真机冒烟（源码 + dist 两环境）——① 干净启动（含广播）托盘图标正常显示、无空白槽位；② `taskkill /F` 强杀后进程无残留、图标消失、无 ghost 占位；③ 强杀后重新启动，广播清理 + 重注册兜底生效，图标稳定恢复显示、其余应用托盘图标排列不变（不误伤）；④ 单实例互斥生效（第二实例自动退出）；⑤ 正常退出路径托盘图标正常消失（v1.9.1 回归 verify_quit_v191 11 项全 PASS）；④ **补充修复（自动退出真根因 + 退出 NIM_DELETE 兜底）**——`_acquire_single_instance()` 调用 `CreateMutexW` 后未清零 `GetLastError`，残留 183 使互斥创建成功却被误判为「已有实例」，触发「激活并退出」分支，表现为启动约 6~12 秒后窗口与托盘图标自动消失（explorer 重启只是更早暴露，非根因）；修复为 `SetLastError(0)` 前置 + `restype/argtypes` 显式声明 + 「返回值非空且 `GetLastError()==ERROR_ALREADY_EXISTS`」双重判定；`_final_cleanup` 在 `icon.stop()` 后新增 `_nim_delete_icon(icon._hwnd, id(icon))` 显式 `Shell_NotifyIconW(NIM_DELETE)`，覆盖 pystray 停止异常路径。回归：verify_ghost_v192 20/20、退出回归 19 项 + 防重入 2 项全 PASS；源码实测启动 12s/30s 存活、强杀重启 15s/30s 存活；⑤ **终验：onefile 双进程事实与残留进程提示**——`-F` 打包 exe 为父子双进程（bootloader + GUI），实测只结束父进程后子进程存活、主窗口与托盘图标仍响应（用户视角「进程已结束但图标点不掉」），且残留子进程占用 `Local\VaultwardenManager_SingleInstance` 互斥导致再次启动「启动即退出」；`_activate_existing_instance()` 改为 `FindWindowW` 6×0.5s 重试，仍无主窗口即判为孤儿残留进程并弹框提示结束全部 `VaultwardenManager.exe`（或 `taskkill /F /T /IM VaultwardenManager.exe`）；⑥ 通知区条目硬指标 `HKCU\Control Panel\NotifyIconSettings` 命中条目数在「运行中/强杀后/强杀重启后」始终为 1（无 ghost 堆积），托盘图标像素采样 3s~51s 持续存在（无 12s 自动消失）；新增独立退出回归 `tests\verify_quit_v192.py` 11/11 PASS（`os._exit()` 收尾规避 Tcl 噪声）。dist 重打包 `VaultwardenManager.exe` 23,271,030 字节、2026-11-04 12:06:15。同步更新 §1 功能表（17）/§4.7/§8 并重新打包 |
| v1.9.3 | 2026-11-04 | Marvis file-agent | **第二实例弹出中文提示框（单实例互斥交互完善）**：根因——v1.9.2 及以前检测到已有实例运行时仅「激活既有窗口后静默退出」，用户看不到任何反馈，孤儿残留场景（有互斥无主窗口）更表现为「双击没反应/打不开」。改动：① 新增第二把互斥 `Local\VaultwardenManager_NoticeLock`（`_acquire_notice_lock()`，`SetLastError(0)` 前置 + `ERROR_ALREADY_EXISTS` 双条件判定），只有抢到锁的第二实例才弹提示，快速连开多个只弹一次、不叠加；② `_activate_existing_instance()` 重写为「先弹提示、再激活」：`MessageBoxW` 标题固定 `VaultwardenManager`，flags `0x50040`（`MB_TOPMOST|MB_SETFOREGROUND|MB_ICONINFORMATION`），正常场景文案「程序已在运行中，请勿重复打开。可从任务栏窗口或系统托盘图标打开已有窗口。」，孤儿残留场景文案引导「结束所有 VaultwardenManager.exe 进程后重新启动」并给出 `taskkill /F /T /IM VaultwardenManager.exe` 命令；激活失败静默容错，不影响提示与退出；③ 新增 `_keep_dialog_topmost()` 守护线程置顶加固——本机 Win11 Build 26200 上 `MB_TOPMOST` 不落到 `WS_EX_TOPMOST` 样式位且 MessageBox 未必抢到前台，故弹框前启动守护线程轮询 `FindWindowW("#32770", ...)`，命中即 `SetWindowPos(h, HWND_TOPMOST, ...)` 显式置顶，保证提示框不被遮挡；④ `main()` 接线 `if not _acquire_single_instance(): if _acquire_notice_lock(): _activate_existing_instance(); return`，提示后自行退出、未创建 Tk 窗口与托盘、零残留；⑤ `vwm/ui.py` `VERSION` → v1.9.3。验证：`tests\verify_single_instance_v193.py` 38/38、exe 真机 `verify_si_dist_v193.py` 15/15（第二实例 1.0s 内弹框、可见且中心点未被遮挡、点确定后 0.5s 退出码 0、连开 3 个只弹 1 次、零残留、第一实例不受影响）、`tests\verify_si_live.py` 提示 1.01s、`tests\verify_si_orphan.py` 3.21s 弹孤儿文案、既有 `tests\verify_quit_v192.py` 11/11 与 `tests\verify_ghost_v192.py` 20/20 无回归（F1 版本判据改为语义比较 «VERSION ≥ v1.9.2»）；PyInstaller `-F -w` 重打包 `dist\VaultwardenManager.exe`（约 22.2MB）。 |
| v1.9.4 | 2026-11-04 | Marvis file-agent | **「一键部署」部署完成后持久禁用（跨重启生效）**：根因——v1.3.0 起「一键部署」仅在「服务运行中」被按钮矩阵临时置灰，服务一停即恢复可点，且「已部署」判断只依赖 `v1.3.0` 的会话内内存标志，程序重启后完全丢失，用户可反复点击对同一目录重复部署（重复下载/覆盖 exe、重装网页版、重跑证书与信任链路）。改动：① 新增 `service.get_deploy_state(cfg)` 纯函数（`vwm/service.py`）——按磁盘实测三态判定：`deployed`（`vaultwarden_dir/exe_name` 存在且 >1MB + `.env` 内 `ADMIN_TOKEN` 键存在且值非空 + `web-vault/index.html` 存在，三项全满足）/ `partial`（前两项就绪、仅缺网页版，允许点击补装）/ `none`（目录不存在、缺核心文件、exe ≤1MB、缺 `.env` 或无有效 ADMIN_TOKEN）；纯读盘不写盘、幂等、异常一律保守返回 `none`，**不依赖任何会话内标志**；② `app._refresh_deploy_state()` 在 `refresh_status()` 中每次轮询前调用，结果存入 `self._deploy_state` / `self._deploy_state_tip`（`__init__` 初始化为 `none`，位于 `_build_ui` 之前），并刷新状态栏副标签：「已部署（一键部署已锁定）」/「部署部分就绪（可点击一键部署补装网页版）」/「未部署（可点击一键部署）」（迁移提示优先覆盖）；③ `update_button_states()` 新增独立分支 `elif key == "deploy" and deployed: DISABLED`（置于「运行中禁用」之后、`stopped` 恢复启用之前）——服务运行中与已停止两种状态下，只要磁盘判定已部署「一键部署」均禁用，**程序重启后首次 `refresh_status()` 即重新检测并自动保持禁用**；`partial`/`none` 仍可点，`_busy` 忙碌、`foreign`、其它 10 个主按钮与「设置/关于/退出/托盘/单实例」逻辑零改动；④ 双保险点击拦截：`on_deploy` 入口先调 `get_deploy_state()`，已部署则刷新状态、置灰按钮、状态栏橙字提示「已完成部署，无需重复部署；如需重新部署请先清理部署目录 <部署目录>」并直接返回，**不启动任何部署线程**（点击禁用按钮无副作用）；⑤ 部署成功回调 `done()` 在 `_finish_deploy_progress` 后立即 `_refresh_deploy_state()` + `update_button_states()`，成功消息追加「｜「一键部署」已锁定（已完成部署，如需重新部署请先清理部署目录）」，实现「本次会话刚部署成功即刻置灰」；⑥ `vwm/ui.py` `VERSION` → v1.9.4。验证：新增 `tests\verify_deploy_lock_v194.py` **42/42 PASS**（三文件编译/VERSION/get_deploy_state 11 组磁盘判定含 exe≤1MB、无 ADMIN_TOKEN、空值、缺网页版 partial、空串目录、幂等/按钮矩阵 8 组：stopped·running·foreign·busy × deployed·partial·none/重启两次判定与禁用保持/on_deploy 已部署拦截与 partial 不误拦/10 项源码静态断言）；新增真机 GUI 冒烟 `tests\verify_deploy_lock_live_v194.py` **12/12 PASS**（真实 `VaultwardenManagerApp` 实例，仅打桩托盘图标/日志读取/服务状态查询：已部署→按钮 `disabled` + 状态栏「已部署（一键部署已锁定）」、点击仅提示且 `_busy` 保持 False、未部署→`normal` + 「未部署」、缺网页版→`normal` 可补装、模拟重启（销毁后重建实例）仍 `disabled` 且点击仍只提示）；既有回归全绿——`tests\verify_single_instance_v193.py` 38/38（A1 版本断言由硬编码 `v1.9.3` 改为语义比较「≥ v1.9.3」）、`tests\verify_ghost_v192.py` 20/20、`tests\verify_quit_v192.py` 11/11；PyInstaller `-F -w --noconfirm --name VaultwardenManager` 重打包 `dist\VaultwardenManager.exe`；同步更新 §1（版本号 + 功能表 11 一键部署）/§4.0 模块表/§4.1（新增 get_deploy_state、deploy_service 持久生效）/§4.5（矩阵锁定分支、点击拦截、状态栏提示）/§8。 |
| v1.9.5 | 2026-11-04 | Marvis file-agent | **加密备份输入密码卡顿修复 + 备份位置可选**：① 卡顿根因（实测定位）——GUI `_periodic_status` 每 `status_check_ms`（3s）在**主线程同步**调用 `get_service_status`，单次耗时约 **3999ms**（`is_process_running` 与 `get_foreign_process_tip` 各起一次 PowerShell `Win32_Process` 查 ExecutablePath，各约 2s），主线程占用率接近 100%，用户点击「加密备份」后弹出密码框、敲键盘、拖动窗口均被卡住（用户感知为「输入密码卡顿」）；加密本身已在 `run_task` 后台线程，非阻塞源。② 探测链路轻量化——新增 `service._tasklist_name_hit(exe_name)`（`tasklist /FO CSV` 一次取进程名，实测约 0.1s）与 `_foreign_tip_from_procs(procs, deploy_dir)`（纯本地判断）；`get_service_status` 改为「tasklist 预检：无同名进程直接返回 `stopped`、不触达 PowerShell；有同名进程才 `find_vw_processes(deploy_dir=None)` 取一次全量路径后本地判定 running/abnormal/foreign/stopped」，四态语义、端口探测条件、foreign 提示文案与 v1.8.1 完全一致，单次耗时 **3999ms → 126ms**。③ 状态轮询异步化——新增 `app.refresh_status_async()` / `_apply_status(res)`：探测放 `vw-status-probe` daemon 线程执行、**立即返回**（实测 <1ms），结果经 `_safe_schedule` 回主线程应用（状态栏文字/颜色 + `_refresh_deploy_state()` + `update_button_states()`）；单飞标志 `_status_probing` 防重复发起；`_periodic_status`、`__init__`（首屏先静态渲染再异步回填）、`_finish_task`、`on_change_port` 全部改调异步版本，同步 `refresh_status()` 保留供即时场景（行为不变）；主线程占用率 **100% → 4.3%**。④ 备份位置可选——`backup.encrypt_backup(cfg, password, out_path=None, stage_cb=None)` 新增自定义落点与阶段回调；新增纯函数 `resolve_enc_target(cfg, out_path=None)`（空 → `backup_dir\data_<时间戳>_<4位hex>.enc` 沿用既有命名规范，非空 → 规范化并自动补 `.enc`）；`on_enc_backup` 在密码框后弹 `filedialog.asksaveasfilename`（`initialdir=backup_dir`、默认文件名沿用、`defaultextension=".enc"`、类型「加密备份 *.enc」），**取消则提示「已取消加密备份（未选择保存位置）」、不调用加密、不产生文件、不进入忙碌态**；路径异常给中文提示（父路径非目录 / 创建目录失败无权限 / 目标是目录），不抛异常、不留半成品。⑤ 明确安全不变——PBKDF2-HMAC-SHA256 **600,000 次迭代未降低**，`VWM_ENC_V2` 格式、`zip_sha256` 完整性校验、防压缩炸弹（条目数/解压总量/压缩比）、v1 旧备份兼容导入全部零改动，自选位置与默认位置备份可互相导入。⑥ `run_task(fn, on_done, busy_text=None)` 支持自定忙碌文案（加密时显示「正在加密备份…」而非泛化「正在执行，请稍候...」），工作线程回主线程统一走 `_safe_schedule()`；`vwm/ui.py` `VERSION` → v1.9.5。验证：`tests\verify_backup_v195.py` **35/35 PASS**（resolve_enc_target 默认/自定义/补后缀/父路径为文件/目标为目录、阶段回调顺序 zip→check→kdf→encrypt→write、自定义位置加密落地 + 导入还原一致、非法路径中文提示、防压缩炸弹、v1 兼容导入、状态探测耗时）；`tests\verify_backup_gui_v195.py` **21/21 PASS**（真实 mainloop 事件驱动：密码框取消、保存框取消均无文件无忙碌态、自定义目录备份落地且可还原、异步探测单飞、心跳间隔正常、忙碌文案「正在加密备份…」不被覆盖）；`bench_v195.py` 实测——状态探测 3999ms→126ms、主线程占用率 100%→4.3%；加密约 5MB data 全链路 291ms（压缩 144ms / 防炸弹校验 1ms / PBKDF2 600k 105ms / 加密 37ms / 写盘 4ms），全在后台线程；既有回归全绿——`tests\verify_single_instance_v193.py` 38/38、`tests\verify_ghost_v192.py` 20/20、`tests\verify_quit_v192.py` 11/11、`tests\verify_deploy_lock_v194.py` 42/42、`tests\verify_deploy_lock_live_v194.py` 12/12；PyInstaller `-F -w --noconfirm --name VaultwardenManager` 重打包 `dist\VaultwardenManager.exe`；同步更新 §2 模块表/§4.1/§4.4/§4.5/§8。 |
| v1.9.6 | 2026-11-04 | Marvis file-agent | **「赞助支持」卡片内显示收款二维码（写死路径）**：`vwm/app.py` 顶部新增常量 `SPONSOR_QR_PATH = r"E:\yscl\shuage-coin-helper\website\ewm\ewmsk.png"`（按需求写死为绝对路径，不随程序目录/打包解包目录变化）与 `SPONSOR_QR_MAX_W = 150`；新增 `_attach_sponsor_qr(parent)` 在 `_build_ui` 赞助卡片文案后调用——① 首选 Pillow `Image.open` + `LANCZOS` 等比缩放（最长边 ≤150px，实际 150×150）+ `ImageTk.PhotoImage`；② Pillow/ImageTk 不可用退回 `tk.PhotoImage(file=...)` + `subsample(factor)` 整数降采样（125×125）；图片引用存 `self._sponsor_qr_photo` 防 GC 空白；`tk.Label` + `pack(pady=(6,0))` 水平居中紧贴文案下方；**容错**：图片缺失/损坏/加载异常仅写一条 `append_manager_log(self.cfg, "赞助支持", ...)` 警告并 `return`，不弹窗不崩溃、卡片保持纯文字、布局不塌陷；因卡片增高，主窗口 `minsize` 由 `860×640` 调整为 `860×690`（默认 960×700 不变），保证最小尺寸下二维码不被裁剪；`vwm/ui.py` `VERSION` 升为 `v1.9.6`。**验证**：`tests\verify_sponsor_qr_v196.py` 27/27 全绿（常量/加载/缩放/居中/两档窗口尺寸不溢出/缺图容错/坏图容错/Pillow 兜底/真机截屏像素校验），既有回归 `tests\verify_backup_v195.py` 35/35、`tests\verify_backup_gui_v195.py` 21/21、`tests\verify_single_instance_v193.py` 38/38、`tests\verify_ghost_v192.py` 20/20、`tests\verify_quit_v192.py` 11/11、`tests\verify_deploy_lock_v194.py` 42/42、`tests\verify_deploy_lock_live_v194.py` 12/12 全部通过；PyInstaller `-F -w --noconfirm --name VaultwardenManager` 重打包 `dist\VaultwardenManager.exe`；同步更新 §4.9 赞助卡片章节。 |
| v1.9.7 | 2026-11-04 | Marvis file-agent | **统一「盾牌安全」风格图标（exe / 窗口 / 托盘全套同步）**：按参考设计图程序化生成图标并接入四类入口。① 图标设计与生成——新增 `temp\make_icon_v197.py`（Pillow 程序化绘制，非位图缩放）：蓝色盾牌主体（`#2196F3` 微渐变至下缘 `#1565C0`）+ 盾内粗描边钥匙孔 + 盾顶银蓝小挂锁，白底板；**小尺寸（≤32px）走简化形态**（近满画布盾牌 + 加粗钥匙孔，去挂锁/去细描边），保证 16/24/32 下清晰可辨不糊；输出 `app_16/24/32/48/64/128/256.png`、`app.png`、`tray.png`（64×64 RGBA 透明底）与多尺寸 `app.ico`（含 256px），全部落地 `assets\`（路径无中文，随包分发）。② 资源解析——`vwm/app.py` 新增 `_asset_path(name)`：依次尝试 `sys._MEIPASS`（PyInstaller 解包目录）→ exe 同级 `assets\` → 项目根 `assets\`，全部缺失返回 `None`。③ 窗口图标——新增 `_apply_window_icon()`，`__init__` 中 `_build_ui` 后调用；双通道先 `iconbitmap(ico, default=...)`（同时作用于后续弹窗/Toplevel），失败回退 `iconphoto(True, PhotoImage(png))`（Pillow 通道），再失败静默跳过。④ 托盘图标——`_create_tray_icon()` 优先读 `assets\tray.png`（RGBA 透明底），读取/构造失败**回退** v1.6.6 的 Pillow 代码绘制 64×64 蓝底白 V；`icon._hwnd`、`_resend_taskbar_created()`（TaskbarCreated 重注册）、`_nim_delete_icon(icon._hwnd, id(icon))` 等 v1.9.2 ghost 清理机制**零改动**。⑤ 容错红线——任一图标加载失败不抛异常、不弹窗、不影响主流程，仅 `append_manager_log(cfg, "图标", ...)` 记一条警告。⑥ 打包——`--icon=assets\app.ico` + `--add-data "assets;assets"`（§6 已更新）。⑦ `vwm/ui.py` `VERSION` → v1.9.7。验证：新增 `tests\verify_icon_v197.py` **44/44 PASS**（I1 资源清单 10 文件存在并校验 PNG/ICO 尺寸、I2 ICO 含 256 多尺寸、I3 `_asset_path` 三档兜底与缺失返回 None、I4 源码接线断言、I5 ghost 机制保留断言、I6 真机窗口图标 Win32 `GetClassLongPtrW(GCLP_HICON)` 取 HICON 像素判定为新盾牌图标）；既有回归全绿——`tests\verify_single_instance_v193.py` 38/38、`tests\verify_quit_v192.py` 11/11、`tests\verify_deploy_lock_v194.py` 42/42、`tests\verify_backup_v195.py` 35/35、`tests\verify_backup_gui_v195.py` 21/21、`tests\verify_ghost_v192.py` 20/20、`tests\verify_sponsor_qr_v196.py` 27/27（S1.4 版本断言由硬编码 v1.9.6 改为语义比较「≥ v1.9.6」）；PyInstaller `-F -w --noconfirm --icon=assets\app.ico --add-data "assets;assets" --name VaultwardenManager` 重打包 `dist\VaultwardenManager.exe`；同步更新 §2 目录结构（assets\ 资源目录）/§4.10（新增图标资源与加载）/§6（打包参数）/§8。 |
| v1.9.8 | 2026-11-04 | Marvis file-agent | **端口占用自动切换 + 服务运行状态记忆自动恢复**：① 端口探测——`vwm/network.py` 新增 `is_port_in_use`（`connect_ex` 连接探测 + 本地绑定探测**双判定**，任一命中即占用）、`is_port_bindable`、`pick_free_port(min=20000, max=65000, tries=30)`（高位区间随机挑端口并校验可绑定，重试 30 次）；② 切换封装——`vwm/service.py` 新增 `PORT_FALLBACK_MIN/MAX`、`_own_service_holds_port(cfg)`（**占用者为自身已运行的 vaultwarden 实例时不判冲突**，避免把正常运行误判为占用）、`_apply_port_change(cfg, port)`（一次性同步 `config.json` 的 `port`/`domain` 与部署目录 `.env` 的 `ROCKET_PORT`/`DOMAIN`/`ROCKET_TLS`）、`ensure_port_available(cfg) -> (ok, msg, switched)` 三态（空闲→无提示不切换；被占→随机切换并返回「端口 X 被占用，已自动切换到 Y…」；无可用端口→中文失败原因）；③ 接线——`deploy.py` 的 `deploy_service` **动作前**调用、切换说明并入部署成功消息并刷新部署状态；`app.py` 的 `on_start` 改为**先检测端口再启动**，切换提示与启动结果合并展示；`cfg["domain"]` 更新后状态栏、「复制地址」、「打开 Web/管理面板」（`resolve_web_url`）自动跟随，既有「修改端口」与证书信任主机名零影响；**单次启动至多切换一次，不漂移**，切换后仍失败给中文错误。④ 状态记忆——`config.py` 新增 `last_exit_service_running`（默认 `false`）、`auto_restore_service`（默认 `true`），旧配置自动补齐；`app.py` 新增 `_record_exit_state(running)`，`_quit_app` worker 中**先记录再停服务**（v1.8.4「退出前先停服务」保留），`_on_stop_result` 停止失败仍退出时标记 `true`，用户先手动停服再退出自然为 `false`；新增 `_maybe_auto_restore()` 于 `__init__` 末尾 `after(1200)` 调度，判定链为「开关开启 + 标志为真 + `get_deploy_state=="deployed"` + 当前未运行」→ 过 `ensure_port_available` 后走既有 `start_service`，忙碌提示「正在自动恢复服务（上次退出时服务在运行）…」并写 `append_manager_log(cfg,"自动恢复",…)`；启动成功/已在运行/未部署（提示「已跳过自动启动」）/开关关闭均**清标志防重复**，仅启动失败**保留标志**下次再试并记中文失败日志。⑤ 设置开关——`ui.py` 设置对话框新增「退出后下次启动自动恢复服务」勾选（默认勾选），保存写回开关，取消勾选即清除记忆标志；`minsize` 540→590。⑥ `vwm/ui.py` `VERSION` → v1.9.8。验证：新增 `tests\verify_port_guard_v198.py` **31/31 PASS**（network 三函数纯逻辑、`ensure_port_available` 空闲/被占/自身占用/无可用端口分支、`_apply_port_change` config+`.env` 同步、deploy/on_start 接线断言）；新增 `tests\verify_restore_v198.py` **37/37 PASS**（默认字段与旧配置补齐、`_record_exit_state` 落盘、`_quit_app` **记录先于停服**与停服保留、无服务运行记 false、`_maybe_auto_restore` 六分支含开关关闭/无标志/未部署/已运行/启动失败保留标志/端口切换消息、UI 开关源码断言）；**真机隔离端到端**（临时目录独立部署一份真实 vaultwarden.exe + vwm 包，不触碰本机真实部署）**ALL PASS**——占用端口 56219→自动切 62778 且 config.json/.env 双同步、真实进程在 62778 监听、隔离实例进程归属校验、停止后端口释放；端口空闲不切换且启动成功；`last_exit_service_running=true` 时真机自动恢复拉起服务并清标志；测试实例清理无残留；既有回归全绿——`tests\verify_icon_v197.py` 44/44（I5.8 版本断言由硬编码 v1.9.7 改为语义比较「≥ v1.9.7」）、`tests\verify_ghost_v192.py` 20/20、`tests\verify_single_instance_v193.py` 38/38、`tests\verify_quit_v192.py` 11/11、`tests\verify_deploy_lock_v194.py` 42/42、`tests\verify_deploy_lock_live_v194.py` 12/12、`tests\verify_backup_v195.py` 35/35、`tests\verify_backup_gui_v195.py` 21/21、`tests\verify_sponsor_qr_v196.py` 27/27；PyInstaller `-F -w --noconfirm --icon=assets\app.ico --add-data "assets;assets" --name VaultwardenManager` 重打包 `dist\VaultwardenManager.exe`；同步更新 §4.11（端口占用自动切换）/§4.12（状态记忆与自动恢复）/§5（两个新配置字段）/§8。 |
| v1.9.9-dev | 2026-11-05 | Marvis file-agent | **工程维护（源码完整性校验 P1 修复；不改 `ui.VERSION`，程序版本仍为 v1.9.8，无功能变更）**：① **`requirements.txt` 清理**——删除 2 行非法中文说明（`（内容由AI生成，仅供参考）`），仅保留 `cryptography>=3.4`/`pystray>=0.19`/`pillow>=8.0` 三条合法依赖（版本约束保持原样）并补齐末尾换行；`pip._internal.req.req_file.parse_requirements` 解析出 3 条需求、`pip install -r requirements.txt --dry-run --no-deps` 退出码 0；② **`tests\` 脚本根路径适配**——13 个回归脚本移入 `tests\` 后 `__file__` 定位层级少一层，项目根错指 `tests\` 致 `import vwm` 失败；将 `sys.path`/`ROOT`/`PROJ`/文内相对路径前导统一上移一级：`Path(__file__).resolve().parent` → `...parent.parent`（`verify_backup_gui_v195`/`verify_backup_v195`/`verify_deploy_lock_v194`/`verify_deploy_lock_live_v194`/`verify_icon_v197`（2 处）/`verify_port_guard_v198`/`verify_restore_v198`（2 处）/`verify_sponsor_qr_v196`），`os.path.dirname(os.path.abspath(__file__))` 改为双层 `dirname`（`verify_ghost_v192`/`verify_single_instance_v193`）；其余 `Path.parent` 属文件对象语义未改动；③ **文档同步**——§2 目录结构移除已删除的 `build\` 条目并新增 `tests\`（13 个 verify_*.py）；正文原以 `dist\vaultwarden` 为「非部署目录同名实例」示例处改为说明性描述（该测试副本已清理）；§4.9 中 `v196_sponsor_*.png` 三处截屏引用改为说明性描述（截图未入库，不指向不存在文件）；全文验证脚本引用统一加 `tests\` 前缀；④ **复验**——25 个 `.py` 全部 `py_compile` 通过（0 失败）；10 个已修脚本根解析均得到 `E:\yscl\vaultwarden-manager` 且 `import vwm` 成功；实跑最轻量 `tests\verify_port_guard_v198.py` 结果 31/31 PASS、退出码 0，无 `ModuleNotFoundError` |
| v1.9.9 | 2026-11-09 | Marvis file-agent | **设置窗口新增「浏览器插件连接」分区（含地址动态拼接 / 复制 / 证书信任 / 扩展入口）**：`vwm/ui.py` `open_settings_dialog` 在「下载地址」与「只读信息」之间新增白色卡片 `card_ext`（标题「浏览器插件连接」11 bold `TEXT_PRIMARY`），① **地址动态拼接（无硬编码端口）**——`plugin_port = cfg.get("port") or DEFAULT_CONFIG.get("port")`，本机地址 `<scheme>://localhost:<port>`、局域网地址 `<scheme>://<本机IP>:<port>`（IP 取自 `network.get_lan_ips()`，经 `win.after(60, ...)` 异步回填，避免卡顿；无网卡时显示「未检测到局域网 IP」且不抛异常），`scheme` 由 `cfg["domain"]` 是否 `http://` 开头决定（默认 https），两行均为只读 `tk.Entry`（`readonlybackground=#f8f9fa`）；② **「复制地址」按钮**——复制当前选中（点击哪个地址即选哪个，`<Button-1>`/`<FocusIn>`）地址到系统剪贴板（`clipboard_clear`+`clipboard_append`+`update_idletasks`），窗口内提示行与主状态栏同步提示「已复制地址：<url>」（成功绿 #2b8a3e / 失败红 #c92a2a），检测到局域网 IP 后默认复制局域网地址；③ **「打开地址信任证书」按钮**——`webbrowser.open` 默认浏览器打开该地址并提示先「高级→继续前往」信任自签证书（否则扩展报无法连接）；④ **「获取扩展（Edge）」「获取扩展（Chrome）」按钮**——`webbrowser.open` 打开配置键 `ext_edge_url` / `ext_chrome_url`（缺键用 `DEFAULT_CONFIG` 兜底）；⑤ **说明文字**——扩展登录页把「服务器地址」填成上述地址再登录账号，曾填错需先在扩展设置清除（或退出登录）再填，服务未启动时地址不可访问；⑥ **布局适配**——卡片区改为 `Canvas + 垂直 Scrollbar`（inner 自适应宽度、`<Configure>` 同步 scrollregion、窗口级 `<MouseWheel>`），窗口 560×690，四张卡片间距/字号/配色与原来一致，底部「保存设置」「取消」固定不滚动，既有保存/关闭逻辑零改动；⑦ **配置与接线**——`vwm/config.py` `build_default_config` 新增 `ext_edge_url` / `ext_chrome_url` 两键（旧 config 由 `load_config` 合并补齐）；`vwm/app.py` `on_settings` 传入 `self.set_msg` 作为新可选参数 `on_status`（不传时仅窗口内提示，向后兼容）；`vwm/ui.py` 新增 `import webbrowser`、`from .config import DEFAULT_CONFIG`、`from .network import get_lan_ips`，`VERSION` → v1.9.9；⑧ **自检**——`py_compile` 全部 `.py` 通过；真实 Tk 冒烟（透明窗口 + 硬看门狗，不弹窗不阻塞）**25/25 PASS**：两地址按 port 动态拼接、点选切换并复制到真实剪贴板、状态栏回调、信任按钮打开同一地址、缺键时打开默认商店地址、端口 44444→11223 后地址随之变化、原三分区与保存/取消按钮零回归；`ui.py` 内无任何端口字面量；未改动正式部署 `vaultwarden\` 下任何数据（本轮不打包 exe）；同步更新 §1 功能表 / §2 / §4.0 / §4.8（新增分区条目）/ §5（两新键）/ §8 |
| v1.9.10 | 2026-11-09 | Marvis file-agent | **设置窗口局域网 IP 识别错误修复（P1）+ 打包体积瘦身 −33.9%**：① **缺陷根因**——v1.9.9 及以前 `network.get_lan_ips()` 只做「UDP 出口地址 + 主机名解析」两路收集后 `sorted()` 字典序取首，真机得到 `['192.0.2.1', '198.51.100.10']`，`192.0.2.1`（Hyper-V `vEthernet (Default Switch)` 虚拟网卡）因字典序靠前被当作局域网地址显示，手机/其它电脑根本连不上（该网段仅 Hyper-V 内部可达）。② **`vwm/network.py` 探测链路重写**——新增 `_udp_outbound_ips()`（对 `8.8.8.8:80`/`114.114.114.114:80`/`223.5.5.5:80` 做 `SOCK_DGRAM connect` 只取 `getsockname()` 不实际发包）、`_parse_ipconfig()`（`CREATE_NO_WINDOW` 子进程 + 8 s 超时 + `mbcs/utf-8/gbk` 逐级解码，解析网卡名/描述/IPv4/默认网关；**修复中文系统「默认网关」字段跨行续行未被解析**导致真实地址被误判虚拟网卡）、`_virtual_reason()`（硬排除 virtualbox/vmware/wsl/docker/loopback/tap/openvpn/wireguard/tailscale/zerotier/teredo/bluetooth/vpn/wan miniport 等关键词；`hyper-v`/`vethernet`/`虚拟` 仅在**无默认网关**时排除，避免把桥接物理网卡的「外部虚拟交换机」唯一可用地址一刀切过滤；`127.*`/`169.254.*` 地址层硬排除）、`_ip_rank()` 打分（私网 192.168.x +30 > 10.x +20 > 172.16–31.x +10 > 100.64/10 +5；有默认网关 +100；与 UDP 出口一致 +60；Hyper-V 桥接 −25）；新增 `get_lan_ip_info(refresh=False) -> dict`（`primary`/`candidates`/`details`/`excluded`/`udp_probe`/`source`/`cached`）与模块级 `_LAN_CACHE`（TTL 30 s）；**`get_lan_ips(refresh=False)` 保持原签名与语义**（返回 `candidates`，供 `cert.py` 证书 SAN 使用），既有调用零改动。③ **`vwm/ui.py` 异步回填**——`_load_lan_ip()` 改为后台 daemon 线程探测 + `win.after(0, _apply_lan_info)` 回主线程回填（窗口已销毁静默放弃），主线程不再执行 `ipconfig`；`_apply_lan_info()` 局域网地址行显示首选地址，提示行在候选 >1 时追加「另有 N 个可用地址，已选用首选」、单候选沿用原文案、无候选显示「未检测到局域网 IP」；`VERSION = "v1.9.10"`。④ **真机实测（DESKTOP-IHABM60）**——选中 `198.51.100.10`（`vEthernet (外部虚拟交换机)`，默认网关 `198.51.100.1`，评分 165，与 UDP 出口一致），排除 `192.0.2.1`（`Default Switch`，无网关）与 `169.254.10.20`（`内部虚拟交换机`，APIPA）；探 0.043 s / 缓存命中 0.0000 s；设置窗口实拍 `https://198.51.100.10:11223`。⑤ **打包瘦身**——`numpy`/`yaml`/`bcrypt` 等系 site-packages 环境被 PyInstaller hook 连带收集（`numpy.libs\libscipy_openblas64_*.dll` 单文件 19.47 MB），项目代码零引用；构建命令固化 `--exclude-module numpy numpy.libs yaml bcrypt scipy pandas matplotlib PyQt5 PySide6`，**exe 35,610,012 字节（33.96 MB）→ 23,527,895 字节（22.44 MB），减少 12,082,117 字节（−33.9%）**，归档条目 1072 → 1025；`cryptography`（3.37 MB）/`pystray`（13 模块）/`PIL`（6.41 MB）/`tkinter` 全部保留。⑥ **功能回归 7 项全通过**——启动两次（4.17 s / 4.09 s 出主窗，976×739，2 s 后存活）、设置窗口真实点击 0.15 s 弹出且四分区滚动逐帧无错位、临时目录备份加密→解密往返成功（明文一致、错误密码/弱密码均被拒）、托盘 `pystray.Icon` 可生成 + 通知区条目存在、归档审计冗余模块全为 0 + `assets\` 12 文件齐全、进程零残留。⑦ **文档**——`DEV.md` 更新头部版本、§4.2 SAN 说明、§4.8 设置窗口分区与异步说明、新增 §4.13「局域网 IP 探测策略」、§6 固化最终打包命令与回归清单、§8 本条记录；清理项目根 `build\`、`VaultwardenManager.spec`，构建日志落中间产物目录。|
| v1.9.11 | 2026-11-09 | Marvis file-agent | **赞助支持区迁入「关于」窗口（并改为内置 `assets` 二维码资源）**：① **参考实现对齐**——参照 `E:\yscl\SysMainToggle` 的 `SponsorMixin`（`_sponsor_qr_file` / `_load_sponsor_qr` / 二维码点击用系统看图器打开 / 缺失降级纯文字）与 `const.py` 的 `SPONSOR_QR_NAME`/`SPONSOR_QR_MAX_W`/`C_SP_*` 配色，按本项目蓝白配色与字号适配落地。② **`vwm/ui.py` 新增赞助区能力**——模块级常量 `SPONSOR_QR_NAME="sponsor_qr.png"`、`SPONSOR_QR_MAX_W=150`、`SPONSOR_QR_MIN_W=96`、`SPONSOR_TITLE="赞助支持"`、`SPONSOR_TEXT`（原三段文案）、`SPONSOR_QR_HINT="手机扫码即可 · 点击二维码可用系统看图器放大"`、`C_SP_CARD="#e9ecef"`、`C_SP_TITLE`/`C_SP_TEXT`/`C_SP_HINT`（复用 `TEXT_PRIMARY`/`TEXT_SECONDARY`/`TEXT_HINT`）；新增 `_sponsor_qr_file()`（三通道路径：`sys._MEIPASS/assets` → exe 同级 `assets` → 项目根 `assets`，全缺返回空串）、`_load_sponsor_qr(max_w=SPONSOR_QR_MAX_W)`（Pillow `Image.LANCZOS` 等比缩放 + `ImageTk.PhotoImage` 优先；失败退回 `tk.PhotoImage` + `subsample` 整数降采样；再失败返回 `(None, path, 原因)` 不抛异常）、`_sponsor_qr_max_w(container)`（容器宽 −60px，夹在 `[96,150]`，未完成布局退化为 150）；新增 `import os`。③ **`show_about_dialog` 重写**——窗口 460×330 → **460×560**（`update_idletasks` 后按 `winfo_reqheight` 取 `max(560, 需求高度)` 二次居中，尺寸不变不多调 `geometry`）；白色信息卡片下方新增浅灰赞助卡片 `sp_card`（`#e9ecef`、`padx/pady=6`、`pack(fill="x", padx=16, pady=(0,4))`）：标题「赞助支持」（10 bold `C_SP_TITLE`）+ 三段文案（8 号 `C_SP_TEXT`、居中、`wraplength=400`）+ 二维码（`tk.Label` 居中、`cursor="hand2"`，绑定 `<Button-1>` → `os.startfile` 交系统看图器放大）+ 提示行（8 号 `C_SP_HINT`）；二维码缺失/损坏时显示「二维码暂不可用（请检查 assets/sponsor_qr.png）」占位（`width=18`/`height=3`），不弹窗不抛异常、布局不塌陷；图片引用挂 `win._sponsor_qr_photo` / `win._sponsor_qr_path` 防 GC 空白。④ **`vwm/app.py` 主窗口移除**——删除 `_build_ui` 中 `sponsor` 容器（left 网格 row7 `columnspan=2` 赞助卡片代码块）、`_attach_sponsor_qr(self, parent)` 方法、顶部 `SPONSOR_QR_PATH`（写死绝对路径 `E:\yscl\shuage-coin-helper\website\ewm\ewmsk.png`）与 `SPONSOR_QR_MAX_W` 常量、`__init__` 中 `self._sponsor_qr_photo = None`；`minsize` 由 `860×690` **回收为 `860×640`**（默认 `960×700` 不变），按钮矩阵（2×6，13 键）/设置·关于（row6）/退出（row5）/状态栏布局零改动；顶部注释说明赞助区已迁至关于窗口。⑤ **设置窗口核对**——设置窗口自 v1.8.5 起即未含赞助分区（赞助区一直在主窗口），复核四个分区（退出记忆 / 下载地址 / 浏览器插件连接 / 只读信息）无任何赞助残留控件与文案；`vwm/config.py` 无赞助专用配置键，旧 `config.json` 无需迁移、不报错。⑥ **版本与文档**——`vwm/ui.py` `VERSION` → `v1.9.11`；DEV.md 更新头部版本与日期、§1 功能表 |17|/|18|、§2 目录结构（`assets\sponsor_qr.png` 说明）、§4.8 关于窗口控件清单、§4.9 全章重写（当前位置/文案配色/三通道路径/双通道加载/宽度自适应/点击交互/容错/主窗口变化/历史沿革）、§8 本条记录。⑦ **自检**——`py_compile` 全部 `.py` 通过；新增 `tests\verify_about_sponsor_v1911.py` **59/59 PASS**（A 常量与二维码资源存在性/尺寸/深色像素、B 加载缩放与缺图坏图容错及宽度夹取、C 源码断言主窗口无赞助卡片与设置窗口无残留、D 真机关于窗口弹出+二维码控件已映射+像素非空白、E 真机主窗口 13 键矩阵完好/无浅灰卡片/版本号 v1.9.11、F 真机设置窗口四分区正常无残留）；新增 `tests\verify_tray_smoke_v1911.py` **13/13 PASS**（托盘真实创建与标题、菜单结构、退出后 `_tray_icon` 清空与 pystray 停止、无非守护线程残留）；真机冒烟全程未触碰正式部署 `vaultwarden\` 数据，关闭后零进程残留；**本轮不打包 exe**。|
| v1.9.11-doc | 2026-11-09 | Marvis file-agent | **开源化整理（仅新增文件与文档改写，无功能变更，`vwm/ui.py` 的 `VERSION` 仍为 v1.9.11，未删除/未移动任何现有文件，未改动 `vwm` 源码逻辑，未执行 `git init` 与提交）**：① **新增 `.gitignore`**——按七类分组收敛红线：部署数据（`vaultwarden/` 整个部署目录；`vwm/vaultwarden/` 开发期遗留测试部署，内含 `.env` 与 `ssl` 私钥）、本地配置（`config.json`（不带斜杠，任意层级生效，覆盖 `vwm/config.json`）、`dist/config.json`、`config.json.bak-*`）、构建产物（`build/`、`dist/*.exe`、`*.spec`、`build_*.log`）、日志（`*.log`、`*.log.[0-9]*`）、Python 缓存与虚拟环境（`__pycache__/`、`*.pyc`、`*.pyo`、`*.pyd`、`.venv/`、`venv/`、`env/`、`.pytest_cache/`）、系统与编辑器（`Thumbs.db`、`ehthumbs.db`、`Desktop.ini`、`.DS_Store`、`.idea/`、`.vscode/*` + `!.vscode/*.example.json` 保留示例）、临时与备份（`temp/`、`tmp/`、`*.tmp`、`*.bak-*`、`*.swp`、`*.enc`）；② **新增 `config.example.json`**——由项目根真实 `config.json`（968B）脱敏而来，保留全部 26 个配置键与键序：`vaultwarden_dir` 由 `E:\yscl\vaultwarden-manager\vaultwarden` 改为相对路径 `vaultwarden`，`ssl_dir`/`backup_dir` 同步改为 `vaultwarden/ssl`、`vaultwarden/backup`，`port` 取默认 `44444`、`domain` 取 `https://localhost:44444`，`quit_confirm_skip` 复位 `false`、`quit_default_action` 复位 `tray`、`last_exit_service_running` 复位 `false`、`auto_restore_service` 复位 `true`；下载地址改用公网 GitHub 官方地址（示例值非本机特有），JSON 严格合法（无注释），`load_config()` 可直接读取（相对路径以程序目录为基准展开）；③ **新增 `LICENSE`**——MIT 协议标准全文，版权行为 `Copyright (c) 2026 杨爽工作室 (Yang Shuang Studio)`；④ **新增 `CHANGELOG.md`**——Keep a Changelog 中文格式，只写对外可感知的功能/变更/修复/安全，不贴内部实现与验证脚本细节，收录 v1.9.11（赞助区迁入关于窗口、二维码内置、主窗口高度回落）、v1.9.10（局域网 IP 误选虚拟网卡修复、异步探测、打包瘦身 −33.9%）、v1.9.9（浏览器插件连接分区、设置窗口滚动布局）、v1.9.8（端口自动切换、状态记忆与自动恢复）、v1.9.7（统一图标）、v1.9.6（赞助卡片二维码）、v1.9.5（备份密码卡顿修复、自选保存位置）、v1.9.4（部署持久置灰）、v1.9.3（重复打开提示）、v1.9.2（幽灵托盘图标）、v1.9.1（退出非阻塞）、v1.9.0（赞助卡片）、v1.8.9（托盘加固 + 操作日志落盘）、v1.8.8（PBKDF2 600k + 完整性校验 + 恶意备份防护 + 弱密码拦截）、v1.8.7（关于窗口制作人/工具）、v1.8.6（关于窗口精简）、v1.8.5（设置/关于窗口），v1.0.0–v1.8.4 指向本手册 §8；⑤ **新增 `CONTRIBUTING.md`**——Windows 10/11 + Python 3.11+、依赖三条、`python vaultwarden_manager.py` 本地运行、打包命令**原样复用 §6 固化版本（含 `--clean` 与全部 `--exclude-module`，并注明漏写会导致 exe 膨胀约 50%）**、提交前自检（全部 `.py` 走 `python -m py_compile`；`tests\` 下 10 个关键回归脚本对照表）、代码约定（全中文文案、统一按钮/文字配色、端口禁止硬编码只能来自 `config.json`、模块单向依赖、配置向后兼容、三条红线）、禁交清单（部署目录/`.env`/`db.sqlite3`/私钥/`config.json`/`*.enc`/构建产物）；⑥ **新增 `SECURITY.md`**——声明为本地自建管理工具、不收集不上传任何数据、唯一网络访问为用户主动触发的下载与浏览器跳转；给出部署目录敏感文件清单（`data\db.sqlite3`、`.env` 的 `ADMIN_TOKEN`、`rsa_key.pem`、`ssl\key.pem`）、严禁入库表格、误提交后的应急处置（换 token、重签证书、清历史）、安全设计取舍（自签证书仅适用本地、备份密码不落盘且不可找回、`ADMIN_TOKEN` 首启生成提示一次、不以管理员运行）、漏洞反馈用占位符（邮箱 `<在此填写你的联系邮箱>` 或平台私密报告）；⑦ **改写 `README.md`**（147 行 → 229 行）为开源首页——版本头、项目简介与适用人群、按 6 类归并的 33 条功能特性表（部署运维 8 / 访问与地址 4 / 备份恢复 3 / 网络与端口 4 / 日志审计 4 / 配置与界面 10，不逐条流水账）、截图占位 `![主界面](assets/preview.png)`（`assets\preview.png` 113,593B 已存在）、系统要求表、快速开始双路径（Releases exe：新建空目录 → 一键部署 6 步自动行为表 → 打开 Web/面板 → 浏览器扩展登录 → 首次备份；源码运行）、配置说明（`Copy-Item config.example.json config.json` + 全字段表 + 相对路径说明）、构建方法（§6 命令原样 + 三条注意事项）、目录结构树、测试（8 个常用回归脚本命令）、版本与更新、参与贡献、许可证（MIT + 版权行）、免责声明（非官方第三方工具、不建议公网暴露、密码库安全自负、请验证恢复流程、下载第三方二进制需自行确认来源、按现状提供不担责）；⑧ **同步 §2 目录结构**——入口文件后补入 `config.example.json`、`.gitignore`、`LICENSE`、`README.md`、`CHANGELOG.md`、`CONTRIBUTING.md`、`SECURITY.md` 七条说明；末尾新增本条记录。**验证**：`.gitignore` / `config.example.json` / `LICENSE` / `CHANGELOG.md` / `CONTRIBUTING.md` / `SECURITY.md` 六个新文件均已落盘；`python -c "json.load(open('config.example.json'))"` 解析通过且键集合与项目根 `config.json` 完全一致（26 键）；README/CHANGELOG/CONTRIBUTING/SECURITY 均为 UTF-8 中文 Markdown；未触碰正式部署 `vaultwarden\`（含 `.env`、`data\db.sqlite3`、`ssl` 私钥）与本机 `config.json`；`vwm` 源码零改动。 |
| v1.9.11-privacy | 2026-11-09 | Marvis file-agent | **开源前敏感信息脱敏（文档 / 测试脚本 / 源码注释，逻辑零变更，`VERSION` 仍为 v1.9.11）**：① **DEV.md 真实内网 IP 全量替换为 RFC 5737 文档保留段占位**——本机真实局域网地址 → `198.51.100.10`、其默认网关 → `198.51.100.1`、Hyper-V `Default Switch` 虚拟网卡地址 → `192.0.2.1`、APIPA 链路本地地址 → `169.254.10.20`（原文真实地址不再保留于文档），共 16 处；占位地址沿用原排序关系（`192.0.2.1` 仍字典序靠前，§4.13 缺陷根因说明与排序示例保持成立），`8.8.8.8` / `114.114.114.114` / `223.5.5.5`（公共 DNS）与 `127.0.0.1`（回环）作为协议说明保留；真机实测数值（评分 165、探测 0.043 s）保留原始记录，脱敏后占位网段与打分规则（私网段加分）的对应关系不再严格一致。② **tests 硬编码根路径改为可移植写法**——`verify_quit_v192.py`（`ROOT`）、`verify_si_live.py`（`BASE`）、`verify_si_orphan.py`（`BASE`）由 `r"E:\yscl\vaultwarden-manager"` 改为 `Path(__file__).resolve().parent.parent` 动态求值（均落在项目根目录）；`verify_sponsor_qr_v196.py` 的外部项目路径 `E:\yscl\shuage-coin-helper\website\ewm\ewmsk.png` 改为项目内 `assets/sponsor_qr.png` 相对定位，并新增两道保护：缺图或当前版本已无 `vwm.app.SPONSOR_QR_PATH`（v1.9.11 起改为 `assets/sponsor_qr.png` + `_sponsor_qr_file()`）时打印 `[SKIP]` 提示后 `sys.exit(0)`，不再抛 `AttributeError`；`verify_about_sponsor_v1911.py` / `verify_tray_smoke_v1911.py` 的测试夹具 IP 同步改为 `198.51.100.10`。③ **`dist\config.json` 去绝对路径**——`vaultwarden_dir` / `ssl_dir` / `backup_dir` 改为相对路径 `vaultwarden` / `vaultwarden/ssl` / `vaultwarden/backup`（与 `config.example.json` 同风格），其余字段不变。**相对路径解析基准实测结论**：`vwm/config.py` 的 `app_dir()` 决定 `CONFIG_PATH`（打包后为 exe 同级 `config.json`），但 `_migrate_legacy_paths()` 用 `Path(old_raw).expanduser().resolve()` 求值，**相对路径按进程当前工作目录（CWD）解析而非 config/exe 所在目录**；实测 `CWD=dist` → `dist\vaultwarden`，`CWD=项目根` → 项目根 `vaultwarden`，`CWD=System32` → `System32\vaultwarden`。因此常规启动（双击/快捷方式工作目录为 exe 目录）解析正确；若从其它工作目录启动且该目录下存在同名 `vaultwarden` 目录，会触发一次迁移复制并把配置改写为 exe 目录绝对路径。如需彻底消除该 CWD 依赖，建议在 `_migrate_legacy_paths()` 内对非绝对路径改按 `APP_DIR` 拼接后重新打包（本次仅脱敏，未改逻辑、未重新打包）。④ **`vwm/network.py` 两处注释中的真实 IP 同步改为占位**（`192.0.2.1` / `198.51.100.10`，纯注释改动、逻辑零不变，已打包 exe 无需重打）。⑤ 七个改动脚本 `python -m py_compile` 全部通过，`verify_sponsor_qr_v196.py` 实跑输出 `[SKIP]` 且退出码 0。⑥ `vaultwarden\` 正式部署目录（`.env` / `data` / `ssl` / `backup`）本轮零改动，未删除任何文件。 |
| v1.9.12 | 2026-11-10 | Marvis file-agent | **设置窗口新增「管理员」分区（「获取令牌」+「打开管理面板」）**：`vwm/service.py` 新增三个**只读**函数——`resolve_deploy_dir(cfg, app_dir=None)` 把 `vaultwarden_dir` 解析为绝对路径，**相对路径一律锚定 APP_DIR（打包=exe 目录，源码=项目根），不读进程 CWD**（规避 `_migrate_legacy_paths` 按 CWD 求值导致目录漂移的已知风险点），空值/非法值回落 `APP_DIR/vaultwarden`；`mask_token(token)` 统一打码口径「前 4 位 + 固定 8 星号 + 长度」，如 `Lsbf********（43 位）`；`read_admin_token(cfg, app_dir=None)` 只读部署目录 `.env` 解析 `ADMIN_TOKEN`（正则 `^\s*ADMIN_TOKEN\s*=(.*)$`、去首尾空白、兼容成对引号、多行取第一个非空值），返回 `{ok, code, token, masked, env_path, message}`，`code` 五态 `ok / no_env / no_token / argon2 / read_error`，**任何异常都转中文 message 不向上抛出**；**只读语义**：不生成令牌、不改 `.env`、不调用 `logs` 任何函数（令牌不落盘不落日志）。`vwm/ui.py` `open_settings_dialog` 在「浏览器插件连接」之后、「当前信息（只读）」之前插入第五张卡片 `card_admin`（白底卡片，标题 + 两行说明、状态区 `admin_mask_var` 初值「令牌：尚未获取」、`ext_btn_cfg` 次级样式「获取令牌」「打开管理面板」两按钮、提示行 `admin_tip_var`、底部安全说明文字），配色沿用 `TEXT_PRIMARY/TEXT_SECONDARY/TEXT_HINT`，随 `Canvas + Scrollbar` 滚动，不破坏既有分区与底部「保存设置/取消」；「获取令牌」经 `clipboard_clear` + `clipboard_append` + `update_idletasks` 写系统剪贴板（不新增依赖），**界面只写打码串**、提示「已复制到剪贴板（…）」并回落状态栏绿字，`tk.TclError` 时提示剪贴板不可用；「打开管理面板」按 `cfg["port"]`（缺省回落 `DEFAULT_CONFIG`）与 `admin_path`（自动补前导 `/`）+ 协议探测结果拼 `%s://localhost:%s%s` 交 `webbrowser.open`，与插件连接分区打开逻辑同源；异常分支均中文提示——`.env` 缺失「未找到 .env 文件…请先在主界面完成『一键部署』」、无 `ADMIN_TOKEN`「该配置未设置管理员令牌…可重新『一键部署』自动生成」、`$argon2` 哈希「无法反解，请使用原始密码登录」、读取失败/权限不足给原因；分区编号 ④→⑤、⑤→⑥；`VERSION` → v1.9.12。验证：新增 `tests\verify_admin_token_v1912.py` **59/59 PASS**（A 常量与接口 / B 正常读取含 CRLF·带引号·多行取首个非空·只读不改 `.env` / C 相对路径按 APP_DIR 解析且 CWD 下同名目录令牌不被读到 / D 异常六分支（缺 `.env`、无 `ADMIN_TOKEN`、值为空、argon2 哈希、权限拒绝、目录非法）/ E 打码规范 / F 只读与日志安全（源码无写盘、无 `append_manager_log`、部署目录未产生 `manager.log`）/ G 真机设置窗口（分区齐全、两按钮、初始文案、点击后打码上屏、界面不含完整令牌、剪贴板与 `.env` 值一致、状态栏提示不含令牌、URL 按 `port`+协议拼接、滚动区域覆盖新增分区、保存/取消在位、关闭无残留）/ G18 HTTP 协议分支）；`py_compile` 对 `vwm/service.py`、`vwm/ui.py` 通过，`import` 校验 `ui.VERSION == "v1.9.12"`；本轮**未重新打包 exe**、未触碰任何部署数据；同步更新 §1 功能表（19）、§2 目录结构、§4.0 模块表、§4.1、§4.8、§8。 |
*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*
