# -*- coding: utf-8 -*-
"""
部署下载模块（v1.8.0）
职责：核心文件 / web-vault 前端自动下载与解压、一键部署编排
      （下载 → 证书 → 信任 → 启动 → 端口轮询）。
依赖：network、service、cert；仅标准库其余依赖。
"""
import shutil
import tarfile
import time
import urllib.request
from pathlib import Path

from .cert import add_system_trust, generate_certificate
from .network import is_port_open
from .service import (ensure_admin_token, ensure_port_available,
                      is_process_running, start_service)

def download_file(url: str, dest: Path, timeout: float = 120.0, progress_cb=None) -> tuple:
    """用标准库 urllib 下载文件到 dest。返回 (ok, msg)；progress_cb(downloaded, total) 报告进度。

    下载失败时清理半成品文件；total 未知（无 Content-Length）时为 0。
    """
    dest = Path(dest)
    downloaded = 0
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "VaultwardenManager/1.4"})
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as f:
            total = 0
            try:
                total = int(resp.headers.get("Content-Length") or 0)
            except (TypeError, ValueError):
                total = 0
            last_report = -1
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                # 节流：每 512KB 报告一次，避免刷爆消息队列
                if progress_cb and downloaded // (512 * 1024) != last_report:
                    last_report = downloaded // (512 * 1024)
                    progress_cb(downloaded, total)
            if progress_cb:
                progress_cb(downloaded, total)
    except Exception as e:  # noqa: BLE001
        try:
            if dest.exists():
                dest.unlink()  # 清理半成品，避免误判下载成功
        except OSError:
            pass
        return False, f"下载失败：{e}"
    return True, f"下载完成：{dest.name}（{downloaded / 1024 / 1024:.1f} MB）"

def extract_webvault_tarball(tgz_path: Path, vw_dir: Path) -> tuple:
    """解压 web-vault 的 tar.gz 到部署目录，返回 (ok, msg)。

    顶层目录处理：压缩包内含 web-vault/ 顶层目录时解到部署目录根（vw_dir）；
    为散文件（顶层无 web-vault 目录）时解到 vw_dir/web-vault/。
    解压完成后校验 vw_dir/web-vault/index.html 存在才算成功。
    安全校验：拒绝绝对路径、含 .. 的穿越路径与符号链接成员。
    """
    vw_dir = Path(vw_dir)
    try:
        with tarfile.open(tgz_path, "r:gz") as tar:
            members = tar.getmembers()
            if not members:
                return False, "解压失败：压缩包为空"
            # 安全检查：绝对路径 / .. 穿越 / 符号链接 / 硬链接一律拒绝
            for m in members:
                name = m.name.replace("\\", "/").lstrip("./")
                if name.startswith("/") or ".." in name.split("/"):
                    return False, "解压失败：压缩包包含非法路径，已拒绝解压"
                if m.issym() or m.islnk():
                    return False, "解压失败：压缩包包含链接成员，已拒绝解压"
            # 顶层目录判断：存在名为 web-vault（或 web-vault/）的顶层条目
            has_top_level = any(
                m.name.replace("\\", "/").lstrip("./").split("/", 1)[0] == "web-vault"
                for m in members
            )
            target = vw_dir if has_top_level else vw_dir / "web-vault"
            target.mkdir(parents=True, exist_ok=True)
            for m in members:
                rel = m.name.replace("\\", "/").lstrip("./")
                parts = rel.split("/")
                if has_top_level:
                    if parts[0] != "web-vault":
                        continue  # 顶层 web-vault 包内不应有其他根条目，跳过
                if not parts:
                    continue  # 顶层目录条目本身
                dest = target.joinpath(*parts)
                if m.isdir():
                    dest.mkdir(parents=True, exist_ok=True)
                elif m.isfile():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with tar.extractfile(m) as src, open(dest, "wb") as out:
                        if src is not None:
                            shutil.copyfileobj(src, out)
                # 其余类型（设备等）跳过
    except Exception as e:  # noqa: BLE001
        return False, f"解压失败：{e}"
    if (vw_dir / "web-vault" / "index.html").exists():
        return True, "网页版解压完成：web-vault/index.html 就绪"
    return False, "解压完成但缺少 web-vault/index.html，网页版不可用"

