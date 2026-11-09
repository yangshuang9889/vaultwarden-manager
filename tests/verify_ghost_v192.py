# -*- coding: utf-8 -*-
"""v1.9.2 一次性验证脚本：托盘 ghost 清理 + 单实例互斥误判修复 + 退出 NIM_DELETE 兜底。

纯静态 + 轻量运行时断言，不创建 Tk 窗口（避免 Tcl_AsyncDelete）。
运行前请确保没有 VaultwardenManager 进程 / 源码实例在运行。
用法：python verify_ghost_v192.py
"""
import os
import py_compile
import sys
import ctypes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "vwm", "app.py")
UI = os.path.join(ROOT, "vwm", "ui.py")
sys.path.insert(0, ROOT)

PASS = []
FAIL = []


def check(name, cond, extra=""):
    if cond:
        PASS.append(name)
        print("[PASS] %s %s" % (name, extra))
    else:
        FAIL.append(name)
        print("[FAIL] %s %s" % (name, extra))


def src(path):
    return open(path, encoding="utf-8").read()


app_src = src(APP)
ui_src = src(UI)
main_src = app_src[app_src.index("def main():"):]

# ---------- A 语法编译 ----------
for label, path in (("A1 compile app.py", APP), ("A2 compile ui.py", UI)):
    try:
        py_compile.compile(path, doraise=True)
        check(label, True)
    except Exception as e:
        check(label, False, str(e))

# ---------- B 启动广播清 ghost ----------
check("B1 _refresh_tray_icons defined", "def _refresh_tray_icons()" in app_src
      and "PostMessageW(HWND_BROADCAST" in app_src)
check("B2 broadcast params", "HWND_BROADCAST = 0xFFFF" in app_src
      and "WM_TIMECHANGE = 0x001A" in app_src
      and "PostMessageW(HWND_BROADCAST, WM_TIMECHANGE, 0, 0)" in app_src)

i_bc = main_src.index("_refresh_tray_icons()")
i_app = main_src.index("VaultwardenManagerApp(cfg)")
i_mutex = main_src.index("_acquire_single_instance()")
check("B3 broadcast before app creation", i_bc < i_app, "(bc=%d app=%d)" % (i_bc, i_app))
check("B4 mutex check first, sleep 2.5 before app",
      i_mutex < i_bc and "time.sleep(2.5)" in main_src[i_bc:i_app])

# B5 运行时：ctypes 异常时静默跳过
import vwm.app as appmod

_real_windll = getattr(ctypes, "windll", None)


class _Boom(object):
    def __getattr__(self, name):
        raise OSError("simulated ctypes failure")


try:
    ctypes.windll = _Boom()
    appmod._refresh_tray_icons()
    B5 = True
except Exception:
    B5 = False
finally:
    ctypes.windll = _real_windll
check("B5 broadcast silent on ctypes error", B5)

# ---------- C 单实例互斥（误判修复） ----------
seg = app_src[app_src.index("def _acquire_single_instance"):app_src.index("def _activate_existing_instance")]
check("C1 SetLastError(0) before CreateMutexW",
      seg.index("SetLastError(0)") < seg.index("CreateMutexW(None"), "")
check("C2 handle kept + 183 dual condition",
      "GetLastError() == 183" in seg and '_SINGLE_INSTANCE_HANDLE' in seg
      and ".restype" in seg and ".argtypes" in seg)

import subprocess
proc_count = 0
try:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq VaultwardenManager.exe", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True, timeout=30).stdout
    proc_count = out.lower().count("vaultwardenmanager.exe")
except Exception:
    pass
check("C0 no running instance before mutex test", proc_count == 0, "count=%d" % proc_count)
check("C3 first acquire True", appmod._acquire_single_instance() is True)
check("C4 second acquire False (same process)", appmod._acquire_single_instance() is False)

# ---------- D 退出 NIM_DELETE 兜底 ----------
fc = app_src[app_src.index("def _final_cleanup"):app_src.index("def _nim_delete_icon")]
check("D1 _final_cleanup calls _nim_delete_icon", "self._nim_delete_icon(_tray_hwnd, _tray_hid)" in fc)
check("D2 NIM_DELETE after icon.stop()",
      fc.index("icon.stop()") < fc.index("_nim_delete_icon("))
nim = app_src[app_src.index("def _nim_delete_icon"):app_src.index("# ---------- 部署进度条")]
check("D3 Shell_NotifyIconW(2) invoked", "Shell_NotifyIconW(2," in nim)
try:
    appmod.VaultwardenManagerApp._nim_delete_icon(None, 0, 123)
    D4 = True
except Exception:
    D4 = False
check("D4 silent on invalid hwnd", D4)
try:
    import pystray._win32 as pw
    psy = src(pw.__file__)
    check("D5 pystray hID == id(self)", "hID = id(self)" in psy or "hID=id(self)" in psy.replace(" ", " "))
except Exception as e:
    check("D5 pystray hID == id(self)", False, str(e))

# ---------- E TaskbarCreated 重注册兜底 ----------
check("E1 _resend_taskbar_created defined",
      "def _resend_taskbar_created(self)" in app_src
      and 'RegisterWindowMessageW("TaskbarCreated")' in app_src
      and "PostMessageW(hwnd, msg, 0, 0)" in app_src)
ct = app_src[app_src.index("def _create_tray_icon"):app_src.index("def _resend_taskbar_created")]
check("E2 delayed resend wired in _create_tray_icon",
      "self.after(2000, self._resend_taskbar_created)" in ct
      and ct.index("_tray_active = True") < ct.index("self.after(2000"))

# ---------- F 版本 ----------
import re as _re
_m = _re.search(r'VERSION\s*=\s*"(v[\d.]+)"', ui_src)
_vt = tuple(int(x) for x in _m.group(1).lstrip("v").split(".")) if _m else (0,)
check("F1 VERSION >= v1.9.2", _vt >= (1, 9, 2), "found=%s" % (_m.group(1) if _m else "none"))

print("\n==== RESULT: PASS=%d FAIL=%d ====" % (len(PASS), len(FAIL)))
if FAIL:
    print("FAILED:", ", ".join(FAIL))
sys.exit(0 if not FAIL else 1)
