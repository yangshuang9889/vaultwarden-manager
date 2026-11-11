# -*- coding: utf-8 -*-
"""v1.9.12 验证：设置窗口新增「管理员」分区 —— 获取令牌 + 打开管理面板。

覆盖：
  A 常量与接口：版本号 v1.9.12、打码参数、service 新增 resolve_deploy_dir / mask_token /
    read_admin_token 三个函数
  B 正常读取：标准 .env、CRLF 换行、注释与其它键混排、带引号写法、多行 ADMIN_TOKEN 取首个非空
  C 相对路径按 APP_DIR 解析（禁止依赖进程 CWD）：CWD 下同名目录的令牌不得被读到
  D 异常分支：.env 缺失 / 无 ADMIN_TOKEN 行 / 值为空 / argon2 哈希 / 读取失败（权限）/
    传入 None 或空 cfg —— 全部返回中文提示且不抛异常
  E 打码规范：前 4 位 + 固定 8 星号 + 长度（如 Lsbf********（43 位）），不含完整令牌
  F 只读与日志安全：不修改 .env、不在部署目录产生 manager.log、ui.py 源码不含日志写入
  G 真机设置窗口：管理员分区 / 两按钮 / 五分区齐全、点「获取令牌」后剪贴板内容与 .env 一致、
    界面仅显示打码、提示含「已复制到剪贴板」、「打开管理面板」URL 按 port 与协议拼接、
    Canvas 滚动区域可覆盖新增分区、底部保存/取消仍在位
"""
import inspect
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from unittest import mock

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

import vwm.ui as ui_mod       # noqa: E402
import vwm.service as service  # noqa: E402

# 合成令牌（43 位，形如真实 ADMIN_TOKEN），测试全程只用合成值，绝不读取真实部署令牌
TOKEN = "Lsbf" + "".join(chr(ord("a") + i % 26) for i in range(39))
TOKEN2 = "Zx9Q" + "".join(chr(ord("0") + i % 10) for i in range(39))
MASK = "Lsbf********（43 位）"

WORK = Path(tempfile.mkdtemp(prefix="vw1912tok_"))


def make_env(path_dir, content, name=".env"):
    path_dir = Path(path_dir)
    path_dir.mkdir(parents=True, exist_ok=True)
    p = path_dir / name
    p.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    return p


# ---------- A 常量与接口 ----------
check("A1 版本号已升为 v1.9.12", ui_mod.VERSION == "v1.9.12", ui_mod.VERSION)
check("A2 打码参数 前4位 + 8星号",
      service.TOKEN_MASK_HEAD == 4 and service.TOKEN_MASK_STARS == 8,
      (service.TOKEN_MASK_HEAD, service.TOKEN_MASK_STARS))
check("A3.1 resolve_deploy_dir 可用", callable(getattr(service, "resolve_deploy_dir", None)))
check("A3.2 mask_token 可用", callable(getattr(service, "mask_token", None)))
check("A3.3 read_admin_token 可用", callable(getattr(service, "read_admin_token", None)))
check("A4 ui.py 已复用 service 的读取与打码函数",
      "read_admin_token" in inspect.getsource(ui_mod) and "mask_token" in inspect.getsource(ui_mod))

# ---------- B 正常读取 ----------
d1 = WORK / "ok1"
make_env(d1, "ROCKET_PORT=44444\nADMIN_TOKEN=%s\nDOMAIN=https://localhost:44444\n" % TOKEN)
i1 = service.read_admin_token({"vaultwarden_dir": str(d1)})
check("B1.1 正常读取成功", i1["ok"] is True and i1["code"] == "ok", i1)
check("B1.2 令牌值与原文件一致", i1["token"] == TOKEN, len(i1["token"]))
check("B1.3 打码串正确", i1["masked"] == MASK, i1["masked"])
check("B1.4 提示含「已复制到剪贴板」", "已复制到剪贴板" in i1["message"], i1["message"])
check("B1.5 env_path 指向部署目录 .env",
      Path(i1["env_path"]) == d1 / ".env", i1["env_path"])

