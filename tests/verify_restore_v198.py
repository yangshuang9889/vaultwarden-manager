"""v1.9.8 验证：服务运行状态记忆 + 下次启动自动恢复 + 设置开关。

覆盖：
  A. config 默认字段（last_exit_service_running=False / auto_restore_service=True）与旧配置自动补齐
  B. _record_exit_state 落盘正确
  C. _quit_app：退出前服务在运行 → 先记录 True 再停服务（顺序正确，标志落盘）
  D. _quit_app：退出前服务未运行 → 记录 False
  E. _maybe_auto_restore 五个分支（开关关闭 / 无标志 / 未部署 / 已部署自动启动成功 / 已在运行 / 启动失败保留标志）
  F. 设置对话框含新开关（源码级断言，避免弹窗阻塞）
"""
import io
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vwm import app as vwm_app
from vwm import config as vwm_config

PASS = []
FAIL = []


def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print(f"PASS {name}")
    else:
        FAIL.append((name, detail))
        print(f"FAIL {name} :: {detail}")


TMP = Path(tempfile.mkdtemp(prefix="vwm198r_"))
CFG_PATH = TMP / "config.json"
ORIG_CFG_PATH = vwm_config.CONFIG_PATH
vwm_config.CONFIG_PATH = CFG_PATH


def fresh_cfg(**over):
    cfg = vwm_config.build_default_config()
    cfg["vaultwarden_dir"] = str(TMP / "vaultwarden")
    cfg.update(over)
    CFG_PATH.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    return cfg


def read_saved():
    return json.loads(CFG_PATH.read_text(encoding="utf-8"))


class FakeApp:
    """只实现 _record_exit_state / _maybe_auto_restore / _quit_app 所需的最小接口。"""

    def __init__(self, cfg):
        self.cfg = cfg
        self.msgs = []
        self.refreshed = 0
        self._quitting = False
        self.buttons = 0
        self.tasks = []

    # 真实方法绑定（被测对象）
    _record_exit_state = vwm_app.VaultwardenManagerApp._record_exit_state
    _maybe_auto_restore = vwm_app.VaultwardenManagerApp._maybe_auto_restore
    _quit_app = vwm_app.VaultwardenManagerApp._quit_app
    _on_stop_result = vwm_app.VaultwardenManagerApp._on_stop_result

    # 桩
    def set_msg(self, text, color=None):
        self.msgs.append(text)

    def update_idletasks(self):
        pass

    def _safe_schedule(self, fn):
        fn()

    def run_task(self, fn, done=None, busy_text=None):
        self.tasks.append(busy_text)
        r = fn()
        if done:
            done(r)

    def refresh_log(self):
        self.refreshed += 1

    def _refresh_deploy_state(self):
        pass

    def update_button_states(self):
        self.buttons += 1

    def _final_cleanup(self):
        self.cleaned = True


