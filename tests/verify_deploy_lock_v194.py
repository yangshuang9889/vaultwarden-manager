"""verify_deploy_lock_v194.py — v1.9.4「一键部署」部署完成锁定 冒烟验证

覆盖：
  A 语法与版本：三文件 py_compile、ui.VERSION = v1.9.4
  B get_deploy_state 磁盘判定：目录不存在/缺 exe/exe 过小/缺 .env/ADMIN_TOKEN 空/缺网页版/全就绪
  C update_button_states 按钮矩阵：stopped·running·foreign×deployed/partial/none/_busy 六组
  D 重启持久性：同一沙盒两次「启动」均判定 deployed 且按钮禁用
  E on_deploy 入口二次拦截：已部署时提示锁定、不进入部署流程
  F 源码静态断言：锁定分支、状态栏部署状态、done 即时刷新、锁定说明文案
"""
import os
import py_compile
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = []


def check(name, cond, extra=""):
    global PASS
    if cond:
        PASS += 1
        print("[PASS] %s" % name)
    else:
        FAIL.append(name)
        print("[FAIL] %s %s" % (name, extra))


# ---------------- A 语法与版本 ----------------
for f in ["vwm/service.py", "vwm/app.py", "vwm/ui.py"]:
    try:
        py_compile.compile(str(ROOT / f), doraise=True)
        check("py_compile %s" % f, True)
    except Exception as e:  # noqa: BLE001
        check("py_compile %s" % f, False, str(e))

import tkinter as tk  # noqa: E402

from vwm import app, service, ui  # noqa: E402

check("ui.VERSION >= v1.9.4（v1.9.5 起持续满足）",
      tuple(int(x) for x in ui.VERSION.lstrip("v").split(".")) >= (1, 9, 4), ui.VERSION)
check("service.get_deploy_state 存在", hasattr(service, "get_deploy_state"))

# ---------------- 沙盒构造 ----------------
SANDBOXES = []


def make_sandbox(exe=True, exe_size=2 * 1024 * 1024, env_text="ROCKET_PORT=44444\nADMIN_TOKEN=abc123\n",
                 webvault=True, mkdir=True):
    d = Path(tempfile.mkdtemp(prefix="vw194_"))
    SANDBOXES.append(d)
    if not mkdir:
        shutil.rmtree(d)
        d = d / "not_exist"
    else:
        if exe:
            with open(d / "vaultwarden.exe", "wb") as fp:
                fp.write(b"\0" * exe_size)
        if env_text is not None:
            (d / ".env").write_text(env_text, encoding="utf-8")
        if webvault:
            (d / "web-vault").mkdir(parents=True, exist_ok=True)
            (d / "web-vault" / "index.html").write_text("<html></html>", encoding="utf-8")
    return {"vaultwarden_dir": str(d), "exe_name": "vaultwarden.exe"}, d


# ---------------- B get_deploy_state 判定 ----------------
cfg, _d = make_sandbox()
state, tip = service.get_deploy_state(cfg)
check("B1 全部就绪 → deployed", state == "deployed", state)
check("B1b deployed 提示含「无需重复部署」", "无需重复部署" in tip, tip)

cfg, _d = make_sandbox(mkdir=False)
state, tip = service.get_deploy_state(cfg)
check("B2 部署目录不存在 → none", state == "none", state)

cfg, _d = make_sandbox(exe=False)
state, tip = service.get_deploy_state(cfg)
check("B3 缺核心文件 exe → none", state == "none" and "核心文件" in tip, (state, tip))

cfg, _d = make_sandbox(exe_size=100)
state, tip = service.get_deploy_state(cfg)
check("B4 exe 小于 1MB → none（疑似未下载完）", state == "none" and "1MB" in tip, (state, tip))

cfg, _d = make_sandbox(env_text=None)
state, tip = service.get_deploy_state(cfg)
check("B5 缺 .env → none", state == "none" and ".env" in tip, (state, tip))

cfg, _d = make_sandbox(env_text="ROCKET_PORT=44444\n")
state, tip = service.get_deploy_state(cfg)
check("B6 .env 无 ADMIN_TOKEN → none", state == "none" and "ADMIN_TOKEN" in tip, (state, tip))

cfg, _d = make_sandbox(env_text="ROCKET_PORT=44444\nADMIN_TOKEN=\n")
state, tip = service.get_deploy_state(cfg)
check("B6b .env ADMIN_TOKEN 空值 → none", state == "none", (state, tip))

cfg, _d = make_sandbox(webvault=False)
state, tip = service.get_deploy_state(cfg)
check("B7 缺 web-vault/index.html → partial（可补装）", state == "partial", (state, tip))

