"""v1.9.8 验证：端口占用检测 + 自动随机端口切换。

覆盖：
  A. network.is_port_in_use / is_port_bindable / pick_free_port 纯函数
  B. service.ensure_port_available 三种分支（空闲不切换 / 被占用自动切换 / 我方服务占用不切换 / 无可用端口报错）
  C. 切换后 config.json(port/domain) 与 .env(ROCKET_PORT/DOMAIN) 同步落盘
  D. _apply_port_change 在部署目录不存在时只更新 config.json
  E. deploy_service 集成：端口被占用时先切换再用新端口启动，成功消息含切换提示

全部通过输出 PASS 计数，任一失败打印 FAIL 明细并以非 0 退出。
"""
import json
import socket
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vwm import config as vwm_config
from vwm import deploy as vwm_deploy
from vwm import network as vwm_network
from vwm import service as vwm_service

PASS = []
FAIL = []


def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print(f"PASS {name}")
    else:
        FAIL.append((name, detail))
        print(f"FAIL {name} :: {detail}")


def occupy(port, host="0.0.0.0"):
    """真实占用一个 TCP 端口（listen 状态）。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    s.listen(5)
    return s


def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def make_cfg(tmp: Path, port: int, with_dir=True):
    vw_dir = tmp / "vaultwarden"
    if with_dir:
        vw_dir.mkdir(parents=True, exist_ok=True)
    return {
        "vaultwarden_dir": str(vw_dir),
        "exe_name": "vaultwarden.exe",
        "port": port,
        "domain": f"https://localhost:{port}",
        "ssl_dir": str(vw_dir / "ssl"),
        "cert_file": "cert.pem",
        "key_file": "key.pem",
        "admin_path": "/admin",
        "log_file": "vaultwarden.log",
        "err_log_file": "vaultwarden.err.log",
        "log_max_mb": 10,
        "vw_download_url": "",
        "vw_webvault_download_url": "",
    }


# ---------------- A. network 纯函数 ----------------
free = find_free_port()
check("A1 空闲端口 is_port_in_use=False", vwm_network.is_port_in_use(free) is False)
check("A2 空闲端口 is_port_bindable=True", vwm_network.is_port_bindable(free) is True)

busy = find_free_port()
sock = occupy(busy)
try:
    check("A3 占用端口 is_port_in_use=True", vwm_network.is_port_in_use(busy) is True,
          f"port={busy}")
    check("A4 占用端口 is_port_bindable=False", vwm_network.is_port_bindable(busy) is False)
finally:
    sock.close()

p = vwm_network.pick_free_port(20000, 65000, exclude=(busy,), tries=60)
check("A5 pick_free_port 落在区间内", 20000 <= p <= 65000, f"p={p}")
check("A6 pick_free_port 结果可绑定", vwm_network.is_port_bindable(p) is True, f"p={p}")
check("A7 pick_free_port 排除集合生效", vwm_network.pick_free_port(20000, 65000, exclude=(p,), tries=40) != p)

# ---------------- B/C. ensure_port_available ----------------
tmp = Path(tempfile.mkdtemp(prefix="vwm198_"))
cfg_path = tmp / "config.json"
orig_cfg_path = vwm_config.CONFIG_PATH
vwm_config.CONFIG_PATH = cfg_path

try:
    # B1 端口空闲 → 不切换、无提示
    idle_port = find_free_port()
    cfg = make_cfg(tmp, idle_port)
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    ok, msg, switched = vwm_service.ensure_port_available(cfg)
    check("B1 端口空闲不切换", (ok, msg, switched) == (True, "", False), f"{ok},{msg},{switched}")
    check("B2 空闲时 cfg.port 不变", cfg["port"] == idle_port, str(cfg["port"]))

    # B3 端口被其它程序占用 → 自动切换随机端口
    port_b = find_free_port()
    s_b = occupy(port_b)
    try:
        cfg = make_cfg(tmp, port_b)
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        # 预置 .env，验证同步更新
        env_path = Path(cfg["vaultwarden_dir"]) / ".env"
        env_path.write_text(f"ROCKET_ADDRESS=0.0.0.0\nROCKET_PORT={port_b}\nDOMAIN=https://localhost:{port_b}\n",
                            encoding="utf-8")
        ok, msg, switched = vwm_service.ensure_port_available(cfg)
        new_port = int(cfg["port"])
        check("B4 被占用→切换成功", ok is True and switched is True, f"{ok},{msg},{switched}")
        check("B5 新端口在 20000-65000", 20000 <= new_port <= 65000, str(new_port))
        check("B6 新端口与原端口不同", new_port != port_b, f"{new_port} vs {port_b}")
        check("B7 提示含中文切换说明",
              f"端口 {port_b} 被占用，已自动切换到 {new_port}" in msg, msg)
        check("B8 cfg.domain 同步", cfg["domain"] == f"https://localhost:{new_port}", cfg["domain"])
        saved = json.loads(cfg_path.read_text(encoding="utf-8"))
        check("B9 config.json port 已落盘", int(saved["port"]) == new_port, str(saved.get("port")))
        check("B10 config.json domain 已落盘",
              saved["domain"] == f"https://localhost:{new_port}", str(saved.get("domain")))
        env_text = env_path.read_text(encoding="utf-8")
        check("B11 .env ROCKET_PORT 已同步", f"ROCKET_PORT={new_port}" in env_text, env_text.replace("\n", "|"))
        check("B12 .env DOMAIN 已同步", f"DOMAIN=https://localhost:{new_port}" in env_text)
    finally:
        s_b.close()

    # B13 端口被本程序服务自身占用 → 不切换
    port_c = find_free_port()
    s_c = occupy(port_c)
    orig_find = vwm_service.find_vw_processes
    orig_listen = vwm_service.get_listen_port
    try:
        vwm_service.find_vw_processes = lambda *a, **k: [{"pid": 4321, "path": ""}]
        vwm_service.get_listen_port = lambda *a, **k: [port_c]
        cfg = make_cfg(tmp, port_c)
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        ok, msg, switched = vwm_service.ensure_port_available(cfg)
        check("B13 我方服务占用不切换",
              (ok, msg, switched) == (True, "", False) and cfg["port"] == port_c,
              f"{ok},{msg},{switched},{cfg['port']}")
    finally:
        vwm_service.find_vw_processes = orig_find
        vwm_service.get_listen_port = orig_listen
        s_c.close()

    # B14 无可用随机端口 → 中文错误
    port_d = find_free_port()
    s_d = occupy(port_d)
    orig_pick = vwm_service.pick_free_port
    try:
        vwm_service.pick_free_port = lambda *a, **k: 0
        cfg = make_cfg(tmp, port_d)
        ok, msg, switched = vwm_service.ensure_port_available(cfg)
        check("B14 无可用端口返回失败", ok is False and switched is False, f"{ok},{msg}")
        check("B15 失败提示为中文且含原端口", f"端口 {port_d} 已被其它程序占用" in msg, msg)
    finally:
        vwm_service.pick_free_port = orig_pick
        s_d.close()

    # C16 部署目录不存在 → 仅更新 config.json，不报 .env 错误
    port_e = find_free_port()
    s_e = occupy(port_e)
    try:
        cfg = make_cfg(tmp / "nodir", port_e, with_dir=False)
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        ok, msg, switched = vwm_service.ensure_port_available(cfg)
        check("C16 部署目录不存在仍切换成功", ok is True and switched is True, f"{ok},{msg}")
        saved = json.loads(cfg_path.read_text(encoding="utf-8"))
        check("C17 config.json 已更新", int(saved["port"]) == int(cfg["port"]), str(saved.get("port")))
        check("C18 无英文异常信息", "OSError" not in msg and "Traceback" not in msg, msg)
    finally:
        s_e.close()

    # ---------------- E. deploy_service 集成 ----------------
    port_f = find_free_port()
    s_f = occupy(port_f)
    orig_start = vwm_deploy.start_service
    orig_running = vwm_deploy.is_process_running
    orig_open = vwm_deploy.is_port_open
    try:
        dcfg = make_cfg(tmp / "dep", port_f)
        vw_dir = Path(dcfg["vaultwarden_dir"])
        (vw_dir / "web-vault").mkdir(parents=True, exist_ok=True)
        (vw_dir / "web-vault" / "index.html").write_text("<html></html>", encoding="utf-8")
        exe = vw_dir / "vaultwarden.exe"
        exe.write_bytes(b"0" * (1024 * 1024 + 1024))  # >1MB，跳过下载与校验
        (vw_dir / "ssl").mkdir(exist_ok=True)
        (vw_dir / "ssl" / "cert.pem").write_text("x", encoding="utf-8")
        (vw_dir / "ssl" / "key.pem").write_text("x", encoding="utf-8")
        cfg_path.write_text(json.dumps(dcfg, ensure_ascii=False), encoding="utf-8")
        called = {"started": False}

        def fake_start(c):
            called["port"] = int(c["port"])
            called["started"] = True
            return True, "启动命令已发出：vaultwarden.exe"

        vwm_deploy.start_service = fake_start
        vwm_deploy.is_process_running = lambda *a, **k: called["started"]
        vwm_deploy.is_port_open = lambda *a, **k: called["started"]
        ok, msg = vwm_deploy.deploy_service(dcfg, timeout=2.0)
        newp = int(dcfg["port"])
        check("E1 部署成功", ok is True, msg)
        check("E2 启动使用切换后的新端口", called.get("port") == newp, str(called))
        check("E3 部署消息含端口切换提示", f"端口 {port_f} 被占用，已自动切换到 {newp}" in msg, msg)
        check("E4 部署消息含部署成功", "部署成功" in msg, msg)
        check("E5 新端口非原端口", newp != port_f, f"{newp} vs {port_f}")
    finally:
        vwm_deploy.start_service = orig_start
        vwm_deploy.is_process_running = orig_running
        vwm_deploy.is_port_open = orig_open
        s_f.close()

    # E6 端口空闲时部署消息不含切换提示
    port_g = find_free_port()
    orig_start = vwm_deploy.start_service
    orig_running = vwm_deploy.is_process_running
    orig_open = vwm_deploy.is_port_open
    try:
        dcfg2 = make_cfg(tmp / "dep2", port_g)
        vw_dir2 = Path(dcfg2["vaultwarden_dir"])
        (vw_dir2 / "web-vault").mkdir(parents=True, exist_ok=True)
        (vw_dir2 / "web-vault" / "index.html").write_text("<html></html>", encoding="utf-8")
        (vw_dir2 / "vaultwarden.exe").write_bytes(b"0" * (1024 * 1024 + 1024))
        (vw_dir2 / "ssl").mkdir(exist_ok=True)
        (vw_dir2 / "ssl" / "cert.pem").write_text("x", encoding="utf-8")
        (vw_dir2 / "ssl" / "key.pem").write_text("x", encoding="utf-8")
        cfg_path.write_text(json.dumps(dcfg2, ensure_ascii=False), encoding="utf-8")
        st = {"started": False}

        def fake_start2(c):
            st["started"] = True
            return True, "启动命令已发出"

        vwm_deploy.start_service = fake_start2
        vwm_deploy.is_process_running = lambda *a, **k: st["started"]
        vwm_deploy.is_port_open = lambda *a, **k: st["started"]
        ok, msg = vwm_deploy.deploy_service(dcfg2, timeout=2.0)
        check("E6 空闲端口部署成功", ok is True, msg)
        check("E7 空闲时无切换提示", "被占用" not in msg and int(dcfg2["port"]) == port_g, msg)
    finally:
        vwm_deploy.start_service = orig_start
        vwm_deploy.is_process_running = orig_running
        vwm_deploy.is_port_open = orig_open
finally:
    vwm_config.CONFIG_PATH = orig_cfg_path

print("\n==== 汇总 ====")
print(f"PASS {len(PASS)} / FAIL {len(FAIL)} / TOTAL {len(PASS) + len(FAIL)}")
if FAIL:
    for name, detail in FAIL:
        print(f"  - {name}: {detail}")
    sys.exit(1)
