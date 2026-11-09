# -*- coding: utf-8 -*-
"""
服务管理模块（v1.8.0）
职责：vaultwarden.exe 进程检测（v1.7.6 路径感知）、.env 运行时同步
      （ROCKET_PORT/DOMAIN/ROCKET_TLS）、ADMIN_TOKEN 自动生成（幂等）、
      服务的启动 / 停止 / 状态判定。
依赖：logs（rotate_log_if_needed）、network（is_port_open）、common。
"""
import json
import re
import secrets
import subprocess
from pathlib import Path

from .common import CREATE_NO_WINDOW
from .logs import rotate_log_if_needed
from .network import get_listen_port, is_port_in_use, is_port_open, pick_free_port

# v1.9.8：端口被占用时自动切换的随机端口区间（高位区间，避开常用服务端口）
PORT_FALLBACK_MIN = 20000
PORT_FALLBACK_MAX = 65000

def find_vw_processes(exe_name: str) -> list:
    """返回运行中的 vaultwarden.exe 进程信息（v1.7.6，Win32_Process 获取真实路径）。

    使用 Get-CimInstance Win32_Process 按进程名查询，返回 [{"pid": int, "exe": str}]；
    查询失败返回空列表。tasklist 仅按名称判定会误认 dist 残留实例（其 .env 无
    ADMIN_TOKEN），故需真实 ExecutablePath 做部署目录归属校验。
    """
    try:
        ps = (
            "Get-CimInstance Win32_Process -Filter \"Name='{0}'\" "
            "| Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"
        ).format(exe_name)
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=8,
            creationflags=CREATE_NO_WINDOW,
        ).stdout.strip()
        if not out:
            return []
        data = json.loads(out)
        if isinstance(data, dict):
            data = [data]
        procs = []
        for d in data:
            pid = d.get("ProcessId")
            exe = (d.get("ExecutablePath") or "").strip()
            if pid is None and not exe:
                continue
            procs.append({"pid": pid, "exe": exe})
        return procs
    except Exception:
        return []

def _in_deploy_dir(exe_path: str, deploy_dir: str) -> bool:
    """判断进程 exe 路径是否属于部署目录（忽略大小写）。未取到路径时按名称视同本服务。"""
    if not exe_path:
        return True
    if not deploy_dir:
        return True
    try:
        p = str(Path(exe_path).resolve()).lower()
        d = str(Path(deploy_dir).resolve()).lower()
        return p.startswith(d.rstrip("\\/") + "\\") or p == d.rstrip("\\/")
    except Exception:
        return True

def _tasklist_name_hit(exe_name: str) -> bool:
    """v1.9.5：按进程名做轻量预检（tasklist，约 30~60ms），不启动 PowerShell。

    用于状态轮询前置过滤：没有任何同名进程时可立即判定「未运行」，跳过
    `find_vw_processes` 的 PowerShell 深查（实测每次约 1.9s）；预检本身异常时
    保守返回 True，交由深查判定（宁可多查，不可误判为已停止）。
    """
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}"],
            capture_output=True, text=True, timeout=8,
            creationflags=CREATE_NO_WINDOW,
        ).stdout or ""
        return exe_name.lower() in out.lower()
    except Exception:
        return True

def is_process_running(exe_name: str, deploy_dir: str = "") -> bool:
    """判断本服务是否运行中（v1.7.6 起路径感知）。

    传 deploy_dir 时：仅当存在 ExecutablePath 属于部署目录的 vaultwarden.exe 实例
    才返回 True——dist\\vaultwarden 残留实例不再冒充"运行中"；未传时退回按进程名
    tasklist 判定（兼容 stop 等按名称兜底场景）。
    """
    if not deploy_dir:
        return _tasklist_name_hit(exe_name)
    for p in find_vw_processes(exe_name):
        if _in_deploy_dir(p.get("exe") or "", deploy_dir):
            return True
    return False

