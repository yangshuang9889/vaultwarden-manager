# -*- coding: utf-8 -*-
"""v1.9.3 单实例提示交互验证脚本。

覆盖：
A. 源码编译 + 版本号
B. 提示文案（正常 / 孤儿残留两分支）+ 标题 + 置顶 flag
C. mock user32：有窗口 → 弹一次提示、标题/flags 正确、提示后激活窗口（ShowWindow 9 + SetForegroundWindow）
D. mock user32：无窗口 → 孤儿文案，且不激活
E. 激活抛异常 → 提示仍弹、函数不抛
F. 提示互斥锁：首次 True、同进程二次 False（同一时刻只弹一次）
G. main() 接线：第二实例路径先抢提示锁再弹提示
运行：python verify_single_instance_v193.py
"""
import os
import re
import sys
import types
import ctypes as REAL_CTYPES  # 顶部先绑定真实 ctypes（此后 fake 替换都用它还原）
import ctypes.wintypes as REAL_WINTYPES
import py_compile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results = []


def check(name, cond, extra=""):
    results.append((name, bool(cond), extra))


# ---------- A. 编译 + 版本 ----------
for f in ("vwm/app.py", "vwm/ui.py"):
    try:
        py_compile.compile(os.path.join(BASE, f), doraise=True)
        check("A 编译 %s" % f, True)
    except Exception as e:  # noqa: BLE001
        check("A 编译 %s" % f, False, repr(e))

sys.path.insert(0, BASE)
for m in [k for k in list(sys.modules) if k == "vwm" or k.startswith("vwm.")]:
    del sys.modules[m]
from vwm import app as appmod  # noqa: E402
from vwm import ui as uimod  # noqa: E402

src_app = open(os.path.join(BASE, "vwm", "app.py"), encoding="utf-8").read()
src_ui = open(os.path.join(BASE, "vwm", "ui.py"), encoding="utf-8").read()

def _ver_tuple(text):
    m = re.search(r"v?(\d+)\.(\d+)\.(\d+)", text or "")
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


# v1.9.4：版本号硬编码断言改为语义比较（>= v1.9.3），避免后续版本升级误报
_ver_ui = re.search(r'VERSION\s*=\s*"([^"]+)"', src_ui)
check("A1 VERSION >= v1.9.3",
      _ver_ui is not None and _ver_tuple(_ver_ui.group(1)) >= (1, 9, 3),
      _ver_ui.group(1) if _ver_ui else "not found")


# ---------- 工具：fake ctypes.user32 ----------
class FakeUser32:
    def __init__(self, hwnd=0, raise_on_activate=False):
        self.hwnd = hwnd
        self.msgs = []
        self.show_calls = []
        self.fg_calls = []
        self.raise_on_activate = raise_on_activate

    def FindWindowW(self, cls, title):  # noqa: N802
        return self.hwnd

    def MessageBoxW(self, owner, text, title, flags):  # noqa: N802
        self.msgs.append((owner, text, title, flags))
        return 1

    def ShowWindow(self, hwnd, cmd):  # noqa: N802
        if self.raise_on_activate:
            raise RuntimeError("activate failed")
        self.show_calls.append((hwnd, cmd))
        return 1

    def SetForegroundWindow(self, hwnd):  # noqa: N802
        self.fg_calls.append(hwnd)
        return 1


def with_fake_user32(fake, fn):
    """仅在 fn 执行期间把 sys.modules['ctypes'] 换成带 fake user32 的模块，退出必还原。"""
    mod = types.ModuleType("ctypes")
    mod.windll = types.SimpleNamespace(user32=fake)
    mod.wintypes = REAL_WINTYPES
    sys.modules["ctypes"] = mod
    try:
        return fn()
    finally:
        sys.modules["ctypes"] = REAL_CTYPES  # 无条件还原真实 ctypes


# ---------- B. 文案与 flag 源码断言 ----------
check("B1 标题固定 VaultwardenManager", '"VaultwardenManager", MB_FLAGS' in src_app)
check("B2 正常文案含「程序已在运行中，请勿重复打开」", "程序已在运行中，请勿重复打开。" in src_app)
check("B3 正常文案含托盘/任务栏指引", "可从任务栏窗口或系统托盘图标打开已有窗口。" in src_app)
check("B4 孤儿文案含结束全部进程指引", "结束所有 VaultwardenManager.exe 进程" in src_app)
check("B5 孤儿文案含 taskkill 命令", "taskkill /F /T /IM VaultwardenManager.exe" in src_app)
check("B6 置顶 flag MB_TOPMOST", "0x00040000" in src_app)
check("B7 前台 flag MB_SETFOREGROUND", "0x00010000" in src_app)
check("B8 信息图标 flag MB_ICONINFORMATION", "0x00000040" in src_app)
check("B9 激活在提示之后（ShowWindow 位于 MessageBoxW 之后）",
      src_app.index("MessageBoxW(None, tip") < src_app.index("user32.ShowWindow(hwnd, 9)"))

