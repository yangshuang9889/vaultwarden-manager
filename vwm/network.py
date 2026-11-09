# -*- coding: utf-8 -*-
"""
网络探测模块（v1.8.0）
职责：端口连通性探测、本机局域网 IP 收集、进程实际监听端口解析、
      协议探测与 Web Vault 动态地址拼接。
依赖：common（CREATE_NO_WINDOW），仅标准库。
"""
import re
import socket
import ssl
import subprocess

from .common import CREATE_NO_WINDOW

def is_port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """探测端口是否可连接。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def is_port_in_use(port: int, host: str = "0.0.0.0", timeout: float = 0.35) -> bool:
    """v1.9.8：判断端口是否已被占用（监听中）。

    双重判定，避免漏判：
    1) 主动连接 127.0.0.1:port —— 有服务监听且接受连接（最常见）；
    2) 绑定 0.0.0.0:port —— 监听中但尚未 accept / 被其它程序占位时连接可能失败，
       此时绑定会因端口已被占用而抛 OSError。
    注意：**不得**设置 SO_REUSEADDR——Windows 下该选项允许抢占已监听端口，
    会导致「已被占用」误判为可用。
    """
    try:
        port = int(port)
    except (TypeError, ValueError):
        return True  # 非法端口保守视为不可用
    if is_port_open(port, "127.0.0.1", timeout):
        return True
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        return False
    except OSError:
        return True
    finally:
        try:
            sock.close()
        except Exception:
            pass

def is_port_bindable(port: int, host: str = "0.0.0.0") -> bool:
    """v1.9.8：端口是否可被本机绑定（随机端口挑选用，语义与 is_port_in_use 相反）。"""
    return not is_port_in_use(port, host)

def pick_free_port(low: int = 20000, high: int = 65000,
                   exclude=None, tries: int = 40) -> int:
    """v1.9.8：在 [low, high] 高位区间随机挑选一个可绑定的空闲端口。

    exclude：需排除的端口集合（避免挑回当前被占用端口）；
    最多尝试 tries 次，全部落空返回 0（由调用方给出中文错误提示）。
    """
    import random
    excluded = set(int(p) for p in (exclude or []) if p)
    if low > high:
        low, high = high, low
    for _ in range(max(1, int(tries))):
        port = random.randint(low, high)
        if port in excluded:
            continue
        if is_port_in_use(port):
            continue
        return port
    return 0

# ============================================================
# 局域网 IP 探测（v1.9.10 重写）
# ------------------------------------------------------------
# v1.9.9 及以前只做「UDP 出口地址 + 主机名解析」并按字符串字典序排序，
# 导致 192.0.2.1（Hyper-V Default Switch 虚拟网卡）排在 198.51.100.10 之前被
# 当作局域网地址显示，手机等外部设备根本无法连上。
# v1.9.10 起改为「真实出口地址优先 + 网卡枚举过滤虚拟网卡 + 私网段/默认网关排序」，
# 并对外暴露完整候选与被排除清单，结果带 TTL 缓存。
# ============================================================

# 明显不承载真实局域网的虚拟/隧道网卡关键词（命中即排除，大小写不敏感）
_VIRTUAL_HARD_KEYWORDS = (
    "virtualbox", "vmware", "vmnet", "wsl", "docker", "loopback", "npcap",
    "tap-windows", "tap adapter", "openvpn", "wireguard", "tailscale",
    "zerotier", "teredo", "bluetooth", "pseudo", "wan miniport",
    "wi-fi direct", "vpn",
)
# Hyper-V / vEthernet 需区别对待：Default Switch、内部交换机、WSL 均为无默认网关的
# 纯虚拟网卡（排除）；而「外部网络交换机」是桥接物理网卡的虚拟交换机，其 IP 可能就是
# 本机真实局域网地址（真机实测：本机唯一可用的 198.51.100.10 即位于此类网卡），
# 故仅在其「无默认网关」时排除，有默认网关时保留为候选并降权。
_VIRTUAL_SOFT_KEYWORDS = ("hyper-v", "vethernet", "虚拟", "virtual ethernet")

# UDP 出口探测目标（CDN/DNS 公网地址，只做 connect 不实际发包）
_UDP_PROBE_TARGETS = (("8.8.8.8", 80), ("114.114.114.114", 80), ("223.5.5.5", 80))

_LAN_CACHE = {"ts": 0.0, "info": None}
_LAN_CACHE_TTL = 30.0        # 秒；设置窗口重复打开/证书生成复用同一次探测结果


def _decode_console(data: bytes) -> str:
    """控制台输出解码：Windows 中文系统为 GBK，优先 mbcs（当前 ANSI 代码页）。

    注：本函数仅在 Windows 下使用；非 Windows 环境下 mbcs 编码不可用会自动跳过。
    """
    if not data:
        return ""
    for enc in ("mbcs", "utf-8", "gbk"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", "replace")


def _udp_outbound_ips() -> list:
    """UDP connect 取本机真实出口地址（不发送任何数据）。"""
    ips = []
    for host, port in _UDP_PROBE_TARGETS:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            sock.connect((host, port))
            ip = sock.getsockname()[0]
            if ip and ip not in ips:
                ips.append(ip)
        except Exception:
            continue
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
    return ips


def _parse_ipconfig() -> list:
    """解析 `ipconfig` 输出为网卡列表（名称/描述/IPv4/默认网关）。

    仅用结构性规则解析（标题行无缩进且以冒号结尾、字段行有缩进且含冒号），
    中英文系统均适用；解析失败返回空列表，绝不影响主流程。
    """
    adapters = []
    try:
        proc = subprocess.run(
            ["ipconfig"], capture_output=True, timeout=8,
            creationflags=CREATE_NO_WINDOW,
        )
        text = _decode_console(proc.stdout or b"")
    except Exception:
        return adapters
    title_prefix = ("以太网适配器", "无线局域网适配器", "隧道适配器", "未知适配器",
                    "Ethernet adapter", "Wireless LAN adapter", "Tunnel adapter",
                    "Unknown adapter")
    cur = None
    last_field = ""
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if not line[:1].isspace():                     # 适配器标题行（顶格）
            name = line.strip().rstrip(":").strip()
            for pfx in title_prefix:
                if name.lower().startswith(pfx.lower()):
                    name = name[len(pfx):].strip()
                    break
            cur = {"name": name, "description": "", "ips": [], "gateways": []}
            adapters.append(cur)
            last_field = ""
            continue
        if cur is None:
            continue
        if ":" in line:
            label, _, value = line.partition(":")
            label_l = label.strip().lower()
            value = value.strip()
            if "ipv4" in label_l:
                last_field = "ip4"
                m = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", value)
                if m:
                    cur["ips"].append(m.group(1))
            elif "网关" in label or "gateway" in label_l:
                last_field = "gw"
                m = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", value)
                if m:
                    cur["gateways"].append(m.group(1))
            elif "描述" in label or "description" in label_l:
                last_field = "desc"
                cur["description"] = value
            else:
                last_field = "other"
        elif last_field == "gw":
            # 续行：网关字段可能跨多行（IPv6 网关在前、IPv4 网关在后），无标签
            m = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", line.strip())
            if m:
                cur["gateways"].append(m.group(1))
    return adapters


def _is_soft_virtual(name: str, desc: str) -> bool:
    """是否属于 Hyper-V / vEthernet 这类「可能是真实出口」的虚拟交换机网卡。"""
    blob = ("%s %s" % (name, desc)).lower()
    return any(kw in blob for kw in _VIRTUAL_SOFT_KEYWORDS)


def _virtual_reason(name: str, desc: str, has_gateway: bool) -> str:
    """返回该网卡应被排除的中文原因；空串表示不是虚拟网卡。"""
    blob = ("%s %s" % (name, desc)).lower()
    for kw in _VIRTUAL_HARD_KEYWORDS:
        if kw in blob:
            return "虚拟/隧道网卡（匹配关键词：%s）" % kw
    if _is_soft_virtual(name, desc) and not has_gateway:
        return "虚拟网卡（Hyper-V/vEthernet，无默认网关）"
    return ""


def _is_172_private(ip: str) -> bool:
    """172.16.0.0/12 判定。"""
    if not ip.startswith("172."):
        return False
    try:
        second = int(ip.split(".")[1])
    except (IndexError, ValueError):
        return False
    return 16 <= second <= 31


def _is_cgnat(ip: str) -> bool:
    """100.64.0.0/10（运营商级 NAT）判定。"""
    if not ip.startswith("100."):
        return False
    try:
        second = int(ip.split(".")[1])
    except (IndexError, ValueError):
        return False
    return 64 <= second <= 127


def _ip_rank(ip: str) -> int:
    """私网段优先级：192.168.x > 10.x > 172.16-31.x > 100.64/10 > 其它。"""
    if ip.startswith("192.168."):
        return 30
    if ip.startswith("10."):
        return 20
    if _is_172_private(ip):
        return 10
    if _is_cgnat(ip):
        return 5
    return 0


def _detect_lan_ip_info() -> dict:
    """执行一次完整探测，返回结构化结果（内部函数）。"""
    udp_ips = _udp_outbound_ips()
    seen = set()
    entries = []
    excluded = []

    for ad in _parse_ipconfig():
        name = ad.get("name", "")
        desc = ad.get("description", "")
        gateways = ad.get("gateways") or []
        has_gw = bool(gateways)
        soft = _is_soft_virtual(name, desc)
        for ip in ad.get("ips", []):
            if ip in seen:
                continue
            seen.add(ip)
            if ip.startswith("127."):
                excluded.append({"ip": ip, "adapter": name, "description": desc,
                                 "reason": "回环地址"})
                continue
            if ip.startswith("169.254."):
                excluded.append({"ip": ip, "adapter": name, "description": desc,
                                 "reason": "自动私有地址（APIPA，未获取到 DHCP）"})
                continue
            reason = _virtual_reason(name, desc, has_gw)
            if reason:
                excluded.append({"ip": ip, "adapter": name, "description": desc,
                                 "reason": reason})
                continue
            score = _ip_rank(ip)
            if has_gw:
                score += 100                     # 有默认网关：真实上网出口，强烈优先
            if ip in udp_ips:
                score += 60                      # 与 UDP 出口探测一致：命中真实出口
            if soft:
                score -= 25                      # 虚拟交换机桥接，降权但仍可作候选
            entries.append({
                "ip": ip, "adapter": name, "description": desc,
                "gateway": gateways[0] if gateways else "",
                "has_gateway": has_gw, "virtual_bridge": soft, "score": score,
            })

    # ipconfig 解析失败或地址未枚举到时，用 UDP 出口地址兜底补入
    for ip in udp_ips:
        if ip in seen:
            continue
        seen.add(ip)
        if ip.startswith("127.") or ip.startswith("169.254."):
            excluded.append({"ip": ip, "adapter": "（UDP 出口探测）", "description": "",
                             "reason": "回环/自动私有地址"})
            continue
        entries.append({
            "ip": ip, "adapter": "（UDP 出口探测）", "description": "",
            "gateway": "", "has_gateway": False, "virtual_bridge": False,
            "score": 100 + 60 + _ip_rank(ip),
        })

    entries.sort(key=lambda e: (-e["score"], e["ip"]))
    candidates = [e["ip"] for e in entries]
    primary = candidates[0] if candidates else ""
    if not primary:
        source = "none"
    elif primary in udp_ips:
        source = "udp"
    else:
        source = "adapter"
    return {
        "primary": primary,
        "candidates": candidates,
        "details": entries,
        "excluded": excluded,
        "udp_probe": udp_ips,
        "source": source,
    }


def get_lan_ip_info(refresh: bool = False) -> dict:
    """获取局域网 IP 探测详情（v1.9.10，带 30 秒缓存）。

    返回字典：
      primary    —— 首选局域网 IP（真实出口优先），无可用地址时为空串
      candidates —— 全部非虚拟候选 IP，已按优先级排序
      details    —— 每个候选的网卡名称/描述/默认网关/评分
      excluded   —— 被排除的地址与中文原因（含虚拟网卡清单）
      udp_probe  —— UDP 出口探测到的原始地址
      source     —— udp / adapter / none
    说明：仅供只读展示与证书 SAN 使用，探测失败返回空候选而非抛异常。
    """
    import time
    now = time.time()
    cached = _LAN_CACHE.get("info")
    if cached is not None and not refresh and (now - _LAN_CACHE.get("ts", 0.0)) < _LAN_CACHE_TTL:
        info = dict(cached)
        info["cached"] = True
        return info
    try:
        info = _detect_lan_ip_info()
    except Exception:
        info = {"primary": "", "candidates": [], "details": [], "excluded": [],
                "udp_probe": [], "source": "none"}
    _LAN_CACHE["ts"] = now
    _LAN_CACHE["info"] = dict(info)
    info["cached"] = False
    return info


def get_lan_ips(refresh: bool = False) -> list:
    """获取本机真实局域网 IPv4 地址列表（按优先级排序，用于证书 SAN / 界面展示）。

    v1.9.10：过滤虚拟网卡并优先真实出口地址；函数签名向后兼容（新增参数均有默认值）。
    """
    return list(get_lan_ip_info(refresh=refresh).get("candidates") or [])

def get_listen_port(exe_name: str) -> list:
    """通过 netstat + tasklist 解析 exe 进程实际监听端口（LISTENING，TCP）。

    返回排序去重的端口列表；进程未运行、解析失败时返回空列表。
    """
    pid2name = {}
    try:
        out = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5,
            creationflags=CREATE_NO_WINDOW,
        ).stdout
        for line in out.splitlines():
            parts = [p.strip('"') for p in line.split('","')]
            if len(parts) >= 2:
                try:
                    pid2name[int(parts[1])] = parts[0].lower()
                except ValueError:
                    continue
    except Exception:
        pass
    ports = set()
    try:
        out = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True, text=True, timeout=5,
            creationflags=CREATE_NO_WINDOW,
        ).stdout
        for line in out.splitlines():
            if "LISTENING" not in line:
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            try:
                pid = int(parts[4])
            except ValueError:
                continue
            if pid2name.get(pid) != exe_name.lower():
                continue
            addr = parts[1]
            m = re.search(r"\[[^\]]+\]:(\d+)$", addr) or re.search(r":(\d+)$", addr)
            if m:
                ports.add(int(m.group(1)))
    except Exception:
        pass
    return sorted(ports)

def detect_scheme(host: str, port: int) -> str:
    """探测 host:port 实际协议：TLS 握手成功返回 https，否则 http；端口未开返回空串。"""
    if not is_port_open(port, host):
        return ""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=1.0) as sock:
            with ctx.wrap_socket(sock, server_hostname="localhost") as ss:
                ss.settimeout(1.0)
                ss.sendall(b"HEAD / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
                ss.recv(16)
        return "https"
    except Exception:
        return "http"

def resolve_web_url(cfg: dict) -> str:
    """按服务实际监听端口与协议动态拼接 Web Vault 基地址（v1.7.0）。

    v1.6.9 起按 cfg['port'] 动态拼端口；v1.7.0 起进一步：
    1) 优先用 netstat 解析 vaultwarden.exe 实际监听端口——config/.env 与运行时漂移时
       打开的地址仍与实际一致；
    2) 探测实际协议（HTTPS/HTTP）——服务未启用 TLS（无 .env ROCKET_TLS）时不再拼 https，
       避免浏览器报网络链接错误。
    服务未运行 / 探测失败时回退 cfg['port'] + https（项目默认期望 HTTPS）。
    """
    port = int(cfg["port"])
    listen_ports = get_listen_port(cfg["exe_name"])
    if listen_ports:
        port = port if port in listen_ports else listen_ports[0]
    scheme = detect_scheme("127.0.0.1", port) or "https"
    return "{}://localhost:{}".format(scheme, port)

