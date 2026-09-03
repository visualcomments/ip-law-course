#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch the course index/embeddings from Google Drive and install it into
COURSE_CORPUS_ROOT/index/ (atomic swap, SHA-256 verified).

Sources (priority):
  1) --url <share-link|direct-link>  (or env COURSE_INDEX_URL)
  2) index-manifest.json in repo root (created from the example once you
     publish the file on Drive and fill "url")

Requires: python3 (+ optional `pip install gdown` for the most reliable
Drive download; a stdlib fallback with confirm-token handling is included).

Usage:
  python tools/index_fetch.py --url "https://drive.google.com/file/d/FILE_ID/view?usp=sharing"
  python tools/index_fetch.py                      # reads index-manifest.json
"""
import argparse
import http.cookiejar
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))


def resolve_root():
    r = os.environ.get("COURSE_CORPUS_ROOT")
    if not r:
        sys.stderr.write("[index_fetch] установите COURSE_CORPUS_ROOT (каталог корпуса, см. CORPUS.md)\n")
        sys.exit(2)
    return r


def drive_download(url, dest):
    """Download a Google Drive file (share or uc link) to dest. gdown preferred."""
    try:
        import gdown  # noqa: PLC0415
        ok = gdown.download(url, dest, quiet=False)
        return bool(ok)
    except ImportError:
        pass
    m = re.search(r"/file/d/([^/]+)", url)
    m2 = re.search(r"[?&]id=([^&]+)", url)
    fid = (m or m2).group(1) if (m or m2) else None
    if not fid:
        sys.stderr.write("[index_fetch] не удалось определить FILE_ID из ссылки: " + url + "\n")
        return False
    base = "https://drive.google.com/uc?export=download&id=" + urllib.parse.quote(fid)
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    req = urllib.request.Request(base, headers={"User-Agent": "Mozilla/5.0"})
    with op.open(req, timeout=180) as r:
        ctype = r.headers.get("Content-Type", "")
        data = r.read()
    if "html" in ctype or data[:16].lstrip().startswith(b"<"):
        # large-file confirm / virus-scan page: follow the form action
        t = data.decode("utf-8", "replace")
        m_action = re.search(r'<form[^>]*action="([^"]+)"', t)
        inputs = dict(re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]*)"', t))
        cm = re.search(r'name="confirm" value="([^"]+)"', t)
        if not (m_action or inputs.get("confirm") or cm):
            sys.stderr.write("[index_fetch] Drive вернул HTML без confirm; проверьте доступность файла (shared: anyone with link)\n")
            return False
        action = m_action.group(1) if m_action else base
        params = {"export": "download", "confirm": (inputs.get("confirm") or cm.group(1) if cm else "t")}
        params["id"] = inputs.get("id", fid)
        if inputs.get("uuid"):
            params["uuid"] = inputs["uuid"]
        url2 = action + "?" + urllib.parse.urlencode(params)
        with op.open(urllib.request.Request(url2, headers={"User-Agent": "Mozilla/5.0"}), timeout=600) as r2:
            data = r2.read()
        if data[:16].lstrip().startswith(b"<"):
            sys.stderr.write("[index_fetch] Drive снова вернул HTML; возможно, нужен pip install gdown (большой файл)\n")
            return False
    with open(dest, "wb") as f:
        f.write(data)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("COURSE_INDEX_URL", ""))
    a = ap.parse_args()

    manifest = None
    mp = os.path.join(REPO, "index-manifest.json")
    if os.path.exists(mp):
        manifest = json.load(open(mp, encoding="utf-8"))
    url = a.url or (manifest or {}).get("archive", {}).get("url") or ""
    if not url:
        sys.stderr.write(
            "[index_fetch] укажите --url (share-ссылка Google Drive) или COURSE_INDEX_URL,\n"
            "либо заполните url в index-manifest.json (см. index-manifest.example.json и docs/GOOGLE-DRIVE.md)\n")
        return 2

    root = resolve_root()
    idx = os.path.join(root, "index")
    os.makedirs(idx, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="index_fetch_")
    try:
        zpath = os.path.join(tmp, "course-index.zip")
        print(f"[index_fetch] скачивание: {url}")
        if not drive_download(url, zpath):
            print("[index_fetch] ОШИБКА: загрузка не удалась")
            return 1
        expect = None
        if manifest:
            expect = manifest["archive"].get("sha256")
        if expect:
            import hashlib  # noqa: PLC0415
            h = hashlib.sha256(open(zpath, "rb").read()).hexdigest().upper()
            if h != expect.upper():
                print(f"[index_fetch] КОНТРОЛЬНАЯ СУММА НЕ СОВПАЛА: {h} != {expect.upper()}")
                return 1
            print("[index_fetch] SHA-256 подтверждена")
        unpack = os.path.join(tmp, "unpacked")
        os.makedirs(unpack)
        with zipfile.ZipFile(zpath) as z:
            z.extractall(unpack)
        if manifest:
            for f in manifest["files"]:
                fp = os.path.join(unpack, f["path"])
                if not os.path.exists(fp):
                    print(f"[index_fetch] в архиве нет файла {f['path']}")
                    return 1
                h = hashlib.sha256(open(fp, "rb").read()).hexdigest().upper()
                if h != f["sha256"].upper():
                    print(f"[index_fetch] файл {f['path']}: контрольная сумма не совпала")
                    return 1
        # atomic swap
        bak = os.path.join(root, "index_old")
        shutil.rmtree(bak, ignore_errors=True)
        if os.path.exists(idx):
            os.rename(idx, bak)
        try:
            os.rename(unpack, idx)
        except OSError:
            shutil.move(unpack, idx)
        print(f"[index_fetch] индекс установлен: {idx}")
        cfg = os.path.join(idx, "config.json")
        if os.path.exists(cfg):
            c = json.load(open(cfg, encoding="utf-8"))
            print(f"[index_fetch] chunks: {c.get('n_chunks')}, files: {c.get('n_files')}, "
                  f"backend: {c.get('backend')}")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())