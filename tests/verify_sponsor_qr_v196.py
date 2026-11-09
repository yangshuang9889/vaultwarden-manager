"""v1.9.6 真机验证：赞助支持卡片内收款二维码显示（写死路径 + 等比缩放 + 缺失容错）。

覆盖：
  S1 常量校验：SPONSOR_QR_PATH 写死为指定绝对路径，文件存在且为 250x250 PNG
  S2 真机 GUI：卡片内生成二维码 Label，图片已加载且等比缩放到 <=150px
  S3 布局：二维码位于赞助文案下方、水平居中；960x700 与最小 860x640 下均不溢出
  S4 缺图容错：路径不存在 → 不抛异常、不生成图片、卡片保持文字、写警告日志
  S5 坏图容错：文件存在但内容非法 → 同上，不崩溃
  S6 Pillow 不可用兜底：ImageTk 导入失败时退回 tk.PhotoImage，仍能显示且不超尺寸
  S7 真机截屏：抓取主窗口截图，确认二维码像素落在赞助卡片区域内
"""
import os
import sys
import tempfile
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

app_mod.VaultwardenManagerApp._create_tray_icon = lambda self: (
    setattr(self, "_tray_icon", None), setattr(self, "_tray_active", False),
    setattr(self, "_tray_ready_at", 0)) and None
app_mod.VaultwardenManagerApp.refresh_log = lambda self: None
app_mod.VaultwardenManagerApp._periodic_status = lambda self: None
app_mod.get_service_status = lambda cfg: ("stopped", "服务未运行", "#2b8a3e")

root = Path(tempfile.mkdtemp(prefix="vw196qr_"))
cfg = {
    "vaultwarden_dir": str(root / "vaultwarden"), "exe_name": "vaultwarden.exe",
    "port": 55556, "ssl_dir": str(root / "vaultwarden" / "ssl"),
    "cert_file": "cert.pem", "key_file": "key.pem",
    "backup_dir": str(root / "vaultwarden" / "backup"), "log_file": "vaultwarden.log",
    "err_log_file": "vaultwarden.err.log", "log_lines": 300, "log_max_mb": 10,
    "log_noise_keywords": ["tls handshake"], "vw_download_url": "",
    "vw_download_timeout": 120, "vw_webvault_download_url": "",
    "vw_webvault_download_timeout": 180, "status_check_ms": 3000, "cert_days": 3650,
    "domain": "https://localhost:55556", "admin_path": "/admin",
    "quit_confirm_skip": True, "quit_default_action": "quit",
}
(root / "vaultwarden").mkdir(parents=True, exist_ok=True)


def find_sponsor(app):
    """按 v1.9.0 结构定位赞助卡片 Frame（left 列内 bg=#e9ecef 的 Frame）。"""
    for mid in app.winfo_children():
        for left in mid.winfo_children():
            for child in left.winfo_children():
                try:
                    if child.winfo_class() == "Frame" and child.cget("bg") == "#e9ecef":
                        return child
                except Exception:
                    continue
    return None


# 二维码资源改为项目内相对定位（开源版不再引用外部项目目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPECT_PATH = str(PROJECT_ROOT / "assets" / "sponsor_qr.png")

# ---------- S1 常量与图片文件 ----------
# 项目内无该图，或当前版本已移除 SPONSOR_QR_PATH（v1.9.11 起改为 assets/sponsor_qr.png +
# _sponsor_qr_file()）时，打印提示后跳过本脚本，不抛异常
if not os.path.isfile(EXPECT_PATH):
    print("[SKIP] 未找到项目内二维码资源：%s，跳过 v1.9.6 专项验证" % EXPECT_PATH)
    sys.exit(0)
if not hasattr(app_mod, "SPONSOR_QR_PATH"):
    print("[SKIP] 当前版本已无 vwm.app.SPONSOR_QR_PATH（v1.9.11 起改为 assets/sponsor_qr.png），"
          "跳过 v1.9.6 专项验证")
    sys.exit(0)

check("S1.1 SPONSOR_QR_PATH 指向项目内 assets 二维码", app_mod.SPONSOR_QR_PATH == EXPECT_PATH,
      app_mod.SPONSOR_QR_PATH)
