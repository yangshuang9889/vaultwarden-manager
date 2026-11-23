# -*- coding: utf-8 -*-
"""
WebDAV 云备份模块（v1.10.0）
职责：WebDAV 客户端（PUT 上传 / MKCOL 递归建目录 / PROPFIND Depth:1 列目录 /
      GET 下载 / DELETE 删除；HTTP Basic 认证；可选跳过 TLS 证书校验；可配置超时；
      401/403/404/507/网络异常统一转中文提示）；Windows 凭据 DPAPI 加解密
      （CryptProtectData / CryptUnprotectData + CRYPTPROTECT_UI_FORBIDDEN），
      config.json 只保存 base64 密文（webdav_password_enc），任何环节不落明文、
      界面不回显明文；按 webdav_keep 清理远端旧备份。
依赖：仅标准库（urllib.request / ssl / base64 / ctypes / xml.etree / email.utils），
      不引入任何第三方依赖；加密备份本身仍由 backup.encrypt_backup 生成（本模块只负责传输）。
上游：config（cfg 字段）、app/ui（调用入口）、logs（由调用方记录 manager.log）。
下游：无（不反向依赖项目内其他模块，避免循环导入）。
"""
import base64
import ctypes
import email.utils
import os
import re
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

# 默认值与常量（与 config.build_default_config 保持一致，缺失键时兜底）
USER_AGENT = "VaultwardenManager/1.10.0"
DEFAULT_TIMEOUT = 60            # 秒
DEFAULT_REMOTE_DIR = "vaultwarden-backup"
ENC_SUFFIX = ".enc"
CRYPTPROTECT_UI_FORBIDDEN = 0x1  # DPAPI：禁止弹出任何系统 UI（后台静默加解密）
_DPAPI_DESCR = "VaultwardenManager WebDAV password"
_CHUNK = 256 * 1024             # 上传/下载分块大小（256KB）
_MIN_TIMEOUT = 5
_MAX_TIMEOUT = 600

# ============================ DPAPI（Windows 凭据保护） ============================


class _DataBlob(ctypes.Structure):
    """Win32 DATA_BLOB 结构（CryptProtectData / CryptUnprotectData 入参出参）。"""
    _fields_ = [
        ("cbData", ctypes.c_uint32),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


class _DpapiUnavailable(Exception):
    """DPAPI 在当前环境不可用（非 Windows 或系统接口缺失）。"""


def can_use_dpapi() -> bool:
    """当前环境是否可用 DPAPI（Windows 且能加载 crypt32/kernel32）。"""
    if os.name != "nt":
        return False
    try:
        ctypes.WinDLL("crypt32")
        ctypes.WinDLL("kernel32")
        return True
    except (AttributeError, OSError):
        return False


def _load_dpapi():
    """加载并声明 DPAPI 函数签名；失败抛 _DpapiUnavailable（中文提示）。"""
    if os.name != "nt":
        raise _DpapiUnavailable("当前系统不是 Windows，无法使用系统凭据保护（DPAPI）加密保存密码")
    try:
        crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    except (AttributeError, OSError) as exc:
        raise _DpapiUnavailable(
            "系统未提供 CryptProtectData / CryptUnprotectData（DPAPI），无法加密保存 WebDAV 密码：%s" % exc)
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(_DataBlob), ctypes.c_wchar_p, ctypes.POINTER(_DataBlob),
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptProtectData.restype = ctypes.c_int
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DataBlob), ctypes.POINTER(ctypes.c_wchar_p), ctypes.POINTER(_DataBlob),
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = ctypes.c_int
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    return crypt32, kernel32


def _blob_in(data: bytes):
    """构造输入 DATA_BLOB，同时返回底层缓冲区（必须持有引用防止 GC 提前释放）。"""
    buf = ctypes.create_string_buffer(data, max(len(data), 1))
    blob = _DataBlob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    return blob, buf


def _blob_out_bytes(kernel32, blob: _DataBlob) -> bytes:
    """从输出 DATA_BLOB 取出字节并用 LocalFree 释放系统分配内存。"""
    try:
        if not blob.pbData or not blob.cbData:
            return b""
        return ctypes.string_at(blob.pbData, int(blob.cbData))
    finally:
        try:
            if blob.pbData:
                kernel32.LocalFree(ctypes.cast(blob.pbData, ctypes.c_void_p))
        except Exception:  # noqa: BLE001 - 释放失败不影响业务结果
            pass


