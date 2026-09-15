"""Callable Atlas Cloud media generation client using the Python standard library."""

from __future__ import annotations

import ipaddress
import json
import mimetypes
import os
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API_BASE = "https://api.atlascloud.ai/api/v1"
USER_AGENT = "starchild-atlas-cloud-media/1.0"
TERMINAL_SUCCESS = {"completed", "succeeded", "success"}
TERMINAL_FAILURE = {"failed", "cancelled", "canceled", "error", "timeout"}
MEDIA_ENDPOINTS = {
    "image": "generateImage",
    "video": "generateVideo",
    "audio": "generateAudio",
}
ALLOWED_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".mp4",
    ".mov",
    ".webm",
    ".mp3",
    ".wav",
    ".m4a",
    ".flac",
    ".ogg",
    ".glb",
    ".gltf",
    ".zip",
}
PREDICTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")


class AtlasCloudError(RuntimeError):
    """Raised when Atlas Cloud or an output download returns an error."""


def _api_key() -> str:
    value = os.environ.get("ATLASCLOUD_API_KEY", "").strip()
    if not value:
        raise AtlasCloudError("ATLASCLOUD_API_KEY is not set")
    return value


def _decode_response(response: Any) -> Any:
    raw = response.read()
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AtlasCloudError("Atlas Cloud returned a non-JSON response") from exc
    if isinstance(body, dict):
        code = body.get("code")
        if code not in (None, 0, 200, "0", "200"):
            message = body.get("message") or body.get("msg") or f"API error {code}"
            raise AtlasCloudError(str(message))
        if "data" in body:
            return body["data"]
    return body


def _request_json(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    authenticated: bool = True,
    timeout: float = 30,
) -> Any:
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if authenticated:
        headers["Authorization"] = f"Bearer {_api_key()}"
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        f"{API_BASE}/{path.lstrip('/')}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return _decode_response(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise AtlasCloudError(f"Atlas Cloud HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise AtlasCloudError(f"Atlas Cloud request failed: {exc.reason}") from exc


