# -*- coding: utf-8 -*-
"""v1.9.3 真机验证：第二实例弹提示→自行退出；快速连开只弹一次；已有实例窗口不受影响。

用法：python verify_si_live.py [exe|src]
  exe = 测 dist\\VaultwardenManager.exe（默认）
  src = 测源码 pythonw vaultwarden_manager.py
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import ctypes
from ctypes import wintypes

BASE = str(Path(__file__).resolve().parent.parent)  # 项目根目录：脚本位于 tests/ 下，向上两级
MODE = (sys.argv[1] if len(sys.argv) > 1 else "exe").lower()

user32 = ctypes.windll.user32
EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

MAIN_TITLE = "Vaultwarden 管理工具"
DLG_TITLE = "VaultwardenManager"

report = {}


def find_windows(title):
    out = []

    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if buf.value == title:
                out.append(hwnd)
        return True

    EnumWindows(EnumWindowsProc(cb), 0)
    return out


def dlg_texts(hwnd):
    """取对话框静态文本（#32770 内的 Static 控件）"""
    texts = []

    def cb(h, _):
        cls = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(h, cls, 64)
        if cls.value == "Static":
            n = user32.GetWindowTextLengthW(h)
            if n:
                b = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(h, b, n + 1)
                if b.value.strip():
                    texts.append(b.value)
        return True

    EnumWindows(EnumWindowsProc(cb), 0)
    # 只保留对话框自身子控件
    texts2 = []
    GW_CHILD = 5
    GW_HWNDNEXT = 2
    child = user32.GetWindow(hwnd, GW_CHILD)
    while child:
        cls = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(child, cls, 64)
        if cls.value == "Static":
            n = user32.GetWindowTextLengthW(child)
            if n:
                b = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(child, b, n + 1)
                if b.value.strip():
                    texts2.append(b.value)
        child = user32.GetWindow(child, GW_HWNDNEXT)
    return texts2 or texts


def pids():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq VaultwardenManager.exe",
                          "/FO", "CSV", "/NH"], capture_output=True, text=True,
                         encoding="gbk", errors="ignore").stdout
    r = []
    for line in out.splitlines():
        parts = [x.strip('"') for x in line.split('","')]
        if parts and parts[0] == "VaultwardenManager.exe":
            r.append(parts[1])
    return r


def py_pids():
    """列出正在运行的 vaultwarden_manager.py 源码实例 PID（PowerShell CIM，wmic 在新系统已移除）"""
    ps = ("Get-CimInstance Win32_Process -Filter \"name='pythonw.exe'\" | "
          "Where-Object { $_.CommandLine -like '*vaultwarden_manager.py*' } | "
          "Select-Object -ExpandProperty ProcessId")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                         capture_output=True, text=True, encoding="utf-8", errors="ignore").stdout
    return [x.strip() for x in out.splitlines() if x.strip().isdigit()]


def launch():
    if MODE == "exe":
        exe = os.path.join(BASE, "dist", "VaultwardenManager.exe")
        return subprocess.Popen([exe], cwd=os.path.dirname(exe))
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return subprocess.Popen([pythonw, os.path.join(BASE, "vaultwarden_manager.py")], cwd=BASE)


def cleanup():
    subprocess.run(["taskkill", "/F", "/T", "/IM", "VaultwardenManager.exe"], capture_output=True)
    subprocess.run(["taskkill", "/F", "/T", "/IM", "pythonw.exe"], capture_output=True)
    time.sleep(1)


def wait_dialog(timeout=15.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        hw = find_windows(DLG_TITLE)
        if hw:
            return hw[0], round(time.time() - t0, 2)
        time.sleep(0.2)
    return 0, None


def close_dialog(hwnd):
    WM_CLOSE = 0x0010
    user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)


def main():
    cleanup()
    report["mode"] = MODE

    # 1) 第一实例（已有实例）
    p1 = launch()
    t0 = time.time()
    while time.time() - t0 < 25:
        if find_windows(MAIN_TITLE):
            break
        time.sleep(0.3)
    time.sleep(1.5)
    report["主窗口出现"] = bool(find_windows(MAIN_TITLE))
    report["第一实例存活"] = p1.poll() is None

    # 2) 第二实例：应弹提示并退出
    p2 = launch()
    hwnd, dt = wait_dialog(18)
    report["第二实例弹出提示"] = bool(hwnd)
    report["提示出现耗时(s)"] = dt
    if hwnd:
        cls = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, cls, 64)
        report["提示框类名"] = cls.value
        report["提示正文"] = dlg_texts(hwnd)
        # 检查置顶样式
        GWL_EXSTYLE = -20
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        report["WS_EX_TOPMOST"] = bool(ex & 0x00000008)
        close_dialog(hwnd)
    # 第二实例退出
    t1 = time.time()
    while time.time() - t1 < 15 and p2.poll() is None:
        time.sleep(0.2)
    report["第二实例退出码"] = p2.poll()
    report["第二实例已退出"] = p2.poll() is not None
    time.sleep(1.0)
    report["第一实例仍存活(未受阻塞)"] = p1.poll() is None
    report["主窗口仍在"] = bool(find_windows(MAIN_TITLE))
    report["进程残留情况"] = (pids() if MODE == "exe" else py_pids())

    # 3) 快速连续启动 3 个第二实例：同一时刻只弹一次提示
    procs = [launch() for _ in range(3)]
    hwnd2, dt2 = wait_dialog(15)
    time.sleep(2.0)
    dlg_count = len(find_windows(DLG_TITLE))
    report["连开3个时同时存在的提示框数"] = dlg_count
    report["连开3个提示出现"] = bool(hwnd2)
    if hwnd2:
        close_dialog(hwnd2)
    t2 = time.time()
    while time.time() - t2 < 20 and any(p.poll() is None for p in procs):
        time.sleep(0.3)
    report["连开3个退出码"] = [p.poll() for p in procs]
    report["连开3个全部退出"] = all(p.poll() is not None for p in procs)
    time.sleep(1.0)
    report["连开后第一实例仍存活"] = p1.poll() is None
    report["连开后主窗口仍在"] = bool(find_windows(MAIN_TITLE))
    report["连开后进程数"] = len(pids() if MODE == "exe" else py_pids())

    cleanup()
    report["清理后残留"] = (pids() if MODE == "exe" else py_pids())
    out_path = os.path.join(BASE, "live_report_%s.json" % MODE)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("REPORT ->", out_path)


if __name__ == "__main__":
    main()