def _foreign_tip_from_procs(procs: list, deploy_dir: str) -> str:
    """v1.9.5：由已取得的进程列表本地生成 foreign 提示（避免二次起 PowerShell）。"""
    if not deploy_dir:
        return ""
    paths = set()
    for p in procs or []:
        exe = (p.get("exe") or "").strip()
        if exe and not _in_deploy_dir(exe, deploy_dir):
            paths.add(exe)
    if not paths:
        return ""
    return "检测到非部署目录的同名实例（" + "；".join(sorted(paths)) + "），请先停止该实例再启动本服务"

def get_foreign_process_tip(exe_name: str, deploy_dir: str) -> str:
    """检测非部署目录的同名实例（v1.7.6），返回状态栏提示；无则空串。不自动结束进程。"""
    if not deploy_dir:
        return ""
    return _foreign_tip_from_procs(find_vw_processes(exe_name), deploy_dir)

def ensure_env_runtime(cfg: dict) -> str:
    """启动前确保部署目录 .env 关键项与 config 一致（v1.7.0）。

    已有证书（ssl/cert.pem + key.pem）时写入 ROCKET_TLS / ROCKET_ADDRESS /
    ROCKET_PORT / DOMAIN，使 HTTPS 真正生效；无证书时仅同步 ROCKET_PORT / DOMAIN
    （服务以 HTTP 运行，resolve_web_url 会自动探测 http）。保留 .env 已有注释与
    其他配置，原位替换目标键。返回提示文本（空串 = 无需变更）。
    """
    vw_dir = Path(cfg["vaultwarden_dir"])
    env_path = vw_dir / ".env"
    port = int(cfg["port"])
    domain = f"https://localhost:{port}"
    ssl_dir = Path(cfg["ssl_dir"])
    has_cert = (ssl_dir / cfg["cert_file"]).exists() and (ssl_dir / cfg["key_file"]).exists()
    cert_path = str(ssl_dir / cfg["cert_file"]).replace("\\", "/")
    key_path = str(ssl_dir / cfg["key_file"]).replace("\\", "/")

    try:
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8", newline="") as f:
                text = f.read()
        else:
            text = ""
    except OSError as e:
        return f"读取 .env 失败：{e}"
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    wanted = {
        "ROCKET_ADDRESS": "0.0.0.0",
        "ROCKET_PORT": str(port),
        "DOMAIN": domain,
    }
    if has_cert:
        wanted["ROCKET_TLS"] = '{{certs="{0}",key="{1}"}}'.format(cert_path, key_path)
    changed = False
    old_port = None
    for key, val in wanted.items():
        pat = re.compile(rf"^(\s*{key}\s*=\s*)\S*")
        found = False
        for i, line in enumerate(lines):
            if pat.match(line):
                if key == "ROCKET_PORT":
                    m = re.match(r"^\s*ROCKET_PORT\s*=\s*(\S*)", line)
                    if m:
                        old_port = m.group(1)
                new_line = pat.sub(rf"\g<1>{val}", line)
                if new_line != line:
                    lines[i] = new_line
                    changed = True
                found = True
                break
        if not found:
            if lines and not lines[-1].endswith(("\n", "\r")):
                lines[-1] += nl
            lines.append(f"{key}={val}{nl}")
            changed = True
    if not changed:
        return ""
    try:
        with open(env_path, "w", encoding="utf-8", newline="") as f:
            f.write("".join(lines))
    except OSError as e:
        return f"更新 .env 失败：{e}"
    tip = "已同步部署目录 .env（ROCKET_PORT/DOMAIN"
    if has_cert:
        tip += "、ROCKET_TLS 已启用 HTTPS"
    tip += "）"
    if old_port is not None and str(old_port) != str(port):
        tip += f"，端口不一致已统一：ROCKET_PORT {old_port} → {port}"
    tip += "，重启生效"
    return tip

