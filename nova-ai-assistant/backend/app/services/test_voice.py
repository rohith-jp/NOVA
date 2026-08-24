import os
from unittest.mock import patch, MagicMock

from app.services.stt import transcribe_audio
from app.services.tts import generate_speech


class MockResponse:
    def __init__(self, status_code, json_data=None, content=None):
        self.status_code = status_code
        self._json_data = json_data
        self.content = content
        self.text = "Error Text"

    def json(self):
        return self._json_data


@patch("httpx.Client.post")
def test_stt_transcription(mock_post):
    print("\n=== TEST 1: STT Transcription ===")

    # Mock successful response
    mock_post.return_value = MockResponse(200, json_data={"text": "Hello world from Whisper."})

    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake_key"}):
        result = transcribe_audio(b"fake_audio_bytes", "test.wav")
        assert result.error is None
        assert result.text == "Hello world from Whisper."
        print("[OK] STT transcribed audio successfully.")


@patch("httpx.Client.post")
def test_stt_missing_api_key(mock_post):
    print("\n=== TEST 2: STT Missing API Key ===")

    with patch.dict(os.environ, clear=True):
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        result = transcribe_audio(b"fake_audio_bytes")
        assert result.text == ""
        assert "OPENAI_API_KEY is not configured" in result.error
        print("[OK] STT handled missing API key.")


@patch("httpx.Client.post")
def test_tts_generation(mock_post):
    print("\n=== TEST 3: TTS Generation ===")

    # Mock successful response
    mock_post.return_value = MockResponse(200, content=b"fake_audio_stream")

    with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "fake_key"}):
        result = generate_speech("Generate this speech.")
        assert result.error is None
        assert result.audio_data == b"fake_audio_stream"
        print("[OK] TTS generated speech successfully.")


@patch("httpx.Client.post")
def test_tts_api_error(mock_post):
    print("\n=== TEST 4: TTS API Error ===")

    # Mock failure response
    mock_post.return_value = MockResponse(401)

    with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "fake_key"}):
        result = generate_speech("Fail this speech.")
        assert result.audio_data is None
        assert "TTS API Error: 401" in result.error
        print("[OK] TTS handled API error correctly.")


def main():
    test_stt_transcription()
    test_stt_missing_api_key()
    test_tts_generation()
    test_tts_api_error()
    print("\n==============================================")
    print(" ALL VOICE PIPELINE TESTS PASSED! ")
    print("==============================================")


if __name__ == "__main__":
    main()
