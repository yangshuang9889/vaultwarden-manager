# -*- coding: utf-8 -*-
"""
GUI 主应用模块（v1.8.0）
职责：VaultwardenManagerApp（tkinter 主窗口：按钮矩阵、托盘、状态轮询、
      日志展示、部署进度、后台任务线程）与 main 入口。
依赖：全部业务模块 + ui + 包级 CRYPTO_OK。
"""
import os
import sys
import threading
import time
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from . import CRYPTO_OK
from .backup import decrypt_and_restore, encrypt_backup, resolve_enc_target
from .config import (CONFIG_PATH, _migration_notice, _write_default_config,
                     apply_quit_memory, clear_quit_memory, load_config, save_config,
                     update_port)
from .deploy import deploy_service
from .logs import append_manager_log, read_log_tail
from .network import is_port_open, resolve_web_url
from .service import (ensure_port_available, find_vw_processes, get_deploy_state,
                      get_service_status, is_process_running, start_service,
                      stop_service)
from .ui import (BTN_BG, BTN_BG_ACTIVE, BTN_DISABLED_FG, BTN_SECONDARY_ACTIVE_BG,
                 BTN_SECONDARY_BG, BTN_SECONDARY_FG, TEXT_HINT, TEXT_PRIMARY,
                 TEXT_SECONDARY, VERSION, ask_quit_or_tray, ask_stop_failed_quit,
                 open_settings_dialog, prompt_password, prompt_port, show_about_dialog)

# v1.9.11：赞助支持卡片已从主窗口移除，「赞助支持 + 收款二维码」统一落到「关于」窗口
# （实现见 vwm/ui.py 的 show_about_dialog 与 SPONSOR_* 常量），主窗口左侧按钮列下方不再占位。


def _asset_path(name: str) -> str:
    """v1.9.7：返回 assets 目录下图标资源可访问的绝对路径，找不到返回空串。

    查找顺序（覆盖源码运行 / PyInstaller 单文件 exe 两种形态）：
    1. sys._MEIPASS/assets/name —— 单文件 exe 运行时 PyInstaller 的解包目录；
    2. exe 同级 assets/name —— exe 旁若摆放了外部 assets 目录（便于用户替换图标）；
    3. 项目根目录 assets/name —— 源码直接运行时的项目资源目录。
    """
    rel = os.path.join("assets", name)
    cands = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        cands.append(os.path.join(meipass, rel))
    if getattr(sys, "frozen", False):
        cands.append(os.path.join(os.path.dirname(os.path.abspath(sys.executable)), rel))
    # 源码运行：本文件位于 <项目根>/vwm/app.py，上跳一级即项目根
    cands.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), rel))
    for c in cands:
        try:
            if os.path.isfile(c):
                return c
        except Exception:
            continue
    return ""