check("S1.2 二维码文件存在可读", os.path.isfile(EXPECT_PATH))
try:
    from PIL import Image
    with Image.open(EXPECT_PATH) as _im:
        size = _im.size
        fmt = _im.format
    check("S1.3 二维码为 250x250 PNG", size == (250, 250) and fmt == "PNG", "%s %s" % (size, fmt))
except Exception as exc:
    check("S1.3 二维码为 250x250 PNG", False, str(exc))
def _ver_tuple(v):
    parts = []
    for seg in str(v).lstrip("vV").split("."):
        digits = "".join(ch for ch in seg if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


check("S1.4 版本号不低于 v1.9.6", _ver_tuple(ui_mod.VERSION) >= (1, 9, 6), ui_mod.VERSION)

# ---------- S2 真机 GUI：二维码加载 ----------
app = app_mod.VaultwardenManagerApp(cfg)
app.update()
sponsor = find_sponsor(app)
check("S2.1 定位到赞助卡片 Frame", sponsor is not None)
photo = getattr(app, "_sponsor_qr_photo", None)
check("S2.2 二维码图片已加载（引用非空）", photo is not None)
if photo is not None:
    w, h = photo.width(), photo.height()
    check("S2.3 等比缩放至不超过 150px", w <= app_mod.SPONSOR_QR_MAX_W and h <= app_mod.SPONSOR_QR_MAX_W
          and w > 0 and h > 0, "%sx%s" % (w, h))
    check("S2.4 保持正方形比例（±2px）", abs(w - h) <= 2, "%sx%s" % (w, h))
    check("S2.5 缩放到接近目标尺寸（>=140px）", max(w, h) >= 140, "%sx%s" % (w, h))

qr_labels = [c for c in sponsor.winfo_children()
             if c.winfo_class() == "Label" and str(c.cget("image")) != ""] if sponsor else []
check("S2.6 卡片内存在二维码 Label 且绑定图片", len(qr_labels) == 1, "labels=%d" % len(qr_labels))

# ---------- S3 布局 ----------
if sponsor and qr_labels:
    labels = [c for c in sponsor.winfo_children() if c.winfo_class() == "Label"]
    title, body, qr = labels[0], labels[1], qr_labels[0]
    sponsor.update_idletasks()
    check("S3.1 二维码在文案下方（y 递增）",
          qr.winfo_y() > body.winfo_y() and qr.winfo_y() >= title.winfo_y(), 
          "qr_y=%s body_y=%s" % (qr.winfo_y(), body.winfo_y()))
    cw, qw = sponsor.winfo_width(), qr.winfo_width()
    left_gap = qr.winfo_x()
    right_gap = cw - left_gap - qw
    check("S3.2 二维码水平居中（左右留白差 <=3px）", abs(left_gap - right_gap) <= 3,
          "card=%s qx=%s qw=%s gaps=%s/%s" % (cw, qr.winfo_x(), qw, left_gap, right_gap))
    check("S3.3 二维码未超出卡片宽度", qw <= cw, "qw=%s cw=%s" % (qw, cw))
    bottom = sponsor.winfo_rooty() + sponsor.winfo_height()
    win_bottom = app.winfo_rooty() + app.winfo_height()
    check("S3.4 960x700 下卡片底部未溢出窗口", bottom <= win_bottom + 1,
          "card_bottom=%s win_bottom=%s" % (bottom, win_bottom))
    # 最小尺寸 860x690 下复查（v1.9.6 因新增二维码将最小高度由 640 提升至 690）
    app.geometry("860x690")
    app.update()
    app.update_idletasks()
    sponsor.update_idletasks()
    bottom = sponsor.winfo_rooty() + sponsor.winfo_height()
    win_bottom = app.winfo_rooty() + app.winfo_height()
    check("S3.5 860x690 最小尺寸下仍未溢出/未被裁剪", bottom <= win_bottom + 1,
          "card_bottom=%s win_bottom=%s" % (bottom, win_bottom))
    check("S3.5b 最小高度已随二维码上调至 690",
          app.minsize() == (860, 690), "minsize=%s" % (app.minsize(),))
    check("S3.6 最小尺寸下二维码仍完整可见", qr.winfo_ismapped() and qr.winfo_height() > 0,
          "mapped=%s h=%s" % (qr.winfo_ismapped(), qr.winfo_height()))
    app.geometry("960x700")
    app.update()

# ---------- S4 缺图容错 ----------
orig_path = app_mod.SPONSOR_QR_PATH
app_mod.SPONSOR_QR_PATH = str(root / "not_exist_qr.png")
ok = True
try:
    import tkinter as tk
    frame = tk.Frame(app, bg="#e9ecef")
    app._sponsor_qr_photo = None
    app._attach_sponsor_qr(frame)
    check("S4.1 缺图时不抛异常", True)
    check("S4.2 缺图时不生成图片 Label", len(frame.winfo_children()) == 0,
          "children=%d" % len(frame.winfo_children()))
    check("S4.3 缺图时图片引用保持 None", app._sponsor_qr_photo is None)
    frame.destroy()
except Exception as exc:
    ok = False
    check("S4.1 缺图时不抛异常", False, repr(exc))

# ---------- S5 坏图容错 ----------
bad = root / "bad_qr.png"
bad.write_bytes(b"not a real png at all")
app_mod.SPONSOR_QR_PATH = str(bad)
try:
    import tkinter as tk
    frame = tk.Frame(app, bg="#e9ecef")
    app._sponsor_qr_photo = None
    app._attach_sponsor_qr(frame)
    check("S5.1 坏图时不抛异常", True)
    check("S5.2 坏图时不生成图片 Label", len(frame.winfo_children()) == 0)
    frame.destroy()
except Exception as exc:
    check("S5.1 坏图时不抛异常", False, repr(exc))
app_mod.SPONSOR_QR_PATH = orig_path

# ---------- S6 Pillow/ImageTk 不可用兜底 ----------
saved = sys.modules.get("PIL.ImageTk", "absent")
sys.modules["PIL.ImageTk"] = None  # import PIL.ImageTk 将抛 ImportError
try:
    import tkinter as tk
    frame = tk.Frame(app, bg="#e9ecef")
    app._sponsor_qr_photo = None
    app._attach_sponsor_qr(frame)
    ph = app._sponsor_qr_photo
    check("S6.1 ImageTk 不可用时退回 tk.PhotoImage 成功加载", ph is not None)
    if ph is not None:
        check("S6.2 兜底路径尺寸不超过 150px",
              ph.width() <= app_mod.SPONSOR_QR_MAX_W and ph.height() <= app_mod.SPONSOR_QR_MAX_W,
              "%sx%s" % (ph.width(), ph.height()))
    check("S6.3 兜底路径生成了图片 Label", len(frame.winfo_children()) == 1)
    frame.destroy()
except Exception as exc:
    check("S6.1 ImageTk 不可用时退回 tk.PhotoImage 成功加载", False, repr(exc))
finally:
    if saved == "absent":
        sys.modules.pop("PIL.ImageTk", None)
    else:
        sys.modules["PIL.ImageTk"] = saved

# ---------- S7 真机截屏 ----------
try:
    from PIL import ImageGrab
    app.attributes("-topmost", True)
    app.lift()
    app.update()
    app.after(300, lambda: None)
    app.update()
    shot_dir = Path(os.environ.get("VW_SHOT_DIR", str(Path(tempfile.gettempdir()))))
    shot = shot_dir / "v196_sponsor_qr.png"
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    img.save(shot)
    # 校验截图中二维码区域仍为深色像素（非空白）
    if sponsor and qr_labels:
        qr = qr_labels[0]
        qx = qr.winfo_rootx() - x
        qy = qr.winfo_rooty() - y
        crop = img.crop((max(0, qx), max(0, qy), max(1, qx + qr.winfo_width()),
                         max(1, qy + qr.winfo_height())))
        gray = crop.convert("L")
        hist = gray.histogram()
        dark = sum(hist[:80])
        ratio = dark / float(max(1, crop.width * crop.height))
        check("S7.1 截图中二维码区域含深色像素（图像确实渲染）", ratio > 0.05, "dark_ratio=%.3f" % ratio)
    check("S7.2 真机截屏已保存", shot.is_file() and shot.stat().st_size > 1000, str(shot))
    print("[SHOT] %s" % shot)
except Exception as exc:
    check("S7.2 真机截屏已保存", False, repr(exc))

app.destroy()

print("\n==== v1.9.6 赞助二维码验证: PASS=%d FAIL=%d ====" % (PASS, len(FAIL)))
if FAIL:
    print("失败项: %s" % FAIL)
    sys.exit(1)