def ensure_admin_token(cfg: dict) -> tuple:
    """确保部署目录 .env 含非空 ADMIN_TOKEN（v1.7.6，新环境部署后 /admin 必现
    "The admin panel is disabled, please configure the 'ADMIN_TOKEN' variable" 的根治）。

    缺失或值为空时自动生成强随机值（secrets.token_urlsafe(32)）写入 .env；保留其他行、
    注释与换行风格，已有非空值绝不覆盖（幂等）。返回 (ADMIN_TOKEN 值或 None, 是否新生成)。
    """
    vw_dir = Path(cfg["vaultwarden_dir"])
    env_path = vw_dir / ".env"
    try:
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8", newline="") as f:
                text = f.read()
        else:
            text = ""
    except OSError:
        return None, False
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    for line in lines:
        m = re.match(r"^\s*ADMIN_TOKEN\s*=\s*(\S+)", line)
        if m:
            return m.group(1), False  # 已有非空值，不覆盖（幂等）
    # 缺失或值为空 → 生成强随机值
    token = secrets.token_urlsafe(32)
    replaced = False
    for i, line in enumerate(lines):
        if re.match(r"^\s*ADMIN_TOKEN\s*=", line):
            body = line.rstrip("\r\n")  # 剥离行尾换行，避免 \s* 贪婪吃掉换行导致 token 落到下一行
            tail = line[len(body):]     # 原换行符，替换后原样保留
            lines[i] = re.sub(r"^(\s*ADMIN_TOKEN\s*=\s*)\S*", rf"\g<1>{token}", body) + tail
            replaced = True
            break
    if not replaced:
        if lines and not lines[-1].endswith(("\n", "\r")):
            lines[-1] += nl
        lines.append(f"ADMIN_TOKEN={token}{nl}")
    try:
        with open(env_path, "w", encoding="utf-8", newline="") as f:
            f.write("".join(lines))
    except OSError:
        return None, False
    return token, True

def _own_service_holds_port(cfg: dict, port: int) -> bool:
    """v1.9.8：端口是否由本程序管理的 vaultwarden 实例自身占用（正常情况，不切换）。

    服务正在运行且监听该端口时，端口必然「被占用」——这是期望状态，
    不能误判为冲突而切换端口（否则每次启动都会漂移端口）。
    """
    exe_name = cfg.get("exe_name", "vaultwarden.exe")
    vw_dir = str(cfg.get("vaultwarden_dir", ""))
    try:
        procs = find_vw_processes(exe_name) or []
    except Exception:  # noqa: BLE001
        procs = []
    if not procs:
        return False
    try:
        ports = set(int(p) for p in get_listen_port(exe_name))
    except Exception:  # noqa: BLE001
        return True  # 无法判定监听端口时保守认为是我方占用，避免误切
    if ports:
        return int(port) in ports
    # 进程在跑但 netstat 未解析出监听端口（启动瞬间）：按部署目录归属判断
    try:
        for p in procs:
            path = str(p.get("path") or "")
            if path and vw_dir and path.casefold().startswith(vw_dir.casefold()):
                return True
    except Exception:  # noqa: BLE001
        pass
    return False

def _apply_port_change(cfg: dict, new_port: int) -> tuple:
    """v1.9.8：端口切换落盘——同步 config.json（port/domain）与部署目录 .env（ROCKET_PORT/DOMAIN）。

    与「修改端口」按钮共用同一持久化语义，但更健壮：部署目录尚不存在（首次部署前）
    时只更新 config.json，.env 留待部署/启动时由 ensure_env_runtime 生成。
    返回 (ok, msg)。
    """
    from .config import save_config  # 局部导入：避免 config → service 的潜在循环依赖

    old_port = cfg.get("port")
    cfg["port"] = int(new_port)
    cfg["domain"] = f"https://localhost:{new_port}"
    if not save_config(cfg):
        return False, "更新 config.json 失败（端口切换未落盘）"
    vw_dir = Path(cfg["vaultwarden_dir"])
    if not vw_dir.is_dir():
        return True, ""
    env_tip = ensure_env_runtime(cfg)  # 同步 .env 的 ROCKET_PORT/DOMAIN
    if env_tip.startswith(("读取 .env 失败", "更新 .env 失败")):
        return False, env_tip
    if str(old_port) != str(new_port):
        return True, env_tip
    return True, env_tip

