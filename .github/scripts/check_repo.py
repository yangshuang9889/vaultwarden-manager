# -*- coding: utf-8 -*-
"""
仓库自检脚本（CI 与本地通用，零第三方依赖）。

检查内容：
  1. 全部 Python 源文件语法编译（py_compile，不执行 import）
  2. 敏感信息扫描（私钥块 / 本机用户路径 / 真实内网 IP / ADMIN_TOKEN 明文 / 邮箱）
  3. 版本号一致性（vwm/ui.py VERSION、vwm/__init__.py __version__、README、CHANGELOG）
  4. 开源必备文件存在性

用法：
    python .github/scripts/check_repo.py
退出码：0 全部通过；1 存在问题。
"""
import os
import re
import sys
import tokenize

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SKIP_DIRS = {".git", "build", "dist", "temp", "tmp", "__pycache__", ".venv", "venv", "node_modules"}
TEXT_EXT = {".py", ".md", ".json", ".txt", ".yml", ".yaml", ".ini", ".cfg", ".ps1", ".bat", ".cmd"}

problems = []
checks = []


def ok(msg):
    checks.append(("PASS", msg))


def bad(msg):
    checks.append(("FAIL", msg))
    problems.append(msg)


def walk_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            yield os.path.join(base, f)


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


# ---------- 1. 语法编译 ----------
py_files = [p for p in walk_files() if p.endswith(".py")]
fail_compile = []
for p in py_files:
    try:
        with tokenize.open(p) as fh:
            src = fh.read()
        compile(src, p, "exec")
    except (SyntaxError, ValueError) as e:
        fail_compile.append((rel(p), f"{type(e).__name__}: {e}"[:200]))
if fail_compile:
    for f, e in fail_compile:
        bad(f"语法错误 {f}: {e}")
else:
    ok(f"Python 语法编译通过（{len(py_files)} 个文件）")

