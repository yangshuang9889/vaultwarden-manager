# -*- coding: utf-8 -*-
"""
Vaultwarden Manager 模块包（v1.8.0 模块化重构）
================================================================
入口   : vaultwarden_manager.py（薄壳，仅转发 vwm.app.main）
模块   : config / service / deploy / cert / backup / logs / network / ui / app
依赖图 : 见 DEV.md「模块结构」章节，无循环依赖。
"""
__version__ = "1.8.0"

try:
    from cryptography import x509
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
    CRYPTO_OK = True
except Exception:  # 打包环境缺 cryptography 时降级，仅证书/加密备份功能不可用
    CRYPTO_OK = False
