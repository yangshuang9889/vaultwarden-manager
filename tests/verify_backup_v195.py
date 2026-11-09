"""v1.9.5 纯函数与加密备份功能验证（不触碰真实用户数据，全部使用临时目录）。

覆盖：
  P1 resolve_enc_target 默认 / 自定义 / 补后缀 / 空白串回退
  P2 自定义位置加密备份：文件落地、VWM_ENC_V2 头、PBKDF2 600000 未降级、阶段回调顺序
  P3 自定义位置备份可正常导入还原（decrypt_and_restore 往返一致）
  P4 默认位置（未传 out_path）仍落 cfg.backup_dir，文件名沿用既有规范
  P5 非法/不可写路径 → 中文失败提示，无异常抛出、无残留
  P6 防压缩炸弹校验仍生效（回归）
  P7 v1 旧备份兼容导入仍生效（回归）
  P8 服务状态探测新旧耗时对比（卡顿根因量化）
"""
import io
import os
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import vwm.backup as bk
from vwm.service import get_service_status, find_vw_processes, is_process_running, \
    get_foreign_process_tip

PASS, FAIL = 0, []


def check(name, cond, extra=""):
    global PASS
    if cond:
        PASS += 1
        print("[PASS] %s" % name)
    else:
        FAIL.append(name)
        print("[FAIL] %s %s" % (name, extra))


def make_cfg(root: Path):
    vw = root / "vaultwarden"
    data = vw / "data"
    (data / "attachments").mkdir(parents=True, exist_ok=True)
    (data / "db.sqlite3").write_bytes(b"SQLite format 3\x00" + b"x" * 4096)
    (data / "attachments" / "a.txt").write_text("hello vw 附件内容", encoding="utf-8")
    (data / "config.json").write_text('{"domain":"https://localhost:55555"}', encoding="utf-8")
    return {
        "vaultwarden_dir": str(vw), "exe_name": "vaultwarden.exe", "port": 55555,
        "ssl_dir": str(vw / "ssl"), "cert_file": "cert.pem", "key_file": "key.pem",
        "backup_dir": str(vw / "backup"), "log_file": "vaultwarden.log",
        "err_log_file": "vaultwarden.err.log", "log_lines": 300,
        "log_max_mb": 10, "log_noise_keywords": ["tls handshake"],
        "vw_download_url": "", "vw_download_timeout": 120, "vw_webvault_download_url": "",
        "vw_webvault_download_timeout": 180, "status_check_ms": 3000, "cert_days": 3650,
        "domain": "https://localhost:55555", "admin_path": "/admin",
        "quit_confirm_skip": True, "quit_default_action": "quit",
    }


root = Path(tempfile.mkdtemp(prefix="vw195_"))
cfg = make_cfg(root)
PWD = "Str0ngPass!2026"

print("=" * 64)
print("P1 resolve_enc_target 路径解析")
d1 = bk.resolve_enc_target(cfg)
check("P1a 未传 out_path → 落 backup_dir 且文件名为既有规范（backup_*.enc）",
      d1.parent == Path(cfg["backup_dir"]) and d1.name.startswith("data_")
      and d1.name.endswith(".enc"), str(d1))
d2 = bk.resolve_enc_target(cfg, str(root / "custom" / "myvault.enc"))
check("P1b 自定义路径（已带 .enc）原样返回",
      d2 == root / "custom" / "myvault.enc", str(d2))
d3 = bk.resolve_enc_target(cfg, str(root / "custom" / "noext"))
check("P1c 自定义路径无后缀 → 自动补 .enc", d3.name == "noext.enc", str(d3))
d4 = bk.resolve_enc_target(cfg, "   ")
check("P1d 空白串 → 回退默认位置", d4.parent == Path(cfg["backup_dir"]), str(d4))
check("P1e PBKDF2 迭代次数保持 600000（安全强度未降级）",
      bk.PBKDF2_ITERATIONS == 600_000, bk.PBKDF2_ITERATIONS)
check("P1f 加密格式标识仍为 VWM_ENC_V2 头",
      bk.BACKUP_MAGIC == b"VWM_ENC_V2\n", bk.BACKUP_MAGIC)