d2 = WORK / "ok2"
make_env(d2, b"# comment\r\nROCKET_PORT=44444\r\nADMIN_TOKEN=" + TOKEN.encode() + b"\r\n")
i2 = service.read_admin_token({"vaultwarden_dir": str(d2)})
check("B2 CRLF 换行文件可正常解析", i2["ok"] and i2["token"] == TOKEN, i2.get("code"))

d3 = WORK / "ok3"
make_env(d3, "\n  ADMIN_TOKEN = \"%s\"  \n" % TOKEN)
i3 = service.read_admin_token({"vaultwarden_dir": str(d3)})
check("B3 兼容带引号 / 前后空格写法", i3["ok"] and i3["token"] == TOKEN, i3.get("message"))

d4 = WORK / "ok4"
make_env(d4, "ADMIN_TOKEN=\nADMIN_TOKEN=%s\n" % TOKEN)
i4 = service.read_admin_token({"vaultwarden_dir": str(d4)})
check("B4 首行为空值时取后续非空值", i4["ok"] and i4["token"] == TOKEN, i4.get("code"))

d5 = WORK / "ok5"
make_env(d5, "ADMIN_TOKEN=%s\n" % TOKEN)
before = (d5 / ".env").read_bytes()
service.read_admin_token({"vaultwarden_dir": str(d5)})
check("B5 读取过程不修改 .env（只读语义）", (d5 / ".env").read_bytes() == before)

# ---------- C 相对路径按 APP_DIR 解析（禁止依赖 CWD）----------
base = WORK / "appdir"
cwd_other = WORK / "cwd_other"
make_env(base / "vwrel", "ADMIN_TOKEN=%s\n" % TOKEN)
make_env(cwd_other / "vwrel", "ADMIN_TOKEN=%s\n" % TOKEN2)
old_cwd = os.getcwd()
try:
    os.chdir(str(cwd_other))
    c1 = service.read_admin_token({"vaultwarden_dir": "vwrel"}, app_dir=base)
    c2 = service.resolve_deploy_dir({"vaultwarden_dir": "vwrel"}, app_dir=base)
finally:
    os.chdir(old_cwd)
check("C1 相对路径按 APP_DIR 解析而非 CWD", c1.get("token") == TOKEN, c1.get("token") == TOKEN2)
check("C2 解析结果为 APP_DIR 下的绝对路径",
      Path(c2) == (base / "vwrel"), str(c2))
check("C3 空 vaultwarden_dir 回落 APP_DIR/vaultwarden",
      service.resolve_deploy_dir({}, app_dir=base) == base / "vaultwarden",
      str(service.resolve_deploy_dir({}, app_dir=base)))

# ---------- D 异常分支 ----------
d_missing = WORK / "no_env"
d_missing.mkdir(parents=True, exist_ok=True)
raises = []


def safe_call(cfg, **kw):
    try:
        return service.read_admin_token(cfg, **kw)
    except Exception as exc:  # noqa: BLE001
        raises.append(repr(exc))
        return {}


i_noenv = safe_call({"vaultwarden_dir": str(d_missing)})
check("D1 .env 缺失 → code=no_env", i_noenv.get("code") == "no_env", i_noenv.get("code"))
check("D2 .env 缺失 → 提示「未找到 .env」",
      "未找到 .env" in (i_noenv.get("message") or ""), i_noenv.get("message"))

d_notok = WORK / "no_token"
make_env(d_notok, "ROCKET_PORT=44444\nDOMAIN=https://localhost:44444\n")
i_notok = safe_call({"vaultwarden_dir": str(d_notok)})
check("D3 无 ADMIN_TOKEN 行 → code=no_token", i_notok.get("code") == "no_token", i_notok.get("code"))
check("D4 无 ADMIN_TOKEN 行 → 提示「未设置管理员令牌」",
      "未设置管理员令牌" in (i_notok.get("message") or ""), i_notok.get("message"))

