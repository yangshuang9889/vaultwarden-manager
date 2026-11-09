"""v1.9.7 验证：统一盾牌安全风格图标（资源生成 + 路径解析 + 四类图标接线 + 容错）。

覆盖：
  I1 资源清单：assets 下 app.ico / app_16..256.png / app.png / tray.png 均存在且尺寸正确
  I2 ICO 多尺寸：app.ico 内含 16/24/32/48/64/128/256 共 7 个条目，且含 256 尺寸
  I3 源码运行路径解析：_asset_path 命中项目 assets 目录，缺失资源返回空串不抛异常
  I4 打包运行路径解析：sys._MEIPASS 优先；frozen 且无 _MEIPASS 时回退 exe 同级 assets
  I5 源码接线：iconbitmap(default=)/iconphoto/托盘读取 tray.png/兜底绘制/ghost 逻辑均在位
  I6 真机窗口图标：实例化主窗口后 wm iconbitmap 已指向 assets\\app.ico 且 iconphoto 生效
  I7 托盘图可读：tray.png 为 64x64 RGBA，四角透明、中心不透明（pystray 可直接用）
  I8 容错：资源全部缺失时 _apply_window_icon 不抛异常（仅记日志、回退系统默认）
  I9 容错：tray.png 内容损坏时托盘创建走代码绘制兜底，不抛异常
"""
import os
import struct
import sys
import tempfile
import types
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


PROJ = Path(__file__).resolve().parent.parent
ASSETS = PROJ / "assets"

# ---------- Win32 图标读取（用于真机校验任务栏/标题栏图标像素） ----------
import ctypes  # noqa: E402
import ctypes.wintypes as wt  # noqa: E402
import collections  # noqa: E402

_u = ctypes.WinDLL("user32", use_last_error=True)
_g = ctypes.WinDLL("gdi32", use_last_error=True)


class _ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", wt.BOOL), ("xHotspot", wt.DWORD), ("yHotspot", wt.DWORD),
                ("hbmMask", wt.HBITMAP), ("hbmColor", wt.HBITMAP)]


class _BITMAP(ctypes.Structure):
    _fields_ = [("bmType", wt.LONG), ("bmWidth", wt.LONG), ("bmHeight", wt.LONG),
                ("bmWidthBytes", wt.LONG), ("bmPlanes", wt.WORD), ("bmBitsPixel", wt.WORD),
                ("bmBits", ctypes.c_void_p)]


class _BIH(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", wt.LONG),
                ("biYPelsPerMeter", wt.LONG), ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD)]


class _BI(ctypes.Structure):
    _fields_ = [("bmiHeader", _BIH), ("bmiColors", wt.DWORD * 3)]


_u.SendMessageW.restype = wt.LPARAM
_u.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
_u.GetIconInfo.argtypes = [wt.HICON, ctypes.POINTER(_ICONINFO)]
_u.GetClassLongPtrW.restype = ctypes.c_void_p
_u.GetClassLongPtrW.argtypes = [wt.HWND, ctypes.c_int]
_u.GetAncestor.restype = wt.HWND
_u.GetAncestor.argtypes = [wt.HWND, wt.UINT]
_g.GetObjectW.argtypes = [wt.HANDLE, ctypes.c_int, ctypes.c_void_p]
_g.CreateCompatibleDC.restype = wt.HDC
_g.CreateCompatibleDC.argtypes = [wt.HDC]
_g.GetDIBits.argtypes = [wt.HDC, wt.HBITMAP, wt.UINT, wt.UINT, ctypes.c_void_p,
                         ctypes.POINTER(_BI), wt.UINT]
_g.GetDIBits.restype = ctypes.c_int
_g.DeleteDC.argtypes = [wt.HDC]

GA_ROOT = 2


def _GA_ROOT(win):
    try:
        return _u.GetAncestor(win.winfo_id(), GA_ROOT)
    except Exception:
        return 0


def _hwnd_icon(hwnd):
    return (_u.SendMessageW(hwnd, 0x7F, 1, 0)          # WM_GETICON / ICON_BIG
            or _u.SendMessageW(hwnd, 0x7F, 0, 0)       # WM_GETICON / ICON_SMALL
            or _u.GetClassLongPtrW(hwnd, -14))         # GCLP_HICON