# ---------- 2. 敏感信息扫描 ----------
ALLOW_IPS = {
    "127.0.0.1", "0.0.0.0", "255.255.255.255",
    "8.8.8.8", "8.8.4.4", "1.1.1.1", "114.114.114.114", "223.5.5.5",
}
DOC_NETS = ("192.0.2.", "198.51.100.", "203.0.113.")
PRIVATE_IP = re.compile(r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b")
PRIV_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----[\s\S]{100,}?-----END")
USER_PATH = re.compile(r"[A-Za-z]:\\Users\\[^\\\s\"']+")
MAIL = re.compile(r"\b[\w.+-]+@(?:qq|163|126|gmail|outlook|hotmail|foxmail|sina|aliyun)\.com\b", re.I)
ADMIN_TOKEN = re.compile(r"ADMIN_TOKEN\s*[=:]\s*\"?([0-9a-fA-F]{20,}|\$argon2[^\s\"]*)")

viol = []
for p in walk_files():
    ext = os.path.splitext(p)[1].lower()
    if ext not in TEXT_EXT:
        continue
    try:
        text = open(p, "r", encoding="utf-8", errors="ignore").read()
    except Exception:
        continue
    rp = rel(p)
    for m in PRIV_KEY.finditer(text):
        viol.append(f"{rp}: 疑似明文私钥块")
        break
    for m in USER_PATH.finditer(text):
        viol.append(f"{rp}: 本机用户绝对路径 {m.group(0)}")
    for m in PRIVATE_IP.finditer(text):
        ip = m.group(0)
        if ip in ALLOW_IPS or ip.startswith(DOC_NETS):
            continue
        # 网段说明（CIDR）与网段基数/广播地址属正常写法，不算泄露
        tail = text[m.end():m.end() + 4]
        if tail.startswith("/"):
            continue
        octets = ip.split(".")
        if octets[2:] == ["0", "0"] or octets[2:] == ["255", "255"]:
            continue
        viol.append(f"{rp}: 真实内网 IP {ip}")
    for m in ADMIN_TOKEN.finditer(text):
        val = m.group(1)
        if val.startswith("$argon2"):
            viol.append(f"{rp}: ADMIN_TOKEN 为 argon2 哈希（应留空）")
        elif len(set(val)) > 3:
            viol.append(f"{rp}: 疑似明文 ADMIN_TOKEN（长度 {len(val)}）")
    for m in MAIL.finditer(text):
        viol.append(f"{rp}: 邮箱地址 {m.group(0)}")

if viol:
    for v in sorted(set(viol)):
        bad("敏感信息 " + v)
else:
    ok("敏感信息扫描通过（无私钥/本机路径/真实内网 IP/明文令牌/邮箱）")

# ---------- 3. 版本一致性 ----------
def read(relpath):
    p = os.path.join(ROOT, relpath)
    if not os.path.exists(p):
        return ""
    return open(p, "r", encoding="utf-8", errors="ignore").read()


ui = read("vwm/ui.py")
init = read("vwm/__init__.py")
readme = read("README.md")
changelog = read("CHANGELOG.md")

m_ui = re.search(r'^VERSION\s*=\s*"([^"]+)"', ui, re.M)
m_init = re.search(r'^__version__\s*=\s*"([^"]+)"', init, re.M)
m_readme = re.search(r"版本\s*(v\d+\.\d+\.\d+)", readme)
m_log = re.search(r"^##\s*\[(\d+\.\d+\.\d+)\]", changelog, re.M)

versions = {
    "vwm/ui.py VERSION": m_ui.group(1) if m_ui else None,
    "vwm/__init__.py __version__": ("v" + m_init.group(1)) if m_init else None,
    "README 版本标注": m_readme.group(1) if m_readme else None,
    "CHANGELOG 最新条目": ("v" + m_log.group(1)) if m_log else None,
}
missing = [k for k, v in versions.items() if not v]
if missing:
    bad("版本号缺失: " + ", ".join(missing))
else:
    distinct = set(versions.values())
    if len(distinct) == 1:
        ok(f"版本号一致（{distinct.pop()}）")
    else:
        bad("版本号不一致: " + ", ".join(f"{k}={v}" for k, v in versions.items()))

# ---------- 4. 必备文件 ----------
required = ["README.md", "LICENSE", "CHANGELOG.md", ".gitignore", "config.example.json",
            "requirements.txt", "vaultwarden_manager.py", "vwm/__init__.py", "vwm/app.py", "vwm/ui.py"]
lack = [f for f in required if not os.path.exists(os.path.join(ROOT, f))]
if lack:
    bad("缺少必备文件: " + ", ".join(lack))
else:
    ok(f"开源必备文件齐全（{len(required)} 项）")

# ---------- 5. GitHub 配置 YAML 语法 ----------
yml_files = [p for p in walk_files()
             if p.lower().endswith((".yml", ".yaml")) and ".github" in rel(p)]
if yml_files:
    try:
        import yaml
    except ImportError:
        checks.append(("SKIP", f"未安装 pyyaml，跳过 {len(yml_files)} 个 YAML 文件语法校验"))
    else:
        yml_bad = []
        for p in yml_files:
            try:
                with open(p, "r", encoding="utf-8") as fh:
                    yaml.safe_load(fh)
            except Exception as e:
                yml_bad.append(f"{rel(p)}: {type(e).__name__}: {e}")
        if yml_bad:
            for b in yml_bad:
                bad("YAML 语法错误 " + b)
        else:
            ok(f"GitHub YAML 配置语法通过（{len(yml_files)} 个文件）")

# ---------- 输出 ----------
print("=" * 60)
print("VaultwardenManager 仓库自检")
print("=" * 60)
for status, msg in checks:
    print(f"[{status}] {msg}")
print("-" * 60)
if problems:
    print(f"结果：{len(problems)} 项问题待处理")
    sys.exit(1)
print("结果：全部通过")
sys.exit(0)