state, tip = service.get_deploy_state({"vaultwarden_dir": "", "exe_name": "vaultwarden.exe"})
check("B8 部署目录为空串 → none", state == "none", state)

# 判定不写盘、幂等（连续两次结果一致）
cfg, _d = make_sandbox()
r1 = service.get_deploy_state(cfg)
r2 = service.get_deploy_state(cfg)
check("B9 判定幂等（连续两次一致）", r1 == r2, (r1, r2))


# ---------------- C 按钮矩阵 ----------------
MAIN_KEYS = ["deploy", "start", "stop", "web", "admin", "enc_backup", "import_backup",
             "change_port", "copy_addr", "raw_log", "exit", "settings", "about"]


class FakeBtn:
    def __init__(self):
        self.state = tk.NORMAL

    def config(self, **kw):
        if "state" in kw:
            self.state = kw["state"]


class FakeApp:
    def __init__(self, status, deploy_state, busy=False):
        self._service_status = status
        self._deploy_state = deploy_state
        self._busy = busy
        self.btns = {k: FakeBtn() for k in MAIN_KEYS}

    def st(self, key):
        return self.btns[key].state


def matrix(status, deploy_state, busy=False):
    fa = FakeApp(status, deploy_state, busy)
    app.VaultwardenManagerApp.update_button_states(fa)
    return fa


fa = matrix("stopped", "deployed")
check("C1 已停止 + 已部署 → 一键部署禁用",
      fa.st("deploy") == tk.DISABLED, fa.st("deploy"))
check("C1b 已停止 + 已部署 → 启动服务仍可用（可启动已部署实例）",
      fa.st("start") == tk.NORMAL, fa.st("start"))
check("C1c 已停止 + 已部署 → 停止服务/打开 Web 保持禁用（原矩阵不变）",
      fa.st("stop") == tk.DISABLED and fa.st("web") == tk.DISABLED, (fa.st("stop"), fa.st("web")))

fa = matrix("running", "deployed")
check("C2 运行中 + 已部署 → 一键部署禁用、启动禁用、停止/打开可用",
      fa.st("deploy") == tk.DISABLED and fa.st("start") == tk.DISABLED
      and fa.st("stop") == tk.NORMAL and fa.st("web") == tk.NORMAL and fa.st("admin") == tk.NORMAL,
      (fa.st("deploy"), fa.st("start"), fa.st("stop"), fa.st("web")))

fa = matrix("foreign", "deployed")
check("C3 foreign 残留实例 + 已部署 → 一键部署禁用、停止可用",
      fa.st("deploy") == tk.DISABLED and fa.st("stop") == tk.NORMAL, (fa.st("deploy"), fa.st("stop")))

fa = matrix("stopped", "none")
check("C4 未部署 → 一键部署可点、启动可点", fa.st("deploy") == tk.NORMAL and fa.st("start") == tk.NORMAL,
      (fa.st("deploy"), fa.st("start")))

fa = matrix("stopped", "partial")
check("C5 部署不完整（网页版缺失）→ 一键部署可点以便补装", fa.st("deploy") == tk.NORMAL, fa.st("deploy"))

fa = matrix("running", "none")
check("C6 运行中 + 未判定已部署 → 一键部署仍禁用（v1.3.0 原逻辑不回归）",
      fa.st("deploy") == tk.DISABLED, fa.st("deploy"))

fa = matrix("stopped", "deployed", busy=True)
check("C7 忙碌 + 已部署 → 主按钮全禁用、退出/原始日志/设置/关于保持可用",
      all(fa.st(k) == tk.DISABLED for k in ["deploy", "start", "stop", "web", "admin",
                                            "enc_backup", "import_backup", "change_port", "copy_addr"])
      and fa.st("exit") == tk.NORMAL and fa.st("raw_log") == tk.NORMAL
      and fa.st("settings") == tk.NORMAL and fa.st("about") == tk.NORMAL)

fa = matrix("stopped", "deployed")
check("C8 已部署不影响备份/端口/复制地址按钮",
      all(fa.st(k) == tk.NORMAL for k in ["enc_backup", "import_backup", "change_port", "copy_addr"]),
      [fa.st(k) for k in ["enc_backup", "import_backup", "change_port", "copy_addr"]])

# ---------------- D 重启持久性 ----------------
cfg, _d = make_sandbox()
s_boot1 = service.get_deploy_state(cfg)[0]
fa1 = matrix("stopped", s_boot1)
s_boot2 = service.get_deploy_state(cfg)[0]
fa2 = matrix("stopped", s_boot2)
check("D1 两次「启动」均判定 deployed（不依赖会话内标志）",
      s_boot1 == "deployed" and s_boot2 == "deployed", (s_boot1, s_boot2))
