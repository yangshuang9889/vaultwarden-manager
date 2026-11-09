---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: b39d940f30a0c1cf547a23c927f28498_8d8e85ecdc1611f1bff2525400cd780f
    ReservedCode1: On8/nJ3odUKaaGTOPzsasgKv0b61ng8LqktExZce1Yl3IQSpz0qU+wuIs0JC9/F5FP9zsdd1x5mL9c9pIwXYIA4puH+Cmey45xwrVrCq7w8pgRtte0we1zHQ+BnwwM/H5IGRk0n2R4iOYeg7kZA331MgVLfW7uOcAF/4CGhI+Yu3yfGigmMjKpA7bto=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: b39d940f30a0c1cf547a23c927f28498_8d8e85ecdc1611f1bff2525400cd780f
    ReservedCode2: On8/nJ3odUKaaGTOPzsasgKv0b61ng8LqktExZce1Yl3IQSpz0qU+wuIs0JC9/F5FP9zsdd1x5mL9c9pIwXYIA4puH+Cmey45xwrVrCq7w8pgRtte0we1zHQ+BnwwM/H5IGRk0n2R4iOYeg7kZA331MgVLfW7uOcAF/4CGhI+Yu3yfGigmMjKpA7bto=
---

# 参与贡献

感谢您关注 VaultwardenManager。本文说明本地开发、自检与提交的基本约定，请在提交前逐项确认。

## 1. 行为准则

- 本项目是自建 Vaultwarden 的 Windows 桌面管理工具，界面与提示文案**全部使用中文**，不接受英文界面文案。
- 讨论与提交请聚焦技术问题，保持克制、具体、可复现。

## 2. 开发环境

| 项目 | 要求 |
|---|---|
| 操作系统 | Windows 10 / 11（x64） |
| Python | 3.11 及以上 |
| GUI | 标准库 `tkinter`（随 Python 安装，无需额外安装） |
| 其他 | 无需 Node.js、无需前端构建工具 |

获取代码：

```powershell
git clone <你的仓库地址> vaultwarden-manager
cd vaultwarden-manager
```

## 3. 安装依赖

```powershell
pip install -r requirements.txt
```

依赖仅三条：`cryptography`（备份加密与证书生成）、`pystray`（系统托盘）、`pillow`（托盘与二维码图标处理）。

打包需要额外安装 PyInstaller：

```powershell
pip install pyinstaller
```

## 4. 本地运行

```powershell
python vaultwarden_manager.py
```

入口文件是薄转发壳（`from vwm.app import main`），实际逻辑在 `vwm` 包内：

- `vwm/config.py` 配置读写与默认值；`vwm/service.py` 服务启停与状态；`vwm/deploy.py` 一键部署；
  `vwm/cert.py` 证书与系统信任；`vwm/backup.py` 加密备份与恢复；`vwm/logs.py` 日志与操作留痕；
  `vwm/network.py` 地址解析与端口探测；`vwm/ui.py` 弹窗与配色常量；`vwm/app.py` 主程序。

开发模式首次运行会在脚本目录自动生成 `config.json`，并把部署目录默认指向 `<脚本目录>\vaultwarden`。
如需自定义，可把 `config.example.json` 复制为 `config.json` 后按需修改（见 README 的配置说明）。

## 5. 打包

打包命令以 DEV.md 第 6 节为准，`--exclude-module` 列表**必须带全**（否则 exe 会因连带收集无用模块而膨胀约 50%）：

```powershell
cd <项目根目录>
python -m PyInstaller -F -w --noconfirm --clean --icon=assets\app.ico --add-data "assets;assets" --exclude-module numpy --exclude-module numpy.libs --exclude-module yaml --exclude-module bcrypt --exclude-module scipy --exclude-module pandas --exclude-module matplotlib --exclude-module PyQt5 --exclude-module PySide6 --name VaultwardenManager vaultwarden_manager.py
```

产物为 `dist\VaultwardenManager.exe`（单文件、无控制台窗口）。

## 6. 提交前自检

1. **语法编译检查**（全部 Python 文件必须通过）：

   ```powershell
   Get-ChildItem -Recurse -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }
   ```

