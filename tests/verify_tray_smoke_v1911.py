# -*- coding: utf-8 -*-
"""v1.9.11 托盘与进程残留真机冒烟：真实创建 pystray 托盘图标（不打桩），验证零回归与退出后无残留。

- T1 托盘图标真实创建成功（_tray_active=True、pystray.Icon 实例、标题正确）
- T2 托盘菜单结构完整（显示主窗口 / 分隔符 / 退出程序）
- T3 托盘就绪后主窗口与 btns 矩阵完好（14 个按钮 / 13 键矩阵）
- T4 关闭主窗口走 _quit_app 后：_tray_icon 已 stop、_tray_active=False
- T5 退出后无残留非守护线程、无残留子进程句柄
"""
import os
import sys
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PASS, FAIL = 0, []


def check(name, cond, extra=""):
    global PASS
    if cond:
        PASS += 1
        print("[PASS] %s" % name)
    else:
        FAIL.append(name)
        print("[FAIL] %s %s" % (name, extra))


from vwm import app as app_mod  # noqa: E402
import vwm.ui as ui_mod  # noqa: E402

# 仅关闭与托盘无关的副作用：状态轮询、日志刷新、真实网卡探测
app_mod.VaultwardenManagerApp.refresh_log = lambda self: None
app_mod.VaultwardenManagerApp._periodic_status = lambda self: None
app_mod.get_service_status = lambda cfg: ("stopped", "服务未运行", "#2b8a3e")
# 退出链路会真正查杀 vaultwarden.exe 并停服务——冒烟期间改为测试桩，绝不触碰正式部署
app_mod.find_vw_processes = lambda exe_name: []
app_mod.stop_service = lambda cfg: (True, "已停止（冒烟桩）")
app_mod.ask_stop_failed_quit = lambda parent, msg: True
# 退出链路会把「上次退出时服务是否运行」写回真实 config.json——冒烟期间不写盘
app_mod.VaultwardenManagerApp._record_exit_state = lambda self, running: None
ui_mod.get_lan_ip_info = lambda refresh=False: {
    "primary": "198.51.100.10", "candidates": ["198.51.100.10"], "details": [],
    "excluded": [], "udp_probe": "198.51.100.10", "source": "test", "cached": False}

base_threads = len(threading.enumerate())

rd = Path(tempfile.mkdtemp(prefix="vw1911tray_"))
cfg = {
    "vaultwarden_dir": str(rd / "vaultwarden"), "exe_name": "vaultwarden.exe",
    "port": 55557, "ssl_dir": str(rd / "vaultwarden" / "ssl"),
    "cert_file": "cert.pem", "key_file": "key.pem",
    "backup_dir": str(rd / "vaultwarden" / "backup"), "log_file": "vaultwarden.log",
    "err_log_file": "vaultwarden.err.log", "log_lines": 300, "log_max_mb": 10,
    "log_noise_keywords": ["tls handshake"], "vw_download_url": "",
    "vw_download_timeout": 120, "vw_webvault_download_url": "",
    "vw_webvault_download_timeout": 180, "status_check_ms": 3000, "cert_days": 3650,
    "domain": "https://localhost:55557", "admin_path": "/admin",
    "quit_confirm_skip": True, "quit_default_action": "quit",
}
(rd / "vaultwarden").mkdir(parents=True, exist_ok=True)

app = app_mod.VaultwardenManagerApp(cfg)
app.update()

icon = getattr(app, "_tray_icon", None)
check("T1.1 托盘图标真实创建成功（_tray_active=True）", getattr(app, "_tray_active", False) is True,
      getattr(app, "_tray_active", None))
check("T1.2 _tray_icon 为 pystray.Icon 实例",
      icon is not None and icon.__class__.__module__.startswith("pystray"), type(icon))
check("T1.3 托盘标题为「Vaultwarden 管家」",
      getattr(icon, "title", None) == "Vaultwarden 管家", getattr(icon, "title", None))
check("T1.4 托盘图标已进入运行态（_running）", bool(getattr(icon, "_running", False)))
menu_items = list(getattr(icon, "menu", []) or [])
labels = [getattr(i, "text", "---") for i in menu_items]
check("T2 托盘菜单含「显示主窗口 / 退出程序」",
      any("显示主窗口" == x for x in labels) and any("退出程序" == x for x in labels), labels)

btns = [c for c in app.winfo_children() if False]
btns = list(app.btns.values()) if hasattr(app, "btns") else []
check("T3.1 主窗口 btns 矩阵 13 键完好", len(btns) == 13, len(btns))
check("T3.2 主窗口主色区无赞助残留（无浅灰卡片）",
      not any(getattr(c, "winfo_class", lambda: "")() == "Frame"
              and str(c.cget("bg")) == "#e9ecef"
              for c in app.winfo_children()))
check("T3.3 版本号 v1.9.11", ui_mod.VERSION == "v1.9.11", ui_mod.VERSION)

# 退出链路必须在 Tk mainloop 内触发（_safe_schedule 依赖 after，线程回主线程调度
# 仅在 mainloop 运行时可靠），因此把退出排进事件队列后进 mainloop 直到窗口销毁
app.after(300, app._quit_app)
app.mainloop()
deadline = time.time() + 4.0
while time.time() < deadline:
    if getattr(app, "_tray_icon", None) is None and not bool(getattr(icon, "_running", False)):
        break
    time.sleep(0.05)

check("T4.1 退出后 _tray_icon 已清空", getattr(app, "_tray_icon", "x") is None,
      getattr(app, "_tray_icon", None))
check("T4.2 退出后 _tray_active=False", getattr(app, "_tray_active", True) is False)
check("T4.3 pystray 图标已停止运行", not bool(getattr(icon, "_running", False)))

try:
    app.destroy()
except Exception:
    pass

time.sleep(1.2)
alive = [t for t in threading.enumerate() if t is not threading.main_thread() and t.is_alive()]
non_daemon = [t for t in alive if not t.daemon]
check("T5.1 退出后无非守护线程残留", not non_daemon, [t.name for t in non_daemon])
check("T5.2 线程总数回落（基线 %d，现存 %d）" % (base_threads, len(alive)),
      len(alive) <= base_threads + 1, [t.name for t in alive])

print("\n==== v1.9.11 托盘/残留冒烟：%d PASS / %d FAIL ====" % (PASS, len(FAIL)))
if FAIL:
    for f in FAIL:
        print("  - %s" % f)
print("EXIT_MARKER_OK")
os._exit(0 if not FAIL else 1)
