# -*- coding: utf-8 -*-
"""
界面组件模块（v1.9.11）
职责：配色常量、居中几何计算、密码/端口输入弹窗、退出方式确认框、设置/关于窗口
（v1.9.11 起「赞助支持」区落在关于窗口内，含 assets/sponsor_qr.png 收款二维码）。
依赖：tkinter 标准库 + config（路径/默认值/保存）+ network（局域网 IP 探测）。
"""
import os
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox

from .config import CONFIG_PATH, DEFAULT_CONFIG, save_config
from .network import get_lan_ip_info

# v1.7.3：统一按钮配色常量——所有按钮（功能矩阵/原始日志切换/退出/刷新日志/弹窗按钮）
# NORMAL 态背景完全一致（协调蓝 #1971c2，白字；按压态同族深蓝 #1864ab）。
BTN_BG = "#1971c2"
BTN_BG_ACTIVE = "#1864ab"

# v1.7.4：文字元素对比度常量——替换低对比浅灰（#868e96/#495057 在浅底上对比不足），
# 统一使用深色高对比灰阶；按钮禁用态文字显式指定深灰提升可读性。
TEXT_PRIMARY = "#212529"     # 主文字/状态标签/消息栏（最深灰，白底对比 >12:1）
TEXT_SECONDARY = "#343a40"   # 次级文字/状态副标签（深灰，白底对比 >7:1）
TEXT_HINT = "#495057"        # 提示文字（深灰，浅底 #f0f2f5 对比 >5:1）
BTN_DISABLED_FG = "#212529"  # v1.7.5：按钮禁用态文字（系统灰底上最深灰，高对比清晰可读）

# v1.9.9：程序版本号（关于窗口展示；版本升级时同步 DEV.md）
VERSION = "v1.9.11"

# v1.8.5：次级按钮（设置/关于）特殊样式——白底蓝字 + 蓝色描边，明显区别于主操作按钮
# （蓝底白字 #1971c2/#1864ab），整体仍与 #1971c2 蓝色系协调。
BTN_SECONDARY_BG = "#ffffff"          # 白底
BTN_SECONDARY_FG = "#1971c2"          # 蓝字（与主色协调）
BTN_SECONDARY_ACTIVE_BG = "#e7f5ff"   # 按压态浅蓝

# v1.9.11：赞助支持区（自 v1.9.0 主窗口赞助卡片迁入「关于」窗口）——浅灰卡片底 +
# 加粗标题 + 三段说明 + 收款二维码，样式对齐 SysMainToggle 的赞助区实现。
SPONSOR_QR_NAME = "sponsor_qr.png"    # assets 目录下的收款二维码文件名（250×250 PNG）
SPONSOR_QR_MAX_W = 150                # 二维码显示最大边长（等比缩放上限）
SPONSOR_QR_MIN_W = 96                 # 二维码显示最小边长（窄窗口下限，保证扫码可辨）
SPONSOR_TITLE = "赞助支持"
SPONSOR_TEXT = ("一元不嫌少，十元不嫌多。\n"
                "无论金额多少，都是对本软件项目的认可。\n"
                "赞助属于自愿行为，不购买任何功能、不享有售后服务，仅表达您的一份善意。")
SPONSOR_QR_HINT = "手机扫码即可 · 点击二维码可用系统看图器放大"
C_SP_CARD = "#e9ecef"    # 赞助卡片底色（较主背景 #f0f2f5 略深，区分明显）
C_SP_TITLE = TEXT_PRIMARY     # 赞助标题文字
C_SP_TEXT = TEXT_SECONDARY    # 赞助说明文字
C_SP_HINT = TEXT_HINT         # 赞助二维码提示文字

def _centered_geometry(parent, w, h):
    """计算相对主窗口居中的 geometry 字符串（v1.6.8）。

    优先用主窗口 winfo_x/y/width/height 计算居中坐标；
    主窗口几何不可用（已最小化 / 值为 1 / 查询异常）时退化为屏幕居中，避免弹到屏幕外。
    """
    try:
        parent.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        if pw > 1 and ph > 1:
            px, py = parent.winfo_x(), parent.winfo_y()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
        else:
            # 最小化/隐藏时 winfo_width/height 为 1，退化为屏幕居中
            raise tk.TclError("parent geometry unavailable")
    except tk.TclError:
        try:
            sw, sh = parent.winfo_screenwidth(), parent.winfo_screenheight()
        except tk.TclError:
            sw, sh = 1920, 1080
        x = (sw - w) // 2
        y = (sh - h) // 2
    return "%dx%d+%d+%d" % (w, h, max(x, 0), max(y, 0))

