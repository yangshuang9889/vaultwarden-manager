"""v1.9.5 真机 GUI 冒烟（真实 Tk mainloop 事件驱动）：加密备份位置选择 + 卡顿优化。

覆盖：
  G1 取消保存对话框 → 优雅中止、无文件、不进入忙碌态
  G2 选择自定义位置 → 「正在加密备份…」即时提示 + 后台加密
  G3 加密过程中主线程保持响应（心跳最大间隔小）+ 阶段进度可见
  G4 完成后文件落地、提示含路径、忙碌态复位
  G5 refresh_status_async 单飞防重入 + 主线程零阻塞 + 结果回填
  G6 按钮矩阵联动 / 加密备份按钮常可用
  G7 GUI 保存的备份可导入还原
"""
import os
import shutil
import sys
import tempfile
import time
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
import vwm.backup as bk  # noqa: E402

app_mod.VaultwardenManagerApp._create_tray_icon = lambda self: (
    setattr(self, "_tray_icon", None), setattr(self, "_tray_active", False),
    setattr(self, "_tray_ready_at", 0)) and None
app_mod.VaultwardenManagerApp.refresh_log = lambda self: None
app_mod.VaultwardenManagerApp._periodic_status = lambda self: None
app_mod.get_service_status = lambda cfg: ("stopped", "服务未运行", "#2b8a3e")

root = Path(tempfile.mkdtemp(prefix="vw195gui_"))
vw = root / "vaultwarden"
data = vw / "data"
(data / "attachments").mkdir(parents=True, exist_ok=True)
(data / "db.sqlite3").write_bytes(b"SQLite format 3\x00" + os.urandom(600000))
(data / "attachments" / "a.bin").write_bytes(os.urandom(400000))
cfg = {
    "vaultwarden_dir": str(vw), "exe_name": "vaultwarden.exe", "port": 55555,
    "ssl_dir": str(vw / "ssl"), "cert_file": "cert.pem", "key_file": "key.pem",
    "backup_dir": str(vw / "backup"), "log_file": "vaultwarden.log",
    "err_log_file": "vaultwarden.err.log", "log_lines": 300, "log_max_mb": 10,
    "log_noise_keywords": ["tls handshake"], "vw_download_url": "",
    "vw_download_timeout": 120, "vw_webvault_download_url": "",
    "vw_webvault_download_timeout": 180, "status_check_ms": 3000, "cert_days": 3650,
    "domain": "https://localhost:55555", "admin_path": "/admin",
    "quit_confirm_skip": True, "quit_default_action": "quit",
}
PWD = "Str0ngPass!2026"
rack = {"dlg_path": "", "dlg_calls": [], "enc_calls": [], "heartbeat_gap": 0.0,
        "stage_texts": []}

app_mod.prompt_password = lambda parent, title="请输入密码": PWD


def fake_asksaveasfilename(**kw):
    rack["dlg_calls"].append(kw)
    return rack["dlg_path"]


app_mod.filedialog.asksaveasfilename = fake_asksaveasfilename
real_encrypt = bk.encrypt_backup


def spy_encrypt(cfg_, pw, out_path=None, stage_cb=None):
    rack["enc_calls"].append({"out_path": out_path, "pw": pw, "has_cb": stage_cb is not None})
    return real_encrypt(cfg_, pw, out_path=out_path, stage_cb=stage_cb)


app_mod.encrypt_backup = spy_encrypt

gui = app_mod.VaultwardenManagerApp(cfg)
custom = root / "我的备份" / "异地" / "manual_v195.enc"


def msg_text():
    try:
        return str(gui.msg_label.cget("text"))
    except Exception:  # noqa: BLE001
        return ""


steps = []


def step(fn):
    steps.append(fn)
    return fn


def wait_until(cond, timeout, done, label):
    """轮询等待 cond 成立（主线程 after 驱动），记录心跳间隔。"""
    t0 = time.time()
    last = t0

    def tick():
        nonlocal last
        now = time.time()
        rack["heartbeat_gap"] = max(rack["heartbeat_gap"], now - last)
        last = now
        if cond():
            done()
        elif now - t0 > timeout:
            print("  [warn] 等待超时：%s" % label)
            done()
        else:
            gui.after(30, tick)

    gui.after(30, tick)


# ---------------- G1 取消保存 ----------------
@step
def g1():
    rack["dlg_path"] = ""
    enc_before = len(rack["enc_calls"])
    files_before = set(vw.rglob("*.enc"))
    gui.on_enc_backup()
    check("G1a 取消保存 → 提示「已取消加密备份（未选择保存位置）」",
          "已取消加密备份（未选择保存位置）" in msg_text(), msg_text())
    check("G1b 取消保存 → 未调用加密、无文件、未进入忙碌态",
          len(rack["enc_calls"]) == enc_before and set(vw.rglob("*.enc")) == files_before
          and gui._busy is False, (len(rack["enc_calls"]), gui._busy))
    kw = rack["dlg_calls"][-1]
    check("G1c 对话框默认定位既有备份目录 + 既有文件名规范",
          Path(kw["initialdir"]) == Path(cfg["backup_dir"])
          and str(kw["initialfile"]).startswith("data_")
          and str(kw["initialfile"]).endswith(".enc"), kw)
    check("G1d 默认扩展名 .enc（沿用既有格式）", kw.get("defaultextension") == ".enc", kw)
    gui.after(50, g2)