def ensure_port_available(cfg: dict) -> tuple:
    """v1.9.8：启动/部署前的端口占用检测，被占用则自动切换到随机可用端口。

    返回 (ok, msg, switched)：
    - ok=True 且 switched=False：端口空闲或由本程序服务自身占用 → 行为不变、无提示；
    - ok=True 且 switched=True：端口被其它程序占用，已自动切换（msg 为切换说明）；
    - ok=False：切换失败（msg 为中文错误，调用方应中止启动/部署）。

    约定：一次启动流程至多调用本函数一次，避免端口反复漂移。
    """
    try:
        port = int(cfg["port"])
    except (KeyError, TypeError, ValueError):
        return True, "", False
    if not is_port_in_use(port):
        return True, "", False
    if _own_service_holds_port(cfg, port):
        return True, "", False
    new_port = pick_free_port(PORT_FALLBACK_MIN, PORT_FALLBACK_MAX, exclude=(port,))
    if not new_port:
        return False, (f"端口 {port} 已被其它程序占用，且 {PORT_FALLBACK_MIN}-{PORT_FALLBACK_MAX}"
                       f" 区间内未找到可用端口，请手动点击「修改端口」后重试"), False
    ok, extra = _apply_port_change(cfg, new_port)
    if not ok:
        return False, f"端口 {port} 已被占用，自动切换端口失败：{extra}", False
    msg = f"端口 {port} 被占用，已自动切换到 {new_port}"
    if extra:
        msg += f"；{extra}"
    return True, msg, True

def start_service(cfg: dict) -> tuple:
    """后台启动 vaultwarden.exe。cwd 必须为部署目录，.env 才会被加载。"""
    vw_dir = Path(cfg["vaultwarden_dir"])
    exe_path = vw_dir / cfg["exe_name"]
    if not exe_path.exists():
        return False, f"未找到 {exe_path}，请检查配置 vaultwarden_dir"
    if is_process_running(cfg["exe_name"], str(vw_dir)):
        return False, "服务已在运行，无需重复启动"
    foreign_tip = get_foreign_process_tip(cfg["exe_name"], str(vw_dir))
    if foreign_tip:
        return False, foreign_tip + "；请先在任务管理器中结束该实例，再点击启动"
    log_path = vw_dir / cfg["log_file"]
    err_path = vw_dir / cfg["err_log_file"]
    # 日志加固：写入前若日志过大先轮转归档，避免单日志无限膨胀
    rotate_log_if_needed(log_path, float(cfg.get("log_max_mb", 10)))
    rotate_log_if_needed(err_path, float(cfg.get("log_max_mb", 10)))
    log_f = open(log_path, "a", encoding="utf-8", errors="ignore")
    err_f = open(err_path, "a", encoding="utf-8", errors="ignore")
    env_tip = ensure_env_runtime(cfg)  # v1.7.0：启动前同步 .env 关键项（ROCKET_PORT/DOMAIN/ROCKET_TLS）
    admin_token, admin_generated = ensure_admin_token(cfg)  # v1.7.6：缺失时自动生成 ADMIN_TOKEN
    try:
        subprocess.Popen(
            [str(exe_path)],
            cwd=str(vw_dir),          # 关键：工作目录=部署目录，保证 .env 生效
            stdin=subprocess.DEVNULL,
            stdout=log_f,
            stderr=err_f,
            creationflags=CREATE_NO_WINDOW,  # 无黑窗
            start_new_session=True,          # 独立会话，关闭管理器不连带退出
        )
        log_f.close()
        err_f.close()
        base = f"启动命令已发出：{exe_path.name}（工作目录 {vw_dir}）"
        if env_tip:
            base += "；" + env_tip
        if admin_generated and admin_token:
            base += (f"；已自动生成 ADMIN_TOKEN，管理面板 https://localhost:{cfg['port']}"
                     f"{cfg.get('admin_path', '/admin')} 登录口令：{admin_token}"
                     f"（请妥善保存，用于登录管理面板）")
        return True, base
    except Exception as e:
        log_f.close()
        err_f.close()
        return False, f"启动失败：{e}"