def list_models(
    kind: str | None = None,
    search: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return current public models, optionally filtered by type and text."""
    if not isinstance(limit, int) or limit < 1 or limit > 500:
        raise ValueError("limit must be an integer between 1 and 500")
    normalized_kind = kind.strip().lower() if kind else None
    if normalized_kind and normalized_kind not in {"image", "video", "audio"}:
        raise ValueError("kind must be Image, Video, or Audio")
    query = search.strip().lower() if search else None
    models = _request_json("GET", "models", authenticated=False)
    if not isinstance(models, list):
        raise AtlasCloudError("Atlas Cloud model catalog has an unexpected shape")
    selected: list[dict[str, Any]] = []
    for model in models:
        if not isinstance(model, dict) or model.get("display_console") is False:
            continue
        if normalized_kind and str(model.get("type", "")).lower() != normalized_kind:
            continue
        if query and query not in json.dumps(model, ensure_ascii=False).lower():
            continue
        selected.append(model)
        if len(selected) >= limit:
            break
    return selected


def _normalize_prediction_id(prediction_id: str) -> str:
    prediction_id = prediction_id.strip()
    if ".." in prediction_id or not PREDICTION_ID_PATTERN.fullmatch(prediction_id):
        raise ValueError("prediction_id must be a non-empty opaque identifier")
    return prediction_id


def prediction_status(prediction_id: str) -> dict[str, Any]:
    """Read one prediction without creating a new billable request."""
    prediction_id = _normalize_prediction_id(prediction_id)
    result = _request_json(
        "GET", f"model/prediction/{urllib.parse.quote(prediction_id, safe='')}"
    )
    if not isinstance(result, dict):
        raise AtlasCloudError("Atlas Cloud prediction response has an unexpected shape")
    return result


def _submit(media_type: str, model: str, values: dict[str, Any]) -> dict[str, Any]:
    endpoint = MEDIA_ENDPOINTS[media_type]
    payload = {"model": model, **values}
    result = _request_json("POST", f"model/{endpoint}", payload)
    if not isinstance(result, dict):
        raise AtlasCloudError("Atlas Cloud submission response has an unexpected shape")
    raw_prediction_id = str(result.get("id") or result.get("request_id") or "")
    try:
        prediction_id = _normalize_prediction_id(raw_prediction_id)
    except ValueError as exc:
        raise AtlasCloudError(
            "Atlas Cloud submission returned an invalid prediction id"
        ) from exc
    if result.get("id"):
        result["id"] = prediction_id
    else:
        result["request_id"] = prediction_id
    return result


def _wait_for_prediction(
    prediction_id: str,
    *,
    timeout: float,
    poll_interval: float,
    max_transient_errors: int = 3,
) -> dict[str, Any]:
    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")
    if poll_interval <= 0:
        raise ValueError("poll_interval must be greater than zero")
    deadline = time.monotonic() + timeout
    transient_errors = 0
    while True:
        try:
            result = prediction_status(prediction_id)
            transient_errors = 0
        except AtlasCloudError:
            transient_errors += 1
            if transient_errors > max_transient_errors:
                raise
            result = {}
        status = str(result.get("status") or "").lower()
        if status in TERMINAL_SUCCESS:
            return result
        if status in TERMINAL_FAILURE:
            message = result.get("error") or result.get("message") or status
            raise AtlasCloudError(f"prediction {prediction_id} failed: {message}")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"prediction {prediction_id} did not finish within {timeout}s"
            )
        delay = min(poll_interval * (2 ** max(0, transient_errors - 1)), remaining)
        time.sleep(delay)


def _validate_public_https_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise AtlasCloudError("output URL must be credential-free HTTPS")
    hostname = parsed.hostname.rstrip(".").lower()
    if (
        hostname == "localhost"
        or hostname.endswith(".localhost")
        or hostname.endswith(".local")
        or "." not in hostname
    ):
        raise AtlasCloudError(f"output URL uses a local hostname: {hostname}")
    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        literal_ip = None
    if literal_ip is not None:
        if not literal_ip.is_global:
            raise AtlasCloudError(f"output URL uses a non-public address: {literal_ip}")
        return

    proxies = urllib.request.getproxies()
    if proxies.get("https") and not urllib.request.proxy_bypass(hostname):
        return
    try:
        addresses = socket.getaddrinfo(
            hostname, parsed.port or 443, type=socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise AtlasCloudError(f"cannot resolve output host: {hostname}") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise AtlasCloudError(f"output host resolves to a non-public address: {ip}")


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):  # noqa: ANN001
        _validate_public_https_url(newurl)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


_download_opener = urllib.request.build_opener(_SafeRedirectHandler())


def _suffix_for(url: str, content_type: str | None) -> str:
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if suffix in ALLOWED_SUFFIXES:
        return suffix
    guessed = mimetypes.guess_extension((content_type or "").split(";", 1)[0].strip())
    return guessed if guessed in ALLOWED_SUFFIXES else ".bin"


def _download_outputs(
    output_urls: list[str], output_dir: str | os.PathLike[str], prediction_id: str
) -> list[str]:
    directory = Path(output_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    local_paths: list[str] = []
    for index, url in enumerate(output_urls, start=1):
        if not isinstance(url, str):
            raise AtlasCloudError("prediction output contains a non-string URL")
        _validate_public_https_url(url)
        request = urllib.request.Request(
            url, headers={"Accept": "*/*", "User-Agent": USER_AGENT}, method="GET"
        )
        try:
            with _download_opener.open(request, timeout=120) as response:
                suffix = _suffix_for(url, response.headers.get("Content-Type"))
                destination = directory / f"{prediction_id}-{index}{suffix}"
                temporary = destination.with_suffix(destination.suffix + ".part")
                with temporary.open("wb") as file:
                    while chunk := response.read(1024 * 1024):
                        file.write(chunk)
                os.replace(temporary, destination)
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
            raise AtlasCloudError(f"failed to download output {index}: {exc}") from exc
        local_paths.append(str(destination))
    return local_paths


def _prediction_outputs(result: dict[str, Any]) -> list[str]:
    output_urls = result.get("outputs")
    if output_urls is None:
        output_urls = result.get("output")
    if isinstance(output_urls, str):
        output_urls = [output_urls]
    if not isinstance(output_urls, list) or not output_urls:
        raise AtlasCloudError("completed prediction returned no output URLs")
    if len(output_urls) > 20:
        raise AtlasCloudError("prediction returned too many output URLs")
    if not all(isinstance(url, str) and url for url in output_urls):
        raise AtlasCloudError("prediction output contains an invalid URL")
    return output_urls


def _generate(
    media_type: str,
    model: str,
    values: dict[str, Any],
    *,
    output_dir: str | os.PathLike[str],
    timeout: float,
    poll_interval: float,
) -> dict[str, Any]:
    model = model.strip()
    if not model:
        raise ValueError("model is required")
    submitted = _submit(media_type, model, values)
    prediction_id = str(submitted.get("id") or submitted.get("request_id"))
    result = _wait_for_prediction(
        prediction_id, timeout=timeout, poll_interval=poll_interval
    )
    output_urls = _prediction_outputs(result)
    local_paths = _download_outputs(output_urls, output_dir, prediction_id)
    return {
        "success": True,
        "prediction_id": prediction_id,
        "status": result.get("status"),
        "model": result.get("model") or model,
        "outputs": output_urls,
        "local_paths": local_paths,
    }


def generate_image(
    prompt: str,
    model: str,
    output_dir: str | os.PathLike[str] = "output/atlas-cloud",
    timeout: float = 300,
    poll_interval: float = 3,
    **params: Any,
) -> dict[str, Any]:
    """Generate and download images. This creates one billable job."""
    if not prompt.strip():
        raise ValueError("prompt is required")
    return _generate(
        "image",
        model,
        {"prompt": prompt, **params},
        output_dir=output_dir,
        timeout=timeout,
        poll_interval=poll_interval,
    )


def generate_video(
    prompt: str,
    model: str,
    output_dir: str | os.PathLike[str] = "output/atlas-cloud",
    timeout: float = 900,
    poll_interval: float = 5,
    **params: Any,
) -> dict[str, Any]:
    """Generate and download videos. This creates one billable job."""
    if not prompt.strip():
        raise ValueError("prompt is required")
    return _generate(
        "video",
        model,
        {"prompt": prompt, **params},
        output_dir=output_dir,
        timeout=timeout,
        poll_interval=poll_interval,
    )


def generate_audio(
    model: str,
    text: str | None = None,
    output_dir: str | os.PathLike[str] = "output/atlas-cloud",
    timeout: float = 600,
    poll_interval: float = 3,
    **params: Any,
) -> dict[str, Any]:
    """Generate and download audio. This creates one billable job."""
    values = dict(params)
    if text is not None:
        if not text.strip():
            raise ValueError("text must not be empty")
        values["text"] = text
    if not values:
        raise ValueError("audio generation requires text or model-specific parameters")
    return _generate(
        "audio",
        model,
        values,
        output_dir=output_dir,
        timeout=timeout,
        poll_interval=poll_interval,
    )
