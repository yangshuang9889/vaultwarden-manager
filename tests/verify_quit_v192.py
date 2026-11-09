# -*- coding: utf-8 -*-
"""v1.9.2 退出路径回归（11 项）。

覆盖：退出取消保留 / 强制退出 / 成功退出 / 防重入 / NIM_DELETE 兜底接线。
本脚本只做进程内 UI 逻辑验证，不触碰真实 Vaultwarden 服务与生产配置。
"""
import os
import sys
import traceback

PASS = 0
FAIL = []


def check(name, cond, detail=""):
    global PASS
    if cond:
        PASS += 1
        print("[PASS] %s %s" % (name, detail))
    else:
        FAIL.append(name)
        print("[FAIL] %s %s" % (name, detail))


from pathlib import Path

ROOT = str(Path(__file__).resolve().parent.parent)  # 项目根目录：脚本位于 tests/ 下，向上两级
sys.path.insert(0, ROOT)

import vwm.app as appmod
from vwm.config import load_config
from vwm.service import _tasklist_pids

src = open(ROOT + r"\vwm\app.py", encoding="utf-8").read()


def real_cfg():
    cfg = load_config()
    cfg["vaultwarden_dir"] = ROOT + r"\vaultwarden"
    cfg["ssl_dir"] = ROOT + r"\vaultwarden\ssl"
    cfg["backup_dir"] = ROOT + r"\vaultwarden\backup"
    cfg["port"] = 44444
    cfg["domain"] = "https://localhost:44444"
    return cfg


def make_app(cfg):
    app = appmod.VaultwardenManagerApp(cfg)
    app.withdraw()
    return app


def safe_destroy(app):
    try:
        app.destroy()
    except Exception:
        pass


def win_gone(app):
    try:
        app.winfo_exists()
        return False
    except Exception:
        return True


cfg = real_cfg()

# E1：进程枚举可用（退出前确认服务停止逻辑依赖的 tasklist 正常）
check("E1 tasklist_pids contains current pid", os.getpid() in _tasklist_pids())

# E2-E4：停止服务失败 + 用户选择"取消退出" → 窗口/托盘/状态全部保留
try:
    app = make_app(cfg)
    appmod.ask_stop_failed_quit = lambda parent, msg: False
    app._quitting = True
    app._on_stop_result(False, "测试停止失败")
    check("E2 cancel quit keeps window", bool(app.winfo_exists()))
    check("E3 cancel quit resets _quitting", app._quitting is False)
    check("E4 cancel quit keeps tray", app._tray_active is True)
    safe_destroy(app)
except Exception:
    check("E2 cancel quit keeps window", False, traceback.format_exc()[-300:])

# E5：停止失败但用户选择"仍然退出" → 窗口销毁/托盘清空
try:
    app = make_app(cfg)
    appmod.ask_stop_failed_quit = lambda parent, msg: True
    app._on_stop_result(False, "测试停止失败")
    check("E5 force quit destroys window", win_gone(app) or app._tray_icon is None)
    safe_destroy(app)
except Exception:
    check("E5 force quit destroys window", False, traceback.format_exc()[-300:])

# E6：服务停止成功 → 窗口销毁/托盘清空
try:
    app = make_app(cfg)
    app._on_stop_result(True, "服务已停止（共终止 1 个实例）")
    check("E6 success destroys window", win_gone(app) or app._tray_icon is None)
    safe_destroy(app)
except Exception:
    check("E6 success destroys window", False, traceback.format_exc()[-300:])

# E7-E8：_quitting 防重入——不重复起停止线程，且保持退出中状态
try:
    app = make_app(cfg)
    n = []
    orig_thread = appmod.threading.Thread
    appmod.threading.Thread = lambda *a, **k: (n.append(1), orig_thread(*a, **k))[1]
    try:
        app._quitting = True
        app._quit_app()
    finally:
        appmod.threading.Thread = orig_thread
    check("E7 reentry no new thread", len(n) == 0, str(len(n)))
    check("E8 reentry keeps _quitting", app._quitting is True)
    safe_destroy(app)
except Exception:
    check("E7 reentry no new thread", False, traceback.format_exc()[-300:])

# E9-E11：退出物理清图标兜底接线
check("E9 quit calls NIM_DELETE fallback", "_nim_delete_icon(_tray_hwnd, _tray_hid)" in src)
check("E10 quit still stops tray", "icon.stop()" in src)
check("E11 final_cleanup clears tray state",
      "_tray_icon = None" in src and "_tray_active = False" in src)

print("==== RESULT: PASS=%d FAIL=%d ====" % (PASS, len(FAIL)))
if FAIL:
    print("FAILED:", FAIL)
sys.stdout.flush()
# tkinter 在解释器退出时销毁 root 会触发 Tcl_AsyncDelete 噪声，直接结束进程
os._exit(1 if FAIL else 0)
