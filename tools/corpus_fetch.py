#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Acquire the course corpus: the RAG index AND the source texts.

The course publishes its corpus as links (Google Drive, HTTPS/S3, GitHub
Releases, HuggingFace). This tool fetches both artifacts, verifies them against
the manifests in the repository root, and installs them atomically into
COURSE_CORPUS_ROOT. A course is not ready to teach until this has succeeded:
without the texts a retrieved fragment cannot be verified, and an unverified
quotation is not evidence.

Manifests (repository root):
  index-manifest.json   - the index: annoy.index, embeddings.npy,
                          chunks.jsonl, config.json
  corpus-manifest.json  - the texts: txt/*.txt

Usage:
  python tools/corpus_fetch.py                    # index + texts
  python tools/corpus_fetch.py --index-only       # index only
  python tools/corpus_fetch.py --texts-only       # texts only
  python tools/corpus_fetch.py --status           # report, download nothing
  python tools/corpus_fetch.py --url <link>       # index override (also COURSE_INDEX_URL)
  python tools/corpus_fetch.py --texts-url <link> # texts override (also COURSE_CORPUS_URL)

Exit codes: 0 ok / already installed, 1 failure, 2 usage or environment error.
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
import urllib.parse
import urllib.request
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))

INDEX_MANIFEST = "index-manifest.json"
TEXTS_MANIFEST = "corpus-manifest.json"


# --------------------------------------------------------------------------
# Environment
# --------------------------------------------------------------------------
def resolve_root():
    r = os.environ.get("COURSE_CORPUS_ROOT")
    if not r:
        sys.stderr.write(
            "[corpus_fetch] установите COURSE_CORPUS_ROOT — каталог корпуса "
            "(см. CORPUS.md)\n"
        )
        sys.exit(2)
    return r


def load_manifest(name):
    p = os.path.join(REPO, name)
    if not os.path.exists(p):
        return None
    try:
        # utf-8-sig: manifests are often written by editors and shells
        # (PowerShell Set-Content, Notepad) that prepend a BOM.
        with open(p, encoding="utf-8-sig") as f:
            return json.load(f)
    except (ValueError, OSError) as e:
        sys.stderr.write("[corpus_fetch] %s не читается: %s\n" % (name, e))
        sys.exit(2)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


# --------------------------------------------------------------------------
# Download (Google Drive needs its own flow; plain HTTP is the other path)
# --------------------------------------------------------------------------
def drive_file_id(url):
    m = re.search(r"/file/d/([^/]+)", url) or re.search(r"[?&]id=([^&]+)", url)
    return m.group(1) if m else None


def http_download(url, dest, timeout=600):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        with open(dest, "wb") as f:
            shutil.copyfileobj(r, f, 1 << 20)
    return True


def drive_download(url, dest):
    """Download a Google Drive file (share or uc link). gdown preferred."""
    try:
        import gdown  # noqa: PLC0415

        return bool(gdown.download(url, dest, quiet=False))
    except ImportError:
        pass

    fid = drive_file_id(url)
    if not fid:
        sys.stderr.write("[corpus_fetch] не удалось определить FILE_ID: %s\n" % url)
        return False

    base = "https://drive.google.com/uc?export=download&id=" + urllib.parse.quote(fid)
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    with op.open(urllib.request.Request(base, headers={"User-Agent": "Mozilla/5.0"}), timeout=180) as r:
        ctype = r.headers.get("Content-Type", "")
        data = r.read()

    if "html" in ctype or data[:16].lstrip().startswith(b"<"):
        # Large-file confirm / virus-scan interstitial: follow the form action.
        t = data.decode("utf-8", "replace")
        m_action = re.search(r'<form[^>]*action="([^"]+)"', t)
        inputs = dict(re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]*)"', t))
        cm = re.search(r'name="confirm" value="([^"]+)"', t)
        if not (m_action or inputs.get("confirm") or cm):
            sys.stderr.write(
                "[corpus_fetch] Drive вернул HTML без confirm — проверьте, что файл "
                "открыт по ссылке (shared: anyone with link)\n"
            )
            return False
        action = m_action.group(1) if m_action else base
        params = {
            "export": "download",
            "confirm": inputs.get("confirm") or (cm.group(1) if cm else "t"),
            "id": inputs.get("id", fid),
        }
        if inputs.get("uuid"):
            params["uuid"] = inputs["uuid"]
        url2 = action + "?" + urllib.parse.urlencode(params)
        with op.open(urllib.request.Request(url2, headers={"User-Agent": "Mozilla/5.0"}), timeout=900) as r2:
            data = r2.read()
        if data[:16].lstrip().startswith(b"<"):
            sys.stderr.write(
                "[corpus_fetch] Drive снова вернул HTML; для большого файла "
                "поставьте gdown: pip install gdown\n"
            )
            return False

    with open(dest, "wb") as f:
        f.write(data)
    return True


def download(url, dest):
    if "drive.google.com" in url:
        return drive_download(url, dest)
    return http_download(url, dest)


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------
def verify_archive(path, manifest):
    """Check the archive hash. Returns (ok, level, expected)."""
    expect = (manifest or {}).get("archive", {}).get("sha256")
    if not expect:
        return True, "не проверено хэшем", None
    got = sha256_file(path)
    if got != expect.upper():
        print("  КОНТРОЛЬНАЯ СУММА АРХИВА НЕ СОВПАЛА")
        print("    ожидалось: %s" % expect.upper())
        print("    получено : %s" % got)
        return False, "хэш не совпал", expect
    return True, "SHA-256 архива подтверждена", expect


def verify_members(unpack, manifest):
    """Check every file listed in the manifest, before installing."""
    for f in (manifest or {}).get("files", []):
        fp = os.path.join(unpack, f["path"])
        if not os.path.exists(fp):
            print("  в архиве нет файла %s" % f["path"])
            return False
        if f.get("sha256"):
            got = sha256_file(fp)
            if got != f["sha256"].upper():
                print("  файл %s: контрольная сумма не совпала" % f["path"])
                return False
        size = f.get("size_bytes")
        if size and os.path.getsize(fp) != size:
            print("  файл %s: размер %d != %d" % (f["path"], os.path.getsize(fp), size))
            return False
    return True


def verify_structure(unpack, kind):
    """Structural fallback when no hashes are published. Says so explicitly."""
    if kind == "index":
        need = ["annoy.index", "embeddings.npy", "chunks.jsonl", "config.json"]
    else:
        need = []
    if not need:
        return True
    if not os.path.isdir(unpack):
        return False
    for n in need:
        if not any(
            os.path.exists(os.path.join(dp, n))
            for dp, _dn, _fn in os.walk(unpack)
        ):
            print("  структурная проверка: нет %s" % n)
            return False
    return True


def find_tree_root(unpack, kind):
    """Archives vary: files may sit at the root or inside a single folder."""
    if kind == "index" and os.path.exists(os.path.join(unpack, "config.json")):
        return unpack
    entries = [e for e in os.listdir(unpack) if not e.startswith(".")]
    if len(entries) == 1 and os.path.isdir(os.path.join(unpack, entries[0])):
        return os.path.join(unpack, entries[0])
    return unpack


# --------------------------------------------------------------------------
# Install
# --------------------------------------------------------------------------
def install_dir(src, dst):
    """Install atomically: move the old aside, then move the new in."""
    bak = dst + "_old"
    shutil.rmtree(bak, ignore_errors=True)
    if os.path.exists(dst):
        os.rename(dst, bak)
    try:
        os.rename(src, dst)
    except OSError:
        shutil.move(src, dst)


def fetch_artifact(label, url, manifest, root, kind, subdir, dest_name):
    """Download, verify and install one artifact. Returns a status string."""
    print()
    print("== %s ==" % label)
    if not url:
        print("  ссылка не задана (ни --url, ни манифест) — пропуск")
        return "no-url"

    target = os.path.join(root, dest_name)
    tmp = tempfile.mkdtemp(prefix="corpus_fetch_")
    try:
        zpath = os.path.join(tmp, "artifact.zip")
        print("  скачивание: %s" % url)
        try:
            if not download(url, zpath):
                print("  ОШИБКА: загрузка не удалась")
                return "download-failed"
        except Exception as e:  # noqa: BLE001 - report, never crash the deploy
            print("  ОШИБКА загрузки: %s: %s" % (type(e).__name__, e))
            return "download-failed"

        ok, level, _exp = verify_archive(zpath, manifest)
        if not ok:
            return "hash-mismatch"
        print("  %s" % level)

        unpack = os.path.join(tmp, "unpacked")
        os.makedirs(unpack)
        try:
            with zipfile.ZipFile(zpath) as z:
                z.extractall(unpack)
        except zipfile.BadZipFile:
            print("  ОШИБКА: скачанный файл не является zip-архивом")
            return "bad-archive"

        if not verify_members(unpack, manifest):
            return "member-mismatch"
        if not verify_structure(unpack, kind):
            return "structure-mismatch"
        if not (manifest or {}).get("archive", {}).get("sha256"):
            print("  структурная проверка пройдена (хэшем НЕ проверялось)")

        src = find_tree_root(unpack, kind)
        os.makedirs(target if not os.path.exists(target) else os.path.dirname(target), exist_ok=True)
        if subdir:
            # Index installs wholesale into <root>/index/.
            pass
        install_dir(src, target)

        print("  установлено: %s" % target)
        cfg = os.path.join(target, "config.json")
        if os.path.exists(cfg):
            try:
                with open(cfg, encoding="utf-8") as f:
                    c = json.load(f)
                print(
                    "  chunks: %s, files: %s, backend: %s"
                    % (c.get("n_chunks"), c.get("n_files"), c.get("backend"))
                )
            except (ValueError, OSError):
                pass
        return "ok"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------
# Status
# --------------------------------------------------------------------------
def status(root, want_index=True, want_texts=True):
    """Report corpus state. `want_*` scopes the verdict to what was requested:
    an index-only run must not be called incomplete because texts are absent."""
    idx = os.path.join(root, "index")
    txt = os.path.join(root, "txt")
    idx_ok = os.path.exists(os.path.join(idx, "config.json"))
    n_txt = len([f for f in os.listdir(txt) if f.endswith(".txt")]) if os.path.isdir(txt) else 0
    print("COURSE_CORPUS_ROOT : %s" % root)
    print("  index/           : %s" % ("есть (config.json найден)" if idx_ok else "НЕТ"))
    print("  txt/             : %s" % ("%d текстов" % n_txt if n_txt else "НЕТ"))

    have = (idx_ok if want_index else True) and (bool(n_txt) if want_texts else True)
    if have:
        print("состояние          : корпус на месте")
        print("  поиск:            make search QUERY=\"...\"")
        print("  проверка цитат:   make verify")
        return 0

    print("состояние          : корпус НЕ УСТАНОВЛЕН или неполон")
    if want_texts and not n_txt:
        print("  цитаты проверять нечем: без текстов фрагмент не подтверждается")
    print("  выполните:        python tools/corpus_fetch.py")
    return 1


def main():
    ap = argparse.ArgumentParser(description="Получение корпуса курса (индекс + тексты)")
    ap.add_argument("--url", default=os.environ.get("COURSE_INDEX_URL", ""),
                    help="ссылка на архив индекса (иначе из index-manifest.json)")
    ap.add_argument("--texts-url", default=os.environ.get("COURSE_CORPUS_URL", ""),
                    help="ссылка на архив текстов (иначе из corpus-manifest.json)")
    ap.add_argument("--index-only", action="store_true", help="только индекс")
    ap.add_argument("--texts-only", action="store_true", help="только тексты")
    ap.add_argument("--status", action="store_true", help="только отчёт, без загрузки")
    ap.add_argument("--force", action="store_true", help="переустановить даже если корпус есть")
    a = ap.parse_args()

    root = resolve_root()

    if a.status:
        return status(root)
    idx_manifest = load_manifest(INDEX_MANIFEST)
    txt_manifest = load_manifest(TEXTS_MANIFEST)

    do_index = not a.texts_only
    do_texts = not a.index_only

    if do_index and not (a.url or (idx_manifest or {}).get("archive", {}).get("url")):
        if not do_texts:
            sys.stderr.write(
                "[corpus_fetch] нет ссылки на индекс: укажите --url или COURSE_INDEX_URL,\n"
                "либо заполните archive.url в %s (см. docs/GOOGLE-DRIVE.md)\n" % INDEX_MANIFEST
            )
            return 2
        print("== индекс ==\n  манифест %s отсутствует или без url — индекс пропущен" % INDEX_MANIFEST)

    if not do_texts and not do_index:
        sys.stderr.write("[corpus_fetch] нечего делать: --index-only и --texts-only вместе\n")
        return 2

    # Idempotence: an installed corpus is left alone unless --force.
    if not a.force:
        st = status(root, want_index=do_index, want_texts=do_texts)
        if st == 0:
            print()
            print("корпус уже установлен; повторная загрузка не нужна (--force чтобы переустановить)")
            return 0

    results = {}

    if do_index:
        url = a.url or (idx_manifest or {}).get("archive", {}).get("url")
        if url:
            results["index"] = fetch_artifact(
                "индекс корпуса", url, idx_manifest, root, "index", None, "index"
            )

    if do_texts:
        url = a.texts_url or (txt_manifest or {}).get("archive", {}).get("url")
        if not url:
            print()
            print("== тексты ==")
            print("  в %s нет archive.url — тексты не опубликованы" % TEXTS_MANIFEST)
            print("  без текстов цитаты проверить нечем (см. CORPUS.md)")
            results["texts"] = "no-url"
        else:
            results["texts"] = fetch_artifact(
                "тексты корпуса", url, txt_manifest, root, "texts", "txt", "txt"
            )

    print()
    print("итог:")
    bad = []
    for k, v in results.items():
        mark = "ок" if v == "ok" else v
        print("  %-6s: %s" % (k, mark))
        if v not in ("ok", "no-url"):
            bad.append(k)

    if bad:
        print()
        print("НЕ УДАЛОСЬ получить: %s" % ", ".join(bad))
        print("  причина указана выше. Мёртвую ссылку СООБЩИТЕ сопровождающему курса;")
        print("  подставлять другую ссылку самостоятельно нельзя.")
        return 1

    print()
    return status(root, want_index=do_index, want_texts=do_texts)


if __name__ == "__main__":
    sys.exit(main())