def _tasklist_pids() -> set:
    """v1.9.1：轻量获取当前全部进程 PID 集合（tasklist CSV，不起 PowerShell）。

    用于 stop_service 轮询确认阶段的存活检测——替代逐轮 `find_vw_processes`
    （每次起 PowerShell 子进程约 2 秒），大幅收敛退出/停止的轮询空耗；
    一次 tasklist 即可判断全部目标 PID 是否已退出。失败返回空集（保守，
    调用方随后按超时处理并回退 find_vw_processes 精确确认）。
    """
    try:
        out = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5,
            creationflags=CREATE_NO_WINDOW,
        ).stdout
    except Exception:
        return set()
    pids = set()
    for line in out.splitlines():
        parts = line.split('","')
        if len(parts) >= 2:
            pid_txt = parts[1].strip('"').strip()
            if pid_txt.isdigit():
                pids.add(int(pid_txt))
    return pids


def stop_service(cfg: dict) -> tuple:
    """停止本用户所有 vaultwarden.exe 实例（v1.8.1 增强，可靠停止）。

    v1.8.1：改为按 Win32_Process 精确 PID 逐个 `taskkill /PID /T /F` 终止——
    不再依赖 tasklist 名称匹配，也不受部署目录过滤影响，**含非部署目录残留实例
    （如 dist\\vaultwarden 旧部署）一并可靠停止**；终止后轮询等待并验证进程全部退出。
    查询到进程但取不到 PID 的异常场景回退 `taskkill /IM /T /F` 按名称兜底。
    停止目标仅限本用户 vaultwarden.exe 同名实例。
    """
    import time
    exe_name = cfg["exe_name"]
    procs = find_vw_processes(exe_name)
    if not procs:
        return False, "未检测到运行中的服务"
    pids = [p["pid"] for p in procs if p.get("pid") is not None]
    try:
        if pids:
            for pid in pids:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True, text=True, timeout=10,
                    creationflags=CREATE_NO_WINDOW,
                )
        else:
            subprocess.run(
                ["taskkill", "/IM", exe_name, "/T", "/F"],
                capture_output=True, text=True, timeout=10,
                creationflags=CREATE_NO_WINDOW,
            )
    except Exception as e:
        return False, f"停止失败：{e}"
    # 轮询等待进程退出并验证无残留（固定时间预算 6 秒；v1.9.1 起用轻量
    # tasklist 按 PID 确认存活，避免每轮起 PowerShell 子进程造成轮询空耗）
    deadline = time.monotonic() + 6.0
    if pids:
        while time.monotonic() < deadline:
            if not (_tasklist_pids() & set(pids)):
                return True, f"服务已停止（共终止 {len(pids)} 个实例）"
            time.sleep(0.2)
    else:
        # 取不到 PID 的异常场景（罕见）：回退 find_vw_processes 轮询确认
        while time.monotonic() < deadline:
            if not find_vw_processes(exe_name):
                return True, "服务已停止"
            time.sleep(0.2)
    left = find_vw_processes(exe_name)
    detail = "；".join(
        f"PID {p.get('pid')}（{p.get('exe') or '路径未知'}）" for p in left
    )
    return False, f"停止命令已执行但仍有 {len(left)} 个实例未退出：{detail}"