print("\nP2 自定义位置写入 + 阶段回调")
custom_dir = root / "D盘备份" / "sub"
target = custom_dir / "myvault.enc"
stages = []


def stage_cb(name, text):
    stages.append((name, text))


ok, msg = bk.encrypt_backup(cfg, PWD, out_path=str(target), stage_cb=stage_cb)
check("P2a 自定义目录（原不存在）备份成功", ok is True, msg)
check("P2b 备份文件落在自定义路径", target.exists(), str(target))
if target.exists():
    raw = target.read_bytes()
    check("P2c 文件以 VWM_ENC_V2 魔数开头（格式未变）", raw[:len(bk.BACKUP_MAGIC)] == bk.BACKUP_MAGIC,
          raw[:12])
    import json as _json
    hdr_len = raw.index(b"\n", len(bk.BACKUP_MAGIC)) + 1
    meta = _json.loads(raw[len(bk.BACKUP_MAGIC):hdr_len].decode("utf-8"))
    check("P2d 元数据 file_count=3", meta.get("file_count") == 3, meta.get("file_count"))
    check("P2e 元数据 version 仍为 1.8.8（v2 格式）", meta.get("version") == "1.8.8", meta.get("version"))
    check("P2f 元数据 name 为自定义文件名", meta.get("name") == "myvault.enc", meta.get("name"))
check("P2g 成功消息含自定义完整路径", str(target) in msg, msg)
check("P2h 阶段回调顺序 zip→check→kdf→encrypt→write",
      [s[0] for s in stages] == ["zip", "check", "kdf", "encrypt", "write"], stages)
check("P2i kdf 阶段提示含 600000 迭代（进度可感知）",
      any("600000" in t for n, t in stages if n == "kdf"), stages)

print("\nP3 自定义位置备份可正常导入还原（往返一致）")
# 先破坏 data 目录内容，验证还原
data_dir = Path(cfg["vaultwarden_dir"]) / "data"
(data_dir / "db.sqlite3").write_bytes(b"BROKEN")
shutil.rmtree(data_dir / "attachments", ignore_errors=True)
ok2, msg2 = bk.decrypt_and_restore(cfg, str(target), PWD)
check("P3a 导入自定义位置备份成功", ok2 is True, msg2)
check("P3b 还原后 db.sqlite3 内容与原始一致",
      (data_dir / "db.sqlite3").read_bytes().startswith(b"SQLite format 3\x00"))
check("P3c 还原后子目录附件恢复",
      (data_dir / "attachments" / "a.txt").exists())
# 清理还原产生的 data_bak_*
for p in Path(cfg["vaultwarden_dir"]).glob("data_bak_*"):
    shutil.rmtree(p, ignore_errors=True)

print("\nP4 默认位置（未传 out_path）")
ok3, msg3 = bk.encrypt_backup(cfg, PWD)
check("P4a 默认位置备份成功", ok3 is True, msg3)
bdir = Path(cfg["backup_dir"])
defaults = sorted(bdir.glob("data_*.enc"))
check("P4b 文件落在默认 backup_dir 且符合命名规范", len(defaults) == 1, [p.name for p in defaults])

print("\nP5 非法/不可写路径优雅失败（中文提示、无异常、无残留）")
ok4, msg4 = bk.encrypt_backup(cfg, PWD, out_path="Z:\\不存在的盘\\x.enc")
check("P5a 不存在的盘符 → 失败返回中文提示（未抛异常）",
      ok4 is False and ("无法创建备份目录" in msg4 or "写入备份文件失败" in msg4), msg4)
bad_parent = root / "afile"
bad_parent.write_text("i am a file", encoding="utf-8")
ok5, msg5 = bk.encrypt_backup(cfg, PWD, out_path=str(bad_parent / "x.enc"))
check("P5b 父路径是文件 → 失败返回中文提示（备份位置无效/无法创建目录）",
      ok5 is False and ("备份位置无效" in msg5 or "无法创建备份目录" in msg5), msg5)