def prompt_password(parent, title: str = "请输入密码") -> str | None:
    """弹出密码输入窗口（掩码显示）。返回密码字符串；用户取消返回 None。"""
    win = tk.Toplevel(parent)
    win.title(title)
    win.resizable(False, False)
    win.transient(parent)
    win.grab_set()
    win.configure(bg="#ffffff")
    tk.Label(win, text="密码：", font=("Microsoft YaHei UI", 12),
             bg="#ffffff", fg="#343a40").grid(row=0, column=0, padx=(16, 4), pady=(16, 4), sticky="e")
    entry = tk.Entry(win, show="*", width=28, font=("Microsoft YaHei UI", 12))
    entry.grid(row=0, column=1, padx=(4, 16), pady=(16, 4))
    result = {"pw": None}

    def on_ok(_=None):
        result["pw"] = entry.get()
        win.destroy()

    def on_cancel(_=None):
        win.destroy()

    tk.Button(win, text="确定", command=on_ok, width=8, font=("Microsoft YaHei UI", 11),
              bg=BTN_BG, fg="white", activebackground=BTN_BG_ACTIVE,
              activeforeground="white", disabledforeground=BTN_DISABLED_FG).grid(row=1, column=0, padx=8, pady=(4, 16))
    tk.Button(win, text="取消", command=on_cancel, width=8, font=("Microsoft YaHei UI", 11),
              bg=BTN_BG, fg="white", activebackground=BTN_BG_ACTIVE,
              activeforeground="white", disabledforeground=BTN_DISABLED_FG).grid(row=1, column=1, padx=8, pady=(4, 16))
    entry.focus_set()
    entry.bind("<Return>", on_ok)
    win.bind("<Escape>", on_cancel)
    parent.wait_window(win)
    return result["pw"]

def prompt_port(parent, current_port: int) -> int | None:
    """弹窗输入新端口号（1-65535），返回端口；取消返回 None。"""
    win = tk.Toplevel(parent)
    win.title("修改端口")
    win.resizable(False, False)
    win.transient(parent)
    win.grab_set()
    win.configure(bg="#ffffff")
    tk.Label(win, text="新端口号（1-65535）：", font=("Microsoft YaHei UI", 12),
             bg="#ffffff", fg="#343a40").grid(row=0, column=0, padx=(16, 4), pady=(16, 4), sticky="e")
    entry = tk.Entry(win, width=12, font=("Microsoft YaHei UI", 12))
    entry.insert(0, str(current_port))
    entry.grid(row=0, column=1, padx=(4, 16), pady=(16, 4))
    result = {"port": None}

    def on_ok(_=None):
        raw = entry.get().strip()
        try:
            p = int(raw)
        except ValueError:
            messagebox.showerror("端口无效", "请输入 1-65535 之间的数字", parent=win)
            return
        if not (1 <= p <= 65535):
            messagebox.showerror("端口无效", "端口号必须在 1-65535 之间", parent=win)
            return
        result["port"] = p
        win.destroy()

    def on_cancel(_=None):
        win.destroy()

    tk.Button(win, text="确定", command=on_ok, width=8, font=("Microsoft YaHei UI", 11),
              bg=BTN_BG, fg="white", activebackground=BTN_BG_ACTIVE,
              activeforeground="white", disabledforeground=BTN_DISABLED_FG).grid(row=1, column=0, padx=8, pady=(4, 16))
    tk.Button(win, text="取消", command=on_cancel, width=8, font=("Microsoft YaHei UI", 11),
              bg=BTN_BG, fg="white", activebackground=BTN_BG_ACTIVE,
              activeforeground="white", disabledforeground=BTN_DISABLED_FG).grid(row=1, column=1, padx=8, pady=(4, 16))
    entry.focus_set()
    entry.select_range(0, tk.END)
    entry.bind("<Return>", on_ok)
    win.bind("<Escape>", on_cancel)
    parent.wait_window(win)
    return result["port"]

def ask_quit_or_tray(parent, remember_default: bool = False):
    """全中文确认框：点击关闭(X)或「退出工具」时询问退出方式。

    v1.8.3：新增勾选框「记住我的选择，下次不再询问」——勾选后选择将被
    持久化（由调用方写 config.json），此后退出不再弹框直接执行记忆动作；
    未勾选则仅本次生效，下次仍询问。remember_default 为 True 时勾选框默认
    选中（用于「按住 Shift 强制询问」场景：默认不选，便于一键恢复每次询问）。

    返回 dict：{"action": "quit"/"tray"/None, "remember": bool}
    - action="quit"（退出程序）/ "tray"（最小化到托盘）/ None（关闭对话框，取消操作）；
    - remember=True 表示用户勾选了「记住我的选择」。
    常规桌面尺寸：按钮 10 号粗体、10 字符宽 × 1 行高。
    """
    dlg = tk.Toplevel(parent)
    dlg.title("退出确认")
    dlg.configure(bg="#f0f2f5")
    # v1.6.8：相对主窗口居中弹出（几何不可用时自动退化为屏幕居中）；v1.8.3 增高容纳勾选框
    dlg.geometry(_centered_geometry(parent, 440, 260))
    dlg.resizable(False, False)
    dlg.transient(parent)
    dlg.grab_set()
    result = {"action": None, "remember": False}
    remember_var = tk.BooleanVar(value=bool(remember_default))

    def choose(action):
        result["action"] = action
        result["remember"] = bool(remember_var.get())
        dlg.destroy()

    dlg.protocol("WM_DELETE_WINDOW", lambda: choose(None))
    tk.Label(dlg, text="要退出 Vaultwarden 管家吗？",
             font=("Microsoft YaHei UI", 13, "bold"),
             bg="#f0f2f5", fg="#343a40").pack(pady=(20, 4))
    tk.Label(dlg, text="退出程序将先停止 Vaultwarden 服务再退出；\n最小化到托盘不会停止服务，可从系统托盘图标恢复窗口。",
             font=("Microsoft YaHei UI", 9), bg="#f0f2f5", fg=TEXT_HINT,
             justify="center").pack(pady=(0, 8))
    tk.Checkbutton(dlg, text="记住我的选择，下次不再询问", variable=remember_var,
                   font=("Microsoft YaHei UI", 9), bg="#f0f2f5", fg=TEXT_PRIMARY,
                   activebackground="#f0f2f5", activeforeground=TEXT_PRIMARY,
                   selectcolor="#ffffff", anchor="w", cursor="hand2").pack(padx=40, pady=(0, 8), fill=tk.X)
    btns = tk.Frame(dlg, bg="#f0f2f5")
    btns.pack(pady=(4, 14))
    btn_cfg = dict(font=("Microsoft YaHei UI", 10, "bold"), width=10, height=1,
                   relief=tk.RAISED, bd=1, cursor="hand2",
                   disabledforeground=BTN_DISABLED_FG)
    tk.Button(btns, text="退出程序", bg=BTN_BG, fg="white",
              activebackground=BTN_BG_ACTIVE, activeforeground="white",
              command=lambda: choose("quit"), **btn_cfg).pack(side=tk.LEFT, padx=8)
    tk.Button(btns, text="最小化到托盘", bg=BTN_BG, fg="white",
              activebackground=BTN_BG_ACTIVE, activeforeground="white",
              command=lambda: choose("tray"), **btn_cfg).pack(side=tk.LEFT, padx=8)
    parent.wait_window(dlg)
    return result