d_empty = WORK / "empty_token"
make_env(d_empty, "ADMIN_TOKEN=\n")
i_empty = safe_call({"vaultwarden_dir": str(d_empty)})
check("D5 ADMIN_TOKEN 值为空 → code=no_token", i_empty.get("code") == "no_token", i_empty.get("code"))

d_argon = WORK / "argon2"
ARGON = "$argon2id$v=19$m=65540,t=3,p=4$c2FsdHNhbHRzYWx0$abcdefghijklmnopqrstuvwxyz12"
make_env(d_argon, "ADMIN_TOKEN=%s\n" % ARGON)
i_argon = safe_call({"vaultwarden_dir": str(d_argon)})
check("D6 argon2 哈希 → code=argon2", i_argon.get("code") == "argon2", i_argon.get("code"))
check("D7 argon2 分支提示含「哈希」与「原始密码」",
      "哈希" in (i_argon.get("message") or "") and "原始密码" in (i_argon.get("message") or ""),
      i_argon.get("message"))
check("D8 argon2 分支不返回可复制令牌", not i_argon.get("token"), i_argon.get("token"))

d_deny = WORK / "deny"
make_env(d_deny, "ADMIN_TOKEN=%s\n" % TOKEN)
with mock.patch.object(Path, "read_text", side_effect=PermissionError(13, "拒绝访问")):
    i_deny = safe_call({"vaultwarden_dir": str(d_deny)})
check("D9 读取失败（权限）→ code=read_error", i_deny.get("code") == "read_error", i_deny.get("code"))
check("D10 读取失败提示含原因与「读取 .env 失败」",
      "读取 .env 失败" in (i_deny.get("message") or "") and "权限" in (i_deny.get("message") or ""),
      i_deny.get("message"))

i_none = safe_call(None, app_dir=WORK)
check("D11 传入 None 不抛异常且给中文提示", i_none.get("code") in ("no_env", "read_error"),
      i_none.get("code"))
i_dir_env = safe_call({"vaultwarden_dir": str(WORK / "ok1" / ".env")})
check("D12 vaultwarden_dir 指向文件也不崩溃", isinstance(i_dir_env, dict) and i_dir_env.get("code"),
      i_dir_env.get("code"))
check("D13 全部异常分支均未向外抛异常", not raises, str(raises))

# ---------- E 打码规范 ----------
check("E1 mask_token 精确格式", service.mask_token(TOKEN) == MASK, service.mask_token(TOKEN))
check("E2 打码串不含完整令牌", TOKEN not in service.mask_token(TOKEN))
check("E3 打码串只保留前 4 位",
      service.mask_token(TOKEN)[:4] == TOKEN[:4]
      and service.mask_token(TOKEN)[4:12] == "*" * 8)
check("E4 长度随令牌真实位数变化（10 位）",
      service.mask_token("abcdefghij").endswith("（10 位）"), service.mask_token("abcdefghij"))
check("E5 mask_token('') 返回空串", service.mask_token("") == "")

# ---------- F 只读与日志安全 ----------
src_reader = inspect.getsource(service.read_admin_token)
check("F1 读取函数无写文件动作",
      all(k not in src_reader for k in ("write_text", "open(", '"w"', "'w'", "os.remove")))
check("F2 读取函数不写操作日志",
      "append_manager_log" not in src_reader and "manager.log" not in src_reader)
src_ui = inspect.getsource(ui_mod)
check("F3 ui.py 不引用操作日志（令牌不上 manager.log）",
      "append_manager_log" not in src_ui and "manager.log" not in src_ui)
check("F4 读取后部署目录未产生 manager.log",
      not (d1 / "manager.log").exists() and not (d5 / "manager.log").exists())
check("F5 界面上屏语句只写打码变量",
      'admin_mask_var.set("令牌：%s" % masked)' in src_ui
      and 'admin_mask_var.set("令牌：%s" % token)' not in src_ui)

