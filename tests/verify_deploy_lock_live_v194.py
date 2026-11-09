"""verify_deploy_lock_live_v194.py — v1.9.4 真机 GUI 冒烟（真实 tkinter 实例）

只打桩三类与本次目标无关的外部副作用：系统托盘图标（避免残留托盘）、日志读取、
服务状态查询（避免每次起 PowerShell 约 2s）。其余全部走真实 VaultwardenManagerApp。

场景：
  L1 已部署（exe + .env(ADMIN_TOKEN) + web-vault/index.html 齐全）→ 一键部署按钮 disabled
  L2 已部署状态栏显示「已部署（一键部署已锁定）」
  L3 已部署点击「一键部署」→ 消息提示锁定原因、不进入忙碌态（无副作用）
  L4 未部署（部署目录不存在）→ 一键部署按钮 normal、状态栏显示「未部署」
  L5 部署不完整（有 exe/.env 但无网页版）→ 一键部署按钮 normal（可补装）
  L6 模拟程序重启（销毁窗口后重新构造 App）→ 仍判定已部署、按钮仍 disabled
  L7 重启后再次点击禁用按钮 → 仍然只提示、无副作用
"""
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


from vwm import app as app_mod  # noqa: E402


# ---- 打桩：与本次目标无关的外部副作用 ----
def _noop_tray(self):
    self._tray_icon = None
    self._tray_active = False
    self._tray_ready_at = 0


app_mod.VaultwardenManagerApp._create_tray_icon = _noop_tray
app_mod.VaultwardenManagerApp.refresh_log = lambda self: None
app_mod.VaultwardenManagerApp._periodic_status = lambda self: None
app_mod.get_service_status = lambda cfg: ("stopped", "服务未运行", "#2b8a3e")


def make_deploy_dir(with_exe=True, with_env=True, with_web=True, size=2 * 1024 * 1024):
    d = Path(tempfile.mkdtemp(prefix="vw194live_"))
    if with_exe:
        with open(d / "vaultwarden.exe", "wb") as fp:
            fp.write(b"\0" * size)
    if with_env:
        (d / ".env").write_text("ROCKET_PORT=44444\nADMIN_TOKEN=live_token_abc\n", encoding="utf-8")
    if with_web:
        (d / "web-vault").mkdir(parents=True, exist_ok=True)
        (d / "web-vault" / "index.html").write_text("<html></html>", encoding="utf-8")
    return d


def make_cfg(d):
    return {
        "vaultwarden_dir": str(d), "exe_name": "vaultwarden.exe", "port": 44444,
        "ssl_dir": str(d / "ssl"), "cert_file": "cert.pem", "key_file": "key.pem",
        "backup_dir": str(d / "backup"), "log_file": "vaultwarden.log",
        "err_log_file": "vaultwarden.err.log", "log_lines": 300, "log_max_mb": 10,
        "log_noise_keywords": ["tls handshake"], "vw_download_url": "",
        "vw_download_timeout": 120, "vw_webvault_download_url": "",
        "vw_webvault_download_timeout": 180, "status_check_ms": 3000, "cert_days": 3650,
        "domain": "https://localhost:44444", "admin_path": "/admin",
        "quit_confirm_skip": True, "quit_default_action": "quit",
    }


def msg_text(a):
    try:
        return str(a.msg_label.cget("text"))
    except Exception:  # noqa: BLE001
        return ""


def sub_text(a):
    try:
        return str(a.status_sub.cget("text"))
    except Exception:  # noqa: BLE001
        return ""


dir_deployed = make_deploy_dir()
dir_empty_ok = make_deploy_dir(with_exe=True, with_env=True, with_web=False)
dir_missing = Path(tempfile.mkdtemp(prefix="vw194none_")) / "not_exist"

gui = app_mod.VaultwardenManagerApp(make_cfg(dir_deployed))
gui.update()

# L1 / L2
check("L1 已部署 → 一键部署按钮 disabled",
      str(gui.btns["deploy"].cget("state")) == "disabled",
      gui.btns["deploy"].cget("state"))
check("L1b 已部署 → 启动服务按钮仍 normal（可启动已部署实例）",
      str(gui.btns["start"].cget("state")) == "normal",
      gui.btns["start"].cget("state"))
check("L2 已部署 → 状态栏含「已部署（一键部署已锁定）」",
      "已部署（一键部署已锁定）" in sub_text(gui), sub_text(gui))

# L3：点击禁用按钮无副作用
busy_before = gui._busy
gui.on_deploy()
gui.update()
check("L3 已部署点击一键部署 → 提示「已完成部署，无需重复部署」",
      "已完成部署，无需重复部署" in msg_text(gui), msg_text(gui))
check("L3b 已部署点击一键部署 → 未进入忙碌态（无部署副作用）",
      gui._busy is False and busy_before is False, gui._busy)
check("L3c 提示含重新部署指引（清理部署目录）",
      "清理部署目录" in msg_text(gui), msg_text(gui))
gui.destroy()

# L4：未部署
gui = app_mod.VaultwardenManagerApp(make_cfg(dir_missing))
gui.update()
check("L4 未部署 → 一键部署按钮 normal",
      str(gui.btns["deploy"].cget("state")) == "normal",
      gui.btns["deploy"].cget("state"))
check("L4b 未部署 → 状态栏含「未部署」", "未部署" in sub_text(gui), sub_text(gui))
gui.destroy()

# L5：部署不完整（缺网页版）
gui = app_mod.VaultwardenManagerApp(make_cfg(dir_empty_ok))
gui.update()
check("L5 缺网页版 → 一键部署按钮 normal（可补装）",
      str(gui.btns["deploy"].cget("state")) == "normal",
      gui.btns["deploy"].cget("state"))
check("L5b 缺网页版 → 状态栏含「部署部分就绪」", "部署部分就绪" in sub_text(gui), sub_text(gui))
gui.destroy()

# L6 / L7：模拟重启
gui = app_mod.VaultwardenManagerApp(make_cfg(dir_deployed))
gui.update()
check("L6 模拟重启后 → 仍判定已部署、按钮仍 disabled",
      str(gui.btns["deploy"].cget("state")) == "disabled"
      and "已部署（一键部署已锁定）" in sub_text(gui),
      (gui.btns["deploy"].cget("state"), sub_text(gui)))
gui.on_deploy()
gui.update()
check("L7 重启后点击禁用按钮 → 仍只提示、无副作用",
      "已完成部署，无需重复部署" in msg_text(gui) and gui._busy is False,
      (msg_text(gui), gui._busy))
gui.destroy()

for d in [dir_deployed, dir_empty_ok]:
    shutil.rmtree(d, ignore_errors=True)
try:
    shutil.rmtree(dir_missing.parent, ignore_errors=True)
except Exception:  # noqa: BLE001
    pass

print("\n==== v1.9.4 真机 GUI 冒烟：%d 项通过，%d 项失败 ====" % (PASS, len(FAIL)))
if FAIL:
    for n in FAIL:
        print(" - %s" % n)
print("DONE")
sys.stdout.flush()
import os  # noqa: E402
os._exit(0 if not FAIL else 1)