# ---------- C. 有窗口分支 ----------
fake = FakeUser32(hwnd=123456)
with_fake_user32(fake, lambda: with_fake_user32(fake, appmod._activate_existing_instance))
# 注：函数内部 `import ctypes` + FindWindowW 取 fake；interval 0.5s，命中即返回（无 sleep）
check("C1 有窗口时弹出且仅弹 1 次提示", len(fake.msgs) == 1, str(len(fake.msgs)))
if fake.msgs:
    owner, text, title, flags = fake.msgs[0]
    check("C2 owner=None（第二实例无父窗口）", owner is None)
    check("C3 标题=VaultwardenManager", title == "VaultwardenManager", title)
    check("C4 flags=MB_OK|ICONINFO|TOPMOST|SETFOREGROUND(0x50040)", flags == 0x50040, hex(flags))
    check("C5 正文为「已在运行中」提示", "程序已在运行中" in text and "请勿重复打开" in text, text[:40])
    check("C6 正文含托盘/任务栏指引", "系统托盘图标" in text and "任务栏" in text)
check("C7 提示后激活窗口 ShowWindow(SW_RESTORE=9)", fake.show_calls == [(123456, 9)], str(fake.show_calls))
check("C8 提示后 SetForegroundWindow", fake.fg_calls == [123456], str(fake.fg_calls))

# ---------- D. 无窗口（孤儿残留）分支 ----------
fake2 = FakeUser32(hwnd=0)
try:
    with_fake_user32(fake2, appmod._activate_existing_instance)
    raised = False
except Exception:  # noqa: BLE001
    raised = True
check("D1 无窗口时不抛异常", not raised)
check("D2 无窗口时仍弹出 1 次提示", len(fake2.msgs) == 1, str(len(fake2.msgs)))
if fake2.msgs:
    text2 = fake2.msgs[0][1]
    check("D3 孤儿文案区分（含残留进程/任务管理器指引）",
          "未找到它的主窗口" in text2 and "taskkill" in text2, text2[:60])
    check("D4 孤儿分支标题仍为 VaultwardenManager", fake2.msgs[0][2] == "VaultwardenManager")
check("D5 无窗口时不执行激活", fake2.show_calls == [] and fake2.fg_calls == [])

# ---------- E. 激活失败不影响提示与退出 ----------
fake3 = FakeUser32(hwnd=777, raise_on_activate=True)
try:
    with_fake_user32(fake3, appmod._activate_existing_instance)
    raised3 = False
except Exception:  # noqa: BLE001
    raised3 = True
check("E1 激活抛异常时不向上抛（静默容错）", not raised3)
check("E2 激活失败仍已弹提示", len(fake3.msgs) == 1, str(len(fake3.msgs)))

# ---------- F. 提示互斥锁（同一时刻只弹一次） ----------
sys.modules["ctypes"] = REAL_CTYPES  # 兜底还原真实 ctypes（前面的 fake 替换必须完全复位）
check("F0 ctypes 已复位（windll.kernel32 可用）", hasattr(sys.modules["ctypes"].windll, "kernel32"))
for k in ("_NOTICE_LOCK_HANDLE",):
    appmod.__dict__.pop(k, None)
first = appmod._acquire_notice_lock()
second = appmod._acquire_notice_lock()
check("F1 提示锁首次获取 True", first is True)
check("F2 提示锁同进程二次获取 False（避免重复弹窗）", second is False, str(second))
check("F3 提示锁名固定为 NoticeLock", "Local\\\\VaultwardenManager_NoticeLock" in src_app
      or "Local\\VaultwardenManager_NoticeLock" in src_app)
check("F4 提示锁遵循 SetLastError(0)+183 双条件",
      src_app.count("kernel32.SetLastError(0)") >= 2 and src_app.count("== 183") >= 2)

# ---------- G. main 接线 ----------
check("G1 main 中第二实例先抢提示锁", "if not _acquire_single_instance():" in src_app
      and "if _acquire_notice_lock():" in src_app)
check("G2 第二实例路径提示后 return（自行退出不残留）",
      re.search(r"if _acquire_notice_lock\(\):\s*\n\s*_activate_existing_instance\(\)\s*\n\s*return", src_app) is not None)
check("G3 第二实例不创建窗口/托盘（return 在 app= 之前）",
      src_app.index("if _acquire_notice_lock():") < src_app.index("app = VaultwardenManagerApp(cfg)"))

# ---------- H 置顶加固（v1.9.3 收尾） ----------
seg_top = src_app[src_app.index("def _keep_dialog_topmost"):src_app.index("def _activate_existing_instance")]
check("H1 _keep_dialog_topmost 定义存在并起守护线程",
      "threading.Thread(target=_worker, daemon=True).start()" in seg_top)
check("H2 置顶使用 SetWindowPos(HWND_TOPMOST)",
      "HWND_TOPMOST = -1" in seg_top and "user32.SetWindowPos(h, HWND_TOPMOST" in seg_top)
check("H3 弹框前先启动置顶守护",
      src_app.index("_keep_dialog_topmost(user32, \"VaultwardenManager\")")
      < src_app.index("user32.MessageBoxW(None, tip, \"VaultwardenManager\", MB_FLAGS)"))

# ---------- 汇总 ----------
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
for name, ok, extra in results:
    if not ok:
        print("FAIL |", name, "|", extra)
print("=" * 60)
print("v1.9.3 单实例提示验证: %d/%d PASS" % (passed, total))
print("=" * 60)
sys.stdout.flush()
os._exit(0 if passed == total else 1)