# ---------------- G2/G3 自定义位置加密 ----------------
@step
def g2():
    rack["dlg_path"] = str(custom)
    rack["heartbeat_gap"] = 0.0
    gui.on_enc_backup()
    check("G2a 立即给出「正在加密备份…」提示（非泛化文案）",
          "正在加密备份" in msg_text(), msg_text())
    check("G2b 进入后台忙碌态（_busy=True）", gui._busy is True, gui._busy)
    check("G2c 加密函数收到 out_path 与 stage_cb",
          rack["enc_calls"] and rack["enc_calls"][-1]["out_path"] == str(custom)
          and rack["enc_calls"][-1]["has_cb"] is True, rack["enc_calls"][-1])

    def sample():
        if gui._busy and not custom.exists():
            t = msg_text()
            if t and (not rack["stage_texts"] or rack["stage_texts"][-1] != t):
                rack["stage_texts"].append(t)
            gui.after(20, sample)

    gui.after(20, sample)
    wait_until(lambda: not gui._busy and custom.exists(), 20, g3, "加密完成")


@step
def g3():
    check("G3a 加密期间主线程心跳最大间隔 < 0.2s（界面不冻结）",
          rack["heartbeat_gap"] < 0.2, "%.3fs" % rack["heartbeat_gap"])
    check("G3b 期间状态栏出现阶段进度文案（非仅泛化提示）",
          any(("正在" in t or "校验" in t or "加密" in t) for t in rack["stage_texts"]),
          rack["stage_texts"])
    check("G3c 自定义路径（多级新目录）备份文件已落地", custom.exists(), str(custom))
    check("G3d 文件为 VWM_ENC_V2 格式",
          custom.exists() and custom.read_bytes().startswith(b"VWM_ENC_V2\n"))
    check("G3e 完成后提示成功且含完整路径、忙碌态复位",
          gui._busy is False and "加密备份完成" in msg_text() and str(custom) in msg_text(),
          (gui._busy, msg_text()))
    gui.after(50, g5)


# ---------------- G5 状态探测异步 ----------------
probe = {"calls": 0}


@step
def g5():
    def slow_probe(cfg_):
        probe["calls"] += 1
        time.sleep(1.2)
        return ("running", "服务运行中（探针）", "#2b8a3e")

    app_mod.get_service_status = slow_probe
    gui._status_probing = False
    t0 = time.perf_counter()
    first = gui.refresh_status_async()
    ms = (time.perf_counter() - t0) * 1000
    second = gui.refresh_status_async()
    check("G5a refresh_status_async 立即返回（主线程零阻塞 <50ms）", ms < 50, "%.1fms" % ms)
    check("G5b 在途重复调用被单飞拦截", first is True and second is False, (first, second))
    wait_until(lambda: probe["calls"] == 1 and gui._status_probing is False, 5, g5b, "探测回填")


@step
def g5b():
    check("G5c 探测只真正执行一次（无重复 PowerShell）", probe["calls"] == 1, probe["calls"])
    check("G5d 结果经主线程回填状态栏",
          "服务运行中（探针）" in str(gui.status_label.cget("text")),
          gui.status_label.cget("text"))
    check("G5e 回填后单飞标志复位", gui._status_probing is False, gui._status_probing)
    gui.after(50, g6)


# ---------------- G6 按钮矩阵 ----------------
@step
def g6():
    gui._apply_status(("stopped", "服务已停止 · 端口 55555", "#c92a2a"))
    check("G6a stopped → 启动 normal / 停止 disabled",
          str(gui.btns["start"].cget("state")) == "normal"
          and str(gui.btns["stop"].cget("state")) == "disabled",
          (gui.btns["start"].cget("state"), gui.btns["stop"].cget("state")))
    gui._apply_status(("running", "服务运行中", "#2b8a3e"))
    check("G6b running → 停止 normal / 启动 disabled",
          str(gui.btns["stop"].cget("state")) == "normal"
          and str(gui.btns["start"].cget("state")) == "disabled",
          (gui.btns["stop"].cget("state"), gui.btns["start"].cget("state")))
    check("G6c 加密备份按钮始终 normal",
          str(gui.btns["enc_backup"].cget("state")) == "normal",
          gui.btns["enc_backup"].cget("state"))
    gui.after(50, g7)


# ---------------- G7 还原回归 ----------------
@step
def g7():
    before = (data / "db.sqlite3").read_bytes()
    (data / "db.sqlite3").write_bytes(b"BROKEN")
    ok, m = bk.decrypt_and_restore(cfg, str(custom), PWD)
    check("G7 GUI 保存的备份可正常导入还原（内容逐字节一致）",
          ok is True and (data / "db.sqlite3").read_bytes() == before, m)
    gui.after(50, finish)


@step
def finish():
    gui.destroy()


# 启动事件链
gui.after(100, g1)
gui.mainloop()

shutil.rmtree(root, ignore_errors=True)
for p in Path(cfg["vaultwarden_dir"]).glob("data_bak_*"):
    shutil.rmtree(p, ignore_errors=True)

print("\n==== v1.9.5 真机 GUI 冒烟：%d 项通过，%d 项失败 ====" % (PASS, len(FAIL)))
for n in FAIL:
    print(" - %s" % n)
print("DONE")
sys.stdout.flush()
os._exit(0 if not FAIL else 1)
