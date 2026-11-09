# -*- coding: utf-8 -*-
"""
日志管理模块（v1.8.0）
职责：日志轮转归档、管家操作日志追加、日志尾部读取与噪音过滤。
依赖：仅标准库；rotate_log_if_needed 被 service/logs 复用。
"""
from datetime import datetime
from pathlib import Path

def rotate_log_if_needed(log_path: Path, max_mb: float) -> str:
    """日志轮转：文件超过 max_mb（MB）时归档为 log.1（已存在则后缀依次递增），并新建空日志。

    返回归档后的文件名（如 vaultwarden.log.1）；未触发轮转或失败返回空字符串。
    """
    try:
        size = log_path.stat().st_size
    except OSError:
        return ""
    if size <= max(1, int(max_mb)) * 1024 * 1024:
        return ""
    idx = 1
    while True:
        target = log_path.with_name(f"{log_path.name}.{idx}")
        if not target.exists():
            break
        idx += 1
    try:
        log_path.replace(target)
        log_path.touch(exist_ok=True)  # 新建空日志
        return target.name
    except OSError:
        return ""

def append_manager_log(cfg: dict, action: str, summary: str) -> str:
    """追加一行管家操作日志到部署目录 manager.log，超阈值复用 rotate_log_if_needed 轮转。

    行格式：[时间戳][操作名] 结果摘要。写入失败不影响主流程，返回错误提示；成功返回空串。
    """
    try:
        log_dir = Path(cfg["vaultwarden_dir"])
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "manager.log"
        rotate_log_if_needed(log_path, float(cfg.get("log_max_mb", 10)))
        now = datetime.now()
        ts = f"{now.year}-{now.month:02d}-{now.day:02d} {now.hour:02d}:{now.minute:02d}:{now.second:02d}"
        line = f"[{ts}][{action}] {summary}\n"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
        return ""
    except OSError as e:
        return f"操作日志写入失败：{e}"

def filter_noise_lines(lines: list, keywords: list) -> tuple:
    """按关键词过滤噪音日志行（大小写不敏感）。返回 (保留行列表, 被过滤行数)。"""
    keys = [str(k).strip().lower() for k in keywords if str(k).strip()]
    if not keys:
        return list(lines), 0
    kept = []
    dropped = 0
    for line in lines:
        if any(k in line.lower() for k in keys):
            dropped += 1
        else:
            kept.append(line)
    return kept, dropped

def read_log_tail(cfg: dict, filter_noise: bool = True) -> tuple:
    """读取 vaultwarden.log 末尾 log_lines 行；超过阈值先自动轮转，读取失败给中文提示。

    filter_noise=True 时按 log_noise_keywords 过滤噪音行（如 tls handshake / HSTS）。
    返回 (内容文本, 被过滤噪音行数)。过滤仅影响展示，不修改 vaultwarden.log 原始落盘。
    """
    log_path = Path(cfg["vaultwarden_dir"]) / cfg["log_file"]
    rotated = rotate_log_if_needed(log_path, float(cfg.get("log_max_mb", 10)))
    if not log_path.exists():
        return ("（日志文件不存在：%s）" % log_path, 0)
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        n = int(cfg["log_lines"])
        tail = lines[-n:]
        dropped = 0
        if filter_noise:
            tail, dropped = filter_noise_lines(tail, cfg.get("log_noise_keywords", ["tls handshake", "HSTS"]))
        prefix = f"[日志已轮转归档：{log_path.name} -> {rotated}，已新建空日志]\n" if rotated else ""
        return prefix + "".join(tail), dropped
    except OSError as e:
        return (f"（读取日志失败：{e}，请检查日志文件是否被其他程序占用）", 0)

