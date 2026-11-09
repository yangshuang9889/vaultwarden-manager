# -*- coding: utf-8 -*-
"""
加密备份模块（v1.8.8，安全加固版）
职责：data 目录 zip 压缩 + Fernet 加密备份（PBKDF2-HMAC-SHA256 高迭代密钥派生、
      随机盐、弱密码校验、完整性元数据校验），.enc 解密恢复（含 zip-slip/路径穿越
      防护、压缩炸弹防护、格式标识与元数据校验、失败回滚、密码不落痕）。
格式：v2（VWM_ENC_V2 明文头 + Fernet token），向后兼容 v1 旧备份（无头 sha256 派生）。
依赖：仅标准库 + 包级 CRYPTO_OK。
"""
import base64
import hashlib
import io
import json
import os
import secrets
import shutil
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

from . import CRYPTO_OK

# cryptography 可选依赖：缺失时 CRYPTO_OK=False，相关功能返回不可用提示
if CRYPTO_OK:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# ---------- 备份格式与安全常量 ----------
BACKUP_MAGIC = b"VWM_ENC_V2\n"
BACKUP_FORMAT = 2
BACKUP_TOOL = "vaultwarden-manager"
PBKDF2_ITERATIONS = 600_000              # PBKDF2-HMAC-SHA256 迭代次数（OWASP 2023 推荐）
SALT_BYTES = 16                          # 随机盐长度
MIN_PASSWORD_LEN = 8                     # 弱密码最小长度
MAX_ZIP_ENTRIES = 50_000                 # 压缩炸弹防护：条目数上限
MAX_TOTAL_UNCOMPRESSED = 2 * 1024 ** 3   # 压缩炸弹防护：解压总大小上限 2 GiB
MAX_COMPRESSION_RATIO = 1000             # 压缩炸弹防护：单条目压缩比上限

def derive_legacy_key(password: str) -> bytes:
    """v1 旧备份兼容：由用户密码派生 Fernet 密钥（SHA-256 摘要 -> urlsafe base64）。
    仅用于导入旧版备份；新版备份一律使用 PBKDF2 高迭代派生。"""
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)

def derive_fernet_key(password: str, salt: bytes) -> bytes:
    """由用户密码派生 Fernet 密钥：PBKDF2-HMAC-SHA256 高迭代 + 随机盐，抗暴力/字典攻击。
    派生完成后立即释放密码字节缓冲区，避免明文密码驻留。"""
    pw = password.encode("utf-8")
    try:
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                         iterations=PBKDF2_ITERATIONS)
        key = kdf.derive(pw)
    finally:
        pw = None
    return base64.urlsafe_b64encode(key)

def validate_password_strength(password: str) -> tuple:
    """弱密码校验：至少 8 位，且包含字母、数字、符号中至少两类。返回 (ok, 中文消息)。"""
    if len(password) < MIN_PASSWORD_LEN:
        return False, f"密码强度不足：至少 {MIN_PASSWORD_LEN} 位（当前 {len(password)} 位），已取消加密备份"
    kinds = 0
    if any(c.islower() for c in password):
        kinds += 1
    if any(c.isupper() for c in password):
        kinds += 1
    if any(c.isdigit() for c in password):
        kinds += 1
    if any(not c.isalnum() for c in password):
        kinds += 1
    if kinds < 2:
        return False, "密码强度不足：需包含字母、数字、符号中至少两类，已取消加密备份"
    return True, ""

