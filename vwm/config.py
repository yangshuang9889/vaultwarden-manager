# -*- coding: utf-8 -*-
"""
配置管理模块（v1.8.0）
职责：程序运行路径定位、默认配置、config.json 读写、旧固定路径迁移、
      端口持久化（同步 config.json 与部署目录 .env 的 ROCKET_PORT/DOMAIN）。
依赖：仅标准库。
"""
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


def app_dir() -> Path:
    """程序所在目录：开发模式为脚本目录，打包后为 exe 所在目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = app_dir()
CONFIG_PATH = APP_DIR / "config.json"

def build_default_config() -> dict:
    """运行时生成默认配置：部署目录跟随程序运行目录（便携化）。

    v1.8.2：端口不写死，默认端口字面量仅存于本函数一处（default_port），
    domain 由 port 派生；运行时全链路（URL 拼接 / 探测 / 部署 / UI / .env 同步）
    一律读取 cfg['port']，禁止在其它位置残留 44444/8000 等硬编码。
    """
    vw_dir = APP_DIR / "vaultwarden"
    default_port = 44444  # 唯一端口字面量：config 默认配置权威值
    return {
        "vaultwarden_dir": str(vw_dir),
        "exe_name": "vaultwarden.exe",
        "port": default_port,
        "ssl_dir": str(vw_dir / "ssl"),
        "cert_file": "cert.pem",
        "key_file": "key.pem",
        "backup_dir": str(vw_dir / "backup"),
        "log_file": "vaultwarden.log",
        "err_log_file": "vaultwarden.err.log",
        "log_lines": 300,
        "log_max_mb": 10,
        "log_noise_keywords": ["tls handshake", "HSTS"],
        "vw_download_url": "https://github.com/nextyancc/Vaultwarden-Windows-Binary/releases/download/1.37.5-windows/vaultwarden-1.37.5-windows-x64.exe",
        "vw_download_timeout": 120,
        "vw_webvault_download_url": "https://github.com/dani-garcia/bw_web_builds/releases/download/v2026.10.1/bw_web_v2026.10.1.tar.gz",
        "vw_webvault_download_timeout": 180,
        "status_check_ms": 3000,
        "cert_days": 3650,
        "domain": f"https://localhost:{default_port}",  # v1.8.2：由 port 派生，不再独立写死端口
        "admin_path": "/admin",
        "quit_confirm_skip": False,      # v1.8.3：勾选「记住我的选择」后置 True，退出直接执行记忆动作不再询问
        "quit_default_action": "tray",   # v1.8.3：记忆的退出动作："tray"=最小化到托盘 / "quit"=退出程序
        # v1.9.8：服务运行状态记忆——退出时记录服务是否在运行，下次启动按需自动恢复启动
        "last_exit_service_running": False,  # 仅「程序退出时服务处于运行状态」置 True
        "auto_restore_service": True,        # 设置开关：是否在下次启动时自动恢复服务（默认开启）
        # v1.9.9：浏览器插件获取入口（设置窗口「浏览器插件连接」分区使用；
        # 旧配置缺该键时由 load_config 用此处默认值自动补齐，用户可自行替换为镜像/商店链接）
        "ext_edge_url": "https://microsoftedge.microsoft.com/addons/search/bitwarden",
        "ext_chrome_url": "https://chromewebstore.google.com/search/bitwarden",
    }


DEFAULT_CONFIG = build_default_config()

_migration_notice = ""  # 部署目录迁移提示，GUI 启动后显示到状态栏

def _timestamp_tag() -> str:
    now = datetime.now()
    return f"{now.year}{now.month:02d}{now.day:02d}-{now.hour:02d}{now.minute:02d}{now.second:02d}"

def _migrate_legacy_paths(cfg: dict) -> dict:
    """将旧固定部署路径迁移到 APP_DIR/vaultwarden（便携化）。

    1) 旧 config.json 备份为 config.json.bak-<时间戳>；
    2) 旧部署目录存在且新目录无数据时，把旧目录内容复制到新目录（保留旧目录）；
    3) 更新 config 指向新路径。新目录已有数据时不重复迁移。
    """
    global _migration_notice
    new_dir = APP_DIR / "vaultwarden"
    new_path = str(new_dir)
    old_raw = str(cfg.get("vaultwarden_dir", "") or "").strip()
    if not old_raw:
        cfg["vaultwarden_dir"] = new_path
        cfg["ssl_dir"] = str(new_dir / "ssl")
        cfg["backup_dir"] = str(new_dir / "backup")
        return cfg
    old_dir = Path(old_raw).expanduser()
    try:
        same_path = str(old_dir.resolve()).casefold() == str(new_dir.resolve()).casefold()
    except OSError:
        same_path = False
    if same_path:
        return cfg

    # 1) 备份旧 config
    bak_path = None
    try:
        bak_path = CONFIG_PATH.with_name(f"config.json.bak-{_timestamp_tag()}")
        shutil.copy2(CONFIG_PATH, bak_path)
    except OSError:
        bak_path = None

    # 2) 复制旧部署目录内容（仅当新目录不存在数据，二次运行不重复迁移）
    copied = False
    try:
        new_has_data = new_dir.exists() and any(new_dir.iterdir())
        if old_dir.is_dir() and not new_has_data:
            _migration_notice = "正在迁移部署目录..."
            shutil.copytree(old_dir, new_dir)
            copied = True
    except OSError:
        copied = False

    # 3) 更新 config 指向新路径
    cfg["vaultwarden_dir"] = new_path
    cfg["ssl_dir"] = str(new_dir / "ssl")
    cfg["backup_dir"] = str(new_dir / "backup")

    bak_tip = f"，旧配置已备份为 {bak_path.name}" if bak_path else ""
    if copied:
        _migration_notice = (
            f"部署目录已迁移至 {new_path}，旧目录已保留{bak_tip}，"
            "如需切换请修改 config.json"
        )
    else:
        _migration_notice = (
            f"部署目录已指向 {new_path}，旧目录已保留{bak_tip}，"
            "如需切换请修改 config.json"
        )
    return cfg

def load_config() -> dict:
    """读取 config.json；文件缺失或损坏时自动重建默认配置；旧固定路径自动迁移。"""
    if not CONFIG_PATH.exists():
        _write_default_config()
        return dict(DEFAULT_CONFIG)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        _write_default_config()
        return dict(DEFAULT_CONFIG)
    merged = dict(DEFAULT_CONFIG)
    merged.update(data)  # 用户配置优先，缺省字段用默认值补齐
    migrated = _migrate_legacy_paths(merged)
    if (
        migrated.get("vaultwarden_dir") != data.get("vaultwarden_dir")
        or migrated.get("ssl_dir") != data.get("ssl_dir")
        or migrated.get("backup_dir") != data.get("backup_dir")
    ):
        try:
            CONFIG_PATH.write_text(
                json.dumps(migrated, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass
    return migrated

def _write_default_config() -> None:
    try:
        CONFIG_PATH.write_text(
            json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass

def save_config(cfg: dict) -> bool:
    """将 cfg 完整写回 config.json（v1.8.3：退出记忆等运行时字段持久化）。
    返回是否写入成功；失败时由调用方提示，不抛异常。"""
    try:
        CONFIG_PATH.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True
    except OSError:
        return False

def apply_quit_memory(cfg: dict, action: str) -> tuple:
    """v1.8.3：持久化退出记忆（确认框勾选「记住我的选择」后调用）。

    action: "tray"=最小化到托盘 / "quit"=退出程序。
    置 quit_confirm_skip=True 并记录 quit_default_action，写回 config.json。
    返回 (cfg, 提示文本)；写盘失败时提示记忆未持久化（本次仍生效）。
    """
    cfg["quit_confirm_skip"] = True
    cfg["quit_default_action"] = action
    ok = save_config(cfg)
    if action == "tray":
        tip = "已记住退出方式为「最小化到托盘」，下次退出不再询问"
    else:
        tip = "已记住退出方式为「退出程序」，下次退出不再询问"
    if not ok:
        tip += "（config.json 写入失败，记忆未持久化，下次仍会询问）"
    else:
        tip += "（如需恢复询问：按住 Shift 点退出，或修改 config.json 的 quit_confirm_skip 为 false）"
    return cfg, tip

def clear_quit_memory(cfg: dict) -> tuple:
    """v1.8.3：清除退出记忆（Shift 强制询问后未勾选「记住」时调用），恢复每次询问。"""
    cfg["quit_confirm_skip"] = False
    ok = save_config(cfg)
    tip = "已恢复每次退出询问（退出记忆已清除）"
    if not ok:
        tip += "（config.json 写入失败，清除未持久化）"
    return cfg, tip

def update_port(cfg: dict, new_port: int) -> tuple:
    """更新 config.json 的 port/domain，并同步修改部署目录 .env 的 ROCKET_PORT。
    保留 .env 原有内容与换行风格；已存在 ROCKET_PORT 则原位替换，不存在则追加。"""
    try:
        new_port = int(new_port)
    except (TypeError, ValueError):
        return False, "端口号无效：必须为 1-65535 之间的数字"
    if not (1 <= new_port <= 65535):
        return False, "端口号无效：必须在 1-65535 之间"
    old_port = cfg["port"]
    cfg["port"] = new_port
    cfg["domain"] = f"https://localhost:{new_port}"
    # 1) 更新 config.json
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        return False, f"更新 config.json 失败：{e}"
    # 2) 更新 .env（保留原内容与换行风格）
    env_path = Path(cfg["vaultwarden_dir"]) / ".env"
    try:
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8", newline="") as f:
                text = f.read()
        else:
            text = ""
    except OSError as e:
        return False, f"读取 .env 失败：{e}"
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    found = False
    new_lines = []
    for line in lines:
        if re.match(r"^\s*ROCKET_PORT\s*=", line):
            new_lines.append(re.sub(r"^(\s*ROCKET_PORT\s*=\s*)\S*", rf"\g<1>{new_port}", line))
            found = True
        else:
            new_lines.append(line)
    if not found:
        if new_lines and not new_lines[-1].endswith(("\n", "\r")):
            new_lines[-1] += nl
        new_lines.append(f"ROCKET_PORT={new_port}{nl}")
    # 2.5) 同步 .env 的 DOMAIN（v1.7.0：避免改端口后 .env 里仍指向旧端口）
    new_domain = f"https://localhost:{new_port}"
    found_domain = False
    domain_lines = []
    for line in new_lines:
        if re.match(r"^\s*DOMAIN\s*=", line):
            domain_lines.append(re.sub(r"^(\s*DOMAIN\s*=\s*)\S*", rf"\g<1>{new_domain}", line))
            found_domain = True
        else:
            domain_lines.append(line)
    if not found_domain:
        if domain_lines and not domain_lines[-1].endswith(("\n", "\r")):
            domain_lines[-1] += nl
        domain_lines.append(f"DOMAIN={new_domain}{nl}")
    new_lines = domain_lines
    try:
        with open(env_path, "w", encoding="utf-8", newline="") as f:
            f.write("".join(new_lines))
    except OSError as e:
        return False, f"更新 .env 失败：{e}"
    return True, (
        f"端口已从 {old_port} 修改为 {new_port}，config.json 与 .env（ROCKET_PORT/DOMAIN）已同步更新\n"
        "需重启服务后生效（停止 → 启动）"
    )

