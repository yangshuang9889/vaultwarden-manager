# -*- coding: utf-8 -*-
"""
证书管理模块（v1.8.0）
职责：自签名证书生成（cryptography）、系统根信任库安装（certutil）。
依赖：network（get_lan_ips）、common、包级 CRYPTO_OK。
"""
import ipaddress
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import CRYPTO_OK
from .common import CREATE_NO_WINDOW
from .network import get_lan_ips

# cryptography 可选依赖：缺失时 CRYPTO_OK=False，相关功能返回不可用提示
if CRYPTO_OK:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

def generate_certificate(cfg: dict) -> tuple:
    """在 ssl 目录重新生成 10 年自签名证书（SAN: localhost / 127.0.0.1 / 本机局域网 IP）。"""
    if not CRYPTO_OK:
        return False, "缺少 cryptography 库，请执行 pip install cryptography 后重试"
    ssl_dir = Path(cfg["ssl_dir"])
    cert_path = ssl_dir / cfg["cert_file"]
    key_path = ssl_dir / cfg["key_file"]
    ssl_dir.mkdir(parents=True, exist_ok=True)
    days = int(cfg["cert_days"])

    # 备份旧证书
    if cert_path.exists() or key_path.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if cert_path.exists():
            shutil.copy2(cert_path, ssl_dir / f"cert.pem.bak-{ts}")
        if key_path.exists():
            shutil.copy2(key_path, ssl_dir / f"key.pem.bak-{ts}")

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Vaultwarden Local"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
    san_entries = [
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
    ]
    lan_ips = get_lan_ips()
    for ip in lan_ips:
        try:
            san_entries.append(x509.IPAddress(ipaddress.ip_address(ip)))
        except Exception:
            continue

    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName(san_entries), critical=False
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=False,
                key_encipherment=True, data_encipherment=False,
                key_agreement=False, key_cert_sign=True, crl_sign=True,
                encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
        )
        .sign(key, hashes.SHA256())
    )

    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    san_text = "、".join(["localhost", "127.0.0.1"] + lan_ips)
    return True, (
        f"证书已重新生成（有效期 {days} 天，SAN: {san_text}）\n"
        f"文件：{cert_path} / {key_path}\n"
        "注意：需重启服务（停止 → 启动）后新证书才生效！"
    )

def add_system_trust(cfg: dict) -> tuple:
    """执行 certutil -addstore -user Root 安装证书到当前用户根信任库。"""
    ssl_dir = Path(cfg["ssl_dir"])
    cert_path = ssl_dir / cfg["cert_file"]
    if not cert_path.exists():
        return False, f"证书不存在：{cert_path}，请先生成证书"
    try:
        res = subprocess.run(
            ["certutil", "-addstore", "-user", "Root", str(cert_path)],
            capture_output=True, text=True, timeout=30,
            creationflags=CREATE_NO_WINDOW,
        )
        out = (res.stdout or "") + (res.stderr or "")
        low = out.lower()
        if res.returncode == 0:
            return True, "证书已安装到当前用户根信任库（certutil -addstore -user Root）"
        if "exist" in low or "已存在" in out:
            return True, "证书已存在于当前用户根信任库（无需重复安装）"
        return False, f"certutil 执行异常（退出码 {res.returncode}）：{out.strip()[:300]}"
    except Exception as e:
        return False, f"添加信任失败：{e}"