try:
    # ---------------- A. 默认字段 ----------------
    d = vwm_config.build_default_config()
    check("A1 默认 last_exit_service_running=False", d.get("last_exit_service_running") is False,
          str(d.get("last_exit_service_running")))
    check("A2 默认 auto_restore_service=True", d.get("auto_restore_service") is True,
          str(d.get("auto_restore_service")))

    legacy = vwm_config.build_default_config()
    legacy.pop("last_exit_service_running", None)
    legacy.pop("auto_restore_service", None)
    legacy["port"] = 45678
    CFG_PATH.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
    loaded = vwm_config.load_config()
    check("A3 旧配置自动补齐 last_exit_service_running",
          loaded.get("last_exit_service_running") is False, str(loaded.get("last_exit_service_running")))
    check("A4 旧配置自动补齐 auto_restore_service",
          loaded.get("auto_restore_service") is True, str(loaded.get("auto_restore_service")))
    check("A5 补齐不影响既有 port", int(loaded.get("port")) == 45678, str(loaded.get("port")))

    # ---------------- B. _record_exit_state ----------------
    cfg = fresh_cfg()
    fa = FakeApp(cfg)
    fa._record_exit_state(True)
    check("B1 flag=True 已落盘", read_saved().get("last_exit_service_running") is True)
    check("B2 内存 cfg 同步", cfg.get("last_exit_service_running") is True)
    fa._record_exit_state(False)
    check("B3 flag=False 已落盘", read_saved().get("last_exit_service_running") is False)

    # ---------------- C. 退出前服务在运行 → 先记录再停服务 ----------------
    order = []
    cfg = fresh_cfg()
    fa = FakeApp(cfg)
    orig_find = vwm_app.find_vw_processes
    orig_stop = vwm_app.stop_service
    orig_record = FakeApp._record_exit_state

    def rec_spy(self, running):
        order.append(("record", running))
        return orig_record(self, running)

    try:
        FakeApp._record_exit_state = rec_spy
        vwm_app.find_vw_processes = lambda *a, **k: [{"pid": 999}]
        vwm_app.stop_service = lambda c: (order.append(("stop", None)) or (True, "服务已停止"))
        fa._quit_app()
        for _ in range(60):
            if order:
                break
            time.sleep(0.05)
        time.sleep(0.35)
        check("C1 记录先于停服务", order[:2] == [("record", True), ("stop", None)], str(order))
        check("C2 退出前运行 → 标志 True", read_saved().get("last_exit_service_running") is True)
        check("C3 退出仍停服务（v1.8.4 保留）", any(x[0] == "stop" for x in order), str(order))
        check("C4 停止成功走清理", getattr(fa, "cleaned", False) is True)
    finally:
        FakeApp._record_exit_state = orig_record
        vwm_app.find_vw_processes = orig_find
        vwm_app.stop_service = orig_stop

    # ---------------- D. 退出前服务未运行 → False ----------------
    cfg = fresh_cfg(last_exit_service_running=True)
    fa = FakeApp(cfg)
    orig_find = vwm_app.find_vw_processes
    orig_stop = vwm_app.stop_service
    try:
        vwm_app.find_vw_processes = lambda *a, **k: []
        vwm_app.stop_service = lambda c: (True, "服务已停止")
        fa._quit_app()
        for _ in range(40):
            if getattr(fa, "cleaned", False):
                break
            time.sleep(0.05)
        check("D1 无服务运行 → 标志 False", read_saved().get("last_exit_service_running") is False,
              str(read_saved().get("last_exit_service_running")))
        check("D2 无服务运行直接退出", getattr(fa, "cleaned", False) is True)
    finally:
        vwm_app.find_vw_processes = orig_find
        vwm_app.stop_service = orig_stop

    # ---------------- E. _maybe_auto_restore ----------------
    orig_gds = vwm_app.get_deploy_state
    orig_run = vwm_app.is_process_running
    orig_epa = vwm_app.ensure_port_available
    orig_start = vwm_app.start_service
    orig_log = vwm_app.append_manager_log
    logs = []
    vwm_app.append_manager_log = lambda *a, **k: logs.append(a[1:])

    # E1 开关关闭 → 不启动且清标志
    cfg = fresh_cfg(last_exit_service_running=True, auto_restore_service=False)
    fa = FakeApp(cfg)
    called = {"start": 0}
    vwm_app.ensure_port_available = lambda c: (True, "", False)
    vwm_app.start_service = lambda c: (called.__setitem__("start", called["start"] + 1) or (True, "已启动"))
    vwm_app.get_deploy_state = lambda c: ("deployed", "")
    vwm_app.is_process_running = lambda *a, **k: False
    fa._maybe_auto_restore()
    check("E1 开关关闭不启动", called["start"] == 0, str(called))
    check("E2 开关关闭清标志", read_saved().get("last_exit_service_running") is False)

    # E3 无标志 → 不启动
    cfg = fresh_cfg(last_exit_service_running=False, auto_restore_service=True)
    fa = FakeApp(cfg)
    called = {"start": 0}
    fa._maybe_auto_restore()
    check("E3 无标志不启动", called["start"] == 0 and not fa.tasks, str(called))
    check("E4 无标志无任务", fa.tasks == [], str(fa.tasks))

    # E5 未部署 → 跳过并清标志
    cfg = fresh_cfg(last_exit_service_running=True, auto_restore_service=True)
    fa = FakeApp(cfg)
    called = {"start": 0}
    vwm_app.get_deploy_state = lambda c: ("none", "未部署")
    fa._maybe_auto_restore()
    check("E5 未部署不启动", called["start"] == 0, str(called))
    check("E6 未部署清标志", read_saved().get("last_exit_service_running") is False)
    check("E7 未部署有中文提示", any("跳过自动启动" in m for m in fa.msgs), str(fa.msgs))

    # E8 已部署 + 服务未运行 → 自动启动并清标志
    cfg = fresh_cfg(last_exit_service_running=True, auto_restore_service=True,
                    port=47891, domain="https://localhost:47891")
    fa = FakeApp(cfg)
    called = {"start": 0, "port": None, "epa": 0}
    vwm_app.get_deploy_state = lambda c: ("deployed", "")
    vwm_app.is_process_running = lambda *a, **k: False

    def fake_epa(c):
        called["epa"] += 1
        return True, "", False

    def fake_start(c):
        called["start"] += 1
        called["port"] = int(c["port"])
        return True, "启动命令已发出：vaultwarden.exe"

    vwm_app.ensure_port_available = fake_epa
    vwm_app.start_service = fake_start
    vwm_app.is_process_running = lambda *a, **k: False
    fa._maybe_auto_restore()
    check("E8 已部署自动启动", called["start"] == 1, str(called))
    check("E9 启动前做端口检测", called["epa"] == 1, str(called))
    check("E10 使用配置端口启动", called["port"] == 47891, str(called["port"]))
    check("E11 启动成功清标志", read_saved().get("last_exit_service_running") is False)
    check("E12 有忙碌提示", any(t and "自动恢复" in t for t in fa.tasks), str(fa.tasks))
    check("E13 日志记录自动恢复", any("自动恢复服务" in str(x) for x in logs), str(logs))

    # E14 已部署但服务已在运行 → 不重复启动，清标志
    cfg = fresh_cfg(last_exit_service_running=True, auto_restore_service=True)
    fa = FakeApp(cfg)
    called = {"start": 0}
    vwm_app.is_process_running = lambda *a, **k: True
    vwm_app.start_service = lambda c: (called.__setitem__("start", called["start"] + 1) or (True, "已启动"))
    fa._maybe_auto_restore()
    check("E14 已在运行不重复启动", called["start"] == 0, str(called))
    check("E15 已在运行清标志", read_saved().get("last_exit_service_running") is False)

    # E16 启动失败 → 保留标志（下次再试）
    cfg = fresh_cfg(last_exit_service_running=True, auto_restore_service=True)
    fa = FakeApp(cfg)
    vwm_app.is_process_running = lambda *a, **k: False
    vwm_app.ensure_port_available = lambda c: (True, "", False)
    vwm_app.start_service = lambda c: (False, "启动失败：未找到 vaultwarden.exe")
    fa._maybe_auto_restore()
    check("E16 启动失败保留标志", read_saved().get("last_exit_service_running") is True,
          str(read_saved().get("last_exit_service_running")))
    check("E17 失败提示为中文", any("启动失败" in str(x) for x in logs), str(logs))

    # E18 端口切换 + 自动启动 → 消息含切换说明
    cfg = fresh_cfg(last_exit_service_running=True, auto_restore_service=True, port=44444)
    fa = FakeApp(cfg)
    vwm_app.is_process_running = lambda *a, **k: False
    vwm_app.ensure_port_available = lambda c: (True, "端口 44444 被占用，已自动切换到 52333", True)
    vwm_app.start_service = lambda c: (True, "启动命令已发出")
    fa._maybe_auto_restore()
    check("E18 自动恢复消息含端口切换", any("已自动切换到 52333" in str(x) for x in logs), str(logs))

    vwm_app.get_deploy_state = orig_gds
    vwm_app.is_process_running = orig_run
    vwm_app.ensure_port_available = orig_epa
    vwm_app.start_service = orig_start
    vwm_app.append_manager_log = orig_log

    # ---------------- F. 设置开关（源码断言，避免弹窗阻塞） ----------------
    ui_src = io.open(Path(__file__).resolve().parent.parent / "vwm" / "ui.py", encoding="utf-8").read()
    check("F1 ui 含新勾选项文案", "退出后下次启动自动恢复服务" in ui_src)
    check("F2 ui 绑定 auto_restore_service 变量", 'cfg.get("auto_restore_service", True)' in ui_src)
    check("F3 ui save 写回开关", 'cfg["auto_restore_service"] = bool(restore_var.get())' in ui_src)
    check("F4 ui 关闭开关时清标志",
          'cfg["last_exit_service_running"] = False' in ui_src)
    check("F5 版本号已升级 v1.9.8", 'VERSION = "v1.9.8"' in ui_src, "")
finally:
    vwm_config.CONFIG_PATH = ORIG_CFG_PATH

print("\n==== 汇总 ====")
print(f"PASS {len(PASS)} / FAIL {len(FAIL)} / TOTAL {len(PASS) + len(FAIL)}")
if FAIL:
    for name, detail in FAIL:
        print(f"  - {name}: {detail}")
    sys.exit(1)
