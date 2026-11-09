# -*- coding: utf-8 -*-
"""v1.9.11 验证：赞助支持区自主窗口迁至「关于」窗口 + 项目内收款二维码。

覆盖：
  A 常量与二维码资源：版本号、赞助常量、assets/sponsor_qr.png 属性、路径解析、加载缩放与非空白像素
  B 容错与自适应：图片缺失/损坏返回占位不抛异常；_sponsor_qr_max_w 按容器宽度夹紧
  C 源码断言：主窗口赞助卡片与 _attach_sponsor_qr / SPONSOR_QR_PATH 已移除、minsize 回收 640
  D 真机关于窗口：标题/尺寸/控件文案、二维码非空白、居中、无裁剪、「确定」可关闭
  E 真机主窗口：无赞助控件、13 个按钮齐全、minsize 860×640、默认 960×700
  F 真机设置窗口：无任何「赞助」控件、无二维码图片、四分区齐全、保存/取消仍在位
"""
import os
import sys
import tempfile
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


PROJ = Path(__file__).resolve().parent.parent

from vwm import app as app_mod  # noqa: E402
import vwm.ui as ui_mod  # noqa: E402

# 隔离：不建托盘、不轮询真实服务、不刷新真实日志、不探测真实网卡
app_mod.VaultwardenManagerApp._create_tray_icon = lambda self: (
    setattr(self, "_tray_icon", None), setattr(self, "_tray_active", False),
    setattr(self, "_tray_ready_at", 0)) and None
app_mod.VaultwardenManagerApp.refresh_log = lambda self: None
app_mod.VaultwardenManagerApp._periodic_status = lambda self: None
app_mod.get_service_status = lambda cfg: ("stopped", "服务未运行", "#2b8a3e")
ui_mod.get_lan_ip_info = lambda refresh=False: {
    "primary": "198.51.100.10", "candidates": ["198.51.100.10"], "details": [],
    "excluded": [], "udp_probe": "198.51.100.10", "source": "test", "cached": False}

root_dir = Path(tempfile.mkdtemp(prefix="vw1911sp_"))
cfg = {
    "vaultwarden_dir": str(root_dir / "vaultwarden"), "exe_name": "vaultwarden.exe",
    "port": 55557, "ssl_dir": str(root_dir / "vaultwarden" / "ssl"),
    "cert_file": "cert.pem", "key_file": "key.pem",
    "backup_dir": str(root_dir / "vaultwarden" / "backup"), "log_file": "vaultwarden.log",
    "err_log_file": "vaultwarden.err.log", "log_lines": 300, "log_max_mb": 10,
    "log_noise_keywords": ["tls handshake"], "vw_download_url": "",
    "vw_download_timeout": 120, "vw_webvault_download_url": "",
    "vw_webvault_download_timeout": 180, "status_check_ms": 3000, "cert_days": 3650,
    "domain": "https://localhost:55557", "admin_path": "/admin",
    "quit_confirm_skip": True, "quit_default_action": "quit",
}
(root_dir / "vaultwarden").mkdir(parents=True, exist_ok=True)


def walk(widget, out=None):
    out = [] if out is None else out
    for child in widget.winfo_children():
        out.append(child)
        walk(child, out)
    return out


def texts(widget):
    vals = []
    for c in walk(widget):
        try:
            t = c.cget("text")
        except Exception:
            continue
        if t:
            vals.append(str(t))
    return vals


def dark_pixels(photo, step=5):
    """把 Tk 实际持有的图片对象转回 PIL 统计深色像素数（验证非空白、确有码点）。"""
    try:
        from PIL import ImageTk
        img = ImageTk.getimage(photo).convert("RGB")
    except Exception:
        return -1
    w, h = img.size
    px = img.load()
    cnt = 0
    for x in range(0, w, step):
        for y in range(0, h, step):
            r, g, b = px[x, y]
            if r < 200 or g < 200 or b < 200:
                cnt += 1
    return cnt


# ---------- A 常量与二维码资源 ----------
check("A1 版本号已升为 v1.9.11", ui_mod.VERSION == "v1.9.11", ui_mod.VERSION)
check("A2.1 SPONSOR_QR_NAME=sponsor_qr.png", ui_mod.SPONSOR_QR_NAME == "sponsor_qr.png")
check("A2.2 SPONSOR_QR_MAX_W=150", ui_mod.SPONSOR_QR_MAX_W == 150)
check("A2.3 SPONSOR_QR_MIN_W=96", ui_mod.SPONSOR_QR_MIN_W == 96)
check("A2.4 SPONSOR_TITLE=赞助支持", ui_mod.SPONSOR_TITLE == "赞助支持")
check("A2.5 赞助文案三段齐全",
      ui_mod.SPONSOR_TEXT.count("\n") == 2 and "一元不嫌少" in ui_mod.SPONSOR_TEXT
      and "赞助属于自愿行为" in ui_mod.SPONSOR_TEXT)
