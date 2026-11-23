# -*- coding: utf-8 -*-
"""v1.10.0 验证脚本：WebDAV 客户端 + DPAPI 密码保护（本地 Mock WebDAV 服务，不联网）。

覆盖：DPAPI 加解密往返、check_ready、MKCOL 递归建目录、PUT 上传、PROPFIND 列目录、
GET 下载、DELETE 删除、按保留份数清理、401/404/507 与网络异常中文提示。
运行：python tests\\verify_webdav_v1100.py
"""
import base64
import email.utils
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from vwm import webdav  # noqa: E402

USER = "davuser"
PWD = "dav pass!@#"
DAV_PREFIX = "/dav"
AUTH = "Basic " + base64.b64encode(("%s:%s" % (USER, PWD)).encode("utf-8")).decode("ascii")

DATA_ROOT = tempfile.mkdtemp(prefix="vwm_dav_")
FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("PASS  %s" % name)
    else:
        print("FAIL  %s  %s" % (name, detail))
        FAILS.append(name)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    # ---- 工具 ----
    def _authed(self):
        if self.headers.get("Authorization") != AUTH:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="dav"')
            self.send_header("Content-Length", "0")
            self.end_headers()
            return False
        return True

    def _fs(self):
        rel = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
        if rel.startswith(DAV_PREFIX):
            rel = rel[len(DAV_PREFIX):]
        rel = rel.strip("/")
        return os.path.join(DATA_ROOT, *rel.split("/")) if rel else DATA_ROOT

    def _empty(self, code):
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self.end_headers()

    # ---- 方法 ----
    def do_MKCOL(self):
        if not self._authed():
            return
        target = self._fs()
        if os.path.isdir(target):
            return self._empty(405)
        parent = os.path.dirname(target)
        if not os.path.isdir(parent):
            return self._empty(409)
        try:
            os.makedirs(target, exist_ok=True)
        except OSError:
            return self._empty(500)
        return self._empty(201)

    def do_PUT(self):
        if not self._authed():
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        target = self._fs()
        if not os.path.isdir(os.path.dirname(target)):
            return self._empty(409)
        with open(target, "wb") as f:
            f.write(body)
        return self._empty(201)

    def do_GET(self):
        if not self._authed():
            return
        target = self._fs()
        if not os.path.isfile(target):
            return self._empty(404)
        with open(target, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()
        self.wfile.write(body)

    def do_DELETE(self):
        if not self._authed():
            return
        target = self._fs()
        if not os.path.isfile(target):
            return self._empty(404)
        try:
            os.remove(target)
        except OSError:
            return self._empty(500)
        return self._empty(204)

    def do_PROPFIND(self):
        if not self._authed():
            return
        target = self._fs()
        if not os.path.isdir(target):
            return self._empty(404)
        entries = [target]
        for name in sorted(os.listdir(target)):
            entries.append(os.path.join(target, name))
        parts = ['<?xml version="1.0" encoding="utf-8"?><d:multistatus xmlns:d="DAV:">']
        for path in entries:
            rel = "/" + os.path.relpath(path, DATA_ROOT).replace(os.sep, "/")
            if os.path.isdir(path):
                rel += "/"
            href = DAV_PREFIX + rel
            st = os.stat(path)
            lm = email.utils.formatdate(st.st_mtime, usegmt=True)
            if os.path.isdir(path):
                parts.append(
                    "<d:response><d:href>%s</d:href><d:propstat><d:prop>"
                    "<d:resourcetype><d:collection/></d:resourcetype>"
                    "<d:getlastmodified>%s</d:getlastmodified>"
                    "</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>"
                    % (href, lm))
            else:
                parts.append(
                    "<d:response><d:href>%s</d:href><d:propstat><d:prop>"
                    "<d:getcontentlength>%d</d:getcontentlength>"
                    "<d:getlastmodified>%s</d:getlastmodified><d:resourcetype/>"
                    "</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>"
                    % (href, st.st_size, lm))
        parts.append("</d:multistatus>")
        body = "".join(parts).encode("utf-8")
        self.send_response(207)
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main():
    # ---------- 1. DPAPI ----------
    st, enc, msg = webdav.protect_password("s3cret-P@ss")
    check("DPAPI 加密成功", st and enc != "" and "s3cret" not in enc, msg)
    st2, plain, msg2 = webdav.unprotect_password(enc)
    check("DPAPI 解密还原", st2 and plain == "s3cret-P@ss", msg2)
    st3, _, msg3 = webdav.protect_password("")
    check("空密码不加密并给中文提示", (not st3) and "密码为空" in msg3, msg3)
    st4, _, msg4 = webdav.unprotect_password("not-a-valid-blob")
    check("损坏密文不抛异常且中文提示", (not st4) and msg4, msg4)

    srv = serve()
    port = srv.server_address[1]
    base = "http://127.0.0.1:%d%s" % (port, DAV_PREFIX)

    cfg = {
        "webdav_enabled": True,
        "webdav_url": base,
        "webdav_username": USER,
        "webdav_password_enc": enc,
        "webdav_verify_ssl": True,
        "webdav_timeout": 20,
        "webdav_keep": 0,
        "webdav_remote_dir": "vaultwarden-backup/sub",
    }
    cfg["webdav_password_enc"] = webdav.protect_password(PWD)[1]

    # ---------- 2. check_ready ----------
    ok, m = webdav.check_ready({})
    check("未配置时 check_ready 返回 False+引导", (not ok) and "设置" in m, m)
    ok, m = webdav.check_ready(cfg)
    check("配置完整时 check_ready 通过", ok, m)

    # ---------- 3. 测试连接（含 MKCOL 递归建目录） ----------
    ok, m = webdav.test_connection(cfg)
    check("测试连接成功（自动建多级目录）", ok, m)
    check("远程目录已真实创建", os.path.isdir(os.path.join(DATA_ROOT, "vaultwarden-backup", "sub")))

    # ---------- 4. 上传 ----------
    local = os.path.join(tempfile.mkdtemp(prefix="vwm_enc_"), "data_20261124_100000_ab12.enc")
    payload = b"VWM_ENC_V2\n" + os.urandom(4096)
    with open(local, "wb") as f:
        f.write(payload)
    ok, m = webdav.upload_backup(cfg, local)
    check("上传加密备份成功且提示含远端路径与大小", ok and "vaultwarden-backup/sub" in m and "MB" in m, m)
    remote_fs = os.path.join(DATA_ROOT, "vaultwarden-backup", "sub", os.path.basename(local))
    check("服务器端文件字节一致", os.path.isfile(remote_fs) and open(remote_fs, "rb").read() == payload)

    # ---------- 5. 列目录 ----------
    ok, items, m = webdav.list_remote_backups(cfg)
    check("列目录返回 1 个 .enc", ok and len(items) == 1 and items[0]["name"] == os.path.basename(local), m)
    if items:
        check("列目录解析出大小", items[0]["size"] == len(payload), str(items[0]))

    # ---------- 6. 下载 ----------
    dl_dir = tempfile.mkdtemp(prefix="vwm_dl_")
    ok, path, m = webdav.download_backup(cfg, os.path.basename(local), dl_dir)
    check("下载成功且内容一致", ok and os.path.isfile(path) and open(path, "rb").read() == payload, m)

    # ---------- 7. 保留份数清理 ----------
    for i, ts in enumerate((time.time() - 300, time.time() - 200)):
        name = "data_2026112%d_090000_%04x.enc" % (i, i)
        with open(os.path.join(os.path.dirname(local), name), "wb") as f:
            f.write(b"VWM_ENC_V2\n" + bytes(64))
        webdav.upload_backup(cfg, os.path.join(os.path.dirname(local), name))
    ok, items, _ = webdav.list_remote_backups(cfg)
    check("清理前共 3 个备份", ok and len(items) == 3, str(len(items)))
    cfg["webdav_keep"] = 1
    ok, m = webdav.prune_remote(cfg)
    check("按保留份数 1 清理旧备份", ok and "已按保留份数 1 清理 2 个" in m, m)
    ok, items, _ = webdav.list_remote_backups(cfg)
    check("清理后仅剩 1 个（最新）", ok and len(items) == 1, str([i["name"] for i in items]))
    cfg["webdav_keep"] = 0
    ok, m = webdav.prune_remote(cfg)
    check("keep=0 不删除任何文件", ok and m == "", m)

    # ---------- 8. 上传后自动按 keep 清理 ----------
    cfg["webdav_keep"] = 1
    with open(os.path.join(os.path.dirname(local), "data_20261124_120000_ff00.enc"), "wb") as f:
        f.write(b"VWM_ENC_V2\n" + bytes(64))
    ok, m = webdav.upload_backup(cfg, os.path.join(os.path.dirname(local), "data_20261124_120000_ff00.enc"))
    check("上传后自动触发清理并提示", ok and "清理" in m, m)
    cfg["webdav_keep"] = 0

    # ---------- 9. 删除 ----------
    ok, items, _ = webdav.list_remote_backups(cfg)
    name = items[0]["name"]
    ok, m = webdav.delete_remote_backup(cfg, name)
    check("删除单个云端备份成功", ok, m)
    ok, m = webdav.delete_remote_backup(cfg, name)
    check("重复删除按成功处理（404 视为已删）", ok, m)

    # ---------- 10. 错误提示 ----------
    bad = dict(cfg)
    bad["webdav_password_enc"] = webdav.protect_password("wrong-pass")[1]
    ok, m = webdav.test_connection(bad)
    check("401 给中文认证失败提示", (not ok) and "401" in m and "认证失败" in m, m)

    missing = dict(cfg)
    ok, path, m = webdav.download_backup(missing, "no_such_file.enc", dl_dir)
    check("下载不存在文件给 404 中文提示", (not ok) and "404" in m, m)

    check("507 提示存储空间不足", "存储空间不足" in webdav._friendly_http_error(507))
    check("403 提示无权限", "拒绝访问" in webdav._friendly_http_error(403))

    closed = socket.socket()
    closed.bind(("127.0.0.1", 0))
    free_port = closed.getsockname()[1]
    closed.close()
    dead = dict(cfg)
    dead["webdav_url"] = "http://127.0.0.1:%d/dav" % free_port
    dead["webdav_timeout"] = 5
    ok, m = webdav.test_connection(dead)
    check("网络不可达给中文提示", (not ok) and ("无法连接" in m or "网络异常" in m), m)

    # ---------- 11. 配置兜底 ----------
    st = webdav.get_settings({})
    check("缺键时配置兜底（超时 60、目录 vaultwarden-backup、keep 0）",
          st["timeout"] == 60 and st["remote_dir"] == "vaultwarden-backup" and st["keep"] == 0, str(st))
    check("远程目录规范化去斜杠", webdav.normalize_remote_dir("/a//b/") == "a/b",
          webdav.normalize_remote_dir("/a//b/"))
    check("地址自动补协议", webdav.normalize_base_url("dav.example.com/x/") == "https://dav.example.com/x",
          webdav.normalize_base_url("dav.example.com/x/"))

    srv.shutdown()
    print("\n==== 结果：%d 项失败 ====" % len(FAILS))
    if FAILS:
        print("失败项：" + "、".join(FAILS))
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