def protect_password(password: str) -> tuple:
    """用 DPAPI 加密 WebDAV 密码。返回 (ok, base64 密文, 中文提示)。

    明文只在内存中停留，返回值只有密文；任何异常都转中文提示，绝不抛出。
    """
    text = password if isinstance(password, str) else str(password or "")
    if not text:
        return False, "", "WebDAV 密码为空，无需加密"
    try:
        crypt32, kernel32 = _load_dpapi()
    except _DpapiUnavailable as exc:
        return False, "", str(exc)
    try:
        raw = text.encode("utf-8")
        blob_in, _buf = _blob_in(raw)
        blob_out = _DataBlob()
        ok = crypt32.CryptProtectData(
            ctypes.byref(blob_in), _DPAPI_DESCR, None, None, None,
            CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out))
        if not ok:
            err = ctypes.get_last_error() or 0
            return False, "", "加密 WebDAV 密码失败（DPAPI 错误码 %s），密码未保存" % err
        enc = _blob_out_bytes(kernel32, blob_out)
        if not enc:
            return False, "", "加密 WebDAV 密码失败：DPAPI 返回空结果，密码未保存"
        return True, base64.b64encode(enc).decode("ascii"), ""
    except Exception as exc:  # noqa: BLE001 - 兜底，绝不让异常冒到 UI 线程
        return False, "", "加密 WebDAV 密码失败：%s" % exc


def unprotect_password(encoded: str) -> tuple:
    """用 DPAPI 解密 config.json 中的 base64 密文。返回 (ok, 明文密码, 中文提示)。

    解密只在本机当前用户上下文中有效；换用户/换机器会失败，此时提示重新填写密码。
    """
    text = (encoded or "").strip() if isinstance(encoded, str) else ""
    if not text:
        return False, "", "尚未保存 WebDAV 密码，请先在设置里填写"
    try:
        crypt32, kernel32 = _load_dpapi()
    except _DpapiUnavailable as exc:
        return False, "", str(exc)
    try:
        blob_in, _buf = _blob_in(base64.b64decode(text.encode("ascii"), validate=False))
        blob_out = _DataBlob()
        descr = ctypes.c_wchar_p()
        ok = crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), ctypes.byref(descr), None, None, None,
            CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out))
        if not ok:
            err = ctypes.get_last_error() or 0
            return False, "", ("解密已保存的 WebDAV 密码失败（DPAPI 错误码 %s）：密码可能由其他 Windows "
                               "账号或其它电脑加密，请在设置里重新填写密码并保存" % err)
        raw = _blob_out_bytes(kernel32, blob_out)
        if descr:
            try:
                kernel32.LocalFree(ctypes.cast(descr, ctypes.c_void_p))
            except Exception:  # noqa: BLE001
                pass
        if not raw:
            return False, "", "解密已保存的 WebDAV 密码失败：DPAPI 返回空结果，请重新填写密码"
        return True, raw.decode("utf-8", "replace"), ""
    except Exception as exc:  # noqa: BLE001
        return False, "", "解密已保存的 WebDAV 密码失败：%s（请在设置里重新填写密码）" % exc


# ============================ 错误提示（中文） ============================

def _friendly_http_error(code: int, url: str = "") -> str:
    """把 HTTP 状态码转成中文提示（401/403/404/507 等分别说明）。"""
    code = int(code or 0)
    if code == 401:
        return "WebDAV 认证失败（401）：账号或密码不正确，请到「设置 → WebDAV 云备份」检查账号与密码"
    if code == 403:
        return "WebDAV 拒绝访问（403）：该账号没有此目录的读/写权限，请更换账号或远程目录"
    if code == 404:
        return "WebDAV 路径不存在（404）：请检查服务器地址与远程目录是否正确"
    if code == 405:
        return "WebDAV 服务器不支持该操作（405）：该地址可能不是标准 WebDAV 服务"
    if code == 409:
        return "WebDAV 目录创建失败（409）：上级目录不存在，请检查远程目录层级"
    if code == 412:
        return "WebDAV 请求被拒绝（412）：服务器要求附加条件，请检查远程目录权限"
    if code == 423:
        return "WebDAV 资源被锁定（423）：文件正被占用，请稍后重试"
    if code == 507:
        return "WebDAV 服务器存储空间不足（507）：请清理云端空间或减少保留份数后重试"
    if code in (500, 502, 503, 504):
        return "WebDAV 服务器内部错误（%d）：请稍后重试或联系网盘服务商" % code
    if code >= 400:
        return "WebDAV 请求失败（HTTP %d）%s" % (code, ("：" + url) if url else "")
    return ""