class VaultwardenManagerApp(tk.Tk):
    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        self.title("Vaultwarden 管理工具")
        self.geometry("960x700")
        # v1.9.11：赞助卡片移出主窗口（改由「关于」窗口承载），左列内容变矮，
        # 最小高度自 690 回收至 640；默认尺寸 960×700 不变。
        self.minsize(860, 640)
        self.configure(bg="#f0f2f5")
        # v1.9.7：统一盾牌安全风格图标——窗口/Tk 各 Toplevel（含弹窗）默认图标。
        self._win_icon_photo = None
        self._apply_window_icon()
        self._busy = False
        # v1.9.4：「一键部署」锁定用的部署状态（deployed/partial/none），一律来自磁盘真实文件判定，
        # 不依赖会话内标志，程序重启后依然生效；须在 refresh_status() 前初始化。
        self._deploy_state = "none"
        self._deploy_state_tip = ""
        # v1.9.5：状态探测异步化后，服务状态先给保守初值 stopped，真实状态由后台探测回填
        self._service_status = "stopped"
        self._status_probing = False
        self._build_ui()
        self._raw_log = False  # 原始日志开关：False=过滤模式（与 UI 默认一致），须在 refresh_log() 前初始化
        if _migration_notice:
            self.status_sub.config(text=_migration_notice, fg="#c92a2a")
        # v1.9.5：启动时先用磁盘判定部署状态并初始化按钮矩阵（纯读盘，毫秒级），
        # 真实服务状态改由 refresh_status_async 后台探测后回填，避免启动与轮询卡顿。
        self._refresh_deploy_state()
        self.update_button_states()
        self.refresh_status_async()
        self.refresh_log()
        self.after(int(cfg["status_check_ms"]), self._periodic_status)
        # v1.6.6：窗口关闭(X)改走确认框；创建系统托盘图标（常驻，可恢复窗口）
        self.protocol("WM_DELETE_WINDOW", self.on_close_request)
        self._tray_icon = None
        self._tray_active = False
        self._create_tray_icon()
        # v1.8.3：Shift 检测——按住 Shift 点退出/关闭时强制弹出确认框（恢复询问入口）
        self._shift_held = False
        self.bind_all("<KeyPress-Shift_L>", self._on_shift_press)
        self.bind_all("<KeyPress-Shift_R>", self._on_shift_press)
        self.bind_all("<KeyRelease-Shift_L>", self._on_shift_release)
        self.bind_all("<KeyRelease-Shift_R>", self._on_shift_release)
        # v1.9.8：上次退出时服务在运行 → 启动后延迟自动恢复（等界面/Tray 就绪再执行）
        self.after(1200, self._maybe_auto_restore)

    def _on_shift_press(self, _event=None):
        self._shift_held = True

    def _on_shift_release(self, _event=None):
        self._shift_held = False

    # ---------- UI ----------
    def _build_ui(self):
        # 顶部状态区
        top = tk.Frame(self, bg="#ffffff", padx=12, pady=8)
        top.pack(fill=tk.X, padx=10, pady=(8, 6))
        self.status_label = tk.Label(
            top, text="正在检测服务状态...", font=("Microsoft YaHei UI", 14, "bold"),
            bg="#ffffff", fg=TEXT_PRIMARY,
        )
        self.status_label.pack(anchor="w")
        self.status_sub = tk.Label(
            top, text="部署目录：%s" % self.cfg["vaultwarden_dir"],
            font=("Microsoft YaHei UI", 9), bg="#ffffff", fg=TEXT_SECONDARY,
        )
        self.status_sub.pack(anchor="w", pady=(2, 0))

        # 中部：左按钮 + 右日志
        mid = tk.Frame(self, bg="#f0f2f5")
        mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        left = tk.Frame(mid, bg="#f0f2f5")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        btn_cfg = dict(font=("Microsoft YaHei UI", 10, "bold"), width=10, height=1,
                       relief=tk.RAISED, bd=1, cursor="hand2",
                       disabledforeground=BTN_DISABLED_FG)
        self.btns = {}
        rows = [
            ("deploy", "一键部署", BTN_BG, self.on_deploy),
            ("start", "启动服务", BTN_BG, self.on_start),
            ("stop", "停止服务", BTN_BG, self.on_stop),
            ("web", "打开 Web", BTN_BG, self.on_web),
            ("admin", "打开面板", BTN_BG, self.on_admin),
            ("enc_backup", "加密备份", BTN_BG, self.on_enc_backup),
            ("import_backup", "导入备份", BTN_BG, self.on_import_backup),
            ("change_port", "修改端口", BTN_BG, self.on_change_port),
            ("copy_addr", "复制地址", BTN_BG, self.on_copy_addr),
            ("raw_log", "原始日志", BTN_BG, self.on_toggle_raw),
            ("exit", "退出工具", BTN_BG, self.on_exit),
        ]
        for i, (key, text, color, cmd) in enumerate(rows):
            b = tk.Button(left, text=text, bg=color, fg="white",
                          activebackground=BTN_BG_ACTIVE, activeforeground="white",
                          command=cmd, **btn_cfg)
            if key == "exit":
                # v1.7.2：退出按钮占最后一行整行：11 个按钮仍填满 2×6 矩阵
                b.grid(row=5, column=0, columnspan=2, padx=4, pady=4, sticky="nsew")
            else:
                b.grid(row=i // 2, column=i % 2, padx=4, pady=4, sticky="nsew")
            self.btns[key] = b
        # v1.8.5：矩阵外新增「设置」「关于」特殊样式按钮（白底蓝字 + 蓝色描边，与主操作
        # 按钮明显区分），位于矩阵底部整行（row6 两列），不参与 2×6 矩阵布局与状态矩阵逻辑。
        secondary_cfg = dict(font=("Microsoft YaHei UI", 10, "bold"), width=10, height=1,
                             relief=tk.SOLID, bd=1, cursor="hand2",
                             disabledforeground=BTN_DISABLED_FG)
        for i, (key, text, cmd) in enumerate(
            (("settings", "设置", self.on_settings), ("about", "关于", self.on_about))
        ):
            b = tk.Button(left, text=text, bg=BTN_SECONDARY_BG, fg=BTN_SECONDARY_FG,
                          activebackground=BTN_SECONDARY_ACTIVE_BG,
                          activeforeground=BTN_SECONDARY_FG,
                          highlightbackground=BTN_SECONDARY_FG, highlightthickness=1,
                          command=cmd, **secondary_cfg)
            b.grid(row=6, column=i, padx=4, pady=(8, 4), sticky="nsew")
            self.btns[key] = b
        # v1.9.11：「赞助支持」卡片（v1.9.0 引入、v1.9.6 加二维码）已整体迁至「关于」窗口，
        # 主窗口左侧不再渲染该卡片，按钮列下方保持留白。
        # 按钮列等宽两列
        left.grid_columnconfigure(0, weight=1)
        left.grid_columnconfigure(1, weight=1)

        right = tk.Frame(mid, bg="#ffffff")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        head = tk.Frame(right, bg="#ffffff")
        head.pack(fill=tk.X)
        tk.Label(head, text="最近日志（vaultwarden.log 尾部）",
                 font=("Microsoft YaHei UI", 10, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=6, pady=6)
        tk.Button(head, text="刷新日志", command=self.refresh_log,
                  font=("Microsoft YaHei UI", 9), bg=BTN_BG, fg="white",
                  activebackground=BTN_BG_ACTIVE, activeforeground="white",
                  disabledforeground=BTN_DISABLED_FG).pack(side=tk.RIGHT, padx=6, pady=6)
        self.log_text = scrolledtext.ScrolledText(
            right, wrap=tk.NONE, font=("Consolas", 9), state="disabled",
            bg="#111418", fg="#c9d1d9", insertbackground="#c9d1d9",
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        # 底部消息区
        bottom = tk.Frame(self, bg="#f0f2f5")
        bottom.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.msg_label = tk.Label(
            bottom, text="就绪", font=("Microsoft YaHei UI", 10),
            bg="#f0f2f5", fg=TEXT_PRIMARY, justify="left", anchor="w", wraplength=940,
        )
        self.msg_label.pack(fill=tk.X)

        # 底部部署进度区（一键部署时显示，初始隐藏）
        deploy_progress = tk.Frame(bottom, bg="#f0f2f5")
        self.progress_label = tk.Label(
            deploy_progress, text="", font=("Microsoft YaHei UI", 11, "bold"),
            bg="#f0f2f5", fg="#1971c2", justify="left", anchor="w", wraplength=940,
        )
        self.progress_label.pack(fill=tk.X, pady=(0, 2))
        style = ttk.Style(self)
        try:
            style.configure("Deploy.Horizontal.TProgressbar", thickness=16)
        except tk.TclError:
            pass  # 极老版本 tk 无此样式能力时忽略，仅高度不加大
        self.progress_bar = ttk.Progressbar(
            deploy_progress, style="Deploy.Horizontal.TProgressbar",
            orient="horizontal", mode="determinate", maximum=100, length=400,
        )
        self.progress_bar.pack(fill=tk.X)
        self._progress_frame = deploy_progress  # 保存引用，便于部署时展开/复位隐藏

    # ---------- 工具方法 ----------
    def set_msg(self, text: str, color: str = TEXT_PRIMARY):
        self.msg_label.config(text=text, fg=color)

    # ---------- 窗口图标（v1.9.7） ----------
    def _apply_window_icon(self):
        """设置主窗口与所有 Toplevel（设置/关于/确认等弹窗）的图标。

        双通道：iconbitmap(default=.ico) 覆盖全部顶层窗口（Windows 任务栏 + 标题栏）；
        iconphoto(.png) 兜底 Tk 未加载 ico 的情况。任一通道失败仅记日志，不影响启动。
        """
        ico = _asset_path("app.ico")
        png = _asset_path("app_128.png")
        ok = False
        if ico:
            try:
                self.iconbitmap(default=ico)
                ok = True
            except Exception as e:
                try:
                    append_manager_log(self.cfg, "图标", "窗口图标(ico)加载失败：%s" % e)
                except Exception:
                    pass
        if png:
            try:
                self._win_icon_photo = tk.PhotoImage(file=png)
                self.iconphoto(True, self._win_icon_photo)
                ok = True
            except Exception as e:
                try:
                    append_manager_log(self.cfg, "图标", "窗口图标(png)加载失败：%s" % e)
                except Exception:
                    pass
        if not ok:
            try:
                append_manager_log(self.cfg, "图标",
                                   "未找到可用图标资源，窗口图标回退为系统默认：%s" % (ico or png or "-"))
            except Exception:
                pass

    # ---------- 系统托盘（v1.6.6） ----------
    def _create_tray_icon(self):
        """创建系统托盘图标（v1.9.7 起优先读取 assets/tray.png 盾牌图标）。

        托盘常驻：单击/双击恢复主窗口；右键菜单含「显示主窗口」「退出程序」；
        托盘回调运行在独立线程，统一经 after(0) 回主线程操作 tkinter 控件。
        tray.png 缺失或读取失败时回退到 Pillow 代码绘制的旧图标（不中断托盘功能）；
        依赖缺失或创建失败时降级：_tray_active=False，关闭窗口直接退出不残留。
        """
        try:
            from pystray import Icon, Menu, MenuItem
            from PIL import Image, ImageDraw
        except Exception as e:
            self.set_msg("托盘不可用（缺少 pystray/Pillow），关闭窗口将直接退出", "#e8590c")
            return
        try:
            img = None
            tray_png = _asset_path("tray.png")
            if tray_png:
                try:
                    img = Image.open(tray_png).convert("RGBA")
                except Exception as e:
                    append_manager_log(self.cfg, "图标", "托盘图标读取失败，回退内置绘制：%s" % e)
                    img = None
            if img is None:
                # 兜底：无 tray.png 时保持 v1.6.6 的代码绘制图标
                img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
                d = ImageDraw.Draw(img)
                d.rounded_rectangle([2, 2, 62, 62], radius=14, fill=(25, 113, 194, 255))
                d.polygon([(16, 16), (24, 16), (32, 44), (40, 16), (48, 16), (36, 52), (28, 52)],
                          fill=(255, 255, 255, 255))

            def _show(icon=None, item=None):
                self._safe_schedule(self._show_from_tray)

            def _quit(icon=None, item=None):
                self._safe_schedule(self._quit_app)

            menu = Menu(
                MenuItem("显示主窗口", _show, default=True),
                Menu.SEPARATOR,
                MenuItem("退出程序", _quit),
            )
            self._tray_icon = Icon("vaultwarden-manager", img, "Vaultwarden 管家", menu)
            if hasattr(self._tray_icon, "run_detached"):
                self._tray_icon.run_detached()
            else:
                threading.Thread(target=self._tray_icon.run, daemon=True).start()
            # v1.8.9：等待托盘线程真正就绪（pystray 异步注册，Shell_NotifyIcon 失败不会抛
            # 异常到主线程）。就绪失败一律降级为"无托盘"模式，避免"窗口隐藏后无图标可恢复"。
            deadline = time.time() + 3.0
            while time.time() < deadline:
                if getattr(self._tray_icon, "_running", False):
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError("托盘图标线程未就绪")
            self._tray_active = True
            # v1.9.2：图标注册稳定后延迟补发 WM_TASKBARCREATED，兜底「进程被强杀后
            # explorer 通知区异常、NIM_ADD 注册不被显示」的场景（实测有效）。
            self.after(2000, self._resend_taskbar_created)
        except Exception as e:
            self._tray_icon = None
            self._tray_active = False
            self.set_msg("托盘创建失败，关闭窗口将直接退出：%s" % e, "#e8590c")

    def _resend_taskbar_created(self):
        """v1.9.2：向自身 pystray 图标窗口补发 WM_TASKBARCREATED（兜底重注册）。

        实测发现：进程被强杀后，explorer 通知区可能处于异常状态，此时 pystray
        的 Shell_NotifyIcon(NIM_ADD) 注册不一定会被 explorer 显示；向 pystray
        图标窗口补发 TaskbarCreated 消息会触发其重新注册图标。同一 hWnd+hID 的
        NIM_ADD 只更新不新增，不会造成图标重复，也不影响其它应用托盘图标。
        """
        try:
            import ctypes
            hwnd = getattr(self._tray_icon, "_hwnd", None)
            if not hwnd:
                return
            user32 = ctypes.windll.user32
            msg = user32.RegisterWindowMessageW("TaskbarCreated")
            user32.PostMessageW(hwnd, msg, 0, 0)
        except Exception:
            pass

    def _safe_schedule(self, fn):
        """v1.8.9：托盘线程安全调度——仅当主窗口仍存活时经 after(0) 回主线程执行。

        pystray 回调运行在独立线程，而 tkinter 控件只能安全地从主线程操作；
        本方法统一在调度前检查窗口存活（winfo_exists 在销毁后抛 TclError），
        避免退出流程 destroy() 之后托盘线程迟到回调访问已销毁控件。
        """
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        try:
            self.after(0, fn)
        except Exception:
            pass

    def on_close_request(self):
        """关闭窗口（X）与「退出工具」共用入口：全中文确认框 + 退出记忆（v1.8.3）。

        托盘不可用时（依赖缺失/创建失败）直接退出，不弹框。
        v1.8.3 记忆逻辑：
        - config.quit_confirm_skip=True 且未按住 Shift → 不再弹框，直接执行记忆动作；
        - 弹框时勾选「记住我的选择」→ 持久化记忆（写 config.json），下次直接执行；
        - 未勾选 → 仅本次生效，下次仍询问；
        - 按住 Shift 强制询问且未勾选 → 清除记忆，恢复每次询问（恢复入口）。
        """
        if not self._tray_active:
            self._quit_app()
            return
        skip = bool(self.cfg.get("quit_confirm_skip"))
        if skip and not self._shift_held:
            action = self.cfg.get("quit_default_action", "tray")
            if action == "quit":
                self._quit_app()
            else:
                self._minimize_to_tray()
            return
        res = ask_quit_or_tray(self, remember_default=False)
        if res["action"] is None:
            return  # 取消
        action = res["action"]
        if res["remember"]:
            _, tip = apply_quit_memory(self.cfg, action)
            self.set_msg(tip, "#2b8a3e")
            append_manager_log(self.cfg, "退出记忆", tip)
        elif skip:
            # Shift 强制询问后未勾选 → 清除记忆，恢复每次询问
            _, tip = clear_quit_memory(self.cfg)
            self.set_msg(tip, "#1971c2")
            append_manager_log(self.cfg, "退出记忆", tip)
        # 未勾选且原本未记忆：仅本次生效，不写盘
        if action == "quit":
            self._quit_app()
        else:
            self._minimize_to_tray()

    def _record_exit_state(self, running: bool):
        """v1.9.8：持久化「退出前服务是否在运行」标志到 config.json。

        仅在程序退出链路（_quit_app 后台线程 / 停止失败仍退出）调用；
        写盘失败静默忽略——不影响退出主流程，最多下次不自动恢复。
        """
        try:
            self.cfg["last_exit_service_running"] = bool(running)
            save_config(self.cfg)
        except Exception:  # noqa: BLE001
            pass

    def _maybe_auto_restore(self):
        """v1.9.8：上次退出时服务在运行 → 本次启动自动恢复启动服务。

        判定顺序：开关 auto_restore_service 关闭/无标志 → 直接跳过；部署状态非
        deployed（未部署/部署不完整）→ 跳过并清除标志；服务已在运行 → 仅清标志。
        启动失败保留标志（下次启动可再试），成功/已在运行则清除，避免重复自动启动。
        """
        if not bool(self.cfg.get("auto_restore_service", True)):
            if self.cfg.get("last_exit_service_running"):
                self._record_exit_state(False)
            return
        if not bool(self.cfg.get("last_exit_service_running")):
            return
        try:
            state, _tip = get_deploy_state(self.cfg)
        except Exception:  # noqa: BLE001
            state = "none"
        if state != "deployed":
            self._record_exit_state(False)
            self.set_msg("上次退出时服务在运行，但当前未完成部署，已跳过自动启动服务", TEXT_HINT)
            append_manager_log(self.cfg, "自动恢复服务", "未完成部署，已跳过自动启动")
            return
        exe_name = self.cfg.get("exe_name", "vaultwarden.exe")
        vw_dir = str(self.cfg["vaultwarden_dir"])

        def job():
            try:
                if is_process_running(exe_name, vw_dir):
                    return True, "服务已在运行，无需自动启动"
            except Exception:  # noqa: BLE001
                pass
            ok, msg, switched = ensure_port_available(self.cfg)
            if not ok:
                return False, msg
            ok2, msg2 = start_service(self.cfg)
            if switched:
                msg2 = f"{msg}；{msg2}"
            return ok2, "自动恢复服务：" + msg2

        def done(r):
            # 启动成功（或本就在运行）→ 清除标志；失败 → 保留标志，下次启动再尝试
            self._record_exit_state(not bool(r[0]))
            append_manager_log(self.cfg, "自动恢复服务", str(r[1]))
            self.refresh_log()
            self._refresh_deploy_state()
            self.update_button_states()

        self.run_task(job, done, busy_text="正在自动恢复服务（上次退出时服务在运行）…")

    def _minimize_to_tray(self):
        """最小化到托盘：隐藏主窗口，托盘图标常驻。v1.8.9 幂等：已隐藏则不重复操作。"""
        if self.state() == "withdrawn":
            return
        self.withdraw()
        self.set_msg("已最小化到系统托盘，单击托盘图标可恢复窗口", "#1971c2")

    def _show_from_tray(self):
        """托盘恢复（主线程执行）：显示并置顶主窗口。v1.8.9 幂等：已显示则仅置顶。"""
        if self.state() != "withdrawn":
            self.lift()
            self.focus_force()
            return
        self.deiconify()
        self.lift()
        self.focus_force()
        self.set_msg("已从系统托盘恢复", "#2b8a3e")

    def _quit_app(self):
        """真正退出：先停止服务（后台线程，UI 不冻结），再清理托盘销毁主窗口。

        v1.8.4：所有「退出程序」路径统一先进本方法——检测到服务在运行则提示
        「正在停止服务…」并停止全部实例；停止失败弹全中文确认框（仍退出/取消
        退出），绝不静默放弃；无服务在运行则直接退出。
        v1.9.1：停止服务改为**后台线程执行**——主线程立即刷新状态提示后返回，
        界面不再被 find_vw_processes / stop_service 的 PowerShell 子进程调用
        阻塞（实测同步退出最坏 6 秒+）；停止结果经 `_safe_schedule` 回主线程
        统一处理（成功→清理；失败→弹框决策），功能行为与 v1.8.4 完全一致
        （退出前仍确保停止服务、日志落盘、取消保留窗口与托盘）。`_quitting`
        防重入：等待期间重复点击退出直接忽略，避免并发启动多个停止线程。
        """
        if getattr(self, "_quitting", False):
            return
        self._quitting = True
        self.set_msg("正在退出…（停止服务中）", "#e8590c")
        try:
            self.update_idletasks()
        except Exception:
            pass
        exe_name = self.cfg.get("exe_name", "vaultwarden.exe")

        def worker():
            # v1.9.8：先记录「退出前服务是否在运行」再停服务——程序退出仍保持
            # v1.8.4「退出前先停服务」行为不变，仅额外持久化本次运行状态，
            # 供下次启动时按需自动恢复（用户先点「停止服务」再退出则为 False）。
            try:
                running = bool(find_vw_processes(exe_name))
            except Exception:
                running = False
            self._record_exit_state(running)
            try:
                if running:
                    ok, msg = stop_service(self.cfg)
                else:
                    ok, msg = True, "未检测到运行中的服务，直接退出"
            except Exception as e:
                ok, msg = False, "停止服务出错：%s" % e
            self._safe_schedule(lambda: self._on_stop_result(ok, msg))

        threading.Thread(target=worker, daemon=True,
                         name="quit-stop-service").start()

    def _on_stop_result(self, ok: bool, msg: str):
        """主线程：停止服务结果回调（v1.9.1）。

        成功 → 直接清理托盘并销毁主窗口；失败 → 弹 `ask_stop_failed_quit`
        决策：仍退出则清理、取消则复位 `_quitting` 并保留主窗口与托盘图标
        （与 v1.8.4 同步阻塞版本行为一致）。
        """
        append_manager_log(self.cfg, "退出程序", msg)
        if not ok:
            if not ask_stop_failed_quit(self, msg):
                self._quitting = False
                self.set_msg("已取消退出，服务可能仍在运行", "#d9480f")
                append_manager_log(self.cfg, "退出程序", "用户取消退出")
                return
            self.set_msg(msg, "#d9480f")
            # v1.9.8：停止失败仍退出 → 服务可能仍在运行，标记为运行中供下次启动判定
            self._record_exit_state(True)
        self._final_cleanup()

    def _final_cleanup(self):
        """主线程：真正清理——托盘 stop（重试兜底 + NIM_DELETE 物理兜底）+ 销毁主窗口。"""
        icon = getattr(self, "_tray_icon", None)
        if icon is not None:
            # v1.9.2：先记录托盘标识——pystray stop() 成功后 _hwnd 会被销毁，
            # 但 Shell_NotifyIcon(NIM_DELETE) 兜底仍可用原标识再删一次
            _tray_hwnd = getattr(icon, "_hwnd", None)
            _tray_hid = None
            try:
                _tray_hid = id(icon)
            except Exception:
                pass
            try:
                icon.stop()
            except Exception:
                pass
            # v1.8.9：退出清理兜底——首次 stop 未生效（异常/超时）时重试一次，
            # 确保托盘图标被移除、不残留僵尸图标
            try:
                if getattr(icon, "_running", False):
                    icon.stop()
            except Exception:
                pass
            # v1.9.2：Shell_NotifyIcon NIM_DELETE 物理兜底——pystray stop 内部
            # 已执行 NIM_DELETE，此处再显式删除一次，保证 explorer 通知区不残留
            self._nim_delete_icon(_tray_hwnd, _tray_hid)
            self._tray_icon = None
            self._tray_active = False
        try:
            self.destroy()
        except Exception:
            pass

    def _nim_delete_icon(self, hwnd, hid):
        """v1.9.2：Shell_NotifyIconW(NIM_DELETE) 兜底删除托盘图标。

        针对 pystray stop() 异常/托盘线程异常退出未清理的场景，用与 pystray
        完全相同的标识（hWnd=图标窗口句柄、uID=id(icon)）物理删除一次。
        只删除自身图标，不影响其它应用托盘图标；ctypes 不可用时静默跳过。
        """
        if not hwnd:
            return
        try:
            import ctypes
            from ctypes import wintypes

            class NOTIFYICONDATAW(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("hWnd", wintypes.HWND),
                    ("uID", wintypes.UINT),
                    ("uFlags", wintypes.UINT),
                    ("uCallbackMessage", wintypes.UINT),
                    ("hIcon", wintypes.HICON),
                    ("szTip", wintypes.WCHAR * 128),
                    ("dwState", wintypes.DWORD),
                    ("dwStateMask", wintypes.DWORD),
                    ("szInfo", wintypes.WCHAR * 256),
                    ("uVersion", wintypes.UINT),
                    ("szInfoTitle", wintypes.WCHAR * 64),
                    ("dwInfoFlags", wintypes.DWORD),
                    ("guidItem", ctypes.c_byte * 16),
                    ("hBalloonIcon", wintypes.HICON),
                ]

            data = NOTIFYICONDATAW()
            data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            data.hWnd = hwnd
            data.uID = hid if isinstance(hid, int) else 0
            ctypes.windll.shell32.Shell_NotifyIconW(2, ctypes.byref(data))  # NIM_DELETE=2
        except Exception:
            pass

    # ---------- 部署进度条（v1.6.3） ----------
    def _show_deploy_progress(self):
        """显示部署进度区并复位到初始状态（消息栏上方展开）。"""
        if not getattr(self, "_progress_frame", None):
            return
        try:
            self._progress_frame.pack(fill=tk.X, before=self.msg_label, pady=(0, 6))
        except tk.TclError:
            pass
        self.progress_bar.stop()
        self.progress_bar.config(mode="determinate", value=0)
        self.progress_label.config(text="准备部署…", fg="#1971c2")

    def _set_progress_determinate(self, pct: int, text: str):
        """主线程：确定进度（下载阶段百分比）。"""
        self.progress_bar.stop()
        self.progress_bar.config(mode="determinate", value=max(0, min(100, int(pct))))
        self.progress_label.config(text=text, fg="#1971c2")

    def _set_progress_indeterminate(self, text: str):
        """主线程：不定进度（部署/启动/未知大小下载），显示"部署中…"提示。"""
        self.progress_bar.stop()
        self.progress_bar.config(mode="indeterminate")
        self.progress_bar.start(15)
        self.progress_label.config(text=text, fg="#1971c2")

    def _start_deploy_poll(self):
        """主线程：部署轮询阶段启动 1 秒一次的状态栏刷新（after 轮询）。"""
        self._deploy_elapsed = 0
        self._deploy_poll_id = self.after(1000, self._deploy_poll_tick)

    def _deploy_poll_tick(self):
        self._deploy_elapsed += 1
        if getattr(self, "_busy", False):
            self.progress_label.config(
                text=f"正在部署/启动服务… 部署中…（已等待 {self._deploy_elapsed} 秒）",
                fg="#1971c2",
            )
            self._deploy_poll_id = self.after(1000, self._deploy_poll_tick)
        else:
            self._deploy_poll_id = None

    def _stop_deploy_poll(self):
        pid = getattr(self, "_deploy_poll_id", None)
        if pid:
            try:
                self.after_cancel(pid)
            except Exception:
                pass
            self._deploy_poll_id = None

    def _finish_deploy_progress(self, ok: bool):
        """主线程：部署结束，进度条恢复初始状态（隐藏并复位）；完成提示由消息栏展示。"""
        self._stop_deploy_poll()
        try:
            self.progress_bar.stop()
        except Exception:
            pass
        try:
            self.progress_bar.config(mode="determinate", value=0)
        except Exception:
            pass
        try:
            self._progress_frame.pack_forget()
        except Exception:
            pass
        self.progress_label.config(text="", fg="#1971c2")

    def set_busy(self, busy: bool):
        self._busy = busy
        self.update_button_states()

    def update_button_states(self):
        """按当前服务状态刷新按钮可用性，与 _busy 忙碌状态协调。

        服务运行中（含 abnormal）：禁用 一键部署/启动服务，启用 停止服务 与 打开 Web/打开面板；
        foreign（v1.8.1：存在非部署目录同名残留实例）：与运行中同侧——启用 停止服务 与
        打开 Web/打开面板、禁用 一键部署/启动服务，让用户可直接清理残留实例，避免
        「启动被拦截 + 停止按钮禁用」的死锁；
        服务停止时：禁用 停止服务 与 打开 Web/打开面板，启用 一键部署/启动服务；
        v1.9.4 「一键部署」部署完成锁定：部署状态为 deployed（磁盘判定：核心文件 + .env 的
        ADMIN_TOKEN + web-vault/index.html 全部就绪）时，无论服务运行中还是已停止，
        「一键部署」一律 DISABLED（点击无响应），需先清理部署目录才会恢复；partial/none 不受锁定。
        其余按钮（复制地址/加密备份/导入备份/修改端口）始终可用；原始日志按钮始终可用；
        操作进行中（_busy）：全部功能按钮临时禁用，退出按钮保持可用。
        """
        running = self._service_status in ("running", "abnormal", "foreign")
        stopped = self._service_status == "stopped"
        deployed = getattr(self, "_deploy_state", "none") == "deployed"
        for key, b in self.btns.items():
            if key == "exit":
                b.config(state=tk.NORMAL)
            elif key == "raw_log":
                # 日志原始/过滤切换为只读展示操作，始终可用
                b.config(state=tk.NORMAL)
            elif key in ("settings", "about"):
                # v1.8.5：设置/关于为辅助入口，始终可用（不参与服务状态/忙碌禁用）
                b.config(state=tk.NORMAL)
            elif self._busy:
                b.config(state=tk.DISABLED)
            elif key in ("deploy", "start") and running:
                b.config(state=tk.DISABLED)
            elif key == "deploy" and deployed:
                # v1.9.4：已部署成功 → 一键部署永久禁用（会话内与重启后一致）
                b.config(state=tk.DISABLED)
            elif key in ("web", "admin") and stopped:
                b.config(state=tk.DISABLED)
            elif key == "stop" and stopped:
                b.config(state=tk.DISABLED)
            else:
                b.config(state=tk.NORMAL)

    def run_task(self, fn, on_done, busy_text="正在执行，请稍候..."):
        """后台线程执行 fn，完成后回到主线程回调 on_done(result)。

        v1.9.5：新增 busy_text 参数，允许调用方给出更具体的忙碌提示
        （如「正在加密备份…」），避免泛化文案覆盖业务阶段提示。
        """
        if self._busy:
            self.set_msg("上一个操作还在执行中，请稍候...", "#e8590c")
            return

        def worker():
            try:
                result = fn()
            except Exception as e:  # noqa: BLE001
                result = (False, f"操作异常：{e}")
            # v1.9.5：跨线程回主线程统一走 _safe_schedule（带存活检查，避免窗口销毁后迟到回调）
            self._safe_schedule(lambda: self._finish_task(result, on_done))

        self.set_busy(True)
        self.set_msg(busy_text, "#1971c2")
        threading.Thread(target=worker, daemon=True).start()

    def _finish_task(self, result, on_done):
        self.set_busy(False)
        if result and result[0]:
            self.set_msg(str(result[1]), "#2b8a3e")
        else:
            self.set_msg(str(result[1]) if result else "操作失败", "#c92a2a")
        if on_done:
            on_done(result)
        # v1.9.5：刷新状态改异步，避免任务结束后主线程被状态探测（历史实测约 4.4s）阻塞
        self.refresh_status_async()

    # ---------- 状态轮询 ----------
    def _refresh_deploy_state(self):
        """v1.9.4：重新按磁盘文件判定部署状态，刷新状态栏副标签并返回 state。

        state=deployed → 「一键部署」永久禁用（重启后同样禁用）；partial（网页版未装）
        与 none（未部署/部署不完整）→ 按钮保持可点。判定异常时保守降级为 none。
        """
        try:
            state, tip = get_deploy_state(self.cfg)
        except Exception:  # noqa: BLE001
            state, tip = "none", "无法判定部署状态（按钮保持可用）"
        self._deploy_state = state
        self._deploy_state_tip = tip
        label = {
            "deployed": "已部署（一键部署已锁定）",
            "partial": "部署部分就绪（网页版未安装，可补装）",
        }.get(state, "未部署")
        text = "部署目录：%s ｜ 部署状态：%s" % (self.cfg["vaultwarden_dir"], label)
        if _migration_notice:
            # 迁移提示保留在状态栏最前，颜色沿用红色提醒
            self.status_sub.config(text=_migration_notice + " ｜ " + text, fg="#c92a2a")
        else:
            self.status_sub.config(text=text, fg=TEXT_SECONDARY)
        return state

    def refresh_status(self):
        status, text, color = get_service_status(self.cfg)
        self._service_status = status
        self.status_label.config(text=f"● {text}", fg=color)
        self._refresh_deploy_state()
        self.update_button_states()
        return status

    def refresh_status_async(self):
        """v1.9.5：状态探测放到后台线程，结果经 after(0) 回主线程应用。

        卡顿根因修复：get_service_status 内部需起 PowerShell 查进程真实路径，
        实测单次约 4.4s；原实现由 _periodic_status 每 status_check_ms(3s) 在主线程
        同步调用，导致主线程几乎被占满——表现为弹密码框/输入密码时界面卡顿。
        此处改为后台探测 + 单飞防重入（_status_probing），探测期间不再重复发起。
        """
        if getattr(self, "_status_probing", False):
            return False
        self._status_probing = True

        def worker():
            try:
                res = get_service_status(self.cfg)
            except Exception as e:  # noqa: BLE001
                res = ("stopped", "状态探测失败：%s" % e, "#c92a2a")
            self._safe_schedule(lambda: self._apply_status(res))

        threading.Thread(target=worker, daemon=True, name="vw-status-probe").start()
        return True

    def _apply_status(self, res):
        """后台探测结果回到主线程后应用（按钮矩阵与状态栏同步刷新）。"""
        self._status_probing = False
        try:
            status, text, color = res
        except Exception:  # noqa: BLE001
            status, text, color = "stopped", "状态探测失败", "#c92a2a"
        self._service_status = status
        self.status_label.config(text=f"● {text}", fg=color)
        self._refresh_deploy_state()
        self.update_button_states()

    def _periodic_status(self):
        self.refresh_status_async()
        self.after(int(self.cfg["status_check_ms"]), self._periodic_status)

    # ---------- 日志 ----------
    def refresh_log(self):
        raw = getattr(self, "_raw_log", False)  # 兜底：防止初始化顺序问题再次触发 AttributeError
        content, dropped = read_log_tail(self.cfg, filter_noise=not raw)
        if not raw and dropped > 0:
            content = "（已过滤 %d 行噪音日志）\n" % dropped + content
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.insert("1.0", content)
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def on_toggle_raw(self):
        """切换 原始日志 / 过滤日志 显示模式（不修改 vaultwarden.log 落盘内容）。"""
        self._raw_log = not self._raw_log
        self.btns["raw_log"].config(text="过滤日志" if self._raw_log else "原始日志")
        self.refresh_log()
        self.set_msg(
            "已切换为原始日志（未过滤）" if self._raw_log else "已切换为过滤日志（噪音已隐藏）",
            "#5c7cfa",
        )

    def _log_action(self, action: str, result):
        """操作完成后追加一行 manager.log；写入失败不影响主流程，仅在状态栏提示。"""
        summary = str(result[1]) if result else "操作失败"
        err = append_manager_log(self.cfg, action, summary)
        if err:
            self.set_msg(err, "#c92a2a")

    # ---------- 按钮回调 ----------
    def on_deploy(self):
        # v1.9.4：点击入口二次拦截——按钮虽已置灰，仍防键盘/程序化触发；判定一律看磁盘
        state, tip = ("none", "")
        try:
            state, tip = get_deploy_state(self.cfg)
        except Exception:  # noqa: BLE001
            state = "none"
        if state == "deployed":
            self._deploy_state = state
            self._deploy_state_tip = tip
            self.update_button_states()
            self.set_msg("已完成部署，无需重复部署；如需重新部署请先清理部署目录 "
                         + str(self.cfg["vaultwarden_dir"]), "#d9480f")
            return
        if is_process_running(self.cfg["exe_name"]) and is_port_open(int(self.cfg["port"])):
            if state == "partial":
                self.set_msg("已部署但网页版未安装：请先点击「停止服务」，再点击「一键部署」补装网页版",
                             "#d9480f")
            else:
                self.set_msg("服务已在运行，无需重复部署", "#d9480f")
            return
        # v1.9.8：端口占用检测与自动随机端口切换在 deploy_service 内部率先执行
        # （切换后 config.json/.env/界面地址均按新端口刷新，失败时直接返回中文错误）。
        self.set_msg("正在部署...", "#1971c2")
        self._show_deploy_progress()
        self._deploy_stage = "core"  # 阶段标志：core=核心文件下载 / webvault=网页版下载 / deploy=启动部署

        def job():
            def progress(downloaded, total):
                # 工作线程回调：通过 after(0) 切回主线程更新进度条与状态栏
                mb = downloaded / 1024 / 1024
                prefix = "正在下载网页版" if getattr(self, "_deploy_stage", "core") == "webvault" else "正在下载核心文件"
                if total > 0:
                    pct = downloaded * 100 // total
                    text = f"{prefix}：{mb:.1f} MB / {total / 1024 / 1024:.1f} MB（{pct}%）"
                    self.after(0, lambda: self._set_progress_determinate(pct, text))
                else:
                    # 无法获取总长度（无 Content-Length）→ 退化为不定进度
                    text = f"{prefix}：{mb:.1f} MB（大小未知，部署中…）"
                    self.after(0, lambda: self._set_progress_indeterminate(text))

            def stage(stage):
                if stage == "webvault":
                    # 进入网页版下载阶段：提示文字区分阶段，等待 progress_cb 更新百分比
                    self._deploy_stage = "webvault"
                    self.after(0, lambda: self._set_progress_indeterminate("正在下载网页版…"))
                elif stage == "cert":
                    # v1.7.2：进入证书生成阶段（无证书时才触发）
                    self._deploy_stage = "cert"
                    self.after(0, lambda: self._set_progress_indeterminate("正在生成证书…"))
                elif stage == "trust":
                    # v1.7.2：进入添加系统信任阶段
                    self._deploy_stage = "trust"
                    self.after(0, lambda: self._set_progress_indeterminate("正在添加系统信任…"))
                elif stage == "deploy":
                    # 下载/校验完成，进入启动与端口轮询阶段 → 不定进度 + 主线程 after 轮询刷新
                    self._deploy_stage = "deploy"
                    self.after(0, lambda: self._set_progress_indeterminate("正在部署/启动服务… 部署中…"))
                    self.after(0, self._start_deploy_poll)

            return deploy_service(self.cfg, progress_cb=progress, stage_cb=stage)

        def done(r):
            self._finish_deploy_progress(r[0])
            # v1.9.4：部署成功后立即按磁盘重算部署状态 → 「一键部署」立刻置灰不可点
            # v1.9.8：端口被占用自动切换后，状态栏/按钮矩阵同步刷新（地址由 cfg['port'] 动态派生）
            self._refresh_deploy_state()
            self.update_button_states()
            msg = r[1]
            if r[0] and self._deploy_state == "deployed":
                msg = f"{msg}｜「一键部署」已锁定（已完成部署，如需重新部署请先清理部署目录）"
            self.set_msg(msg, "#099268" if r[0] else "#c92a2a")
            self.refresh_log()
            self._log_action("一键部署", (r[0], msg))

        self.run_task(job, done)

    def on_start(self):
        """v1.9.8：启动前做端口占用检测，被占用则自动切换随机端口后再启动。

        一次启动至多切换一次端口（ensure_port_available 只调用一次），避免端口反复漂移；
        端口空闲 / 由本程序服务自身占用时行为与旧版完全一致，不产生多余提示。
        """
        def job():
            ok, msg, switched = ensure_port_available(self.cfg)
            if not ok:
                return False, msg
            ok2, msg2 = start_service(self.cfg)
            if switched:
                msg2 = f"{msg}；{msg2}"
            return ok2, msg2

        def done(r):
            self.refresh_log()
            self._log_action("启动服务", r)
            self._refresh_deploy_state()
            self.update_button_states()

        self.run_task(job, done, busy_text="正在启动服务…")

    def on_stop(self):
        self.run_task(lambda: stop_service(self.cfg),
                      lambda r: (self.refresh_log(), self._log_action("停止服务", r)))

    def on_web(self):
        # v1.6.9：按 cfg['port'] 动态拼 URL（不再写死 8000 / 依赖可能不同步的 domain）
        url = resolve_web_url(self.cfg)
        try:
            webbrowser.open(url)
        except Exception as e:
            self.set_msg(f"打开浏览器失败：{e}", "#c92a2a")
            return
        self.set_msg(f"已在浏览器打开 Web Vault：{url}", "#1971c2")

    def on_admin(self):
        # v1.6.9：按 cfg['port'] 动态拼 URL + admin_path
        url = resolve_web_url(self.cfg) + self.cfg["admin_path"]
        try:
            webbrowser.open(url)
        except Exception as e:
            self.set_msg(f"打开浏览器失败：{e}", "#c92a2a")
            return
        self.set_msg(f"已在浏览器打开管理面板：{url}", "#1971c2")

    def on_enc_backup(self):
        if not CRYPTO_OK:
            self.set_msg("缺少 cryptography 库，请执行 pip install cryptography 后重试", "#c92a2a")
            return
        pw = prompt_password(self, "加密备份 - 请输入密码")
        if pw is None:
            self.set_msg("已取消加密备份", TEXT_HINT)
            return
        # v1.9.5：新增「选择备份位置」——默认定位到既有备份目录与既有文件名规范，
        # 用户可自定义目录/文件名；取消选择则优雅中止（不产生任何文件、不报错）。
        default_path = resolve_enc_target(self.cfg)
        try:
            chosen = filedialog.asksaveasfilename(
                title="选择加密备份保存位置",
                initialdir=str(default_path.parent),
                initialfile=default_path.name,
                defaultextension=".enc",
                filetypes=[("加密备份", "*.enc"), ("所有文件", "*.*")],
            )
        except Exception as e:  # noqa: BLE001
            self.set_msg(f"打开保存对话框失败：{e}", "#c92a2a")
            return
        if not chosen:
            self.set_msg("已取消加密备份（未选择保存位置）", TEXT_HINT)
            return
        out_path = str(chosen)

        def _stage(_name, text):
            # 工作线程回调 → 经 _safe_schedule(0) 回主线程更新状态栏，避免跨线程操作控件
            self._safe_schedule(lambda: self.set_msg(text, "#1971c2"))

        self.set_msg("正在加密备份…", "#1971c2")
        self.run_task(lambda: encrypt_backup(self.cfg, pw, out_path=out_path, stage_cb=_stage),
                      lambda r: self._log_action("加密备份", r),
                      busy_text="正在加密备份…")

    def on_import_backup(self):
        if not CRYPTO_OK:
            self.set_msg("缺少 cryptography 库，请执行 pip install cryptography 后重试", "#c92a2a")
            return
        path = filedialog.askopenfilename(
            title="选择加密备份文件（.enc）",
            filetypes=[("加密备份", "*.enc"), ("所有文件", "*.*")],
        )
        if not path:
            self.set_msg("已取消导入备份", TEXT_HINT)
            return
        pw = prompt_password(self, "导入备份 - 请输入密码")
        if pw is None:
            self.set_msg("已取消导入备份", TEXT_HINT)
            return
        if not messagebox.askyesno(
            "确认恢复",
            "即将用备份包覆盖当前 data 目录：\n%s\n\n现有 data 目录会先改名备份为 data_bak_<时间戳>，以防误操作。\n是否继续？" % path,
        ):
            self.set_msg("已取消恢复", TEXT_HINT)
            return
        self.run_task(lambda: decrypt_and_restore(self.cfg, path, pw),
                      lambda r: self._log_action("导入备份", r))

    def on_copy_addr(self):
        url = self.cfg["domain"]
        self.clipboard_clear()
        self.clipboard_append(url)
        self.update()
        self.set_msg(f"已复制 Web Vault 地址：{url}", "#2b8a3e")
        self._log_action("复制地址", (True, f"已复制 Web Vault 地址：{url}"))

    def on_change_port(self):
        new_port = prompt_port(self, int(self.cfg["port"]))
        if new_port is None:
            self.set_msg("已取消修改端口", TEXT_HINT)
            return
        ok, msg = update_port(self.cfg, new_port)
        self.set_msg(msg, "#2b8a3e" if ok else "#c92a2a")
        self.refresh_status_async()  # v1.9.5：端口变更后状态异步回填，不阻塞界面
        self._log_action("修改端口", (ok, msg))

    def on_settings(self):
        """v1.8.5：打开设置窗口；保存后同步 self.cfg 并提示。

        v1.9.9：传入 self.set_msg，使设置窗口内「复制地址」等操作结果同步到主窗口状态栏。
        """
        res = open_settings_dialog(self, self.cfg, self.set_msg)
        if res is None:
            self.set_msg("已取消设置", TEXT_HINT)
            return
        self.cfg = res
        self.set_msg("设置已保存（config.json 已更新）", "#2b8a3e")
        append_manager_log(self.cfg, "设置", "设置已保存（config.json 已更新）")

    def on_about(self):
        """v1.8.5：打开关于窗口（软件名称/版本/作者版权/部署目录/配置文件路径）。"""
        show_about_dialog(self, self.cfg)
        self.set_msg("已打开关于窗口", TEXT_HINT)

    def on_exit(self):
        # v1.6.6：与关闭确认保持一致（弹出同一确认框，或托盘不可用时直接退出）
        self.on_close_request()

def _acquire_single_instance() -> bool:
    """v1.8.9：Windows 单实例互斥。返回 True=本进程获得运行权；False=已有实例在运行。

    使用固定互斥名（不带版本号），保证新旧版本 exe 之间也互斥，杜绝同一时刻
    出现多个管家窗口/多个托盘图标导致的通知区域堆积。
    """
    try:
        import ctypes
        from ctypes import wintypes
        # v1.9.2 修复：CreateMutexW【成功】创建互斥后 GetLastError 仍可能残留 183
        # （ERROR_ALREADY_EXISTS）——ctypes 未清零错误码时，刚启动的进程会被误判为
        # 「已有实例在运行」，随后走 _activate_existing_instance 的激活/弹框路径并
        # 退出，真机表现为「启动后约 6~12 秒进程自动退出、托盘图标消失」。
        # 修复：调用前 SetLastError(0) 清零，再以返回值 + 错误码判定互斥是否已存在。
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.SetLastError(0)  # 清零错误码，杜绝成功创建时的 183 残留误判
        handle = kernel32.CreateMutexW(None, False, "Local\\VaultwardenManager_SingleInstance")
        if not handle:
            return True  # 创建失败（罕见）不阻塞运行
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS：互斥已存在
            kernel32.CloseHandle(handle)
            return False
        globals()["_SINGLE_INSTANCE_HANDLE"] = handle  # 持有句柄直至进程退出
        return True
    except Exception:
        return True


def _acquire_notice_lock() -> bool:
    """v1.9.3：第二实例的「提示框互斥锁」。返回 True=本次由我弹提示；False=其它实例正在弹。

    快速连续启动多个第二实例时，若无此锁会同时弹出多个相同提示框。用命名互斥
    `Local\\VaultwardenManager_NoticeLock` 抢占：先抢到者弹提示，其余静默退出。
    判定同样遵循「调用前 SetLastError(0) + 返回值非空 + 错误码 183」双条件，避免
    v1.9.2 曾出现的错误码残留误判（把成功创建误判成「已被占用」而漏弹提示）。
    """
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.SetLastError(0)
        handle = kernel32.CreateMutexW(None, False, "Local\\VaultwardenManager_NoticeLock")
        if not handle:
            return True
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS：别人正在弹提示
            kernel32.CloseHandle(handle)
            return False
        globals()["_NOTICE_LOCK_HANDLE"] = handle
        return True
    except Exception:
        return True


def _find_main_window(attempts: int, interval: float = 0.5) -> int:
    """v1.9.3：查找已有实例的主窗口句柄，找不到返回 0。"""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        for _ in range(max(1, attempts)):
            hwnd = user32.FindWindowW("TkTopLevel", "Vaultwarden 管理工具")
            if hwnd:
                return hwnd
            time.sleep(interval)
    except Exception:
        pass
    return 0


def _keep_dialog_topmost(user32, title: str, tries: int = 60, interval: float = 0.05) -> None:
    """v1.9.3 加固：守护线程在提示框出现后补一次 SetWindowPos(HWND_TOPMOST)。

    MB_TOPMOST 在部分 Windows 版本/桌面状态下不会落到对话框的 WS_EX_TOPMOST 样式位，
    导致无父窗口的提示框可能被其它窗口压住。这里不阻塞调用方：另起守护线程轮询查找
    标题为 title 的对话框（#32770），命中即置顶，之后自然结束。全程静默容错。
    """
    def _worker():
        try:
            import ctypes
            HWND_TOPMOST = -1
            SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x0001, 0x0002, 0x0010
            user32.SetWindowPos.argtypes = [
                ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint,
            ]
            user32.SetWindowPos.restype = ctypes.c_int
            for _ in range(tries):
                h = user32.FindWindowW("#32770", title)
                if h:
                    user32.SetWindowPos(h, HWND_TOPMOST, 0, 0, 0, 0,
                                        SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
                    return
                time.sleep(interval)
        except Exception:
            return
    try:
        threading.Thread(target=_worker, daemon=True).start()
    except Exception:
        pass


def _activate_existing_instance() -> None:
    """v1.9.3：已有实例运行时——先弹中文提示框告知「程序已在运行中」，再尝试激活其窗口。

    交互约束（v1.9.3）：
    ① **必须弹框**：标题固定「VaultwardenManager」，正文明确「程序已在运行中，请勿重复打开」；
    ② **置顶可见**：`MB_TOPMOST | MB_SETFOREGROUND`，第二实例尚无父窗口，无主窗口归属时
       也不会被其它窗口遮挡或压在后台；
    ③ **不阻塞已有实例**：提示框属于本进程（第二实例），已有实例的窗口/托盘不受影响；
    ④ **提示后必定退出**：函数返回后 `main()` 直接 return，进程结束不残留（激活失败也不影响）；
    ⑤ **区分孤儿残留**：有互斥但长时间无主窗口 → 判定为强杀遗留的孤儿进程，文案改为引导用户
       结束全部 VaultwardenManager.exe 后重试。
    """
    try:
        import ctypes
        user32 = ctypes.windll.user32
        # 先快速探测（1s 内命中即弹框，不让用户干等）；未命中再补探 2s，
        # 覆盖已有实例正处于「启动广播 2.5s + 托盘就绪轮询」尚未建窗的早期阶段。
        hwnd = _find_main_window(2)
        if not hwnd:
            hwnd = _find_main_window(4)
        if hwnd:
            tip = ("程序已在运行中，请勿重复打开。\n\n"
                   "可从任务栏窗口或系统托盘图标打开已有窗口。")
        else:
            tip = ("程序已在运行中，但未找到它的主窗口（可能是上次被强制结束后遗留的残留进程）。\n\n"
                   "请打开任务管理器 →「详细信息」，结束所有 VaultwardenManager.exe 进程后重新启动；"
                   "也可在命令行执行：taskkill /F /T /IM VaultwardenManager.exe")
        # MB_OK | MB_ICONINFORMATION | MB_TOPMOST | MB_SETFOREGROUND
        MB_FLAGS = 0x00000000 | 0x00000040 | 0x00040000 | 0x00010000
        # v1.9.3 加固：守护线程补一次 SetWindowPos(HWND_TOPMOST)，确保提示框真正置顶可见
        _keep_dialog_topmost(user32, "VaultwardenManager")
        user32.MessageBoxW(None, tip, "VaultwardenManager", MB_FLAGS)
        # 提示后再激活已有窗口（v1.9.3：激活失败不影响提示与退出，全部静默容错）
        if hwnd:
            try:
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE：从最小化/隐藏恢复
                user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
    except Exception:
        pass


def _refresh_tray_icons():
    """v1.9.2：广播通知区刷新，清理历史幽灵托盘图标（ghost icon）。

    进程被强杀（taskkill /F / 任务管理器结束）时进程无法执行
    Shell_NotifyIcon(NIM_DELETE)，explorer 托盘区可能残留已死进程的 ghost 图标。
    向 HWND_BROADCAST 广播 WM_TIMECHANGE 是 Windows 通知区公认的安全刷新手法：
    explorer 收到后重读通知区并清理失效图标；该消息只触发托盘刷新，不会删除
    其它应用正常注册的图标，不误伤系统托盘。ctypes 不可用时静默跳过。
    """
    try:
        import ctypes
        HWND_BROADCAST = 0xFFFF
        WM_TIMECHANGE = 0x001A
        ctypes.windll.user32.PostMessageW(HWND_BROADCAST, WM_TIMECHANGE, 0, 0)
    except Exception:
        pass


def main():
    # v1.8.9：先做单实例检查——已有管家进程时不创建窗口/托盘，激活已有实例后退出，
    # 从源头保证「托盘图标唯一」，避免重复启动堆积图标。
    # v1.9.3：第二实例必须弹出中文提示框告知「程序已在运行中」，提示后自行退出；
    # 并用 _acquire_notice_lock() 保证快速连续启动多个第二实例时「同一时刻只弹一次提示」。
    if not _acquire_single_instance():
        if _acquire_notice_lock():
            _activate_existing_instance()
        return
    # v1.9.2：在自身托盘图标注册【之前】广播通知区刷新，清理上一轮强杀遗留的
    # ghost 托盘图标。实测验证：若在图标注册之后再广播 WM_TIMECHANGE，explorer
    # 重建通知区时会丢掉本程序已注册的图标（pystray 的 WM_TASKBARCREATED 重注册
    # 在 Win11 新版通知区不生效）；因此必须「先广播清 ghost、等 explorer 重建
    # 完成、再注册自身图标」。广播只触发托盘刷新，不影响其它应用正常图标。
    _refresh_tray_icons()
    # 等待 explorer 完成通知区重建（2.5s），随后创建的托盘图标才会稳定显示
    time.sleep(2.5)
    # 程序启动自动创建缺失配置文件
    cfg = load_config()
    if not CONFIG_PATH.exists():
        _write_default_config()
    app = VaultwardenManagerApp(cfg)
    app.mainloop()