def ask_stop_failed_quit(parent, detail: str) -> bool:
    """v1.8.4：退出前停止服务失败时的全中文确认弹窗（仍退出 / 取消退出）。

    仅用于「退出程序」前 stop_service 失败（超时仍有残留）或异常时的决策：
    - 返回 True = 用户选择「仍退出」——调用方继续清理托盘并销毁主窗口；
    - 返回 False = 用户选择「取消退出」——调用方保留主窗口与托盘图标；
    关闭弹窗（X）视为取消退出，绝不静默放行。
    """
    dlg = tk.Toplevel(parent)
    dlg.title("停止服务失败")
    dlg.configure(bg="#f0f2f5")
    dlg.geometry(_centered_geometry(parent, 440, 250))
    dlg.resizable(False, False)
    dlg.transient(parent)
    dlg.grab_set()
    result = {"quit": False}

    def choose(quit_yes: bool):
        result["quit"] = quit_yes
        dlg.destroy()

    dlg.protocol("WM_DELETE_WINDOW", lambda: choose(False))
    tk.Label(dlg, text="退出前停止 Vaultwarden 服务失败",
             font=("Microsoft YaHei UI", 13, "bold"),
             bg="#f0f2f5", fg="#c92a2a").pack(pady=(20, 6))
    tk.Label(dlg, text=detail, font=("Microsoft YaHei UI", 9),
             bg="#f0f2f5", fg=TEXT_HINT, justify="center",
             wraplength=380).pack(padx=30, pady=(0, 6))
    tk.Label(dlg, text="仍要退出程序吗？（选择「取消退出」将保留程序与当前服务状态）",
             font=("Microsoft YaHei UI", 9), bg="#f0f2f5", fg=TEXT_PRIMARY,
             justify="center", wraplength=380).pack(padx=30, pady=(0, 10))
    btns = tk.Frame(dlg, bg="#f0f2f5")
    btns.pack(pady=(2, 16))
    btn_cfg = dict(font=("Microsoft YaHei UI", 10, "bold"), width=10, height=1,
                   relief=tk.RAISED, bd=1, cursor="hand2",
                   disabledforeground=BTN_DISABLED_FG)
    tk.Button(btns, text="仍退出", bg=BTN_BG, fg="white",
              activebackground=BTN_BG_ACTIVE, activeforeground="white",
              command=lambda: choose(True), **btn_cfg).pack(side=tk.LEFT, padx=8)
    tk.Button(btns, text="取消退出", bg=BTN_BG, fg="white",
              activebackground=BTN_BG_ACTIVE, activeforeground="white",
              command=lambda: choose(False), **btn_cfg).pack(side=tk.LEFT, padx=8)
    parent.wait_window(dlg)
    return result["quit"]