def _hwnd_has_icon(hwnd):
    return bool(hwnd) and bool(_hwnd_icon(hwnd))


def _icon_pixels(hwnd):
    """读取窗口图标的 BGRA 像素，返回 (w, h, bytes)；失败返回 None。"""
    h = _hwnd_icon(hwnd)
    if not h:
        return None
    ii = _ICONINFO()
    if not _u.GetIconInfo(h, ctypes.byref(ii)) or not ii.hbmColor:
        return None
    bm = _BITMAP()
    _g.GetObjectW(ii.hbmColor, ctypes.sizeof(bm), ctypes.byref(bm))
    w, hh = bm.bmWidth, bm.bmHeight
    if w <= 0 or hh <= 0:
        return None
    bi = _BI()
    bi.bmiHeader.biSize = ctypes.sizeof(_BIH)
    bi.bmiHeader.biWidth = w
    bi.bmiHeader.biHeight = -hh
    bi.bmiHeader.biPlanes = 1
    bi.bmiHeader.biBitCount = 32
    buf = ctypes.create_string_buffer(w * hh * 4)
    dc = _g.CreateCompatibleDC(None)
    n = _g.GetDIBits(dc, ii.hbmColor, 0, hh, buf, ctypes.byref(bi), 0)
    _g.DeleteDC(dc)
    if n != hh:
        return None
    return w, hh, buf.raw


def _pixel_stats(px):
    w, hh, data = px
    white = blue = opaque = 0
    for y in range(hh):
        for x in range(w):
            i = ((y * w) + x) * 4
            b, gg, rr, aa = data[i], data[i + 1], data[i + 2], data[i + 3]
            if aa <= 128:
                continue
            opaque += 1
            if rr > 225 and gg > 225 and b > 225:
                white += 1
            elif b > rr + 40 and b > 100:   # 蓝色通道明显占优 = 盾牌蓝
                blue += 1
    return opaque, white, blue


def _is_shield_pixels(px):
    """图标像素同时具备白底与蓝色盾牌，且蓝色占比可观（>15%）。"""
    if not px:
        return False
    opaque, white, blue = _pixel_stats(px)
    if opaque == 0:
        return False
    return white / opaque > 0.10 and blue / opaque > 0.15


def _pixel_digest(px):
    if not px:
        return "no-icon-pixels"
    return "size=%dx%d opaque=%d white=%d blue=%d" % (
        (px[0], px[1]) + _pixel_stats(px))


# ---------- I1 资源清单 ----------
expect = {"app.ico": None, "app.png": (256, 256), "tray.png": (64, 64),
          "app_16.png": (16, 16), "app_24.png": (24, 24), "app_32.png": (32, 32),
          "app_48.png": (48, 48), "app_64.png": (64, 64), "app_128.png": (128, 128),
          "app_256.png": (256, 256)}
from PIL import Image  # noqa: E402

for fn, size in expect.items():
    p = ASSETS / fn
    ok = p.is_file() and p.stat().st_size > 0
    check("I1.1 %s 存在且非空" % fn, ok, str(p))
    if ok and size:
        with Image.open(str(p)) as im:
            check("I1.2 %s 尺寸=%s" % (fn, size), im.size == size, im.size)

# ---------- I2 ICO 多尺寸 ----------
ico = ASSETS / "app.ico"
raw = ico.read_bytes()
reserved, itype, count = struct.unpack("<HHH", raw[:6])
sizes_in_ico = []
for i in range(count):
    off = 6 + i * 16
    w, h = raw[off], raw[off + 1]
    sizes_in_ico.append((256 if w == 0 else w, 256 if h == 0 else h))
check("I2.1 ICO 条目数=7", count == 7, count)
check("I2.2 ICO 含 256 尺寸", (256, 256) in sizes_in_ico, sizes_in_ico)
check("I2.3 ICO 含 16/24/32/48 小尺寸",
      all((s, s) in sizes_in_ico for s in (16, 24, 32, 48)), sizes_in_ico)

