import unittest

import httpx

from app.services.llm.base import LlmError
from app.services.llm.gemini_client import GeminiClient


class GeminiClientTest(unittest.TestCase):
    def test_generate_text_posts_prompt_and_extracts_text(self):
        http_post = FakeHttpPost(
            FakeResponse(
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [{"text": "Grounded answer."}],
                            },
                        }
                    ],
                }
            )
        )
        client = GeminiClient(
            api_key="test-key",
            model="gemini-test-model",
            http_post=http_post,
        )

        answer = client.generate_text("Use transcript only.")

        self.assertEqual(answer, "Grounded answer.")
        self.assertEqual(
            http_post.last_url,
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-test-model:generateContent",
        )
        self.assertEqual(http_post.last_headers["x-goog-api-key"], "test-key")
        self.assertEqual(
            http_post.last_json["contents"][0]["parts"][0]["text"],
            "Use transcript only.",
        )

    def test_generate_text_raises_llm_error_when_http_fails(self):
        client = GeminiClient(
            api_key="test-key",
            model="gemini-test-model",
            http_post=FakeHttpPost(FailingResponse()),
        )

        with self.assertRaises(LlmError):
            client.generate_text("Use transcript only.")


class FakeHttpPost:
    def __init__(self, response):
        self._response = response
        self.last_url = None
        self.last_headers = None
        self.last_json = None

    def __call__(self, url, *, headers, json, timeout):
        self.last_url = url
        self.last_headers = headers
        self.last_json = json
        self.last_timeout = timeout
        return self._response


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class FailingResponse:
    def raise_for_status(self) -> None:
        raise httpx.HTTPError("request failed")


if __name__ == "__main__":
    unittest.main()