def _friendly_network_error(exc, timeout) -> str:
    """网络层异常（URLError/证书/超时/DNS/拒绝连接）转中文提示。"""
    reason = getattr(exc, "reason", None)
    text = str(reason if reason is not None else exc)
    low = text.lower()
    if isinstance(reason, ssl.SSLCertVerificationError) or "certificate verify failed" in low \
            or "certificate" in low or "ssl" in low:
        return ("TLS 证书校验失败（%s）：若 WebDAV 服务器使用自签名证书，请在设置里勾选"
                "「跳过证书校验」后重试" % text)
    if isinstance(reason, socket.timeout) or "timed out" in low or "timeout" in low:
        return "连接 WebDAV 服务器超时（%s 秒）：请检查网络或地址，必要时增大超时时间" % timeout
    if "getaddrinfo" in low or "name or service not known" in low or "nodename" in low:
        return "无法解析 WebDAV 服务器地址：请检查地址拼写与网络连接（%s）" % text
    if "refused" in low:
        return "无法连接 WebDAV 服务器：目标端口拒绝连接，请检查地址与端口（%s）" % text
    if "403" in low:
        return _friendly_http_error(403)
    if "401" in low:
        return _friendly_http_error(401)
    return "网络异常，无法访问 WebDAV 服务器：%s" % text


# ============================ 配置读取与 URL 处理 ============================

def _as_bool(value, default: bool = False) -> bool:
    """把 config.json 里的 bool/字符串统一转 bool（"false"/"0"/"no" 视为 False）。"""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on", "y"):
        return True
    if text in ("0", "false", "no", "off", "n", ""):
        return False
    return default


def _as_int(value, default: int) -> int:
    """把配置值转 int，非法值回退默认值（配置损坏时不让程序崩）。"""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def normalize_remote_dir(raw) -> str:
    """规范化远程目录：去掉首尾斜杠、压缩重复斜杠，空值回退默认目录。

    返回形如 "vaultwarden-backup" 或 "backup/vaultwarden"（不含首尾 "/"）。
    """
    text = str(raw or "").strip().replace("\\", "/")
    segs = [s for s in text.split("/") if s.strip()]
    if not segs:
        return DEFAULT_REMOTE_DIR
    return "/".join(segs)


def normalize_base_url(url) -> str:
    """规范化 WebDAV 地址：补协议、去尾斜杠、去首尾空白。"""
    text = str(url or "").strip()
    if not text:
        return ""
    if not re.match(r"^https?://", text, re.I):
        text = "https://" + text
    return text.rstrip("/")


def _quote_seg(seg: str) -> str:
    return urllib.parse.quote(seg, safe="")


def get_settings(cfg: dict) -> dict:
    """从 cfg 提取 WebDAV 相关配置并做类型/取值兜底（缺键也能正常工作）。"""
    cfg = cfg or {}
    return {
        "enabled": _as_bool(cfg.get("webdav_enabled", False), False),
        "url": normalize_base_url(cfg.get("webdav_url", "")),
        "username": str(cfg.get("webdav_username") or "").strip(),
        "password_enc": str(cfg.get("webdav_password_enc") or "").strip(),
        "verify_ssl": _as_bool(cfg.get("webdav_verify_ssl", True), True),
        "timeout": max(_MIN_TIMEOUT, min(_MAX_TIMEOUT,
                                        _as_int(cfg.get("webdav_timeout", DEFAULT_TIMEOUT), DEFAULT_TIMEOUT))),
        "keep": max(0, _as_int(cfg.get("webdav_keep", 0), 0)),
        "remote_dir": normalize_remote_dir(cfg.get("webdav_remote_dir", DEFAULT_REMOTE_DIR)),
    }