check("D2 两次「启动」按钮均为禁用", fa1.st("deploy") == tk.DISABLED and fa2.st("deploy") == tk.DISABLED)


# ---------------- E on_deploy 入口二次拦截 ----------------
class FakeApp2:
    def __init__(self, cfg):
        self.cfg = cfg
        self._service_status = "stopped"
        self._deploy_state = "none"
        self._deploy_state_tip = ""
        self._busy = False
        self.msgs = []
        self.btns = {k: FakeBtn() for k in MAIN_KEYS}

    def set_msg(self, text, color=None):
        self.msgs.append(str(text))

    def update_button_states(self):
        app.VaultwardenManagerApp.update_button_states(self)

    def run_task(self, *a, **k):
        raise AssertionError("已部署时不应进入部署流程")


cfg, _d = make_sandbox()
f2 = FakeApp2(cfg)
app.VaultwardenManagerApp.on_deploy(f2)
check("E1 已部署点击一键部署 → 提示「已完成部署，无需重复部署」",
      bool(f2.msgs) and "已完成部署，无需重复部署" in f2.msgs[-1], f2.msgs)
check("E2 已部署点击一键部署 → 未启动部署任务（无副作用）", True)
check("E3 已部署点击一键部署 → 拦截后按钮被置为禁用", f2.btns["deploy"].state == tk.DISABLED)

cfg2, _d2 = make_sandbox(webvault=False)
f3 = FakeApp2(cfg2)
entered = {"flag": False}
f3._show_deploy_progress = lambda: None


def _run_task_stub(*a, **k):
    entered["flag"] = True


f3.run_task = _run_task_stub
f3.set_busy = lambda *a, **k: None
app.VaultwardenManagerApp.on_deploy(f3)
# partial 且服务未运行 → 不拦截，会进入部署流程（补装网页版）；此处校验未命中「已完成部署」分支
check("E4 partial 状态未被误拦截（仍可点击补装）",
      not any("已完成部署" in m for m in f3.msgs) and entered["flag"], (f3.msgs, entered))

# ---------------- F 源码静态断言 ----------------
src_app = (ROOT / "vwm" / "app.py").read_text(encoding="utf-8")
src_svc = (ROOT / "vwm" / "service.py").read_text(encoding="utf-8")
check("F1 update_button_states 含已部署禁用分支",
      'elif key == "deploy" and deployed:' in src_app)
check("F2 update_button_states 读取 _deploy_state",
      'deployed = getattr(self, "_deploy_state", "none") == "deployed"' in src_app)
check("F3 refresh_status 调用 _refresh_deploy_state",
      "def refresh_status" in src_app and "_refresh_deploy_state()" in src_app)
check("F4 状态栏展示「一键部署已锁定」", "已部署（一键部署已锁定）" in src_app)
check("F5 done 回调部署成功后即时重算并锁定",
      "self._refresh_deploy_state()" in src_app and "「一键部署」已锁定" in src_app)
check("F6 on_deploy 入口二次拦截文案", "已完成部署，无需重复部署；如需重新部署请先清理部署目录" in src_app)
check("F7 __init__ 初始化 _deploy_state（在 _build_ui 前）",
      src_app.index('self._deploy_state = "none"') < src_app.index("self._build_ui()"))
check("F8 service.get_deploy_state 三段式判定",
      all(s in src_svc for s in ['return "deployed"', 'return "partial"', 'return "none"']))
check("F9 service 判定含 ADMIN_TOKEN 与 web-vault 索引",
      "ADMIN_TOKEN" in src_svc and '"web-vault" / "index.html"' in src_svc)
check("F10 app 已导入 get_deploy_state", "get_deploy_state" in src_app.split("class VaultwardenManagerApp")[0])

# 真实本机部署目录状态（信息项）
try:
    from vwm.config import load_config
    real_cfg = load_config()
    real_state, real_tip = service.get_deploy_state(real_cfg)
    print("[INFO] 本机部署状态：%s — %s" % (real_state, real_tip))
except Exception as e:  # noqa: BLE001
    print("[INFO] 读取本机配置失败：%s" % e)

# ---------------- 清理 ----------------
for d in SANDBOXES:
    try:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
    except Exception:  # noqa: BLE001
        pass

print("\n==== v1.9.4 一键部署锁定验证：%d 项通过，%d 项失败 ====" % (PASS, len(FAIL)))
if FAIL:
    print("失败项：")
    for n in FAIL:
        print(" - %s" % n)
    sys.exit(1)
sys.exit(0)