def deploy_service(cfg: dict, timeout: float = 15.0, progress_cb=None, stage_cb=None) -> tuple:
    """一键部署：核心文件缺失时按 vw_download_url 自动下载；web-vault 前端缺失时按
    vw_webvault_download_url 自动下载 tar.gz 并解压（失败不阻塞启动）；无证书时自动生成自签名证书
    并添加系统信任（失败不阻塞启动）；随后启动并轮询等待端口开放。

    返回 (ok, msg)。下载进度通过 progress_cb(downloaded, total) 上报（须在后台线程中调用）；
    下载/校验完成、进入启动与端口轮询阶段时通过 stage_cb("deploy") 通知（须在后台线程中调用）；
    进入网页版下载阶段时通过 stage_cb("webvault") 通知；
    进入证书生成 / 添加系统信任阶段时分别通过 stage_cb("cert") / stage_cb("trust") 通知。
    核心文件缺失且未配置下载地址时中止并给出明确提示。
    """
    exe_name = cfg["exe_name"]
    # v1.9.8：部署前先做端口占用检测，被其它程序占用则自动切换到随机可用端口
    # （同步 config.json 的 port/domain 与部署目录 .env 的 ROCKET_PORT/DOMAIN）。
    # 必须放在读取 port 之前，后续启动与端口轮询一律使用切换后的端口。
    port_tip = ""
    ok_port, msg_port, switched = ensure_port_available(cfg)
    if not ok_port:
        return False, msg_port
    if switched:
        port_tip = msg_port
    port = int(cfg["port"])
    vw_dir = Path(cfg["vaultwarden_dir"])
    exe_path = vw_dir / exe_name

    if is_process_running(exe_name) and is_port_open(port):
        return False, "服务已在运行，无需重复部署"

    # 核心文件缺失 → 尝试自动下载
    if not exe_path.exists():
        url = str(cfg.get("vw_download_url", "")).strip()
        if not url:
            return False, "核心文件缺失且未配置下载地址，请在 config.json 的 vw_download_url 填入下载地址"
        ok, msg = download_file(url, exe_path, float(cfg.get("vw_download_timeout", 120)), progress_cb)
        if not ok:
            return False, msg
        try:
            if not exe_path.exists() or exe_path.stat().st_size <= 1024 * 1024:
                return False, "下载完成但文件校验失败（不存在或小于 1MB），请检查下载地址是否正确"
        except OSError:
            return False, "下载完成但文件校验失败（无法读取文件大小），请检查下载地址是否正确"

    # Web Vault 前端缺失 → 尝试自动下载并解压（失败不阻塞启动，仅在返回消息中提示）
    webvault_tip = ""
    if not (vw_dir / "web-vault" / "index.html").exists():
        webvault_tip = "网页版未安装，服务已启动（仅 API 可用）"
        wv_url = str(cfg.get("vw_webvault_download_url", "") or "").strip()
        if wv_url:
            if stage_cb:
                stage_cb("webvault")  # 进入网页版下载阶段（界面提示"正在下载网页版…"）
            tgz_path = vw_dir / "web-vault.tar.gz"
            ok, msg = download_file(wv_url, tgz_path, float(cfg.get("vw_webvault_download_timeout", 180)), progress_cb)
            if ok:
                ok2, msg2 = extract_webvault_tarball(tgz_path, vw_dir)
                if ok2:
                    webvault_tip = ""  # 网页版安装成功
                # 解压失败保留 webvault_tip，不阻塞启动
            try:
                if tgz_path.exists():
                    tgz_path.unlink()  # 清理下载包，失败不影响流程
            except OSError:
                pass

    # v1.7.2：自动完成证书生成 + 添加系统信任（无证书才生成、已有跳过；失败不阻塞启动）
    cert_tip = ""
    trust_tip = ""
    cert_file_p = Path(cfg["ssl_dir"]) / cfg["cert_file"]
    key_file_p = Path(cfg["ssl_dir"]) / cfg["key_file"]
    if cert_file_p.exists() and key_file_p.exists():
        cert_tip = "证书已存在，跳过生成"
    else:
        if stage_cb:
            stage_cb("cert")  # 进入证书生成阶段（界面提示"正在生成证书…"）
        ok_cert, msg_cert = generate_certificate(cfg)
        if ok_cert and cert_file_p.exists():
            cert_tip = "已自动生成自签名证书"
        else:
            cert_tip = f"警告：证书生成失败（{msg_cert}）"
    if cert_file_p.exists():
        if stage_cb:
            stage_cb("trust")  # 进入添加信任阶段（界面提示"正在添加系统信任…"）
        ok_trust, msg_trust = add_system_trust(cfg)
        if ok_trust:
            trust_tip = "已自动添加系统信任"
        else:
            trust_tip = f"警告：添加系统信任失败（{msg_trust}）"
    else:
        trust_tip = "警告：证书缺失，未添加系统信任"

    if stage_cb:
        stage_cb("deploy")  # 下载/校验完成，进入启动与端口轮询阶段（界面切换为不定进度）
    admin_token, admin_generated = ensure_admin_token(cfg)  # v1.7.6：缺失时自动生成 ADMIN_TOKEN（start_service 内幂等复用）
    ok, msg = start_service(cfg)
    if not ok:
        return False, msg
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(1.0)
        if is_process_running(exe_name, str(vw_dir)) and is_port_open(port):
            ok_msg = f"部署成功：{exe_name} 已运行，端口 {port} 已开放（{cfg['domain']}）"
            if port_tip:
                ok_msg = port_tip + "；" + ok_msg
            if cert_tip:
                ok_msg += f"；{cert_tip}"
            if trust_tip:
                ok_msg += f"；{trust_tip}"
            if webvault_tip:
                ok_msg += f"；{webvault_tip}"
            if admin_generated and admin_token:
                ok_msg += (f"；管理面板 https://localhost:{port}{cfg.get('admin_path', '/admin')}"
                           f" 登录口令（ADMIN_TOKEN）：{admin_token}，请妥善保存")
            return True, ok_msg
    # 超时后最后再确认一次，避免临界点误报
    if is_process_running(exe_name, str(vw_dir)) and is_port_open(port):
        ok_msg = f"部署成功：{exe_name} 已运行，端口 {port} 已开放（{cfg['domain']}）"
        if port_tip:
            ok_msg = port_tip + "；" + ok_msg
        if cert_tip:
            ok_msg += f"；{cert_tip}"
        if trust_tip:
            ok_msg += f"；{trust_tip}"
        if webvault_tip:
            ok_msg += f"；{webvault_tip}"
        if admin_generated and admin_token:
            ok_msg += (f"；管理面板 https://localhost:{port}{cfg.get('admin_path', '/admin')}"
                       f" 登录口令（ADMIN_TOKEN）：{admin_token}，请妥善保存")
        return True, ok_msg
    return False, f"部署超时：{int(timeout)} 秒内端口 {port} 未开放，请刷新日志查看服务状态"