def check_ready(cfg: dict) -> tuple:
    """检查 WebDAV 是否已配置完整。返回 (ok, 中文提示)。"""
    st = get_settings(cfg)
    if not st["url"]:
        return False, "尚未配置 WebDAV 云备份：请在「设置 → WebDAV 云备份」填写服务器地址、账号与密码"
    if not st["username"]:
        return False, "尚未填写 WebDAV 账号：请在「设置 → WebDAV 云备份」补充账号"
    if not st["password_enc"]:
        return False, "尚未保存 WebDAV 密码：请在「设置 → WebDAV 云备份」填写密码并保存"
    if not can_use_dpapi():
        return False, "当前系统无法使用 DPAPI 读取已保存的 WebDAV 密码，请在设置里重新填写"
    return True, ""


# ============================ WebDAV 客户端 ============================

class _ProgressReader:
    """文件读取包装器：供 urllib 流式 PUT 上传时统计进度。"""

    def __init__(self, fh, total: int, callback=None):
        self._fh = fh
        self._total = max(int(total), 0)
        self._done = 0
        self._cb = callback

    def read(self, size: int = -1) -> bytes:
        chunk = self._fh.read(size if size and size > 0 else _CHUNK)
        if chunk:
            self._done += len(chunk)
            if callable(self._cb):
                try:
                    self._cb(self._done, self._total)
                except Exception:  # noqa: BLE001 - 进度回调异常不影响传输
                    pass
        return chunk