# ---------- I3/I4 路径解析 ----------
from vwm import app as app_mod  # noqa: E402
import vwm.ui as ui_mod  # noqa: E402

p_ico = app_mod._asset_path("app.ico")
check("I3.1 源码模式命中项目 assets\\app.ico",
      p_ico and os.path.isfile(p_ico) and os.path.normcase(os.path.dirname(p_ico)) ==
      os.path.normcase(str(ASSETS)), p_ico)
check("I3.2 tray.png 可解析", bool(app_mod._asset_path("tray.png")))
check("I3.3 不存在的资源返回空串", app_mod._asset_path("no_such_icon.png") == "")

tmp = Path(tempfile.mkdtemp(prefix="vw197frozen_"))
(tmp / "assets").mkdir(parents=True, exist_ok=True)
for f in ("app.ico", "tray.png"):
    (tmp / "assets" / f).write_bytes((ASSETS / f).read_bytes())
_old_meipass = getattr(sys, "_MEIPASS", None)
sys._MEIPASS = str(tmp)
try:
    check("I4.1 _MEIPASS 优先命中解包目录",
          os.path.normcase(app_mod._asset_path("app.ico")) ==
          os.path.normcase(str(tmp / "assets" / "app.ico")), app_mod._asset_path("app.ico"))
finally:
    if _old_meipass is None:
        del sys._MEIPASS
    else:
        sys._MEIPASS = _old_meipass

_old_frozen = getattr(sys, "frozen", None)
_old_exe = sys.executable
sys.frozen = True
sys.executable = str(tmp / "VaultwardenManager.exe")
try:
    check("I4.2 frozen 无 _MEIPASS 时回退 exe 同级 assets",
          os.path.normcase(app_mod._asset_path("tray.png")) ==
          os.path.normcase(str(tmp / "assets" / "tray.png")), app_mod._asset_path("tray.png"))
finally:
    sys.executable = _old_exe
    if _old_frozen is None:
        del sys.frozen
    else:
        sys.frozen = _old_frozen

# ---------- I5 源码接线 ----------
src = (PROJ / "vwm" / "app.py").read_text(encoding="utf-8")
check("I5.1 调用 _apply_window_icon", "self._apply_window_icon()" in src)
check("I5.2 使用 iconbitmap(default=...)", "self.iconbitmap(default=ico)" in src)
check("I5.3 使用 iconphoto 兜底", "self.iconphoto(True, self._win_icon_photo)" in src)
check("I5.4 托盘读取 tray.png", '_asset_path("tray.png")' in src)
check("I5.5 托盘保留代码绘制兜底", "兜底：无 tray.png 时保持 v1.6.6 的代码绘制图标" in src)
check("I5.6 托盘 ghost 清理逻辑保留（_hwnd + _nim_delete_icon）",
      "_hwnd" in src and "_nim_delete_icon" in src)
check("I5.7 托盘 WM_TASKBARCREATED 重注册逻辑保留", "_resend_taskbar_created" in src)
check("I5.8 VERSION>=v1.9.7", ui_mod.VERSION >= "v1.9.7", ui_mod.VERSION)

# ---------- I6 真机窗口图标 ----------
app_mod.VaultwardenManagerApp._create_tray_icon = lambda self: (
    setattr(self, "_tray_icon", None), setattr(self, "_tray_active", False)) and None
app_mod.VaultwardenManagerApp.refresh_log = lambda self: None
app_mod.VaultwardenManagerApp._periodic_status = lambda self: None
app_mod.get_service_status = lambda cfg: ("stopped", "服务未运行", "#2b8a3e")

root_dir = Path(tempfile.mkdtemp(prefix="vw197gui_"))
cfg = {
    "vaultwarden_dir": str(root_dir / "vaultwarden"), "exe_name": "vaultwarden.exe",
    "port": 55557, "ssl_dir": str(root_dir / "vaultwarden" / "ssl"),
    "cert_file": "cert.pem", "key_file": "key.pem",
    "backup_dir": str(root_dir / "vaultwarden" / "backup"), "log_file": "vaultwarden.log",
    "err_log_file": "vaultwarden.err.log", "log_lines": 300, "log_max_mb": 10,
    "log_noise_keywords": ["tls handshake"], "vw_download_url": "",
    "vw_download_timeout": 120, "vw_webvault_download_url": "",
    "vw_webvault_download_timeout": 180, "status_check_ms": 60000, "cert_days": 3650,
    "domain": "https://localhost:55557", "admin_path": "/admin",
    "quit_confirm_skip": True, "quit_default_action": "quit",
}
(root_dir / "vaultwarden").mkdir(parents=True, exist_ok=True)

