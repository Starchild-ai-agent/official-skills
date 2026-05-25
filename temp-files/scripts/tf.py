#!/usr/bin/env python3
"""Workroom temp-files CLI — single entry point for the temp-files skill.

Subcommands:
    put   <local> <remote-path> [--ttl-days N] [--ttl-seconds N]
    put-dir <local-dir> <remote-prefix> [--ttl-days N]
    get   <remote-path> <local-dest> [--zip]
    list  [--prefix PATH] [--json]
    rm    <remote-path> [--recursive]
    link  <remote-path> [--zip|--file|--auto] [--ttl-seconds N]
    links [--json]
    unlink <code>
    fetch <code> <local-dest>

Environment:
    CONTAINER_JWT       Required.
    TEMP_STORAGE_URL    Optional. Defaults to http://sc-agent-backup.internal:8080.

Exit codes:
    0   success (or "nothing to list" — stdout tells the story)
    1   transport / auth / protocol failure (stderr has the detail)
    2   bad CLI usage
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_STORAGE = "http://sc-agent-backup.internal:8080"
PUT_TIMEOUT = 600
GET_TIMEOUT = 600
DEFAULT_TIMEOUT = 30
MAX_TTL_DAYS = 60
MAX_LINK_TTL_SECONDS = 7 * 24 * 3600


def _storage_url() -> str:
    return os.environ.get("TEMP_STORAGE_URL", DEFAULT_STORAGE).rstrip("/")


def _jwt() -> str:
    token = os.environ.get("CONTAINER_JWT", "").strip()
    if not token:
        print("ERROR: CONTAINER_JWT env var is not set.", file=sys.stderr)
        sys.exit(1)
    return token


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_jwt()}"}


OUTPUT_JSON = False
VERBOSE = False


def _emit_json_error(msg: str, *, err: str = "error", detail: str = "", code: int = 1,
                     meta: dict | None = None) -> None:
    payload = {
        "ok": False,
        "error": err,
        "message": msg,
        "detail": detail or "",
        "exit_code": code,
    }
    if VERBOSE and meta:
        payload["meta"] = meta
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)


def _fail(msg: str, *, detail: str = "", err: str = "error", code: int = 1,
          meta: dict | None = None) -> None:
    if OUTPUT_JSON:
        _emit_json_error(msg, err=err, detail=detail, code=code, meta=meta)
    else:
        print(f"ERROR: {msg}", file=sys.stderr)
        if detail:
            print(f"DETAIL: {detail}", file=sys.stderr)
        if VERBOSE and meta:
            print(f"META: {json.dumps(meta, ensure_ascii=False)}", file=sys.stderr)
    sys.exit(code)


def _usage_fail(msg: str) -> None:
    _fail(msg, err="usage_error", code=2)


def _parse_error_fields(body: bytes) -> tuple[str, str, str]:
    text = (body or b"").decode("utf-8", errors="replace").strip()
    if not text:
        return "", "", ""
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            err = str(obj.get("error") or "").strip()
            message = str(obj.get("message") or "").strip()
            detail = obj.get("detail")
            if isinstance(detail, (dict, list)):
                detail = json.dumps(detail, ensure_ascii=False)
            detail = str(detail or "").strip()
            return err, message, detail
    except json.JSONDecodeError:
        pass
    return "", text, ""


def _error_detail(body: bytes) -> str:
    err, message, detail = _parse_error_fields(body)
    parts = []
    if err:
        parts.append(f"error={err}")
    if message:
        parts.append(f"message={message}")
    if detail:
        parts.append(f"detail={detail}")
    if parts:
        return ", ".join(parts)
    text = (body or b"").decode("utf-8", errors="replace").strip()
    return text


def _http_fail(action: str, status: int, body: bytes, *, code: int = 1) -> None:
    err, message, detail = _parse_error_fields(body)
    summary = _error_detail(body)
    _fail(
        f"{action} failed: HTTP {status}",
        detail=summary,
        err=err or "http_error",
        code=code,
        meta={"status": status, "error": err, "message": message, "detail": detail},
    )


def _print_result(data: dict, *, compact: dict | None = None) -> None:
    """Emit a successful result.

    - Plain mode (no --json): dump `compact` (or full `data` if --verbose).
    - Envelope mode (--json): stable schema
        {ok, error, message, detail, data}
      where `data` is the compact view by default, full payload with --verbose.

    Envelope shape matches SKILL.md's documented contract so downstream agents
    can parse it without reading the per-command field list.
    """
    plain_out = data if (VERBOSE or compact is None) else compact
    if OUTPUT_JSON:
        envelope = {
            "ok": True,
            "error": "",
            "message": "ok",
            "detail": "",
            "data": data if VERBOSE else (compact if compact is not None else data),
        }
        print(json.dumps(envelope, ensure_ascii=False))
    else:
        print(json.dumps(plain_out, ensure_ascii=False))


def _validate_ttl_days(days: float | None) -> None:
    if days is None:
        return
    if days <= 0:
        raise ValueError("--ttl-days must be > 0")
    if days > MAX_TTL_DAYS:
        raise ValueError(f"--ttl-days must be <= {MAX_TTL_DAYS}")


def _validate_ttl_seconds(seconds: int | None) -> None:
    if seconds is None:
        return
    if seconds <= 0:
        raise ValueError("--ttl-seconds must be > 0")


def _validate_link_ttl_seconds(seconds: int | None) -> None:
    if seconds is None:
        return
    if not (1 <= seconds <= MAX_LINK_TTL_SECONDS):
        raise ValueError(
            f"--ttl-seconds for link must be in [1, {MAX_LINK_TTL_SECONDS}]"
        )


def _validate_nonempty(name: str, value: str) -> str:
    v = (value or "").strip()
    if not v:
        raise ValueError(f"{name} cannot be empty")
    return v


def _do_request(req: urllib.request.Request, *, timeout: int = DEFAULT_TIMEOUT,
                stream_to: Path | None = None) -> tuple[int, bytes, dict]:
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            headers = dict(resp.headers.items())
            if stream_to is not None:
                stream_to.parent.mkdir(parents=True, exist_ok=True)
                with open(stream_to, "wb") as f:
                    while True:
                        chunk = resp.read(1024 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                return status, b"", headers
            body = resp.read()
            return status, body, headers
    except urllib.error.HTTPError as e:
        body = e.read() or b""
        return e.code, body, dict(e.headers.items()) if e.headers else {}
    except urllib.error.URLError as e:
        _fail(
            "cannot reach temp-files storage over Fly internal network. "
            "This must run inside a Fly machine.",
            detail=str(e),
        )
    except OSError as e:
        _fail("network error", detail=str(e))


def _parse_json(body: bytes) -> dict:
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        _fail("server returned non-JSON", detail=str(e))


# ---------------------------------------------------------------------------
# put / put-dir
# ---------------------------------------------------------------------------

def cmd_put(args) -> None:
    local = Path(args.local).expanduser()
    if not local.is_file():
        _usage_fail(f"local file does not exist: {local}")

    try:
        _validate_ttl_days(args.ttl_days)
        _validate_ttl_seconds(args.ttl_seconds)
        remote = _validate_nonempty("remote path", args.remote).lstrip("/")
    except ValueError as e:
        _usage_fail(str(e))
    qs = {}
    if args.ttl_seconds is not None:
        qs["ttl_seconds"] = str(args.ttl_seconds)
    elif args.ttl_days is not None:
        qs["ttl_days"] = str(args.ttl_days)
    qstr = ("?" + urllib.parse.urlencode(qs)) if qs else ""
    url = f"{_storage_url()}/temp-files/{urllib.parse.quote(remote)}{qstr}"

    size = local.stat().st_size
    with open(local, "rb") as f:
        req = urllib.request.Request(
            url,
            data=f.read() if size <= 64 * 1024 * 1024 else f,
            method="PUT",
            headers={
                **_auth_headers(),
                "Content-Type": "application/octet-stream",
                "Content-Length": str(size),
            },
        )
        status, body, _ = _do_request(req, timeout=PUT_TIMEOUT)

    if status not in (200, 201):
        _http_fail("upload", status, body)
    data = _parse_json(body)
    compact = {k: data.get(k) for k in ("path", "size_bytes", "sha256", "expires_at") if k in data}
    _print_result(data, compact=compact)


def cmd_put_dir(args) -> None:
    local = Path(args.local_dir).expanduser()
    if not local.is_dir():
        _usage_fail(f"local dir does not exist: {local}")
    try:
        _validate_ttl_days(args.ttl_days)
        remote_prefix = _validate_nonempty("remote prefix", args.remote_prefix).strip("/")
    except ValueError as e:
        _usage_fail(str(e))

    qs_extra = ""
    if args.ttl_days is not None:
        qs_extra = f"?ttl_days={args.ttl_days}"

    uploaded = []
    for f in sorted(local.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(local).as_posix()
        remote = f"{remote_prefix}/{rel}" if remote_prefix else rel
        url = f"{_storage_url()}/temp-files/{urllib.parse.quote(remote)}{qs_extra}"
        size = f.stat().st_size
        with open(f, "rb") as fp:
            req = urllib.request.Request(
                url,
                data=fp.read() if size <= 64 * 1024 * 1024 else fp,
                method="PUT",
                headers={
                    **_auth_headers(),
                    "Content-Type": "application/octet-stream",
                    "Content-Length": str(size),
                },
            )
            status, body, _ = _do_request(req, timeout=PUT_TIMEOUT)
        if status not in (200, 201):
            _http_fail(f"upload on {remote}", status, body)
        uploaded.append({"path": remote, "size_bytes": size})
    data = {"uploaded": uploaded, "count": len(uploaded)}
    compact = {"count": len(uploaded)}
    _print_result(data, compact=compact)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

def cmd_list(args) -> None:
    qs = {}
    if args.prefix:
        qs["prefix"] = args.prefix.strip("/")
    url = f"{_storage_url()}/temp-files"
    if qs:
        url += "?" + urllib.parse.urlencode(qs)
    req = urllib.request.Request(url, method="GET", headers=_auth_headers())
    status, body, _ = _do_request(req)
    if status != 200:
        _http_fail("list", status, body)
    data = _parse_json(body)
    # In envelope mode emit the structured payload via the standard helper.
    # In plain mode keep the human-readable directory print — agents and
    # humans both find it easier to scan than indented JSON.
    if OUTPUT_JSON:
        _print_result(data, compact=data)
        return
    entries = data.get("entries", [])
    if not entries:
        print("(empty)")
        return
    prefix = data.get("prefix", "") or ""
    scope = data.get("agent_scope", "")
    print(f"prefix: {prefix or '(root)'}  scope: {scope}")
    for e in entries:
        kind = e.get("kind", "?")
        path = e.get("path", "?")
        if kind == "dir":
            print(f"  [dir]  {path}")
        else:
            size = e.get("size_bytes", 0)
            exp = e.get("expires_at", 0)
            when = time.strftime("%Y-%m-%d %H:%M", time.gmtime(exp)) if exp else "?"
            print(f"  [file] {path}  ({size} B, expires {when} UTC)")


# ---------------------------------------------------------------------------
# get / fetch
# ---------------------------------------------------------------------------

def _download(url: str, dest: Path) -> tuple[int, bytes, dict]:
    req = urllib.request.Request(url, method="GET", headers=_auth_headers())
    status, body, headers = _do_request(req, timeout=GET_TIMEOUT, stream_to=dest)
    return status, body, headers


def _parse_filename_from_cd(cd: str) -> str:
    """Pull the filename out of a Content-Disposition header. Best-effort."""
    if not cd:
        return ""
    m = re.search(r'filename="([^"]+)"', cd)
    if m:
        return m.group(1)
    m = re.search(r"filename=([^;]+)", cd)
    if m:
        return m.group(1).strip()
    return ""


def _normalize_saved(dest: Path, headers: dict) -> tuple[Path, str, str, str]:
    """Reconcile what the server returned with the local destination the
    caller asked for.

    - Reads Content-Type and Content-Disposition.
    - kind is 'zip' if Content-Type is application/zip, else 'file'.
    - If the caller's dest extension doesn't match what the server is
      sending (e.g. caller said .bin but server is sending zip), rename the
      saved file in-place so downstream tools (unzip, `file`, the agent's
      own type sniffing) see the right extension.

    Returns (final_dest, kind, content_type, server_filename).
    """
    ct = (headers.get("Content-Type") or headers.get("content-type") or "").split(";")[0].strip().lower()
    cd = headers.get("Content-Disposition") or headers.get("content-disposition") or ""
    server_filename = _parse_filename_from_cd(cd)
    kind = "zip" if ct == "application/zip" else "file"

    final = dest
    if kind == "zip" and dest.suffix.lower() != ".zip":
        # Replace the wrong suffix (or add one if there was none) so the
        # file actually looks like a zip on disk. Avoid clobbering an
        # existing unrelated file at the target.
        candidate = dest.with_suffix(".zip") if dest.suffix else dest.parent / (dest.name + ".zip")
        try:
            dest.rename(candidate)
            final = candidate
        except OSError as e:
            print(f"WARN: zip kind but rename failed: {e}", file=sys.stderr)
    return final, kind, ct, server_filename


def _emit_download_result(dest: Path, headers: dict, *,
                          extract_to: Path | None = None) -> None:
    final, kind, ct, server_filename = _normalize_saved(dest, headers)
    sha = headers.get("X-Sha256") or headers.get("x-sha256") or ""
    out = {
        "saved": str(final),
        "kind": kind,
        "bytes": final.stat().st_size,
        "sha256": sha,
        "content_type": ct,
    }
    if server_filename:
        out["server_filename"] = server_filename

    if extract_to is not None:
        archive_kind = _sniff_archive(final, ct)
        if archive_kind is None:
            out["extract_skipped"] = "not a recognized archive"
        else:
            try:
                target = _resolve_extract_target(final, extract_to)
                _extract_archive(final, target, archive_kind)
                out["extracted_kind"] = archive_kind
                out["extracted_to"] = str(target)
                # List the immediate children so the agent can see what
                # landed without having to ls separately.
                top = sorted(p.name + ("/" if p.is_dir() else "")
                             for p in target.iterdir())
                out["extracted_top"] = top[:50]
            except _ExtractError as e:
                out["extract_error"] = str(e)
    elif kind == "zip":
        out["hint"] = (
            f"This is a ZIP archive. Re-run with `--extract` to auto-unpack, "
            f"or `python3 -c \"import zipfile; "
            f"zipfile.ZipFile('{final}').extractall('{final.with_suffix('')}/')\"`"
        )
    compact_keys = ["saved", "kind", "bytes", "sha256", "extracted_to", "extract_error"]
    compact = {k: out.get(k) for k in compact_keys if k in out}
    _print_result(out, compact=compact)


# ---------------------------------------------------------------------------
# Archive sniff + safe extract
# ---------------------------------------------------------------------------

class _ExtractError(Exception):
    pass


_AUTO_EXTRACT_SENTINEL = object()


def _sniff_archive(path: Path, content_type: str = "") -> str | None:
    """Return 'zip' | 'tar' | 'tar.gz' | 'tar.bz2' | 'tar.xz' | None.

    Trusts magic bytes first, then content-type, then filename suffix.
    """
    try:
        with open(path, "rb") as f:
            head = f.read(8)
    except OSError:
        return None
    if head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06"):
        return "zip"
    if head.startswith(b"\x1f\x8b"):
        # gzip — could be plain .gz or tar.gz. tarfile.open will tell us.
        try:
            with tarfile.open(path, "r:gz"):
                return "tar.gz"
        except tarfile.TarError:
            return None
    if head.startswith(b"BZh"):
        try:
            with tarfile.open(path, "r:bz2"):
                return "tar.bz2"
        except tarfile.TarError:
            return None
    if head.startswith(b"\xfd7zXZ"):
        try:
            with tarfile.open(path, "r:xz"):
                return "tar.xz"
        except tarfile.TarError:
            return None
    # Plain tar has no magic in the first bytes — check tarfile-style.
    try:
        if tarfile.is_tarfile(path):
            return "tar"
    except OSError:
        pass
    # Fall through to content-type / suffix hint.
    if content_type == "application/zip":
        return "zip"
    if path.suffix.lower() == ".zip":
        return "zip"
    return None


def _resolve_extract_target(archive: Path, requested: Path | object) -> Path:
    """Pick the extract directory. If the caller passed the sentinel (i.e.
    used `--extract` with no value), derive a sibling dir from the archive
    name; otherwise use the explicit path."""
    if requested is _AUTO_EXTRACT_SENTINEL:
        stem = archive.name
        for suf in (".tar.gz", ".tar.bz2", ".tar.xz", ".zip", ".tar", ".tgz"):
            if stem.lower().endswith(suf):
                stem = stem[: -len(suf)]
                break
        else:
            stem = archive.stem
        target = archive.parent / (stem or archive.name + ".unpacked")
    else:
        target = Path(requested)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _is_safe_member(name: str) -> bool:
    """Reject paths that would write outside the extract dir (zip-slip /
    tar-slip). Also reject absolute paths."""
    if not name:
        return False
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        return False
    parts = Path(name).parts
    return ".." not in parts


def _extract_archive(archive: Path, target: Path, kind: str) -> None:
    """Extract `archive` into `target`, refusing any zip-slip / tar-slip
    member. Raises _ExtractError on bad entries."""
    target = target.resolve()
    if kind == "zip":
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                if not _is_safe_member(info.filename):
                    raise _ExtractError(
                        f"unsafe zip member: {info.filename!r} (zip-slip refused)"
                    )
            zf.extractall(target)
        return
    tarmode = {"tar": "r:", "tar.gz": "r:gz", "tar.bz2": "r:bz2", "tar.xz": "r:xz"}[kind]
    with tarfile.open(archive, tarmode) as tf:
        for member in tf.getmembers():
            if not _is_safe_member(member.name):
                raise _ExtractError(
                    f"unsafe tar member: {member.name!r} (tar-slip refused)"
                )
            if member.islnk() or member.issym():
                # Symlinks can also escape; drop them.
                raise _ExtractError(
                    f"unsafe tar link member: {member.name!r}"
                )
        # Python 3.12+ supports filter='data' for tarfile.extractall — use
        # it if available for an extra defence-in-depth pass.
        try:
            tf.extractall(target, filter="data")
        except TypeError:
            tf.extractall(target)


def cmd_get(args) -> None:
    try:
        remote = _validate_nonempty("remote path", args.remote).lstrip("/")
    except ValueError as e:
        _usage_fail(str(e))
    dest = Path(args.local_dest).expanduser()
    suffix = "?download=zip" if args.zip else ""
    url = f"{_storage_url()}/temp-files/{urllib.parse.quote(remote)}{suffix}"
    status, body, headers = _download(url, dest)
    if status != 200:
        try:
            dest.unlink()
        except OSError:
            pass
        _http_fail("download", status, body)
    _emit_download_result(dest, headers, extract_to=_extract_arg(args))


def cmd_fetch(args) -> None:
    try:
        code = _validate_nonempty("code", args.code)
    except ValueError as e:
        _usage_fail(str(e))
    dest = Path(args.local_dest).expanduser()
    url = f"{_storage_url()}/t/{urllib.parse.quote(code)}"
    status, body, headers = _download(url, dest)
    if status != 200:
        try:
            dest.unlink()
        except OSError:
            pass
        _http_fail("fetch", status, body)
    _emit_download_result(dest, headers, extract_to=_extract_arg(args))


def _extract_arg(args):
    """Translate argparse's --extract handling to either None, the sentinel
    (auto-derive dir), or an explicit Path."""
    val = getattr(args, "extract", None)
    if val is None:
        return None
    if val == "__AUTO__":
        return _AUTO_EXTRACT_SENTINEL
    return Path(val).expanduser()


# ---------------------------------------------------------------------------
# rm
# ---------------------------------------------------------------------------

def cmd_rm(args) -> None:
    try:
        remote = _validate_nonempty("remote path", args.remote).lstrip("/")
    except ValueError as e:
        _usage_fail(str(e))
    suffix = "?recursive=1" if args.recursive else ""
    url = f"{_storage_url()}/temp-files/{urllib.parse.quote(remote)}{suffix}"
    req = urllib.request.Request(url, method="DELETE", headers=_auth_headers())
    status, body, _ = _do_request(req)
    if status in (200, 204):
        if body:
            data = _parse_json(body)
        else:
            data = {"removed": True}
        compact = {k: data.get(k) for k in ("removed", "path") if k in data}
        _print_result(data, compact=compact)
        return
    _http_fail("delete", status, body)


# ---------------------------------------------------------------------------
# link / links / unlink
# ---------------------------------------------------------------------------

def cmd_link(args) -> None:
    try:
        _validate_link_ttl_seconds(args.ttl_seconds)
        remote = _validate_nonempty("remote path", args.remote).lstrip("/")
    except ValueError as e:
        _usage_fail(str(e))

    download_mode = "auto"
    if args.zip:
        download_mode = "zip"
    elif args.file:
        download_mode = "file"
    body = {
        "path": remote,
        "download": download_mode,
    }
    if args.ttl_seconds is not None:
        body["ttl_seconds"] = args.ttl_seconds
    req = urllib.request.Request(
        f"{_storage_url()}/temp-links",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={**_auth_headers(), "Content-Type": "application/json"},
    )
    status, resp, _ = _do_request(req)
    if status != 201:
        _http_fail("link create", status, resp)
    data = _parse_json(resp)
    compact = {k: data.get(k) for k in ("code", "target_path", "expires_at", "url") if k in data}
    _print_result(data, compact=compact)


def cmd_links(args) -> None:
    req = urllib.request.Request(
        f"{_storage_url()}/temp-links",
        method="GET",
        headers=_auth_headers(),
    )
    status, body, _ = _do_request(req)
    if status != 200:
        _http_fail("links list", status, body)
    data = _parse_json(body)
    if OUTPUT_JSON:
        _print_result(data, compact=data)
        return
    links = data.get("links", [])
    if not links:
        print("(no active short links)")
        return
    for rec in links:
        code = rec.get("code", "?")
        target = rec.get("target_path", "?")
        exp = rec.get("expires_at", 0)
        when = time.strftime("%Y-%m-%d %H:%M", time.gmtime(exp)) if exp else "?"
        uses = rec.get("uses", 0)
        print(f"{code}  → {target}  (expires {when} UTC, uses={uses})")


def cmd_unlink(args) -> None:
    try:
        code = _validate_nonempty("code", args.code)
    except ValueError as e:
        _usage_fail(str(e))
    req = urllib.request.Request(
        f"{_storage_url()}/temp-links/{urllib.parse.quote(code)}",
        method="DELETE",
        headers=_auth_headers(),
    )
    status, body, _ = _do_request(req)
    if status == 204:
        data = {"revoked": code}
        _print_result(data, compact=data)
        return
    _http_fail("unlink", status, body)


# ---------------------------------------------------------------------------
# argparse wiring
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tf", description="Workroom temp-files CLI")
    p.add_argument("--verbose", action="store_true", help="show full payload/error meta")
    p.add_argument("--json", action="store_true", help="stable JSON envelope output")
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("put", help="upload (or overwrite) a single file")
    pp.add_argument("local")
    pp.add_argument("remote")
    pp.add_argument("--ttl-days", type=float)
    pp.add_argument("--ttl-seconds", type=int)
    pp.set_defaults(func=cmd_put)

    pd = sub.add_parser("put-dir", help="recursively upload a local dir")
    pd.add_argument("local_dir")
    pd.add_argument("remote_prefix")
    pd.add_argument("--ttl-days", type=float)
    pd.set_defaults(func=cmd_put_dir)

    pl = sub.add_parser("list", help="list a prefix (one level)")
    pl.add_argument("--prefix", default="")
    pl.set_defaults(func=cmd_list)

    pg = sub.add_parser("get", help="download a file or zipped dir")
    pg.add_argument("remote")
    pg.add_argument("local_dest")
    pg.add_argument("--zip", action="store_true", help="force directory zip")
    pg.add_argument("--extract", nargs="?", const="__AUTO__", default=None,
                    metavar="DIR",
                    help="auto-unpack zip/tar.gz/tar.bz2/tar.xz after download; "
                         "with no value, picks a sibling dir from the archive name")
    pg.set_defaults(func=cmd_get)

    pr = sub.add_parser("rm", help="delete file or directory")
    pr.add_argument("remote")
    pr.add_argument("--recursive", action="store_true")
    pr.set_defaults(func=cmd_rm)

    pk = sub.add_parser("link", help="create a short-link record")
    pk.add_argument("remote")
    grp = pk.add_mutually_exclusive_group()
    grp.add_argument("--zip", action="store_true")
    grp.add_argument("--file", action="store_true")
    pk.add_argument("--ttl-seconds", type=int)
    pk.set_defaults(func=cmd_link)

    pls = sub.add_parser("links", help="list active short-links")
    pls.set_defaults(func=cmd_links)

    pu = sub.add_parser("unlink", help="revoke a short-link")
    pu.add_argument("code")
    pu.set_defaults(func=cmd_unlink)

    pf = sub.add_parser("fetch", help="resolve a short-link and save")
    pf.add_argument("code")
    pf.add_argument("local_dest")
    pf.add_argument("--extract", nargs="?", const="__AUTO__", default=None,
                    metavar="DIR",
                    help="auto-unpack zip/tar.gz/tar.bz2/tar.xz after download; "
                         "with no value, picks a sibling dir from the archive name")
    pf.set_defaults(func=cmd_fetch)

    return p


def main() -> None:
    global OUTPUT_JSON, VERBOSE
    args = build_parser().parse_args()
    OUTPUT_JSON = bool(getattr(args, "json", False))
    VERBOSE = bool(getattr(args, "verbose", False))
    try:
        args.func(args)
    except ValueError as e:
        _usage_fail(str(e))


if __name__ == "__main__":
    main()