class WebDAVClient:
    """最小可用的 WebDAV 客户端（仅标准库）。

    支持 PUT / MKCOL / PROPFIND(Depth:1) / GET / DELETE，HTTP Basic 认证，
    可选跳过 TLS 证书校验，可配置超时；所有方法返回中文提示，不抛异常。
    """

    def __init__(self, base_url: str, username: str = "", password: str = "",
                 verify_ssl: bool = True, timeout: int = DEFAULT_TIMEOUT):
        url = normalize_base_url(base_url)
        if not url:
            raise ValueError("WebDAV 地址为空")
        self.base_url = url
        self.username = username or ""
        self._password = password or ""
        self.verify_ssl = bool(verify_ssl)
        self.timeout = max(_MIN_TIMEOUT, min(_MAX_TIMEOUT, int(timeout or DEFAULT_TIMEOUT)))
        self._auth_header = ""
        if self.username or self._password:
            raw = ("%s:%s" % (self.username, self._password)).encode("utf-8")
            self._auth_header = "Basic " + base64.b64encode(raw).decode("ascii")
        self._opener = self._build_opener()

    # ---------- 内部工具 ----------
    def _build_opener(self):
        try:
            ctx = ssl.create_default_context() if self.verify_ssl else ssl._create_unverified_context()
        except Exception:  # noqa: BLE001 - 极端环境下退回默认上下文
            ctx = None
        handlers = []
        if ctx is not None:
            handlers.append(urllib.request.HTTPSHandler(context=ctx))
        return urllib.request.build_opener(*handlers)

    def _origin(self) -> str:
        parts = urllib.parse.urlsplit(self.base_url)
        return "%s://%s" % (parts.scheme, parts.netloc)

    def _dir_url(self, remote_dir=None) -> str:
        rd = normalize_remote_dir(remote_dir) if remote_dir else ""
        if not rd:
            return self.base_url + "/"
        return self.base_url + "/" + "/".join(_quote_seg(s) for s in rd.split("/")) + "/"

    def _file_url(self, remote_name: str, remote_dir=None) -> str:
        return self._dir_url(remote_dir) + _quote_seg(str(remote_name or "").strip().lstrip("/"))

    def _dir_segments(self, remote_dir=None) -> list:
        rd = normalize_remote_dir(remote_dir) if remote_dir else ""
        return rd.split("/") if rd else []

    def _request(self, method: str, url: str, data=None, headers=None, timeout=None):
        """发起请求，返回 (response|None, status_code, 中文错误提示)。

        HTTP 错误与网络异常都不抛出，统一转成中文提示由调用方决定如何呈现。
        """
        hdrs = {"User-Agent": USER_AGENT}
        if self._auth_header:
            hdrs["Authorization"] = self._auth_header
        if headers:
            hdrs.update(headers)
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        to = self.timeout if timeout is None else timeout
        try:
            resp = self._opener.open(req, timeout=to)
        except urllib.error.HTTPError as exc:
            code = int(getattr(exc, "code", 0) or 0)
            try:
                exc.close()
            except Exception:  # noqa: BLE001
                pass
            return None, code, _friendly_http_error(code, url)
        except urllib.error.URLError as exc:
            return None, 0, _friendly_network_error(exc, to)
        except (socket.timeout, TimeoutError):
            return None, 0, "连接 WebDAV 服务器超时（%s 秒）：请检查网络或增大超时时间" % to
        except ssl.SSLError as exc:
            return None, 0, ("TLS 握手失败：%s（如服务器使用自签名证书，请勾选「跳过证书校验」）" % exc)
        except Exception as exc:  # noqa: BLE001 - 兜底，绝不抛出
            return None, 0, "WebDAV 请求异常：%s" % exc
        return resp, int(getattr(resp, "status", 0) or 0), ""

    @staticmethod
    def _close(resp):
        try:
            if resp is not None:
                resp.close()
        except Exception:  # noqa: BLE001
            pass

    # ---------- MKCOL：递归建目录 ----------
    def ensure_dir(self, remote_dir=None) -> tuple:
        """递归创建远程目录。返回 (ok, 中文提示)。目录已存在（405/301/302）视为成功。"""
        segs = self._dir_segments(remote_dir)
        if not segs:
            return True, ""
        path = ""
        for seg in segs:
            path += "/" + _quote_seg(seg)
            url = self.base_url + path + "/"
            resp, code, err = self._request("MKCOL", url)
            self._close(resp)
            if code in (200, 201, 204, 301, 302, 405):
                continue          # 创建成功，或目录已存在（405 Method Not Allowed）
            if code == 0:
                return False, err or "创建 WebDAV 目录失败：网络异常"
            return False, err or ("创建 WebDAV 目录失败（HTTP %d）：%s" % (code, url))
        return True, ""

    # ---------- PROPFIND：列目录 ----------
    def list_dir(self, remote_dir=None) -> tuple:
        """列远程目录（Depth:1）。返回 (ok, items, 中文提示)。

        items 每项：{"name","url","size","is_dir","mtime","mtime_ts"}，按修改时间从新到旧排序。
        """
        url = self._dir_url(remote_dir)
        body = ('<?xml version="1.0" encoding="utf-8"?>'
                '<d:propfind xmlns:d="DAV:"><d:prop>'
                '<d:displayname/><d:getcontentlength/><d:getlastmodified/><d:resourcetype/>'
                '</d:prop></d:propfind>').encode("utf-8")
        resp, code, err = self._request(
            "PROPFIND", url, data=body,
            headers={"Depth": "1", "Content-Type": "application/xml; charset=utf-8"})
        if resp is None:
            if code == 404:
                return False, [], "远程目录不存在（404）：首次使用点「测试连接」会自动创建，或检查远程目录设置"
            return False, [], err or ("读取 WebDAV 目录失败（HTTP %d）" % code)
        try:
            raw = resp.read()
        except Exception as exc:  # noqa: BLE001
            return False, [], "读取 WebDAV 目录响应失败：%s" % exc
        finally:
            self._close(resp)
        if code not in (200, 207):
            return False, [], "读取 WebDAV 目录失败（HTTP %d）" % code
        items = self._parse_propfind(raw, url)
        if items is None:
            return False, [], "解析 WebDAV 目录响应失败：服务器返回的不是标准 WebDAV XML"
        items.sort(key=lambda it: it.get("mtime_ts") or 0, reverse=True)
        return True, items, ""

    def _parse_propfind(self, raw: bytes, dir_url: str):
        """解析 PROPFIND 多状态响应；解析失败返回 None。"""
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return None
        dir_path = urllib.parse.urlsplit(dir_url).path.rstrip("/")
        out = []
        for resp_el in root.iter():
            if _local_name(resp_el.tag) != "response":
                continue
            href = ""
            size = 0
            mtime = ""
            is_dir = False
            for child in resp_el:
                name = _local_name(child.tag)
                if name == "href":
                    href = (child.text or "").strip()
                elif name == "propstat":
                    for prop_wrap in child:
                        if _local_name(prop_wrap.tag) != "prop":
                            continue
                        for prop in prop_wrap:
                            pname = _local_name(prop.tag)
                            if pname == "getcontentlength":
                                size = _as_int(prop.text, 0)
                            elif pname == "getlastmodified":
                                mtime = (prop.text or "").strip()
                            elif pname == "resourcetype":
                                is_dir = any(_local_name(c.tag) == "collection" for c in prop)
            if not href:
                continue
            path = urllib.parse.urlsplit(href).path if href.lower().startswith("http") else href
            decoded = urllib.parse.unquote(path).rstrip("/")
            if not decoded:
                continue
            if dir_path and decoded == dir_path:
                continue          # 跳过目录自身条目
            leaf = decoded.split("/")[-1]
            if not leaf:
                continue
            item_url = href if href.lower().startswith("http") else self._origin() + urllib.parse.quote(
                path if path.startswith("/") else "/" + path, safe="/%:@!$&'()*+,;=~")
            out.append({
                "name": leaf,
                "url": item_url,
                "size": int(size),
                "is_dir": bool(is_dir),
                "mtime": mtime,
                "mtime_ts": _parse_http_date(mtime),
            })
        return out

    # ---------- PUT：上传 ----------
    def upload_file(self, local_path: str, remote_name: str, remote_dir=None, progress_cb=None) -> tuple:
        """上传本地文件。返回 (ok, 远端 URL, 字节数, 中文提示)。"""
        if not os.path.isfile(local_path):
            return False, "", 0, "本地文件不存在：%s" % local_path
        ok, msg = self.ensure_dir(remote_dir)
        if not ok:
            return False, "", 0, msg
        try:
            total = os.path.getsize(local_path)
        except OSError as exc:
            return False, "", 0, "读取本地文件大小失败：%s" % exc
        url = self._file_url(remote_name, remote_dir)
        try:
            fh = open(local_path, "rb")
        except OSError as exc:
            return False, "", 0, "打开本地文件失败：%s" % exc
        try:
            reader = _ProgressReader(fh, total, progress_cb)
            resp, code, err = self._request(
                "PUT", url, data=reader,
                headers={"Content-Type": "application/octet-stream", "Content-Length": str(total)})
            self._close(resp)
        finally:
            try:
                fh.close()
            except Exception:  # noqa: BLE001
                pass
        if code in (200, 201, 204):
            return True, url, total, ""
        if code == 0:
            return False, url, 0, err or "上传失败：网络异常"
        return False, url, 0, err or ("上传失败（HTTP %d）" % code)

    # ---------- GET：下载 ----------
    def download_file(self, remote_name: str, dest_path: str, remote_dir=None,
                      progress_cb=None) -> tuple:
        """下载远端文件到本地路径。返回 (ok, 本地路径, 字节数, 中文提示)。"""
        url = self._file_url(remote_name, remote_dir)
        resp, code, err = self._request("GET", url)
        if resp is None:
            if code == 404:
                return False, "", 0, "云端文件不存在（404）：%s 可能已被删除" % remote_name
            return False, "", 0, err or ("下载失败（HTTP %d）" % code)
        total = _as_int(resp.headers.get("Content-Length"), 0)
        done = 0
        tmp = dest_path + ".part"
        try:
            os.makedirs(os.path.dirname(os.path.abspath(dest_path)) or ".", exist_ok=True)
            with open(tmp, "wb") as out:
                while True:
                    chunk = resp.read(_CHUNK)
                    if not chunk:
                        break
                    out.write(chunk)
                    done += len(chunk)
                    if callable(progress_cb):
                        try:
                            progress_cb(done, total)
                        except Exception:  # noqa: BLE001
                            pass
            os.replace(tmp, dest_path)
        except Exception as exc:  # noqa: BLE001
            self._close(resp)
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass
            return False, "", 0, "下载云端备份失败：%s" % exc
        self._close(resp)
        return True, dest_path, done, ""

    # ---------- DELETE：删除 ----------
    def delete_file(self, remote_name: str, remote_dir=None) -> tuple:
        """删除远端文件。返回 (ok, 中文提示)；404 视为已不存在（成功）。"""
        url = self._file_url(remote_name, remote_dir)
        resp, code, err = self._request("DELETE", url)
        self._close(resp)
        if code in (200, 202, 204):
            return True, ""
        if code == 404:
            return True, "云端文件已不存在（404），视为删除完成"
        if code == 0:
            return False, err or "删除失败：网络异常"
        return False, err or ("删除失败（HTTP %d）" % code)

    # ---------- PROPFIND Depth:0：探测地址可用 ----------
    def probe(self, remote_dir=None) -> tuple:
        """探测远程目录是否存在（Depth:0）。返回 (ok, 是否存在, 中文提示)。"""
        url = self._dir_url(remote_dir)
        body = ('<?xml version="1.0" encoding="utf-8"?>'
                '<d:propfind xmlns:d="DAV:"><d:prop><d:resourcetype/></d:prop></d:propfind>').encode("utf-8")
        resp, code, err = self._request("PROPFIND", url, data=body,
                                       headers={"Depth": "0",
                                                "Content-Type": "application/xml; charset=utf-8"})
        self._close(resp)
        if code in (200, 207):
            return True, True, ""
        if code == 401 or code == 403:
            return False, False, err or ("WebDAV 请求被拒绝（HTTP %d）：请检查账号密码与目录权限" % code)
        if code == 404:
            return True, False, ""
        if code == 0:
            return False, True, err or "连接 WebDAV 失败：网络异常"
        return False, False, err or ("WebDAV 探测失败（HTTP %d）" % code)


