from __future__ import annotations

import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).parents[1] / "atlas_cloud.py"
SPEC = importlib.util.spec_from_file_location("atlas_cloud_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
atlas = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(atlas)


class _DownloadResponse:
    def __init__(self, payload: bytes, content_type: str = "audio/mpeg") -> None:
        self._stream = io.BytesIO(payload)
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)


class AtlasCloudMediaTests(unittest.TestCase):
    def test_decode_response_accepts_string_success_code(self):
        response = _DownloadResponse(b'{"code":"200","data":[{"model":"audio/one"}]}')
        self.assertEqual(atlas._decode_response(response), [{"model": "audio/one"}])

    def test_list_models_filters_kind_search_and_hidden_models(self):
        catalog = [
            {"model": "image/one", "type": "Image", "display_console": True},
            {"model": "image/hidden", "type": "Image", "display_console": False},
            {"model": "audio/one", "type": "Audio", "display_console": True},
        ]
        with mock.patch.object(atlas, "_request_json", return_value=catalog):
            self.assertEqual(
                atlas.list_models(kind="image", search="one"), [catalog[0]]
            )

    def test_list_models_rejects_invalid_kind(self):
        with self.assertRaisesRegex(ValueError, "Image, Video, or Audio"):
            atlas.list_models(kind="Text")

    def test_prediction_status_rejects_path_input(self):
        with self.assertRaises(ValueError):
            atlas.prediction_status("../secret")

    def test_submission_posts_exactly_once_when_it_fails(self):
        with mock.patch.object(
            atlas, "_request_json", side_effect=atlas.AtlasCloudError("failed")
        ) as request:
            with self.assertRaises(atlas.AtlasCloudError):
                atlas._submit("image", "image/model", {"prompt": "test"})
        request.assert_called_once_with(
            "POST", "model/generateImage", {"model": "image/model", "prompt": "test"}
        )

    def test_submission_rejects_unsafe_prediction_id(self):
        with mock.patch.object(atlas, "_request_json", return_value={"id": "../file"}):
            with self.assertRaisesRegex(atlas.AtlasCloudError, "invalid prediction id"):
                atlas._submit("image", "image/model", {"prompt": "test"})

    def test_wait_returns_completed_prediction(self):
        with (
            mock.patch.object(
                atlas,
                "prediction_status",
                side_effect=[
                    {"status": "processing"},
                    {"status": "completed", "outputs": ["x"]},
                ],
            ),
            mock.patch.object(atlas.time, "sleep"),
        ):
            result = atlas._wait_for_prediction("id", timeout=30, poll_interval=1)
        self.assertEqual(result["status"], "completed")

    def test_wait_raises_terminal_failure(self):
        with mock.patch.object(
            atlas,
            "prediction_status",
            return_value={"status": "failed", "error": "bad input"},
        ):
            with self.assertRaisesRegex(atlas.AtlasCloudError, "bad input"):
                atlas._wait_for_prediction("id", timeout=30, poll_interval=1)

    def test_download_does_not_forward_authorization(self):
        response = _DownloadResponse(b"ID3-audio")
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(atlas, "_validate_public_https_url"),
            mock.patch.object(
                atlas._download_opener, "open", return_value=response
            ) as opener,
        ):
            paths = atlas._download_outputs(
                ["https://cdn.example.test/output.mp3"], directory, "prediction"
            )
            request = opener.call_args.args[0]
            self.assertNotIn("Authorization", request.headers)
            self.assertEqual(Path(paths[0]).read_bytes(), b"ID3-audio")

    def test_output_url_rejects_private_ip_even_with_proxy(self):
        with mock.patch.object(
            atlas.urllib.request, "getproxies", return_value={"https": "http://proxy"}
        ):
            with self.assertRaisesRegex(atlas.AtlasCloudError, "non-public address"):
                atlas._validate_public_https_url("https://127.0.0.1/output.mp3")

    def test_proxy_routed_hostname_does_not_resolve_locally(self):
        with (
            mock.patch.object(
                atlas.urllib.request,
                "getproxies",
                return_value={"https": "http://proxy"},
            ),
            mock.patch.object(atlas.urllib.request, "proxy_bypass", return_value=False),
            mock.patch.object(atlas.socket, "getaddrinfo") as resolver,
        ):
            atlas._validate_public_https_url("https://cdn.example.test/output.mp3")
        resolver.assert_not_called()

    def test_generate_audio_runs_submit_poll_and_download(self):
        with (
            mock.patch.object(
                atlas, "_submit", return_value={"id": "pred-1"}
            ) as submit,
            mock.patch.object(
                atlas,
                "_wait_for_prediction",
                return_value={
                    "id": "pred-1",
                    "status": "completed",
                    "outputs": ["https://x/y.mp3"],
                },
            ),
            mock.patch.object(atlas, "_download_outputs", return_value=["/tmp/y.mp3"]),
        ):
            result = atlas.generate_audio(
                model="xai/tts-v1", text="hello", language="en", voice_id="eve"
            )
        submit.assert_called_once_with(
            "audio",
            "xai/tts-v1",
            {"language": "en", "voice_id": "eve", "text": "hello"},
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["local_paths"], ["/tmp/y.mp3"])

    def test_prediction_outputs_accepts_single_output_field(self):
        self.assertEqual(
            atlas._prediction_outputs({"output": "https://x/y.mp3"}),
            ["https://x/y.mp3"],
        )


if __name__ == "__main__":
    unittest.main()