def open_settings_dialog(parent, cfg: dict, on_status=None):
    """v1.8.5：设置窗口；v1.9.9 新增「浏览器插件连接」分区 + 卡片区滚动布局。

    内容（全中文、居中、与主界面风格一致：浅底 #f0f2f5 + 白色卡片分区 + 蓝主色）：
    ① 退出记忆设置：quit_confirm_skip 开关（跳过退出确认）、quit_default_action 选择
       （最小化到托盘 / 退出程序），一键恢复「每次退出都询问」（清除记忆并保存）；
    ② 部署相关下载地址：vw_download_url、vw_webvault_download_url 可查看/编辑；
    ③ 服务自动恢复（v1.9.8）：auto_restore_service 开关——退出时服务在运行则
       下次启动软件自动启动服务（关闭时清除 last_exit_service_running 标志）；
    ④ 浏览器插件连接（v1.9.9）：按 config.json 的 port 与 domain 动态拼接本机地址
       https://localhost:<port> 与局域网地址 https://<本机IP>:<port>（端口不写死），
       提供「复制地址」（写系统剪贴板 + 状态栏提示）、「打开地址信任证书」（默认浏览器
       打开地址，需先接受自签证书）、「获取浏览器扩展」（Edge/Chrome 商店地址取自配置
       键 ext_edge_url / ext_chrome_url，缺失时用默认值兜底）三个操作按钮与使用说明；
    ⑤ 当前信息（只读）：端口、部署目录。

    布局：v1.9.9 起卡片区放入 Canvas + 垂直滚动条（分区增多后内容超出固定高度，
    小屏/高 DPI 下仍可访问全部分区）；底部「保存设置」「取消」固定在窗口底部不滚动。
    on_status：可选回调 (text, color)，用于把「复制地址」等操作结果同步到主窗口状态栏；
    不传时仅窗口内提示行显示，保持与旧调用方式兼容。

    保存：把界面值写回传入的 cfg 并调用 save_config 持久化到 config.json（不破坏
    其他字段），关闭窗口并提示；取消/关闭(X)：不写盘。返回更新后的 cfg，取消返回 None。
    """
    win = tk.Toplevel(parent)
    win.title("设置")
    win.configure(bg="#f0f2f5")
    win.geometry(_centered_geometry(parent, 560, 690))
    win.resizable(False, False)
    win.transient(parent)
    win.grab_set()
    result = {"cfg": None}

    # ---- v1.9.9：卡片区滚动容器（卡片本身样式/间距不变，仅更换承载容器）----
    body = tk.Frame(win, bg="#f0f2f5")
    body.pack(fill=tk.BOTH, expand=True)
    canvas = tk.Canvas(body, bg="#f0f2f5", highlightthickness=0, bd=0)
    vsb = tk.Scrollbar(body, orient=tk.VERTICAL, command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    inner = tk.Frame(canvas, bg="#f0f2f5")
    inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _sync_scrollregion(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _sync_inner_width(event):
        try:
            canvas.itemconfigure(inner_id, width=event.width)
        except tk.TclError:
            pass

    def _on_mousewheel(event):
        try:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except tk.TclError:
            pass

    inner.bind("<Configure>", _sync_scrollregion)
    canvas.bind("<Configure>", _sync_inner_width)
    win.bind("<MouseWheel>", _on_mousewheel)

    skip_var = tk.BooleanVar(value=bool(cfg.get("quit_confirm_skip")))
    action_var = tk.StringVar(value=cfg.get("quit_default_action", "tray"))
    url_var = tk.StringVar(value=cfg.get("vw_download_url", ""))
    webvault_var = tk.StringVar(value=cfg.get("vw_webvault_download_url", ""))
    # v1.9.8：退出后下次启动是否自动恢复服务（默认开启）
    restore_var = tk.BooleanVar(value=bool(cfg.get("auto_restore_service", True)))

    # ---- 卡片一：退出记忆设置 ----
    card = tk.Frame(inner, bg="#ffffff")
    card.pack(fill=tk.X, padx=16, pady=(14, 4))
    tk.Label(card, text="退出记忆设置", font=("Microsoft YaHei UI", 11, "bold"),
             bg="#ffffff", fg=TEXT_PRIMARY).pack(anchor="w", padx=14, pady=(12, 4))
    tk.Checkbutton(card, text="跳过退出确认（记住退出方式后退出不再询问）",
                   variable=skip_var, font=("Microsoft YaHei UI", 10), bg="#ffffff",
                   fg=TEXT_PRIMARY, activebackground="#ffffff", activeforeground=TEXT_PRIMARY,
                   selectcolor="#ffffff", anchor="w", cursor="hand2").pack(fill=tk.X, padx=18, pady=(0, 2))
    tk.Label(card, text="默认退出动作（未勾选跳过确认时使用）：",
             font=("Microsoft YaHei UI", 9), bg="#ffffff", fg=TEXT_HINT).pack(anchor="w", padx=18, pady=(2, 0))
    radio = tk.Frame(card, bg="#ffffff")
    radio.pack(fill=tk.X, padx=18)
    tk.Radiobutton(radio, text="最小化到托盘（不停止服务）", variable=action_var, value="tray",
                   font=("Microsoft YaHei UI", 9), bg="#ffffff", fg=TEXT_SECONDARY,
                   activebackground="#ffffff", activeforeground=TEXT_SECONDARY,
                   selectcolor="#ffffff", cursor="hand2").pack(side=tk.LEFT)
    tk.Radiobutton(radio, text="退出程序（先停止服务再退出）", variable=action_var, value="quit",
                   font=("Microsoft YaHei UI", 9), bg="#ffffff", fg=TEXT_SECONDARY,
                   activebackground="#ffffff", activeforeground=TEXT_SECONDARY,
                   selectcolor="#ffffff", cursor="hand2").pack(side=tk.LEFT, padx=(18, 0))

    def restore_ask():
        # 一键恢复：清除退出记忆（quit_confirm_skip=False）并立即写盘
        cfg["quit_confirm_skip"] = False
        ok = save_config(cfg)
        skip_var.set(False)
        tip = "已恢复「每次退出都询问」并保存"
        if not ok:
            tip = "config.json 写入失败，恢复未持久化"
        messagebox.showinfo("退出记忆", tip, parent=win)

    tk.Checkbutton(card, text="退出后下次启动自动恢复服务（退出时服务在运行则下次启动自动启动）",
                   variable=restore_var, font=("Microsoft YaHei UI", 10), bg="#ffffff",
                   fg=TEXT_PRIMARY, activebackground="#ffffff", activeforeground=TEXT_PRIMARY,
                   selectcolor="#ffffff", anchor="w", cursor="hand2").pack(fill=tk.X, padx=18, pady=(8, 0))
    tk.Label(card, text="关闭后不再自动启动服务，并清除已记录的服务运行状态。",
             font=("Microsoft YaHei UI", 9), bg="#ffffff", fg=TEXT_HINT).pack(anchor="w", padx=34, pady=(0, 4))

    tk.Button(card, text="一键恢复「每次退出都询问」", command=restore_ask,
              font=("Microsoft YaHei UI", 9, "bold"), bg="#ffffff", fg=BTN_SECONDARY_FG,
              activebackground=BTN_SECONDARY_ACTIVE_BG, activeforeground=BTN_SECONDARY_FG,
              relief=tk.SOLID, bd=1, cursor="hand2", highlightbackground=BTN_SECONDARY_FG,
              highlightthickness=1).pack(anchor="w", padx=18, pady=(6, 12))

    # ---- 卡片二：部署相关下载地址 ----
    card2 = tk.Frame(inner, bg="#ffffff")
    card2.pack(fill=tk.X, padx=16, pady=4)
    tk.Label(card2, text="部署相关下载地址", font=("Microsoft YaHei UI", 11, "bold"),
             bg="#ffffff", fg=TEXT_PRIMARY).pack(anchor="w", padx=14, pady=(12, 4))

    def addr_row(row_parent, label, var):
        row = tk.Frame(row_parent, bg="#ffffff")
        row.pack(fill=tk.X, padx=18, pady=(2, 6))
        tk.Label(row, text=label, font=("Microsoft YaHei UI", 9), bg="#ffffff",
                 fg=TEXT_SECONDARY, width=15, anchor="w").pack(side=tk.LEFT)
        tk.Entry(row, textvariable=var, font=("Microsoft YaHei UI", 9),
                 bg="#ffffff", fg=TEXT_PRIMARY, relief=tk.SOLID, bd=1).pack(side=tk.LEFT, fill=tk.X, expand=True)

    addr_row(card2, "核心程序下载地址", url_var)
    addr_row(card2, "网页版下载地址", webvault_var)

    # ---- 卡片三：浏览器插件连接（v1.9.9）----
    # 地址按 config.json 动态拼接：端口取自 cfg["port"]（缺失时用 DEFAULT_CONFIG 兜底，
    # 不写死任何端口字面量）；domain 仅用于判断 https/http 协议。
    card_ext = tk.Frame(inner, bg="#ffffff")
    card_ext.pack(fill=tk.X, padx=16, pady=4)
    tk.Label(card_ext, text="浏览器插件连接", font=("Microsoft YaHei UI", 11, "bold"),
             bg="#ffffff", fg=TEXT_PRIMARY).pack(anchor="w", padx=14, pady=(12, 4))

    plugin_port = cfg.get("port") or DEFAULT_CONFIG.get("port") or ""
    domain_raw = str(cfg.get("domain") or "").strip()
    plugin_scheme = "http" if domain_raw.lower().startswith("http://") else "https"
    local_url = "%s://localhost:%s" % (plugin_scheme, plugin_port)
    lan_var = tk.StringVar(value="")
    local_var = tk.StringVar(value=local_url)
    sel = {"url": local_url}          # 当前待复制的地址（默认本机，检测到局域网 IP 后切换）
    plugin_tip_var = tk.StringVar(value="")

    tk.Label(card_ext,
             text="安装 Bitwarden 浏览器扩展后，在扩展登录页点「设置」把「服务器地址」填成下面的地址，再用账号登录即可同步。",
             font=("Microsoft YaHei UI", 9), bg="#ffffff", fg=TEXT_HINT,
             justify="left", anchor="w", wraplength=460).pack(fill=tk.X, padx=18, pady=(0, 6))

    def plugin_addr_row(label, var, hint=""):
        row = tk.Frame(card_ext, bg="#ffffff")
        row.pack(fill=tk.X, padx=18, pady=(2, 4))
        tk.Label(row, text=label, font=("Microsoft YaHei UI", 9), bg="#ffffff",
                 fg=TEXT_SECONDARY, width=15, anchor="w").pack(side=tk.LEFT)
        ent = tk.Entry(row, textvariable=var, font=("Microsoft YaHei UI", 9),
                       bg="#f8f9fa", fg=TEXT_PRIMARY, relief=tk.SOLID, bd=1,
                       state="readonly", readonlybackground="#f8f9fa")
        ent.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def _pick(_event=None, v=var):
            url = v.get().strip()
            if url and "（" not in url:      # 跳过「未检测到…」提示文本
                sel["url"] = url

        ent.bind("<Button-1>", _pick)        # 点击哪个地址就复制哪个
        ent.bind("<FocusIn>", _pick)
        return ent

    plugin_addr_row("本机地址", local_var)
    plugin_addr_row("局域网地址", lan_var)

    def _apply_lan_info(info):
        """把探测结果回填到界面（v1.9.10：展示首选地址 + 候选数量）。"""
        try:
            if not win.winfo_exists():
                return
        except tk.TclError:
            return
        ips = list((info or {}).get("candidates") or [])
        if ips:
            lan_url = "%s://%s:%s" % (plugin_scheme, ips[0], plugin_port)
            lan_var.set(lan_url)
            sel["url"] = lan_url            # 默认复制局域网地址（手机/其它电脑也能用）
            if len(ips) > 1:
                plugin_tip_var.set(
                    "已检测到局域网 IP：%s（另有 %d 个可用地址，已选用首选；"
                    "其它设备需与电脑在同一网络）" % (ips[0], len(ips) - 1))
            else:
                plugin_tip_var.set(
                    "已检测到局域网 IP：%s（其它设备需与电脑在同一网络）" % ips[0])
        else:
            lan_var.set("未检测到局域网 IP（请检查网络连接）")
            plugin_tip_var.set("仅能用本机地址连接；如需其它设备访问，请先连通网络后重开本窗口")

    def _load_lan_ip():
        """后台线程探测局域网 IP，完成后回主线程回填（v1.9.10 起探测不占主线程）。"""
        def _work():
            try:
                info = get_lan_ip_info()
            except Exception:
                info = {}
            try:
                win.after(0, lambda: _apply_lan_info(info))
            except Exception:
                pass            # 窗口已销毁时静默放弃回填

        threading.Thread(target=_work, daemon=True).start()

    ext_btn_cfg = dict(font=("Microsoft YaHei UI", 9, "bold"), bg="#ffffff", fg=BTN_SECONDARY_FG,
                       activebackground=BTN_SECONDARY_ACTIVE_BG, activeforeground=BTN_SECONDARY_FG,
                       relief=tk.SOLID, bd=1, cursor="hand2", highlightbackground=BTN_SECONDARY_FG,
                       highlightthickness=1)

    def copy_plugin_addr():
        url = sel["url"] or local_url
        ok = True
        try:
            win.clipboard_clear()
            win.clipboard_append(url)
            win.update_idletasks()          # 立即生效，窗口关闭后剪贴板内容仍保留
        except tk.TclError:
            ok = False
        tip = "已复制地址：%s" % url if ok else "复制失败：系统剪贴板不可用"
        plugin_tip_var.set(tip)
        if callable(on_status):
            on_status(tip, "#2b8a3e" if ok else "#c92a2a")

    def open_trust_url():
        url = sel["url"] or local_url
        msg = "已用默认浏览器打开 %s —— 若提示「您的连接不是私密连接」，请点「高级」→「继续前往」信任自签证书，之后扩展才能连接。" % url
        try:
            webbrowser.open(url)
        except Exception:
            msg = "打开浏览器失败，请手动复制地址 %s 到浏览器访问。" % url
        plugin_tip_var.set(msg)
        if callable(on_status):
            on_status("已在默认浏览器打开插件连接地址（需先信任自签证书）", TEXT_HINT)

    def open_ext_page(key, name):
        url = str(cfg.get(key) or DEFAULT_CONFIG.get(key) or "").strip()
        if not url:
            plugin_tip_var.set("未配置%s扩展地址（config.json 的 %s），请手动在商店搜索 Bitwarden。" % (name, key))
            return
        try:
            webbrowser.open(url)
            plugin_tip_var.set("已用默认浏览器打开%s扩展页面：%s" % (name, url))
        except Exception:
            plugin_tip_var.set("打开浏览器失败，请手动访问：%s" % url)

    act_row1 = tk.Frame(card_ext, bg="#ffffff")
    act_row1.pack(fill=tk.X, padx=18, pady=(4, 2))
    tk.Button(act_row1, text="复制地址", command=copy_plugin_addr,
              **ext_btn_cfg).pack(side=tk.LEFT)
    tk.Button(act_row1, text="打开地址信任证书", command=open_trust_url,
              **ext_btn_cfg).pack(side=tk.LEFT, padx=(8, 0))

    act_row2 = tk.Frame(card_ext, bg="#ffffff")
    act_row2.pack(fill=tk.X, padx=18, pady=(2, 4))
    tk.Button(act_row2, text="获取扩展（Edge）",
              command=lambda: open_ext_page("ext_edge_url", "Edge"),
              **ext_btn_cfg).pack(side=tk.LEFT)
    tk.Button(act_row2, text="获取扩展（Chrome）",
              command=lambda: open_ext_page("ext_chrome_url", "Chrome"),
              **ext_btn_cfg).pack(side=tk.LEFT, padx=(8, 0))

    tk.Label(card_ext, textvariable=plugin_tip_var, font=("Microsoft YaHei UI", 8),
             bg="#ffffff", fg=TEXT_HINT, justify="left", anchor="w",
             wraplength=460).pack(fill=tk.X, padx=18, pady=(0, 2))
    tk.Label(card_ext,
             text="说明：地址需与服务端口一致；若扩展里曾填错服务器地址，请先到扩展设置页清除（或退出登录）后重新填写，否则会一直提示无法连接。服务未启动时地址无法访问，请先在主界面启动服务。",
             font=("Microsoft YaHei UI", 8), bg="#ffffff", fg=TEXT_HINT,
             justify="left", anchor="w", wraplength=460).pack(fill=tk.X, padx=18, pady=(0, 12))
    win.after(60, _load_lan_ip)             # 异步探测，避免打开窗口时卡顿

    # ---- 卡片四：当前信息（只读） ----
    card3 = tk.Frame(inner, bg="#ffffff")
    card3.pack(fill=tk.X, padx=16, pady=4)
    tk.Label(card3, text="当前信息（只读）", font=("Microsoft YaHei UI", 11, "bold"),
             bg="#ffffff", fg=TEXT_PRIMARY).pack(anchor="w", padx=14, pady=(12, 4))
    tk.Label(card3, text="端口：%s" % cfg.get("port", ""),
             font=("Microsoft YaHei UI", 9), bg="#ffffff", fg=TEXT_SECONDARY).pack(anchor="w", padx=18, pady=(0, 2))
    tk.Label(card3, text="部署目录：%s" % cfg.get("vaultwarden_dir", ""),
             font=("Microsoft YaHei UI", 9), bg="#ffffff", fg=TEXT_SECONDARY).pack(anchor="w", padx=18, pady=(0, 12))

    # ---- 底部按钮 ----
    btns = tk.Frame(win, bg="#f0f2f5")
    btns.pack(pady=(10, 16))
    btn_cfg = dict(font=("Microsoft YaHei UI", 10, "bold"), width=10, height=1,
                   relief=tk.RAISED, bd=1, cursor="hand2", disabledforeground=BTN_DISABLED_FG)

    def save():
        cfg["quit_confirm_skip"] = bool(skip_var.get())
        cfg["quit_default_action"] = action_var.get()
        cfg["vw_download_url"] = url_var.get().strip()
        cfg["vw_webvault_download_url"] = webvault_var.get().strip()
        # v1.9.8：开关关闭时清除「退出前服务在运行」标志，避免下次启动仍尝试自动恢复
        cfg["auto_restore_service"] = bool(restore_var.get())
        if not cfg["auto_restore_service"]:
            cfg["last_exit_service_running"] = False
        ok = save_config(cfg)
        if ok:
            result["cfg"] = cfg
            messagebox.showinfo("设置", "设置已保存（config.json 已更新）", parent=win)
            win.destroy()
        else:
            messagebox.showerror("设置", "config.json 写入失败，设置未保存", parent=win)

    def cancel():
        result["cfg"] = None
        win.destroy()

    tk.Button(btns, text="保存设置", command=save, bg=BTN_BG, fg="white",
              activebackground=BTN_BG_ACTIVE, activeforeground="white", **btn_cfg).pack(side=tk.LEFT, padx=8)
    tk.Button(btns, text="取消", command=cancel, bg=BTN_BG, fg="white",
              activebackground=BTN_BG_ACTIVE, activeforeground="white", **btn_cfg).pack(side=tk.LEFT, padx=8)
    win.protocol("WM_DELETE_WINDOW", cancel)
    parent.wait_window(win)
    return result["cfg"]


def _sponsor_qr_file() -> str:
    """v1.9.11：返回赞助收款二维码图片可访问的绝对路径，找不到返回空串。

    查找顺序（覆盖源码运行 / PyInstaller 单文件 exe 两种形态）：
    1. sys._MEIPASS/assets/sponsor_qr.png —— 单文件 exe 运行时 PyInstaller 的解包目录；
    2. exe 同级 assets/sponsor_qr.png —— exe 旁摆放的外部 assets 目录（便于替换图片）；
    3. 项目根目录 assets/sponsor_qr.png —— 源码直接运行时的项目资源目录。
    """
    import sys as _sys

    rel = os.path.join("assets", SPONSOR_QR_NAME)
    cands = []
    meipass = getattr(_sys, "_MEIPASS", None)
    if meipass:
        cands.append(os.path.join(meipass, rel))
    if getattr(_sys, "frozen", False):
        cands.append(os.path.join(os.path.dirname(os.path.abspath(_sys.executable)), rel))
    # 本文件位于 <项目根>/vwm/ui.py，上跳一级即项目根
    cands.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), rel))
    for c in cands:
        try:
            if os.path.isfile(c):
                return c
        except Exception:
            continue
    return ""