def _local_name(tag) -> str:
    """取 XML 标签本地名（去掉 {namespace} 前缀），兼容不同 DAV 命名空间写法。"""
    text = str(tag or "")
    return text.rsplit("}", 1)[-1].lower()


def _parse_http_date(text: str) -> float:
    """把 HTTP Last-Modified（RFC 1123）转时间戳；解析失败返回 0。"""
    raw = (text or "").strip()
    if not raw:
        return 0.0
    try:
        dt = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return 0.0
    if dt is None:
        return 0.0
    try:
        return dt.timestamp()
    except (OverflowError, OSError, ValueError):
        return 0.0


# ============================ 面向 cfg 的便捷封装（供 app/ui 调用） ============================

def make_client(cfg: dict, password: str = None) -> tuple:
    """按 cfg 构造客户端。返回 (client|None, 中文提示)。

    password 传 None 时从 cfg 的 webdav_password_enc 解密；显式传值（如设置窗口里
    刚填的明文）则优先使用，便于「测试连接」在保存前验证。
    """
    st = get_settings(cfg)
    if not st["url"]:
        return None, "尚未配置 WebDAV 地址：请在「设置 → WebDAV 云备份」填写服务器地址"
    if password is None:
        if st["password_enc"]:
            ok, pw, msg = unprotect_password(st["password_enc"])
            if not ok:
                return None, msg
        else:
            pw = ""
    else:
        pw = password
    try:
        client = WebDAVClient(st["url"], st["username"], pw,
                              verify_ssl=st["verify_ssl"], timeout=st["timeout"])
    except Exception as exc:  # noqa: BLE001
        return None, "初始化 WebDAV 客户端失败：%s" % exc
    return client, ""