2. **回归脚本**：`tests\` 下为按版本沉淀的回归脚本，命名规范 `verify_<主题>_v<版本>.py`，
   直接 `python tests\verify_xxx.py` 运行，输出结论含 PASS/FAIL 计数。改动涉及对应模块时必须跑通：

   | 脚本 | 覆盖范围 |
   |---|---|
   | `tests\verify_port_guard_v198.py` | 端口占用探测与自动切换 |
   | `tests\verify_restore_v198.py` | 服务状态记忆与自动恢复 |
   | `tests\verify_backup_v195.py` | 加密备份格式、篡改与恶意备份防护 |
   | `tests\verify_backup_gui_v195.py` | 备份界面流程（保存位置、取消、忙碌文案） |
   | `tests\verify_deploy_lock_v194.py` | 一键部署完成后的持久禁用 |
   | `tests\verify_icon_v197.py` | 图标资源与加载链路 |
   | `tests\verify_about_sponsor_v1911.py` | 关于窗口与赞助区 |
   | `tests\verify_single_instance_v193.py` | 单实例互斥与提示框 |
   | `tests\verify_ghost_v192.py` | 托盘残留图标清理 |
   | `tests\verify_quit_v192.py` | 退出链路与清理 |

   真机类脚本（启动真实窗口 / 真实进程）请在无人值守的桌面会话中运行，避免弹窗打断。

3. **打包变更**：若改动影响打包，须按 DEV.md 第 6 节的「打包后功能回归清单」逐项验证。

## 7. 代码与文案约定

- **全中文**：GUI 文案、状态提示、日志摘要、异常提示均为中文；代码注释与 docstring 使用中文。
- **配色与按钮**：所有按钮使用统一蓝底白字（`BTN_BG` / `BTN_BG_ACTIVE`），次级按钮为白底蓝字，
  文字颜色使用 `TEXT_PRIMARY` / `TEXT_SECONDARY` / `TEXT_HINT`，不得自行引入低对比度浅灰。
- **不得硬编码端口**：端口唯一权威来源是 `config.json` 的 `port`，界面拼接、地址解析、部署与 `.env` 同步
  一律运行时读取，默认值只允许出现在 `vwm/config.py` 的 `build_default_config()` 一处。
- **模块单向依赖**：`vwm` 包内模块只允许依赖 `common` 与编号更靠前的兄弟模块，禁止循环导入。
- **配置向后兼容**：新增配置键必须并入默认配置，旧 `config.json` 缺失字段自动补齐，缺键不得报错。
- **三条红线不可破坏**：启动服务时工作目录必须是部署目录（保证 `.env` 生效）；项目路径不得含中文；
  配置文件缺失时必须自动创建默认值而不是抛异常。
- **文档同步**：功能、配置、打包方式变更时同步更新 `DEV.md` 对应章节，并在 `DEV.md` 第 8 节与
  `CHANGELOG.md` 追加记录（日期、版本、变更摘要）。

## 8. 禁止提交的内容（硬性要求）

以下内容**一律不得**出现在提交与 Pull Request 中（`.gitignore` 已覆盖，请勿强行 `git add -f`）：

- 部署目录 `vaultwarden\`（含 `.env` 里的 `ADMIN_TOKEN`、`data\db.sqlite3`、`rsa_key.pem`、
  `ssl\` 私钥与证书、`web-vault\`、运行日志、备份文件）。
- 任何 `config.json`（含本机绝对路径），以及 `*.enc` 备份、`*.pem` / `*.key` 证书私钥。
- 构建产物 `build\`、`dist\*.exe`、`*.spec`、构建与运行日志。
- 虚拟环境、`__pycache__`、编辑器与系统临时文件。

若不确定某文件是否敏感，请先在本地 `git status` 核对，必要时改为在 issue 中粘贴脱敏后的片段。

## 9. 提交信息

建议使用简洁的中文说明，写清「改了什么 + 为什么」，例如：

```
修复局域网地址误选虚拟网卡

设置窗口显示的局域网地址可能取到 Hyper-V 默认交换机，
其它设备无法连接。改为按默认网关与私网网段打分排序。
```

## 10. 安全相关问题

涉及安全漏洞请勿直接开公开 issue，按 [SECURITY.md](SECURITY.md) 的方式反馈。
*（内容由AI生成，仅供参考）*