check("A2.6 二维码提示文案含点击放大", "点击二维码" in ui_mod.SPONSOR_QR_HINT)
check("A2.7 卡片配色常量齐备",
      ui_mod.C_SP_CARD == "#e9ecef" and ui_mod.C_SP_TITLE and ui_mod.C_SP_TEXT and ui_mod.C_SP_HINT)

qr_asset = PROJ / "assets" / "sponsor_qr.png"
check("A3.1 assets/sponsor_qr.png 存在", qr_asset.is_file(), str(qr_asset))
try:
    from PIL import Image
    with Image.open(qr_asset) as _im:
        size, fmt = _im.size, _im.format
    check("A3.2 二维码为 250×250 PNG", size == (250, 250) and fmt == "PNG", "%s %s" % (size, fmt))
except Exception as exc:
    check("A3.2 二维码为 250×250 PNG", False, str(exc))

path = ui_mod._sponsor_qr_file()
check("A4 路径解析命中项目 assets 绝对路径",
      bool(path) and os.path.isabs(path) and os.path.isfile(path)
      and path.lower().endswith("assets\\sponsor_qr.png"), path)

# ---------- C 源码断言（不依赖 Tk） ----------
src_app = (PROJ / "vwm" / "app.py").read_text(encoding="utf-8")
src_ui = (PROJ / "vwm" / "ui.py").read_text(encoding="utf-8")
check("C1.1 app.py 已无 SPONSOR_QR_PATH 常量", "SPONSOR_QR_PATH" not in src_app)
check("C1.2 app.py 已无 _attach_sponsor_qr 方法", "_attach_sponsor_qr" not in src_app)
check("C1.3 app.py 已无写死外链二维码路径", "ewmsk" not in src_app)
check("C1.4 app.py 已无赞助卡片控件（无 text=\"赞助支持\" / e9ecef 卡片）",
      'text="赞助支持"' not in src_app and '"#e9ecef"' not in src_app)
check("C1.5 app.py 无 _sponsor_qr_photo 残留", "_sponsor_qr_photo" not in src_app)
check("C2 主窗口 minsize 回收为 860×640", "self.minsize(860, 640)" in src_app)
check("C3.1 ui.py 关于窗口使用 SPONSOR_TITLE", "text=SPONSOR_TITLE" in src_ui)
check("C3.2 ui.py 关于窗口使用 SPONSOR_TEXT", "text=SPONSOR_TEXT" in src_ui)
check("C3.3 ui.py 关于窗口含二维码占位提示", "二维码暂不可用" in src_ui)

print("\n---- 启动真机 GUI ----")
app = app_mod.VaultwardenManagerApp(cfg)
app.update()

# ---------- A 续：真实 Tk 下的加载与缩放 ----------
photo150, p150, err150 = ui_mod._load_sponsor_qr(150)
check("A5.1 加载并等比缩放至 150×150",
      photo150 is not None and photo150.width() == 150 and photo150.height() == 150,
      "%s %s" % (getattr(photo150, "width", lambda: None)(), err150))
check("A5.2 缩放后像素非空白（含深色码点）", dark_pixels(photo150) > 50,
      "dark=%d" % dark_pixels(photo150))
photo96, _p96, err96 = ui_mod._load_sponsor_qr(96)
check("A6 小尺寸自适应缩放至 96×96",
      photo96 is not None and photo96.width() == 96 and photo96.height() == 96, err96)

# ---------- B 容错与自适应 ----------
_orig_file = ui_mod._sponsor_qr_file
try:
    ui_mod._sponsor_qr_file = lambda: ""
    miss = ui_mod._load_sponsor_qr(150)
    check("B1.1 图片缺失时返回 None 且不抛异常", miss[0] is None and miss[1] == "", str(miss[2]))
    bad_png = root_dir / "bad_qr.png"
    bad_png.write_bytes(b"not a png at all")
    ui_mod._sponsor_qr_file = lambda: str(bad_png)
    bad = ui_mod._load_sponsor_qr(150)
    check("B1.2 图片损坏时返回 None 且带错误原因", bad[0] is None and bad[2] != "", str(bad[2]))
finally:
    ui_mod._sponsor_qr_file = _orig_file