def test_connection(cfg: dict, password: str = None) -> tuple:
    """测试连接：建目录 + 列目录，返回 (ok, 中文提示)。"""
    st = get_settings(cfg)
    client, msg = make_client(cfg, password)
    if client is None:
        return False, msg
    ok, emsg = client.ensure_dir(st["remote_dir"])
    if not ok:
        return False, "测试连接失败：%s" % emsg
    ok, items, lmsg = client.list_dir(st["remote_dir"])
    if not ok:
        return False, "测试连接失败：%s" % lmsg
    backups = [it for it in items if not it.get("is_dir") and str(it.get("name", "")).lower().endswith(ENC_SUFFIX)]
    return True, ("连接成功：远程目录 %s 可读写（现有加密备份 %d 个）" % (st["remote_dir"], len(backups)))


def upload_backup(cfg: dict, enc_path: str, progress_cb=None) -> tuple:
    """上传加密备份并按 webdav_keep 清理旧备份。返回 (ok, 中文提示)。

    提示里包含远端路径与文件大小，便于写入 manager.log。
    """
    st = get_settings(cfg)
    path = str(enc_path or "")
    if not os.path.isfile(path):
        return False, "待上传的加密备份不存在：%s" % path
    client, msg = make_client(cfg)
    if client is None:
        return False, "上传失败：%s" % msg
    name = os.path.basename(path)
    ok, remote_url, size, umsg = client.upload_file(path, name, st["remote_dir"], progress_cb)
    if not ok:
        return False, "上传云端失败：%s" % (umsg or "未知错误")
    head = "已上传云端：%s（%.2f MB）" % (remote_url, size / 1048576.0)
    tail = ""
    if st["keep"] > 0:
        pok, pmsg = prune_remote(cfg, st["keep"])
        if pok and pmsg:
            tail = "；" + pmsg
        elif not pok:
            tail = "；但清理旧备份失败：%s" % pmsg
    return True, head + tail