def generate_enc_filename() -> str:
    """生成防覆盖备份文件名：data_<YYYYMMDD_HHMMSS>_<4位随机hex>.enc。"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rand = secrets.token_hex(2)
    return f"data_{ts}_{rand}.enc"

def _build_header(meta: dict) -> bytes:
    """构造 v2 明文头部：魔数行 + JSON 元数据行。头部仅含非敏感元数据，不含密码。"""
    return BACKUP_MAGIC + json.dumps(meta, ensure_ascii=False).encode("utf-8") + b"\n"

def _parse_header(raw: bytes) -> tuple:
    """解析 v2 明文头部。返回 (meta, token, ok, 中文消息)。"""
    try:
        body = raw[len(BACKUP_MAGIC):]
        line, sep, token = body.partition(b"\n")
        if not sep:
            return {}, b"", False, "备份格式无法识别（头部损坏），已取消恢复"
        meta = json.loads(line.decode("utf-8"))
        if not isinstance(meta, dict) or "salt" not in meta or "zip_sha256" not in meta:
            return {}, b"", False, "备份元数据不完整，已取消恢复"
        return meta, token, True, ""
    except Exception:
        return {}, b"", False, "备份格式无法识别（元数据解析失败），已取消恢复"

def _check_zip_safety(zf) -> tuple:
    """zip-slip / 路径穿越 / 压缩炸弹 / 符号链接防护。返回 (ok, 中文消息)。"""
    infos = zf.infolist()
    if len(infos) > MAX_ZIP_ENTRIES:
        return False, f"备份包含 {len(infos)} 个条目，超过上限 {MAX_ZIP_ENTRIES}，已中止"
    total = 0
    for info in infos:
        name = info.filename
        norm = name.replace("\\", "/")
        if not norm:
            return False, "备份包含空路径条目，已中止"
        if norm.startswith("/"):
            return False, f"备份包含非法绝对路径：{name}"
        parts = norm.split("/")
        # zipfile 标准目录条目以尾部斜杠结尾（如 "sub/"），允许该尾部空段；
        # 其余空段（如 a//b）、"."、穿越段 ".." 一律拒绝
        tail_dir = parts[-1] == "" and len(parts) > 1
        check_parts = parts[:-1] if tail_dir else parts
        if any(p in ("", ".", "..") for p in check_parts):
            return False, f"备份包含非法路径（穿越/重复分隔）：{name}"
        if ":" in parts[0]:
            return False, f"备份包含盘符路径：{name}"
        mode = (info.external_attr >> 16) & 0o170000
        if mode == 0o120000:
            return False, f"备份包含符号链接条目，已中止：{name}"
        if info.file_size < 0:
            return False, f"备份条目大小异常：{name}"
        total += info.file_size
    if total > MAX_TOTAL_UNCOMPRESSED:
        return False, (f"备份解压总大小超过上限（{total / 1024 / 1024:.0f} MB > "
                       f"{MAX_TOTAL_UNCOMPRESSED / 1024 / 1024:.0f} MB），疑似压缩炸弹，已中止")
    for info in infos:
        if info.compress_size > 0 and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
            return False, f"备份压缩比异常（疑似压缩炸弹）：{info.filename}"
    return True, ""

def _extract_zip_safely(zf, target_dir: Path) -> tuple:
    """逐条目安全解压：每个条目解析后校验最终路径在目标目录内，拒绝越界。返回 (ok, 中文消息)。"""
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_res = str(target_dir.resolve())
    for info in zf.infolist():
        norm = info.filename.replace("\\", "/")
        rel = PurePosixPath(norm)
        dest = (target_dir / rel).resolve()
        try:
            common = os.path.commonpath([target_res, str(dest)])
        except ValueError:
            return False, f"备份条目越界：{info.filename}"
        if common != target_res:
            return False, f"备份条目越界：{info.filename}"
        if info.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            with zf.open(info) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out, length=1024 * 1024)
        except Exception as e:
            return False, f"解压条目失败：{info.filename}（{e}）"
    return True, ""

def resolve_enc_target(cfg: dict, out_path: str | None = None) -> Path:
    """v1.9.5：解析加密备份的最终落盘路径。

    out_path 为空/空白 → 沿用既有默认位置（backup_dir + generate_enc_filename()），
    保证不改默认行为；否则使用用户通过「选择备份位置」对话框指定的路径，
    若未带 .enc 后缀则自动补全（沿用既有加密备份扩展名）。纯函数，不做 IO。
    """
    if out_path and str(out_path).strip():
        p = Path(str(out_path).strip())
        if p.suffix.lower() != ".enc":
            p = p.with_name(p.name + ".enc")
        return p
    return Path(cfg["backup_dir"]) / generate_enc_filename()

def encrypt_backup(cfg: dict, password: str, out_path: str | None = None,
                   stage_cb=None) -> tuple:
    """将 data 目录压缩为 zip，经 PBKDF2 高迭代派生密钥 + Fernet 加密为 v2 .enc。

    存放到默认备份目录，或 out_path 指定的自定义位置（v1.9.5 选择备份位置）。
    含弱密码校验、压缩包自身安全检查、随机盐、完整性元数据；全程不落盘明文密码。

    v1.9.5：新增 stage_cb(stage, text) 阶段回调（在工作线程内被调用，供 UI 显示
    压缩/派生/加密/写入各阶段进度），加解密格式 VWM_ENC_V2 与 PBKDF2 迭代
    次数（600000）完全不变，仅优化反馈与保存位置。
    """
    def _stage(name: str, text: str):
        if stage_cb is None:
            return
        try:
            stage_cb(name, text)
        except Exception:
            pass  # 进度回调异常不得影响备份

    if not CRYPTO_OK:
        return False, "缺少 cryptography 库，请执行 pip install cryptography 后重试"
    if not password:
        return False, "密码不能为空，已取消加密备份"
    ok, msg = validate_password_strength(password)
    if not ok:
        return False, msg
    vw_dir = Path(cfg["vaultwarden_dir"])
    data_dir = vw_dir / "data"
    if not data_dir.exists():
        return False, f"data 目录不存在：{data_dir}"
    enc_path = resolve_enc_target(cfg, out_path)
    # v1.9.5：自定义位置时目录可能不存在或无写权限，此处给出中文提示，不抛出异常
    try:
        if enc_path.parent.exists() and not enc_path.parent.is_dir():
            return False, f"备份位置无效：{enc_path.parent} 不是目录。请更换备份位置"
        if not enc_path.parent.exists():
            enc_path.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        return False, f"无法创建备份目录：{enc_path.parent}（{e}）。请更换备份位置或检查权限"
    if enc_path.exists() and enc_path.is_dir():
        return False, f"备份位置无效：{enc_path} 是目录。请指定文件名"
    if enc_path.exists():
        try:
            if not os.access(str(enc_path), os.W_OK):
                return False, f"目标文件不可写：{enc_path}。请更换备份位置或检查权限"
        except Exception:
            pass

    _stage("zip", "正在压缩 data 目录…")
    buf = io.BytesIO()
    files = [f for f in data_dir.rglob("*") if f.is_file()]
    try:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                try:
                    zf.write(f, arcname=f.relative_to(data_dir).as_posix())
                except (OSError, PermissionError):
                    continue
        zip_bytes = buf.getvalue()
    except Exception as e:
        return False, f"压缩 data 失败：{e}"

    # 防御性检查：本工具生成的 zip 不应触发安全红线
    _stage("check", "正在校验备份内容安全…")
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            ok_s, msg_s = _check_zip_safety(zf)
            if not ok_s:
                return False, f"备份内容安全校验未通过：{msg_s}"
    except Exception as e:
        return False, f"备份内容校验失败：{e}"

    salt = secrets.token_bytes(SALT_BYTES)
    _stage("kdf", f"正在派生密钥（PBKDF2-HMAC-SHA256 {PBKDF2_ITERATIONS} 次迭代）…")
    key = derive_fernet_key(password, salt)
    _stage("encrypt", "正在加密备份包…")
    token = Fernet(key).encrypt(zip_bytes)
    header = _build_header({
        "tool": BACKUP_TOOL,
        "format": BACKUP_FORMAT,
        "version": "1.8.8",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "salt": base64.b64encode(salt).decode("ascii"),
        "zip_sha256": hashlib.sha256(zip_bytes).hexdigest(),
        "file_count": len(files),
        "name": enc_path.name,
    })
    _stage("write", "正在写入备份文件…")
    try:
        enc_path.write_bytes(header + token)
    except (PermissionError, OSError) as e:
        return False, f"写入备份文件失败：{enc_path}（{e}）。请更换备份位置或检查权限"
    except Exception as e:
        return False, f"写入备份文件失败：{e}"
    size_mb = (len(header) + len(token)) / 1024 / 1024
    return True, f"加密备份完成：{enc_path}（{size_mb:.2f} MB，{len(files)} 个文件，PBKDF2 高迭代加密）"

def decrypt_and_restore(cfg: dict, enc_path: str, password: str) -> tuple:
    """解密 .enc 并安全恢复 data 目录。v2 格式：校验格式标识/元数据/完整性后解压；
    v1 旧格式：兼容导入（无新完整性元数据校验，给出明确提示）。
    密码错误/文件损坏/路径穿越/压缩炸弹/CRC 失败均给出明确中文提示；失败回滚、无残留。"""
    if not CRYPTO_OK:
        return False, "缺少 cryptography 库，请执行 pip install cryptography 后重试"
    if not password:
        return False, "密码不能为空，已取消恢复"
    try:
        raw = Path(enc_path).read_bytes()
    except Exception as e:
        return False, f"读取备份文件失败：{e}"
    if not raw:
        return False, "备份文件为空，已取消恢复"

    legacy = False
    try:
        if raw.startswith(BACKUP_MAGIC):
            # ---- v2 新格式：格式标识 + 元数据 + 高迭代派生 + 完整性校验 ----
            meta, token, ok_h, msg_h = _parse_header(raw)
            if not ok_h:
                return False, msg_h
            if meta.get("tool") != BACKUP_TOOL or int(meta.get("format", -1)) != BACKUP_FORMAT:
                return False, "备份格式无法识别（非本工具加密备份），已取消恢复"
            try:
                salt = base64.b64decode(meta["salt"])
                key = derive_fernet_key(password, salt)
                zip_bytes = Fernet(key).decrypt(token)
            except InvalidToken:
                return False, "解密失败：密码错误或文件已被修改/损坏"
            except Exception:
                return False, "解密失败：密码错误或文件已被修改/损坏"
            if hashlib.sha256(zip_bytes).hexdigest() != str(meta.get("zip_sha256", "")):
                return False, "备份完整性校验失败：内容与记录不一致（文件可能被修改或损坏）"
        else:
            # ---- v1 旧格式兼容：无明文头，走旧 SHA-256 派生 ----
            legacy = True
            try:
                zip_bytes = Fernet(derive_legacy_key(password)).decrypt(raw)
            except InvalidToken:
                return False, "解密失败：密码错误或文件已损坏"
            except Exception:
                return False, "解密失败：密码错误或文件已损坏"
    except Exception as e:
        return False, f"备份解析失败：{e}"

    vw_dir = Path(cfg["vaultwarden_dir"])
    data_dir = vw_dir / "data"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak_dir = vw_dir / f"data_bak_{ts}"
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            # 完整性：zip CRC 全量校验（损坏/篡改在此拦截）
            bad = zf.testzip()
            if bad:
                return False, f"备份内容校验失败（CRC 不匹配）：{bad}，文件可能已损坏或被篡改"
            # 安全红线：zip-slip / 路径穿越 / 压缩炸弹 / 符号链接
            ok_s, msg_s = _check_zip_safety(zf)
            if not ok_s:
                return False, f"备份安全检查未通过：{msg_s}，已取消恢复"
            # 解压前先改名现有 data 以防误操作
            if data_dir.exists():
                shutil.move(str(data_dir), str(bak_dir))
            try:
                ok_x, msg_x = _extract_zip_safely(zf, data_dir)
                if not ok_x:
                    raise ValueError(msg_x)
            except Exception:
                # 失败回滚：删除半成品目录，恢复原 data
                if data_dir.exists():
                    shutil.rmtree(data_dir, ignore_errors=True)
                if bak_dir.exists():
                    shutil.move(str(bak_dir), str(data_dir))
                raise
    except Exception as e:
        return False, f"恢复失败：{e}"
    count = sum(1 for _ in data_dir.rglob("*") if _.is_file())
    msg = f"恢复完成：{data_dir}（{count} 个文件）"
    if legacy:
        msg += "\n（按旧版备份格式导入，未含新版完整性元数据校验）"
    if bak_dir.exists():
        msg += f"\n原 data 已备份为 {bak_dir}"
    return True, msg

