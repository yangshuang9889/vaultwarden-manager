# -*- coding: utf-8 -*-
"""v1.9.3 孤儿残留分支验证：持有单实例互斥但不建窗口 → 第二实例应弹「孤儿残留」文案。

用法：python verify_si_orphan.py [exe|src]
"""
import ctypes
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes

from pathlib import Path

BASE = str(Path(__file__).resolve().parent.parent)  # 项目根目录：脚本位于 tests/ 下，向上两级
MODE = (sys.argv[1] if len(sys.argv) > 1 else "src").lower()
user32 = ctypes.windll.user32
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
DLG_TITLE = "VaultwardenManager"
report = {"mode": MODE}

HOLDER = os.path.join(os.environ.get("TEMP", "."), "hold_mutex_v193.py")
with open(HOLDER, "w", encoding="utf-8") as f:
    f.write('''import ctypes, time
from ctypes import wintypes
k = ctypes.windll.kernel32
k.CreateMutexW.restype = wintypes.HANDLE
k.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
h = k.CreateMutexW(None, False, "Local\\\\VaultwardenManager_SingleInstance")
print("holding", h, flush=True)
time.sleep(60)
''')


def find_dialog(timeout=20.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        hw = []

        def cb(h, _):
            if not user32.IsWindowVisible(h):
                return True
            n = user32.GetWindowTextLengthW(h)
            if n:
                b = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(h, b, n + 1)
                if b.value == DLG_TITLE:
                    hw.append(h)
            return True

        user32.EnumWindows(EnumWindowsProc(cb), 0)
        if hw:
            return hw[0], round(time.time() - t0, 2)
        time.sleep(0.2)
    return 0, None


def dlg_text(hwnd):
    child = user32.GetWindow(hwnd, 5)  # GW_CHILD
    out = []
    while child:
        cls = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(child, cls, 64)
        if cls.value == "Static":
            n = user32.GetWindowTextLengthW(child)
            if n:
                b = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(child, b, n + 1)
                if b.value.strip():
                    out.append(b.value)
        child = user32.GetWindow(child, 2)  # GW_HWNDNEXT
    return out


# 1) 启动互斥持有者（模拟强杀遗留的孤儿进程）
pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
holder = subprocess.Popen([pythonw, HOLDER])
time.sleep(2.0)
report["孤儿互斥持有者已启动"] = holder.poll() is None

# 2) 启动程序（应视为第二实例，走孤儿文案分支）
if MODE == "exe":
    exe = os.path.join(BASE, "dist", "VaultwardenManager.exe")
    p = subprocess.Popen([exe], cwd=os.path.dirname(exe))
else:
    p = subprocess.Popen([pythonw, os.path.join(BASE, "vaultwarden_manager.py")], cwd=BASE)

hwnd, dt = find_dialog(25)
report["弹出提示"] = bool(hwnd)
report["提示耗时(s)"] = dt
if hwnd:
    report["提示正文"] = dlg_text(hwnd)
    user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
t0 = time.time()
while time.time() - t0 < 15 and p.poll() is None:
    time.sleep(0.2)
report["程序退出码"] = p.poll()
report["程序已退出"] = p.poll() is not None

# 3) 清理
try:
    holder.kill()
except Exception:
    pass
subprocess.run(["taskkill", "/F", "/T", "/IM", "VaultwardenManager.exe"], capture_output=True)

out = os.path.join(BASE, "live_report_orphan_%s.json" % MODE)
with open(out, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("REPORT ->", out)
