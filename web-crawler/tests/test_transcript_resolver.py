"""Regression tests for get_transcript / podcast_transcript.
Pure unit tests: network + yt-dlp are stubbed. Run: python -m pytest web-crawler/tests -q
Each case is a real review finding on official-skills #179 (2026-09-17)."""
import os, sys, types, unittest
from datetime import datetime, timezone
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
if "core.http_client" not in sys.modules:  # skill loads outside the agent runtime
    core = types.ModuleType("core"); hc = types.ModuleType("core.http_client")
    hc.proxied_get = hc.proxied_post = lambda *a, **k: None
    core.http_client = hc; sys.modules["core"] = core; sys.modules["core.http_client"] = hc
import exports as w  # noqa: E402

D = datetime(2026, 9, 16, 10, tzinfo=timezone.utc)
LONG = "word " * 300


class _R:
    def __init__(self, status, text):
        self.status_code, self.text, self.content = status, text, text.encode()


class Exports(unittest.TestCase):
    def test_new_entry_points_are_exported(self):  # P1: __all__
        for n in ("get_transcript", "podcast_transcript", "resolve_podcast_episode",
                  "media_info", "captions_from_media_info"):
            self.assertIn(n, w.__all__, n)


class BodyValidation(unittest.TestCase):  # P1: 403 body reported as transcript
    def test_403_body_rejected(self):
        self.assertFalse(w._ok_body(_R(403, "<html>403 Forbidden</html>" * 40), 500))

    def test_200_access_denied_rejected(self):
        self.assertFalse(w._ok_body(_R(200, "Access Denied. " * 100), 500))

    def test_short_body_rejected(self):
        self.assertFalse(w._ok_body(_R(200, "ok"), 500))

    def test_real_body_accepted(self):
        self.assertTrue(w._ok_body(_R(200, LONG * 3), 500))

    def test_rss_transcript_falls_through_on_403(self):
        item = '<podcast:transcript url="https://x/t.srt" type="application/x-subrip"/>'
        with mock.patch.object(w, "_pget", return_value=_R(403, "403 Forbidden " * 50)):
            self.assertIsNone(w._rss_transcript(item))


