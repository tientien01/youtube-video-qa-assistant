import unittest

from app.services.extraction.video_url_service import extract_youtube_video_id


class VideoUrlServiceTest(unittest.TestCase):
    def test_extracts_watch_url(self):
        video_id = extract_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        self.assertEqual(video_id, "dQw4w9WgXcQ")

    def test_extracts_short_url(self):
        video_id = extract_youtube_video_id("https://youtu.be/dQw4w9WgXcQ")

        self.assertEqual(video_id, "dQw4w9WgXcQ")

    def test_rejects_non_youtube_url(self):
        with self.assertRaises(ValueError):
            extract_youtube_video_id("https://example.com/watch?v=dQw4w9WgXcQ")


if __name__ == "__main__":
    unittest.main()
