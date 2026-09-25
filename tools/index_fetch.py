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
import hashlib
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
        sys.stderr.write(
            "[index_fetch] установите COURSE_CORPUS_ROOT (каталог корпуса, см. CORPUS.md)\n"
        )
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
        sys.stderr.write(
            "[index_fetch] не удалось определить FILE_ID из ссылки: " + url + "\n"
        )
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
        inputs = dict(
            re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]*)"', t)
        )
        cm = re.search(r'name="confirm" value="([^"]+)"', t)
        if not (m_action or inputs.get("confirm") or cm):
            sys.stderr.write(
                "[index_fetch] Drive вернул HTML без confirm; проверьте доступность файла (shared: anyone with link)\n"
            )
            return False
        action = m_action.group(1) if m_action else base
        params = {
            "export": "download",
            "confirm": (inputs.get("confirm") or cm.group(1) if cm else "t"),
        }
        params["id"] = inputs.get("id", fid)
        if inputs.get("uuid"):
            params["uuid"] = inputs["uuid"]
        url2 = action + "?" + urllib.parse.urlencode(params)
        with op.open(
            urllib.request.Request(url2, headers={"User-Agent": "Mozilla/5.0"}),
            timeout=600,
        ) as r2:
            data = r2.read()
        if data[:16].lstrip().startswith(b"<"):
            sys.stderr.write(
                "[index_fetch] Drive снова вернул HTML; возможно, нужен pip install gdown (большой файл)\n"
            )
            return False
    with open(dest, "wb") as f:
        f.write(data)
    return True


def safe_extract(zpath, dest):
    """Extract a zip, refusing path traversal, absolute paths and symlinks.

    Returns the number of files extracted. Raises RuntimeError on a bad member.
    """
    dest_abs = os.path.abspath(dest)
    count = 0
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            name = info.filename
            # Reject absolute paths and Windows drive/UNC prefixes.
            if name.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", name):
                raise RuntimeError(f"���� �������: ���������� ���� {name!r}")
            # Reject traversal after normalisation.
            target = os.path.abspath(os.path.join(dest_abs, name))
            if target != dest_abs and not target.startswith(dest_abs + os.sep):
                raise RuntimeError(f"���� �������: ����� �� ����� {name!r}")
            # Reject symlinks (external attribute bit 0xA000).
            mode = (info.external_attr >> 16) & 0xF000
            if mode == 0xA000:
                raise RuntimeError(f"���� �������: ���ᨭ����� ������ {name!r}")
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
            count += 1
    return count



def hf_fetch_manifest_files(repo_url, manifest, root, unpack_dir):
    """Fetch the four index files individually from a HuggingFace dataset repo.

    HF serves each file at                                                      :resolve/main/<name>.
    We download each file, verify its sha256 against the manifest (per-file),
    and write it into unpack_dir -- so the rest of main()'s atomic-swap logic
    stays identical to the Drive Zip path.
    """
    base = repo_url.rstrip("/")
    if base.endswith("/repos/"):
        base = base[:-len("/repos/")]
    # Normalise a HF repo URL to the resolve form.
    m = re.search(r"huggingface\.co/(datasets/)?([^/]+/[^/]+?)(/.*)?$", base)
    if not m:
        sys.stderr.write("[index_fetch] not a HF repo URL: %s\n" % repo_url)
        return False
    repo_id = m.group(2)
    if not repo_id.startswith("datasets/"):
        repo_id = "datasets/" + repo_id
    # per-file resolve URL (public repo, no token needed)
    n = 0
    for f in manifest.get("files", []):
        path = f["path"]
        fname = path.split("/")[-1]
        url = ("https://huggingface.co/%s/resolve/main/%s"
               % (repo_id, urllib.parse.quote(fname)))
        dest = os.path.join(unpack_dir, fname)
        sys.stdout.write("[index_fetch] HF download %s -> %s\n" % (fname, url))
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=600) as r:
            data = r.read()
            # follow the Content-Disposition/LFS redirect if any
        h = hashlib.sha256(data).hexdigest().upper()
        want = f["sha256"].upper()
        if h != want:
            sys.stderr.write(
                "[index_fetch] HF file %s: sha256 mismatch %s != %s\n"
                % (fname, h, want))
            return False
        with open(dest, "wb") as fh:
            fh.write(data)
        n += 1
    return n > 0


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
            "либо заполните url в index-manifest.json (см. index-manifest.example.json и docs/GOOGLE-DRIVE.md)\n"
        )
        return 2

    root = resolve_root()
    idx = os.path.join(root, "index")
    os.makedirs(idx, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="index_fetch_")
    tmp = tempfile.mkdtemp(prefix="index_fetch_")
    try:
        # HuggingFace source: manifest pins archive.kind=="huggingface", or --url is an
        # HF repo URL. Then fetch the four files individually (resolve/main URLs).
        hf_url = None
        if "huggingface.co" in url:
            hf_url = url
        elif manifest and manifest.get("archive", {}).get("kind") == "huggingface":
            hf_url = manifest["archive"].get("url") or manifest["archive"].get("repo_id") or ""
        if hf_url:
            unpack = os.path.join(tmp, "unpacked")
            os.makedirs(unpack)
            print("[index_fetch] source: HuggingFace")
            if not hf_fetch_manifest_files(hf_url, manifest, root, unpack):
                print("[index_fetch] ERROR: HF fetch failed")
                return 1
            n_extracted = len(manifest.get("files", []))
        else:
            zpath = os.path.join(tmp, "course-index.zip")
            print(f"[index_fetch] downloading: {url}")
            if not drive_download(url, zpath):
                print("[index_fetch] ERROR: download failed")
                return 1
            expect = None
            if manifest:
                expect = manifest["archive"].get("sha256")
            if expect:
                h = hashlib.sha256(open(zpath, "rb").read()).hexdigest().upper()
                if h != expect.upper():
                    print("[index_fetch] SHA256 MISMATCH: %s != %s" % (h, expect.upper()))
                    return 1
                print("[index_fetch] SHA-256 OK")
            else:
                print("[index_fetch] NO archive.sha256 - structural check only")
            unpack = os.path.join(tmp, "unpacked")
            os.makedirs(unpack)
            try:
                n_extracted = safe_extract(zpath, unpack)
            except (RuntimeError, zipfile.BadZipFile) as exc:
                print("[index_fetch] archive rejected by safe_extract: %s" % exc)
                return 1
            print("[index_fetch] extracted files: %d" % n_extracted)
        if manifest:
            for f in manifest["files"]:
                fn = f["path"].split("/")[-1]
                fp = os.path.join(unpack, fn)
                if not os.path.exists(fp):
                    print("[index_fetch] missing file %s" % f["path"])
                    return 1
                h = hashlib.sha256(open(fp, "rb").read()).hexdigest().upper()
                if h != f["sha256"].upper():
                    print("[index_fetch] file %s: sha256 mismatch" % f["path"])
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
        # Drop the backup once the new index is in place: at rest the root
        # must hold exactly one index, not two (index_old leaked 61 MB before).
        shutil.rmtree(bak, ignore_errors=True)
        print(f"[index_fetch] индекс установлен: {idx}")
        cfg = os.path.join(idx, "config.json")
        if os.path.exists(cfg):
            c = json.load(open(cfg, encoding="utf-8"))
            print(
                f"[index_fetch] chunks: {c.get('n_chunks')}, files: {c.get('n_files')}, "
                f"backend: {c.get('backend')}"
            )
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