class EpisodeIdentity(unittest.TestCase):  # P1: same channel/day/length is not identity
    def test_channel_key_ignores_stopwords_and_differs(self):
        self.assertEqual(w._key("The a16z Show"), "a16z")
        self.assertNotEqual(w._key("The a16z Show"), w._key("The Cooking Show"))

    def test_duration_mismatch_not_candidate(self):
        self.assertEqual(w._same_episode(3163, 1900, D, D)[0], False)

    def test_date_far_not_candidate(self):
        far = datetime(2026, 8, 1, tzinfo=timezone.utc)
        self.assertEqual(w._same_episode(3163, 3124, D, far)[0], False)

    def test_same_day_same_length_different_title_and_notes_is_NOT_confirmed(self):
        ok, why = w._confirm_identity(
            "The AI-Native CRM", "Alex Rampell and Joe Schmidt with Lightfield CEO Keith Peiris on CRM",
            "Why Robotics Needs New Chips", "Erin Price-Wright with Skild founders on humanoid robotics hardware")
        self.assertFalse(ok, why)

    def test_retitled_upload_with_same_show_notes_is_confirmed(self):
        notes = ("a16z's Alex Rampell and Joe Schmidt sit down with Lightfield co-founder and CEO "
                 "Keith Peiris to discuss what it takes to rethink the CRM for an AI-native world. "
                 "Keith previously built Tome to 25 million users")
        ok, why = w._confirm_identity("The AI-Native CRM", notes,
                                      "How AI Is Rewriting Software From First Principles", notes)
        self.assertTrue(ok, why)
        self.assertIn("description_overlap", why)

    def test_title_agreement_alone_confirms(self):
        ok, _ = w._confirm_identity("Pricing, Pricing, Pricing", "", "Pricing Pricing Pricing | a16z", "")
        self.assertTrue(ok)

    def test_unconfirmed_candidate_is_surfaced_not_delivered(self):
        ep = {"show": "The a16z Show", "episode": "The AI-Native CRM", "duration": 3600,
              "release_date": "2026-09-16T10:00:00Z", "description": "Keith Peiris Lightfield CRM"}
        flat = {"channel": "a16z", "entries": [{"id": "v1", "duration": 3600, "title": "Robotics Chips"}]}
        full = {"upload_date": "20260916", "duration": 3600, "title": "Robotics Chips",
                "description": "Skild humanoid robots hardware", "channel": "a16z"}
        with mock.patch.object(w, "media_info", side_effect=lambda u, **k: flat if "/videos" in u else full):
            confirmed, cand = w._youtube_match(ep, channel_url="https://www.youtube.com/@a16z")
        self.assertIsNone(confirmed)
        self.assertEqual(cand["url"], "https://www.youtube.com/watch?v=v1")

    def test_podcast_transcript_returns_candidate_with_found_false(self):
        ep = {"show": "S", "episode": "E", "feed_url": None, "release_date": None,
              "duration": 3600, "provider": "x", "description": None}
        cand = {"url": "https://www.youtube.com/watch?v=v1", "title": "Other", "channel": "S",
                "score": 1.0, "identity": "title_sim=0.1 shared=0 jaccard=0.00"}
        with mock.patch.object(w, "resolve_podcast_episode", return_value=ep), \
             mock.patch.object(w, "_youtube_match", return_value=(None, cand)), \
             mock.patch.object(w, "_youtube_text") as yt_text:
            r = w.podcast_transcript("https://podcasts.apple.com/us/podcast/s/id1?i=2")
        self.assertFalse(r["found"])
        self.assertEqual(r["candidate"]["url"], cand["url"])
        self.assertIn("confirm", r["note"])
        yt_text.assert_not_called()


class YouTubeRoute(unittest.TestCase):  # P1: captions API skipped when yt-dlp fails
    def test_captions_api_runs_when_media_info_empty_and_never_scrapes(self):
        calls = []
        with mock.patch.object(w, "media_info", return_value={}), \
             mock.patch.object(w, "youtube_transcript",
                               side_effect=lambda u, **k: (calls.append("api"), {"transcript_only_text": LONG})[1]), \
             mock.patch.object(w, "scrape_markdown", side_effect=lambda u, **k: (calls.append("scrape"), "# page " + LONG)[1]):
            r = w.get_transcript("https://www.youtube.com/watch?v=abc")
        self.assertTrue(r["found"]); self.assertEqual(r["source"], "youtube_transcript")
        self.assertEqual(calls, ["api"])

    def test_youtube_without_captions_is_found_false_not_page_text(self):
        with mock.patch.object(w, "media_info", return_value={}), \
             mock.patch.object(w, "youtube_transcript", return_value={"transcript_only_text": ""}), \
             mock.patch.object(w, "scrape_markdown", return_value="# page " + LONG) as sc:
            r = w.get_transcript("https://youtu.be/abc")
        self.assertFalse(r["found"]); self.assertEqual(r["kind"], "youtube")
        sc.assert_not_called()

    def test_native_captions_preferred_when_available(self):
        info = {"extractor": "youtube", "title": "T", "automatic_captions": {"en": [{"ext": "json3", "url": "u"}]}}
        with mock.patch.object(w, "media_info", return_value=info), \
             mock.patch.object(w, "captions_from_media_info", return_value={"text": LONG, "kind": "automatic_captions", "lang": "en", "ext": "json3"}):
            r = w.get_transcript("https://www.youtube.com/watch?v=abc")
        self.assertTrue(r["found"]); self.assertTrue(r["source"].startswith("native_captions"))


if __name__ == "__main__":
    unittest.main()