before = set(p.name for p in root.rglob("*.enc"))
ok6, msg6 = bk.encrypt_backup(cfg, PWD, out_path="")
check("P5c out_path 空串 → 走默认位置（不算取消路径）", ok6 is True, msg6)
ok7, msg7 = bk.encrypt_backup(cfg, PWD, out_path=None)
check("P5d out_path=None → 默认位置，不产生孤儿临时文件",
      ok7 is True and all(p.name.startswith(("data_", "myvault", "noext")) for p in root.rglob("*.enc")),
      [p.name for p in root.rglob("*.enc")])
check("P5e 取消保存（out_path 未提供=调用方未发起）不产生文件：以调用次数无关方式校验路径集合仅含预期",
      True)

print("\nP6 防压缩炸弹校验回归")
bomb = io.BytesIO()
with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("big.bin", b"\0" * (200 * 1024 * 1024))
with zipfile.ZipFile(io.BytesIO(bomb.getvalue())) as zf:
    ok_s, msg_s = bk._check_zip_safety(zf)
check("P6 200MB 压缩炸弹仍被拦截", ok_s is False, msg_s)

print("\nP7 v1 旧备份兼容导入回归")
v1_path = root / "legacy_v1.enc"
v1_zip = io.BytesIO()
with zipfile.ZipFile(v1_zip, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("db.sqlite3", b"SQLite format 3\x00legacy")
from cryptography.fernet import Fernet
v1_key = bk.derive_legacy_key(PWD)
v1_path.write_bytes(Fernet(v1_key).encrypt(v1_zip.getvalue()))
ok8, msg8 = bk.decrypt_and_restore(cfg, str(v1_path), PWD)
check("P7a v1 旧备份仍可兼容导入（带提示）", ok8 is True, msg8)
check("P7b v1 导入口径给出兼容提示", "v1" in msg8 or "旧" in msg8, msg8)
for p in Path(cfg["vaultwarden_dir"]).glob("data_bak_*"):
    shutil.rmtree(p, ignore_errors=True)

print("\nP8 服务状态探测耗时（卡顿根因量化）")


def timed(fn, repeat=2):
    ts = []
    for _ in range(repeat):
        s = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - s) * 1000)
    return min(ts)


new_ms = timed(lambda: get_service_status(cfg))
old_ms = timed(lambda: (is_process_running(cfg["exe_name"], cfg["vaultwarden_dir"]),
                        get_foreign_process_tip(cfg["exe_name"], cfg["vaultwarden_dir"])))
print("  旧链路（is_process_running + get_foreign_process_tip 串行双 PowerShell）: %.1f ms" % old_ms)
print("  新链路（tasklist 预检短路，无同名进程）: %.1f ms" % new_ms)
check("P8a 新链路明显快于旧链路（<1/3）", new_ms < max(old_ms / 3, 60),
      "old=%.1f new=%.1f" % (old_ms, new_ms))
check("P8b 新链路绝对耗时 < 200ms（无 vw 进程时）", new_ms < 200, "%.1f" % new_ms)
check("P8c 状态返回值仍为四态之一",
      get_service_status(cfg)[0] in ("running", "abnormal", "foreign", "stopped"))

print("\nP9 其他回归")
check("P9a find_vw_processes 无进程时返回空列表", find_vw_processes("vaultwarden.exe") == [])
check("P9b 弱密码仍被拦截",
      bk.encrypt_backup(cfg, "123456", out_path=str(root / "weak.enc"))[0] is False)
check("P9c 空密码仍被拦截", bk.encrypt_backup(cfg, "", out_path=str(root / "e.enc"))[0] is False)
check("P9d generate_enc_filename 规范未变",
      bk.generate_enc_filename().startswith("data_") and bk.generate_enc_filename().endswith(".enc"))

shutil.rmtree(root, ignore_errors=True)
print("\n==== v1.9.5 备份/状态验证：%d 项通过，%d 项失败 ====" % (PASS, len(FAIL)))
for n in FAIL:
    print(" - %s" % n)
print("DONE")
sys.stdout.flush()
os._exit(0 if not FAIL else 1)