# ---------- G 真机设置窗口 ----------
app = tk.Tk()
app.geometry("960x700+120+80")
app.update_idletasks()

ui_mod.get_lan_ip_info = lambda refresh=False: {
    "primary": "198.51.100.10", "candidates": ["198.51.100.10"], "details": [],
    "excluded": [], "udp_probe": "198.51.100.10", "source": "test", "cached": False}

opened_urls = []
ui_mod.webbrowser = mock.MagicMock()
ui_mod.webbrowser.open = lambda url, *a, **k: opened_urls.append(url)

settings_dir = WORK / "settings"
make_env(settings_dir, "ROCKET_PORT=55557\nADMIN_TOKEN=%s\n" % TOKEN)
status_msgs = []
cfg = {"vaultwarden_dir": str(settings_dir), "port": 55557,
       "domain": "https://localhost:55557", "admin_path": "/admin",
       "quit_confirm_skip": False, "quit_default_action": "tray",
       "vw_download_url": "", "vw_webvault_download_url": "", "auto_restore_service": True}


def walk(widget, out=None):
    out = [] if out is None else out
    for child in widget.winfo_children():
        out.append(child)
        walk(child, out)
    return out


def texts(widget):
    """收集控件文案（含 textvariable 当前值）。"""
    vals = []
    for c in walk(widget):
        try:
            tv = str(c.cget("textvariable") or "")
        except Exception:
            tv = ""
        if tv:
            try:
                vals.append(str(widget.getvar(tv)))
            except Exception:
                pass
        try:
            t = c.cget("text")
        except Exception:
            continue
        if t:
            vals.append(str(t))
    return vals


def find_win(title):
    for c in app.winfo_children():
        if isinstance(c, tk.Toplevel) and c.title() == title:
            return c
    return None


def find_btn(win, label):
    for c in walk(win):
        if c.winfo_class() == "Button":
            try:
                if str(c.cget("text")) == label:
                    return c
            except Exception:
                continue
    return None


def force_close(win):
    if win is not None and win.winfo_exists():
        win.destroy()


_s = {}


def _probe():
    win = find_win("设置")
    if win is None:
        _s["found"] = False
        return
    _s["found"] = True
    win.update_idletasks()
    _s["texts"] = texts(win)
    _s["w"], _s["h"] = win.winfo_width(), win.winfo_height()

    canvas = None
    for c in walk(win):
        if c.winfo_class() == "Canvas":
            canvas = c
            break
    if canvas is not None:
        canvas.update_idletasks()
        try:
            region = [int(float(x)) for x in canvas.cget("scrollregion").split()]
            _s["region"] = region
            _s["canvas_h"] = canvas.winfo_height()
        except Exception:
            _s["region"] = None

    btn = find_btn(win, "获取令牌")
    _s["has_token_btn"] = btn is not None
    _s["has_panel_btn"] = find_btn(win, "打开管理面板") is not None
    if btn is not None:
        btn.invoke()
        win.update_idletasks()
        win.update()
        _s["texts_after"] = texts(win)
        try:
            _s["clip"] = win.clipboard_get()
        except Exception as exc:  # noqa: BLE001
            _s["clip"] = "ERR:%r" % exc
        panel = find_btn(win, "打开管理面板")
        if panel is not None:
            panel.invoke()
            win.update_idletasks()
            _s["texts_panel"] = texts(win)
    cancel = find_btn(win, "取消")
    if cancel is not None:
        cancel.invoke()
    else:
        win.destroy()


app.after(700, _probe)
app.after(4000, lambda: force_close(find_win("设置")))
ui_mod.open_settings_dialog(app, cfg, on_status=lambda t, c=None: status_msgs.append(t))
app.update()

check("G1 设置窗口正常弹出", _s.get("found") is True)
_g = _s.get("texts") or []
check("G2 新增「管理员」分区标题", any(x == "管理员" for x in _g),
      [x for x in _g if len(x) <= 8][:10])