def list_remote_backups(cfg: dict) -> tuple:
    """列出远端 .enc 备份。返回 (ok, items, 中文提示)，items 按修改时间从新到旧。"""
    st = get_settings(cfg)
    client, msg = make_client(cfg)
    if client is None:
        return False, [], msg
    ok, items, lmsg = client.list_dir(st["remote_dir"])
    if not ok:
        return False, [], lmsg
    files = [it for it in items
             if not it.get("is_dir") and str(it.get("name", "")).lower().endswith(ENC_SUFFIX)]
    return True, files, ""


def download_backup(cfg: dict, remote_name: str, local_dir: str, progress_cb=None) -> tuple:
    """下载远端备份到本地目录。返回 (ok, 本地路径, 中文提示)。"""
    st = get_settings(cfg)
    name = os.path.basename(str(remote_name or "").strip().replace("\\", "/"))
    if not name:
        return False, "", "未指定要下载的云端备份文件名"
    client, msg = make_client(cfg)
    if client is None:
        return False, "", msg
    try:
        os.makedirs(local_dir, exist_ok=True)
    except OSError as exc:
        return False, "", "创建本地临时目录失败：%s" % exc
    dest = os.path.join(local_dir, name)
    ok, dest_path, size, dmsg = client.download_file(name, dest, st["remote_dir"], progress_cb)
    if not ok:
        return False, "", "下载云端备份失败：%s" % (dmsg or "未知错误")
    return True, dest_path, "已下载云端备份到本地临时位置：%s（%.2f MB）" % (dest_path, size / 1048576.0)


def delete_remote_backup(cfg: dict, remote_name: str) -> tuple:
    """删除远端单个备份。返回 (ok, 中文提示)。"""
    st = get_settings(cfg)
    client, msg = make_client(cfg)
    if client is None:
        return False, msg
    return client.delete_file(remote_name, st["remote_dir"])


def prune_remote(cfg: dict, keep: int = None) -> tuple:
    """按保留份数清理远端旧备份：按修改时间从新到旧，只删除超出 keep 的旧文件。

    keep 为空时取 cfg 的 webdav_keep；keep<=0 表示不删除任何云端文件（默认 0）。
    返回 (ok, 中文提示)；无可清理时提示为空串。
    """
    st = get_settings(cfg)
    limit = st["keep"] if keep is None else max(0, _as_int(keep, 0))
    if limit <= 0:
        return True, ""
    ok, files, msg = list_remote_backups(cfg)
    if not ok:
        return False, msg
    if len(files) <= limit:
        return True, ""
    client, cmsg = make_client(cfg)
    if client is None:
        return False, cmsg
    removed = []
    failed = []
    for item in files[limit:]:
        rok, rmsg = client.delete_file(item["name"], st["remote_dir"])
        if rok:
            removed.append(item["name"])
        else:
            failed.append("%s（%s）" % (item["name"], rmsg))
    if failed:
        return False, "已删除 %d 个旧备份，%d 个删除失败：%s" % (
            len(removed), len(failed), "；".join(failed))
    return True, "已按保留份数 %d 清理 %d 个旧备份：%s" % (limit, len(removed), "、".join(removed))