def _load_sponsor_qr(max_w: int = SPONSOR_QR_MAX_W):
    """v1.9.11：加载赞助二维码并等比缩放到最长边 ≤ max_w，返回 (photo, path, error)。

    双通道：① 首选 Pillow `Image.LANCZOS` 高质量等比缩放（保证二维码边缘清晰可扫）；
    ② Pillow / ImageTk 不可用时退回 tk 原生 `PhotoImage` + `subsample()` 整数降采样。
    图片缺失 / 损坏 / 两通道均失败时返回 (None, path, 原因)，由调用方显示占位提示，绝不抛异常。
    """
    path = _sponsor_qr_file()
    if not path:
        return None, "", "未找到 assets/sponsor_qr.png"
    try:  # 首选 Pillow：高质量等比缩放
        from PIL import Image, ImageTk
        with Image.open(path) as im:
            im.load()
            src = im.convert("RGBA")
        w, h = src.size
        scale = min(1.0, max_w / float(max(w, h) or 1))
        if scale < 1.0:
            src = src.resize((max(1, int(w * scale)), max(1, int(h * scale))),
                             Image.LANCZOS)
        return ImageTk.PhotoImage(src), path, ""
    except Exception:
        pass
    try:  # 兜底：tk 原生 PNG 解码 + 整数降采样
        raw = tk.PhotoImage(file=path)
        factor = max(1, -(-max(raw.width(), raw.height()) // max_w))
        return (raw.subsample(factor, factor) if factor > 1 else raw), path, ""
    except Exception as exc:
        return None, path, str(exc)


def _sponsor_qr_max_w(container) -> int:
    """v1.9.11：按容器实际宽度自适应计算二维码最大显示边长。

    取容器宽度减去左右留白 60px，并夹在 [SPONSOR_QR_MIN_W, SPONSOR_QR_MAX_W] 区间内；
    窗口未完成布局（宽度 ≤1）时退化为 SPONSOR_QR_MAX_W，保证不出现 1px 或超大图。
    """
    try:
        container.update_idletasks()
        avail = int(container.winfo_width()) - 60
    except Exception:
        avail = SPONSOR_QR_MAX_W
    if avail <= 1:
        avail = SPONSOR_QR_MAX_W
    return max(SPONSOR_QR_MIN_W, min(SPONSOR_QR_MAX_W, avail))


def show_about_dialog(parent, cfg: dict):
    """v1.9.11：关于窗口——软件名称、版本、作者/版权、制作人/制作工具、简要说明，
    以及「赞助支持」区（赞助文案 + assets/sponsor_qr.png 收款二维码）。

    居中、全中文、白卡片风格；赞助区沿用原主窗口赞助卡片的浅灰底居中样式，
    二维码按卡片宽度自适应等比缩放，图片缺失/损坏时显示占位提示不崩溃。
    点击「确定」或关闭按钮退出。
    """
    win = tk.Toplevel(parent)
    win.title("关于")
    win.configure(bg="#f0f2f5")
    win.geometry(_centered_geometry(parent, 460, 560))
    win.resizable(False, False)
    win.transient(parent)
    win.grab_set()
    card = tk.Frame(win, bg="#ffffff")
    card.pack(fill=tk.X, padx=16, pady=(16, 4))
    tk.Label(card, text="VaultwardenManager", font=("Microsoft YaHei UI", 15, "bold"),
             bg="#ffffff", fg="#1971c2").pack(pady=(18, 2))
    tk.Label(card, text="版本：%s" % VERSION, font=("Microsoft YaHei UI", 10),
             bg="#ffffff", fg=TEXT_SECONDARY).pack(pady=(0, 2))
    tk.Label(card, text="作者 / 版权：杨爽工作室", font=("Microsoft YaHei UI", 10),
             bg="#ffffff", fg=TEXT_SECONDARY).pack(pady=(0, 2))
    tk.Label(card, text="制作人：杨爽", font=("Microsoft YaHei UI", 10),
             bg="#ffffff", fg=TEXT_SECONDARY).pack(pady=(0, 2))
    tk.Label(card, text="制作工具：Marvis", font=("Microsoft YaHei UI", 10),
             bg="#ffffff", fg=TEXT_SECONDARY).pack(pady=(0, 2))
    tk.Label(card, text="本工具用于管理本机 Vaultwarden 密码管理器服务：\n支持启动/停止服务、日志查看、加密备份与导入、一键部署、证书与端口管理等。",
             font=("Microsoft YaHei UI", 9), bg="#ffffff", fg=TEXT_HINT, justify="center",
             wraplength=400).pack(pady=(8, 18))

    # v1.9.11：赞助支持区（由主窗口迁入关于窗口，样式沿用原赞助卡片）
    sp_card = tk.Frame(win, bg=C_SP_CARD, padx=6, pady=6)
    sp_card.pack(fill=tk.X, padx=16, pady=(0, 4))
    tk.Label(sp_card, text=SPONSOR_TITLE, font=("Microsoft YaHei UI", 10, "bold"),
             bg=C_SP_CARD, fg=C_SP_TITLE).pack(fill=tk.X, pady=(2, 0))
    tk.Label(sp_card, text=SPONSOR_TEXT, font=("Microsoft YaHei UI", 8),
             bg=C_SP_CARD, fg=C_SP_TEXT, justify="center", anchor="center",
             wraplength=400).pack(fill=tk.X, pady=(2, 0))
    qr_photo, qr_path, qr_err = _load_sponsor_qr(_sponsor_qr_max_w(sp_card))
    qr_wrap = tk.Frame(sp_card, bg=C_SP_CARD)
    qr_wrap.pack(pady=(6, 0))
    if qr_photo is not None:
        qr_label = tk.Label(qr_wrap, image=qr_photo, bg=C_SP_CARD, bd=0,
                            highlightthickness=0, cursor="hand2")
        qr_label.pack()
        # 引用挂到窗口对象上，避免 PhotoImage 被垃圾回收后图片变空白
        win._sponsor_qr_photo = qr_photo  # noqa: SLF001
        win._sponsor_qr_path = qr_path  # noqa: SLF001

        def _open_qr(_event=None, _path=qr_path):
            try:
                os.startfile(_path)  # noqa: S606 - 本地图片，交系统看图器
            except Exception:
                pass

        qr_label.bind("<Button-1>", _open_qr)
        tk.Label(sp_card, text=SPONSOR_QR_HINT, font=("Microsoft YaHei UI", 8),
                 bg=C_SP_CARD, fg=C_SP_HINT, justify="center").pack(fill=tk.X, pady=(4, 2))
    else:
        # 占位提示：图片缺失/损坏时不崩溃、不塌陷，仅提示文字
        tk.Label(qr_wrap, text="二维码暂不可用\n（请检查 assets/sponsor_qr.png）",
                 font=("Microsoft YaHei UI", 9), bg=C_SP_CARD, fg=C_SP_HINT,
                 justify="center", width=18, height=3).pack()
        tk.Label(sp_card, text=SPONSOR_QR_HINT, font=("Microsoft YaHei UI", 8),
                 bg=C_SP_CARD, fg=C_SP_HINT, justify="center").pack(fill=tk.X, pady=(4, 2))

    btn = tk.Frame(win, bg="#f0f2f5")
    btn.pack(pady=(8, 16))
    tk.Button(btn, text="确定", command=win.destroy, font=("Microsoft YaHei UI", 10, "bold"),
              width=10, height=1, bg=BTN_BG, fg="white", activebackground=BTN_BG_ACTIVE,
              activeforeground="white", relief=tk.RAISED, bd=1, cursor="hand2",
              disabledforeground=BTN_DISABLED_FG).pack()
    # 内容较多时按实际需求高度回收/扩展窗口，保证赞助区与按钮完整可见不被裁剪
    win.update_idletasks()
    need_h = max(560, int(win.winfo_reqheight()))
    if need_h != 560:
        win.geometry(_centered_geometry(parent, 460, need_h))
    win.protocol("WM_DELETE_WINDOW", win.destroy)
    parent.wait_window(win)