def get_deploy_state(cfg: dict) -> tuple:
    """判定部署目录是否已完成部署（v1.9.4，供 GUI 锁定「一键部署」按钮）。

    返回 (state, tip)：state = "deployed" / "partial" / "none"。
    判据全部取自磁盘真实文件，不使用任何会话内内存标志，程序重启后同样有效：
      - 核心文件 <vaultwarden_dir>/<exe_name> 存在且 >1MB（与 deploy_service 下载校验阈值一致）；
      - <vaultwarden_dir>/.env 存在且含非空 ADMIN_TOKEN（v1.7.6 起部署/启动链路必写入）；
      - <vaultwarden_dir>/web-vault/index.html 存在 → 网页版就绪，缺则为 partial
        （服务仅 API 可用，保留「一键部署」可点以便补装网页版）。
    目录不存在、文件缺失、读取异常一律保守判为 "none"（按钮保持可点，不阻断用户）。
    """
    vw_raw = str(cfg.get("vaultwarden_dir", "") or "").strip()
    exe_name = str(cfg.get("exe_name", "") or "vaultwarden.exe")
    if not vw_raw:
        return "none", "未部署：未配置部署目录"
    vw_dir = Path(vw_raw)
    try:
        if not vw_dir.exists():
            return "none", f"未部署：部署目录不存在（{vw_dir}）"
    except OSError:
        return "none", "未部署：无法访问部署目录"
    exe_path = vw_dir / exe_name
    try:
        if not exe_path.exists():
            return "none", f"未部署：缺少核心文件 {exe_name}"
        if exe_path.stat().st_size <= 1024 * 1024:
            return "none", f"部署不完整：{exe_name} 小于 1MB（疑似下载未完成）"
    except OSError:
        return "none", f"未部署：无法读取 {exe_name}"
    env_path = vw_dir / ".env"
    try:
        env_text = env_path.read_text(encoding="utf-8", errors="ignore") if env_path.exists() else ""
    except OSError:
        env_text = ""
    if not env_text.strip():
        return "none", "未部署：部署目录缺少 .env 配置文件"
    if re.search(r"(?m)^\s*ADMIN_TOKEN\s*=\s*\S+", env_text) is None:
        return "none", "部署不完整：.env 缺少 ADMIN_TOKEN（点击一键部署可自动生成）"
    if not (vw_dir / "web-vault" / "index.html").exists():
        return "partial", "已部署但网页版未安装（仅 API 可用），可再次点击一键部署补装"
    return "deployed", "已部署：核心文件、.env（ADMIN_TOKEN）与网页版均就绪，无需重复部署"

def get_service_status(cfg: dict) -> tuple:
    """返回 (状态码, 状态文本, 颜色)。status: running / abnormal / foreign / stopped。

    v1.7.6：运行判定按部署目录路径校验；检测到非部署目录同名实例时状态栏橙色提示
    （不自动结束进程，避免误杀）。
    v1.8.1：foreign 场景返回独立状态码 "foreign"（不再混用 "stopped"），
    供 GUI 按钮矩阵据此启用「停止服务」，打破「启动被拦截 + 停止按钮禁用」死锁。
    v1.9.5：性能重构——原实现串行调用 is_process_running / get_foreign_process_tip
    共起 3 次 PowerShell（实测单次约 4.4s，是密码框输入卡顿的根因）。改为「tasklist
    轻量预检 + 一次 find_vw_processes 本地判定」：无同名进程时约 40ms、有同名进程时
    约 1.9s，且判定语义（running/abnormal/foreign/stopped）完全不变。
    """
    deploy_dir = str(Path(cfg["vaultwarden_dir"]))
    exe_name = cfg["exe_name"]
    if not _tasklist_name_hit(exe_name):
        # 轻量预检命中「无同名进程」→ 直接判定已停止，跳过 PowerShell 深查
        return "stopped", f"服务已停止 · 端口 {cfg['port']}", "#c92a2a"
    procs = find_vw_processes(exe_name)  # 仅一次 PowerShell，后续判定全部在本地完成
    running = any(_in_deploy_dir(p.get("exe") or "", deploy_dir) for p in procs)
    open_port = is_port_open(int(cfg["port"]))
    if running and open_port:
        return "running", f"服务运行中 · 端口 {cfg['port']} · {cfg['domain']}", "#2b8a3e"
    if running:
        return "abnormal", f"进程存在但端口 {cfg['port']} 未响应（可能仍在启动或异常）", "#d9480f"
    foreign_tip = _foreign_tip_from_procs(procs, deploy_dir)
    if foreign_tip:
        return "foreign", foreign_tip, "#d9480f"
    return "stopped", f"服务已停止 · 端口 {cfg['port']}", "#c92a2a"