class _FakeBox:
    def __init__(self, w):
        self._w = w

    def update_idletasks(self):
        return None

    def winfo_width(self):
        return self._w


check("B2.1 宽窗口（460px）自适应取上限 150", ui_mod._sponsor_qr_max_w(_FakeBox(460)) == 150,
      ui_mod._sponsor_qr_max_w(_FakeBox(460)))
check("B2.2 中等宽度（200px）自适应取 140", ui_mod._sponsor_qr_max_w(_FakeBox(200)) == 140,
      ui_mod._sponsor_qr_max_w(_FakeBox(200)))
check("B2.3 窄窗口（100px）不低下限 96", ui_mod._sponsor_qr_max_w(_FakeBox(100)) == 96,
      ui_mod._sponsor_qr_max_w(_FakeBox(100)))
check("B2.4 未布局（宽度 1）退化为上限 150", ui_mod._sponsor_qr_max_w(_FakeBox(1)) == 150,
      ui_mod._sponsor_qr_max_w(_FakeBox(1)))

# ---------- D 真机关于窗口 ----------
res = {}


def _about_probe(attempt=0):
    win = None
    for c in app.winfo_children():
        if isinstance(c, tk.Toplevel) and c.title() == "关于":
            win = c
            break
    if win is None:
        res["found"] = False
        return
    res["found"] = True
    win.update_idletasks()
    win.update()
    # 首次探测时窗口可能尚未完成映射，稍后再测一次，避免误判
    _lab_now = [c for c in walk(win)
                if c.winfo_class() == "Label" and str(c.cget("image") or "")]
    if _lab_now and not _lab_now[0].winfo_ismapped() and attempt < 3:
        app.after(300, lambda: _about_probe(attempt + 1))
        return
    res["title"] = win.title()
    res["w"], res["h"] = win.winfo_width(), win.winfo_height()
    res["texts"] = texts(win)
    photo = getattr(win, "_sponsor_qr_photo", None)
    res["photo"] = photo
    if photo is not None:
        res["pw"], res["ph"] = photo.width(), photo.height()
        res["dark"] = dark_pixels(photo)
        lab = [c for c in walk(win)
               if c.winfo_class() == "Label" and str(c.cget("image") or "")]
        res["qr_labels"] = len(lab)
        if lab:
            res["qr_visible"] = lab[0].winfo_ismapped()
            res["qr_bottom"] = lab[0].winfo_rooty() - win.winfo_rooty() + lab[0].winfo_height()
            res["qr_center_x"] = (lab[0].winfo_rootx() - win.winfo_rootx()
                                  + lab[0].winfo_width() // 2)
    bottom = 0
    for c in walk(win):
        try:
            bottom = max(bottom, c.winfo_rooty() - win.winfo_rooty() + c.winfo_height())
        except Exception:
            continue
    res["bottom"] = bottom
    btns = [c for c in walk(win) if c.winfo_class() == "Button" and str(c.cget("text")) == "确定"]
    res["ok_btn"] = len(btns)
    if btns:
        btns[0].invoke()


app.after(500, _about_probe)
ui_mod.show_about_dialog(app, cfg)
app.update()

check("D1 关于窗口正常弹出", res.get("found") is True)
check("D2 窗口标题为「关于」", res.get("title") == "关于", res.get("title"))
check("D3 窗口宽度 460、高度不小于 560",
      res.get("w") == 460 and res.get("h", 0) >= 560, "%sx%s" % (res.get("w"), res.get("h")))
_t = res.get("texts") or []
check("D4.1 保留软件名称", any("VaultwardenManager" == x for x in _t))
check("D4.2 保留版本行 v1.9.11", any("版本：v1.9.11" == x for x in _t), str(_t[:3]))
check("D4.3 保留作者/制作人/制作工具",
      any("杨爽工作室" in x for x in _t) and any("制作人：杨爽" == x for x in _t)
      and any("制作工具：Marvis" == x for x in _t))
check("D4.4 新增赞助标题「赞助支持」", any("赞助支持" == x for x in _t))
check("D4.5 新增赞助文案（含一元不嫌少）", any("一元不嫌少" in x for x in _t))
check("D5.1 二维码图片已加载（引用非空）", res.get("photo") is not None)
check("D5.2 二维码显示 150×150",
      res.get("pw") == 150 and res.get("ph") == 150, "%sx%s" % (res.get("pw"), res.get("ph")))
check("D5.3 二维码像素非空白（含深色码点）", res.get("dark", 0) > 50, "dark=%s" % res.get("dark"))
check("D5.4 二维码控件在窗口内可见（已映射）", bool(res.get("qr_visible")))
check("D5.5 二维码水平居中（误差 ≤6px）",
      abs(res.get("qr_center_x", 0) - 230) <= 6, res.get("qr_center_x"))
check("D5.6 二维码提示行存在", any("点击二维码" in x for x in _t),
      str([x for x in _t if "二维码" in x]))
check("D6 窗口内容无裁剪（子控件底边 ≤ 窗口高度）",
      res.get("bottom", 9999) <= res.get("h", 0),
      "bottom=%s h=%s" % (res.get("bottom"), res.get("h")))
check("D7 「确定」按钮存在且点击后关闭窗口",
      res.get("ok_btn") == 1
      and not any(isinstance(c, tk.Toplevel) and c.title() == "关于"
                  for c in app.winfo_children()))

# ---------- E 真机主窗口 ----------
app.update_idletasks()
_mw = {}
_mw["size"] = (app.winfo_width(), app.winfo_height())
_mw["min"] = app.minsize()
_mw["texts"] = texts(app)
grey = 0
for c in walk(app):
    try:
        if c.winfo_class() == "Frame" and str(c.cget("bg")) == "#e9ecef":
            grey += 1
    except Exception:
        continue
_mw["grey"] = grey
_mw["btns"] = [c for c in walk(app) if c.winfo_class() == "Button"]
check("E1 主窗口无赞助浅灰卡片", _mw["grey"] == 0, "grey=%d" % _mw["grey"])
check("E2 主窗口无「赞助支持」文字", not any("赞助支持" in x for x in _mw["texts"]))
check("E3 主窗口无二维码图片控件",
      not any(str(c.cget("image") or "") for c in walk(app) if c.winfo_class() == "Label"))
check("E4 主窗口按钮共 14 个（矩阵 13 键 + 刷新日志）", len(_mw["btns"]) == 14, len(_mw["btns"]))
check("E4.1 主窗口 btns 矩阵 13 键完整", len(getattr(app, "btns", {})) == 13,
      len(getattr(app, "btns", {})))
_names = [str(b.cget("text")) for b in _mw["btns"]]
check("E5 设置/关于按钮仍在位", "设置" in _names and "关于" in _names, _names)
check("E6 minsize 为 860×640", _mw["min"] == (860, 640), _mw["min"])
check("E7 默认窗口 960×700", _mw["size"] == (960, 700), _mw["size"])

# ---------- F 真机设置窗口 ----------
_s = {}


def _settings_probe():
    win = None
    for c in app.winfo_children():
        if isinstance(c, tk.Toplevel) and c.title() == "设置":
            win = c
            break
    if win is None:
        _s["found"] = False
        return
    _s["found"] = True
    win.update_idletasks()
    _s["texts"] = texts(win)
    _s["w"], _s["h"] = win.winfo_width(), win.winfo_height()
    _s["sponsor_widgets"] = [x for x in _s["texts"] if "赞助" in x]
    _s["qr_widgets"] = len([c for c in walk(win)
                            if c.winfo_class() == "Label" and str(c.cget("image") or "")])
    for c in walk(win):
        if c.winfo_class() == "Button" and str(c.cget("text")) == "取消":
            c.invoke()
            break
    else:
        win.destroy()


app.after(600, _settings_probe)
ui_mod.open_settings_dialog(app, cfg)
app.update()

check("F1 设置窗口正常弹出", _s.get("found") is True)
check("F2 设置窗口无任何「赞助」控件", _s.get("sponsor_widgets") == [],
      str(_s.get("sponsor_widgets")))
check("F3 设置窗口无二维码图片控件", _s.get("qr_widgets") == 0, _s.get("qr_widgets"))
_st = _s.get("texts") or []
check("F4 四分区标题齐全",
      all(any(k in x for x in _st)
          for k in ("退出记忆设置", "部署相关下载地址", "浏览器插件连接", "当前信息")),
      [x for x in _st if len(x) < 12][:12])
check("F5 底部保存/取消按钮仍在",
      any(x == "保存设置" for x in _st) and any(x == "取消" in x for x in _st))
check("F6 设置窗口已关闭",
      not any(isinstance(c, tk.Toplevel) and c.title() == "设置" for c in app.winfo_children()))

# ---------- 收尾：主窗口销毁后无残留 ----------
app.destroy()

print("\n==== v1.9.11 赞助区迁移验证：%d PASS / %d FAIL ====" % (PASS, len(FAIL)))
if FAIL:
    print("失败项：")
    for f in FAIL:
        print("  - %s" % f)
sys.exit(0 if not FAIL else 1)