check("G3 五个分区标题齐全",
      all(any(k in x for x in _g) for k in
          ("退出记忆设置", "部署相关下载地址", "浏览器插件连接", "管理员", "当前信息")),
      [x for x in _g if len(x) <= 8][:12])
check("G4 「获取令牌」按钮存在", _s.get("has_token_btn") is True)
check("G5 「打开管理面板」按钮存在", _s.get("has_panel_btn") is True)
check("G6 初始状态显示「令牌：尚未获取」",
      any("尚未获取" in x for x in _g), [x for x in _g if "令牌" in x])
check("G7 说明文字含 ADMIN_TOKEN", any("ADMIN_TOKEN" in x for x in _g))

_ga = _s.get("texts_after") or []
check("G8 点击后界面显示打码信息 %s" % MASK,
      any(MASK in x for x in _ga), [x for x in _ga if "令牌" in x][:3])
check("G9 界面任何文案都不含完整令牌",
      all(TOKEN not in x for x in _ga), "leak!")
check("G10 提示文字含「已复制到剪贴板」",
      any("已复制到剪贴板" in x for x in _ga), [x for x in _ga if "复制" in x][:3])
check("G11 剪贴板内容与 .env 中的令牌完全一致", _s.get("clip") == TOKEN,
      "clip=%r" % (_s.get("clip"),))
check("G12 主窗口状态栏收到成功提示（不含令牌）",
      any("已复制管理员令牌到剪贴板" == m for m in status_msgs)
      and all(TOKEN not in m for m in status_msgs), str(status_msgs[:2]))

_gp = _s.get("texts_panel") or []
check("G13 「打开管理面板」URL 按 port 与协议拼接",
      opened_urls[:1] == ["https://localhost:55557/admin"], str(opened_urls))
check("G14 打开面板提示回显地址",
      any("https://localhost:55557/admin" in x for x in _gp),
      [x for x in _gp if "管理面板" in x][:3])

_region = _s.get("region")
_ch = _s.get("canvas_h") or 0
check("G15 滚动区域高度不超出设定窗口（可完整滚动访问全部卡片）",
      bool(_region) and _region[3] > _ch and _s.get("h", 0) == 690,
      "region=%s canvas_h=%s win_h=%s" % (_region, _ch, _s.get("h")))
check("G16 底部保存/取消按钮仍在位",
      any(x == "保存设置" for x in _g) and any(x == "取消" for x in _g))
check("G17 窗口已关闭且无残留",
      not any(isinstance(c, tk.Toplevel) and c.title() == "设置" for c in app.winfo_children()))

# G18：HTTP 协议场景（domain 为 http:// 时打开面板应用 http）
opened_urls.clear()
cfg_http = dict(cfg)
cfg_http["port"] = 8080
cfg_http["domain"] = "http://localhost:8080"
settings_dir2 = WORK / "settings_http"
make_env(settings_dir2, "ADMIN_TOKEN=%s\n" % TOKEN2)
cfg_http["vaultwarden_dir"] = str(settings_dir2)
_s2 = {}


def _probe2():
    win = find_win("设置")
    if win is None:
        _s2["found"] = False
        return
    _s2["found"] = True
    win.update_idletasks()
    panel = find_btn(win, "打开管理面板")
    if panel is not None:
        panel.invoke()
        _s2["texts"] = texts(win)
    cancel = find_btn(win, "取消")
    if cancel is not None:
        cancel.invoke()
    else:
        win.destroy()


app.after(700, _probe2)
app.after(4000, lambda: force_close(find_win("设置")))
ui_mod.open_settings_dialog(app, cfg_http)
app.update()
check("G18 HTTP 协议下管理面板地址为 http://localhost:8080/admin",
      opened_urls[:1] == ["http://localhost:8080/admin"], str(opened_urls))

app.destroy()

print("\n==== v1.9.12 获取令牌验证：%d PASS / %d FAIL ====" % (PASS, len(FAIL)))
if FAIL:
    print("失败项：")
    for f in FAIL:
        print("  - %s" % f)
sys.exit(0 if not FAIL else 1)