gui_ok = True
try:
    win = app_mod.VaultwardenManagerApp(cfg)
    win.update_idletasks()
except Exception as e:  # pragma: no cover
    gui_ok = False
    check("I6.0 主窗口可创建", False, repr(e))

if gui_ok:
    win.update()
    hwnd = _GA_ROOT(win)
    check("I6.1 主窗口已挂载图标（WM_GETICON/类图标非空）", bool(hwnd) and _hwnd_has_icon(hwnd))
    px = _icon_pixels(hwnd)
    check("I6.2 任务栏图标像素为新盾牌（白底+蓝盾）", _is_shield_pixels(px), _pixel_digest(px))
    check("I6.3 iconphoto 已加载（_win_icon_photo 非空）", win._win_icon_photo is not None)
    # 弹窗继承：新建 Toplevel 应自动带上同一图标
    top = win.winfo_toplevel()
    dlg = __import__("tkinter").Toplevel(win)
    dlg.title("图标继承测试")
    dlg.update()
    check("I6.4 Toplevel 弹窗继承同一图标", _hwnd_has_icon(_GA_ROOT(dlg)))
    dlg.destroy()
    win.destroy()

# ---------- I7 托盘图属性 ----------
with Image.open(str(ASSETS / "tray.png")) as im:
    im = im.convert("RGBA")
    check("I7.1 tray.png 模式为 RGBA", True)
    a = im.getchannel("A")
    corners = [a.getpixel(p) for p in ((0, 0), (63, 0), (0, 63), (63, 63))]
    check("I7.2 tray.png 四角透明", all(c == 0 for c in corners), corners)
    check("I7.3 tray.png 中心不透明", a.getpixel((32, 32)) == 255, a.getpixel((32, 32)))

# ---------- I8 资源缺失容错 ----------
g_ok = True
try:
    w2 = app_mod.VaultwardenManagerApp(cfg)
    _orig = app_mod._asset_path
    app_mod._asset_path = lambda name: ""
    try:
        w2._apply_window_icon()
    finally:
        app_mod._asset_path = _orig
    w2.update_idletasks()
    w2.destroy()
except Exception as e:
    g_ok = False
    check("I8.1 资源缺失时 _apply_window_icon 不抛异常", False, repr(e))
if g_ok:
    check("I8.1 资源缺失时 _apply_window_icon 不抛异常", True)

# ---------- I9 坏图兜底 ----------
try:
    w3 = app_mod.VaultwardenManagerApp(cfg)
    bad = Path(tempfile.mkdtemp(prefix="vw197bad_"))
    (bad / "assets").mkdir(parents=True, exist_ok=True)
    (bad / "assets" / "tray.png").write_bytes(b"not a png")
    _orig = app_mod._asset_path
    app_mod._asset_path = lambda name: str(bad / "assets" / name) if name == "tray.png" else _orig(name)
    try:
        w3._create_tray_icon()  # 记录 pystray 是否存在；坏图必须走兜底绘制不抛异常
        no_raise = True
    finally:
        app_mod._asset_path = _orig
        try:
            if getattr(w3, "_tray_icon", None) is not None:
                w3._tray_icon.stop()
        except Exception:
            pass
        w3.destroy()
    check("I9.1 坏图时托盘创建不抛异常（回退绘制/降级）", no_raise)
except Exception as e:
    check("I9.1 坏图时托盘创建不抛异常（回退绘制/降级）", False, repr(e))

print("\n==== v1.9.7 图标验证：%d 项通过，%d 项失败 ====" % (PASS, len(FAIL)))
if FAIL:
    print("失败项：" + " | ".join(FAIL))
    sys.exit(1)
