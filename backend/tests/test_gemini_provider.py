import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import httpx
from app.schemas.translation import Language
from app.services.translators.gemini import GeminiTranslationProvider


def test_gemini_missing_consent_rejected(client: TestClient):
    payload = {
        "source_lang": "python",
        "target_lang": "javascript",
        "code": "print('hello')",
        "provider_config": {
            "provider": "gemini",
            "api_key": "test-key-12345",
            "consent_granted": False
        }
    }
    response = client.post("/api/translate", json=payload)
    assert response.status_code == 502
    data = response.json()
    assert "consent is required" in data["detail"]["message"].lower()


def test_gemini_missing_api_key_rejected(client: TestClient):
    payload = {
        "source_lang": "python",
        "target_lang": "javascript",
        "code": "print('hello')",
        "provider_config": {
            "provider": "gemini",
            "api_key": "",
            "consent_granted": True
        }
    }
    response = client.post("/api/translate", json=payload)
    assert response.status_code == 503
    data = response.json()
    assert "api key is required" in data["detail"]["message"].lower()


def test_provider_test_endpoint_mock(client: TestClient):
    payload = {
        "provider": "mock",
        "model": "mock-test-model"
    }
    response = client.post("/api/providers/test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["provider"] == "mock"


def test_provider_test_endpoint_gemini_missing_key(client: TestClient):
    payload = {
        "provider": "gemini",
        "api_key": ""
    }
    response = client.post("/api/providers/test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["error_type"] == "MissingApiKey"


@pytest.mark.asyncio
async def test_gemini_successful_mocked_translation(client: TestClient):
    fake_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "translated_code": "console.log('hello from gemini');",
                                "explanation": "Converted Python print to JS console.log.",
                                "warnings": ["Review async behavior if applicable."]
                            })
                        }
                    ]
                }
            }
        ]
    }

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_gemini_response

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        payload = {
            "source_lang": "python",
            "target_lang": "javascript",
            "code": "print('hello from gemini')",
            "provider_config": {
                "provider": "gemini",
                "api_key": "valid-test-key-xyz",
                "model": "gemini-3.8-flash",
                "consent_granted": True
            }
        }
        response = client.post("/api/translate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["translated_code"] == "console.log('hello from gemini');"
        assert data["provider_info"]["provider"] == "gemini"
        assert data["provider_info"]["model"] == "gemini-3.8-flash"
        assert data["provider_info"]["verified"] is False


@pytest.mark.asyncio
async def test_gemini_rate_limit_handled(client: TestClient):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 429
    mock_resp.text = "Quota exceeded"

    with patch("httpx.AsyncClient.post", return_value=mock_resp), patch("asyncio.sleep", return_value=None):
        payload = {
            "source_lang": "python",
            "target_lang": "javascript",
            "code": "print('quota test')",
            "provider_config": {
                "provider": "gemini",
                "api_key": "valid-test-key-xyz",
                "model": "gemini-3.8-flash",
                "consent_granted": True
            }
        }
        response = client.post("/api/translate", json=payload)
        assert response.status_code == 503
        data = response.json()
        assert "gemini is temporarily busy" in data["detail"]["message"].lower()
        assert data["detail"]["error_type"] == "ProviderBusy"
        assert data["detail"]["can_switch_provider"] is True


@pytest.mark.asyncio
async def test_gemini_404_error_does_not_recommend_same_model(client: TestClient):
    """Verify that a 404 from Gemini generates an actionable error that never recommends the failed model."""
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 404

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        payload = {
            "source_lang": "python",
            "target_lang": "javascript",
            "code": "print('test')",
            "provider_config": {
                "provider": "gemini",
                "api_key": "valid-test-key-xyz",
                "model": "gemini-2.5-flash",
                "consent_granted": True
            }
        }
        response = client.post("/api/translate", json=payload)
        assert response.status_code == 502
        data = response.json()
        error_msg = data["detail"]["message"]
        # Error must mention that gemini-2.5-flash was not found
        assert "gemini-2.5-flash" in error_msg
        # But suggestions must NEVER recommend gemini-2.5-flash!
        assert "such as gemini-2.5-flash" not in error_msg
        assert "gemini-3.8-flash" in error_msg


def test_dynamic_mock_provider_override(client: TestClient):
    """Verify that a user can choose mock provider in provider_config even when default is Ollama."""
    payload = {
        "source_lang": "python",
        "target_lang": "javascript",
        "code": "def hello():\n    print('world')\n    return True",
        "provider_config": {
            "provider": "mock"
        }
    }
    response = client.post("/api/translate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "console.log" in data["translated_code"]
    assert data["provider_info"]["provider"] == "mock"


@pytest.mark.asyncio
async def test_gemini_javascript_to_python_translation(client: TestClient):
    fake_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "translated_code": "def greet(name):\n    print(f'Hello, {name}')\n    return True",
                                "explanation": "Converted JS arrow function and console.log to Python def and print.",
                                "warnings": []
                            })
                        }
                    ]
                }
            }
        ]
    }

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_gemini_response

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        payload = {
            "source_lang": "javascript",
            "target_lang": "python",
            "code": "const greet = (name) => { console.log(`Hello, ${name}`); return true; };",
            "provider_config": {
                "provider": "gemini",
                "api_key": "valid-test-key-xyz",
                "model": "gemini-3.8-flash",
                "consent_granted": True
            }
        }
        response = client.post("/api/translate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "def greet" in data["translated_code"]
        assert data["provider_info"]["provider"] == "gemini"
        assert data["provider_info"]["model"] == "gemini-3.8-flash"


@pytest.mark.asyncio
async def test_provider_test_endpoint_gemini_valid_key(client: TestClient):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [
            {
                "name": "models/gemini-3.8-flash",
                "displayName": "Gemini 3.8 Flash",
                "supportedGenerationMethods": ["generateContent"]
            },
            {
                "name": "models/gemini-3.5-flash-lite",
                "displayName": "Gemini 3.5 Flash-Lite",
                "supportedGenerationMethods": ["generateContent"]
            }
        ]
    }

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        payload = {
            "provider": "gemini",
            "api_key": "AIzaSyFakeValidKey123",
            "model": "gemini-3.8-flash"
        }
        response = client.post("/api/providers/test", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["provider"] == "gemini"
        assert "connected successfully" in data["message"].lower()
        assert len(data["available_models"]) == 2
        assert data["available_models"][0]["id"] == "gemini-3.8-flash"


@pytest.mark.asyncio
async def test_provider_test_endpoint_gemini_unavailable_model(client: TestClient):
    """Verify that testing an unavailable model returns valid=False and recommends an available model."""
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [
            {
                "name": "models/gemini-3.8-flash",
                "displayName": "Gemini 3.8 Flash",
                "supportedGenerationMethods": ["generateContent"]
            }
        ]
    }

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        payload = {
            "provider": "gemini",
            "api_key": "AIzaSyFakeValidKey123",
            "model": "gemini-2.5-flash"  # Not in the returned models!
        }
        response = client.post("/api/providers/test", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["error_type"] == "ModelUnavailable"
        assert "gemini-3.8-flash" in data["message"]
        # Must not recommend the same failed model
        assert "alternative: 'gemini-2.5-flash'" not in data["message"]


@pytest.mark.asyncio
async def test_provider_test_endpoint_gemini_invalid_key_400(client: TestClient):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 400
    mock_resp.text = json.dumps({"error": {"message": "API key not valid. Please pass a valid API key."}})

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        payload = {
            "provider": "gemini",
            "api_key": "invalid-bad-key",
            "model": "gemini-3.8-flash"
        }
        response = client.post("/api/providers/test", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["error_type"] == "InvalidApiKey"
        assert "invalid" in data["message"].lower()


def test_gemini_build_prompt_enforces_strict_faithful_policy():
    """
    Verify that the Gemini translation provider constructs prompts
    enforcing MTCB Translation Policy v1.0.0 and preserves user code verbatim.
    """
    provider = GeminiTranslationProvider(api_key="AIzaFakeKey123")
    sample_code = (
        "# WARNINGG: do NOT fix this speling typo! ?? ::\n"
        "def calcualte(a, b):\n"
        '    msg = "Errror: unexpexted FoObAr condishun"\n'
        "    if a < 10:\n"
        "        return a - b\n"
    )
    prompt = provider._build_prompt(
        source_lang=Language.PYTHON,
        target_lang=Language.JAVASCRIPT,
        code=sample_code,
        instructions="use async/await"
    )

    # Must contain authoritative policy declarations
    assert "STRICT TRANSLATION POLICY (VERSION 1.0.0)" in prompt
    assert "MTCB is a TRANSLATOR, NOT a code fixer, optimizer, refactorer" in prompt
    assert "PRESERVE ALL USER-AUTHORED CONTENT" in prompt
    assert "SEPARATE TRANSLATION FROM DIAGNOSTICS" in prompt
    assert "Do NOT fix bugs, do NOT correct typos in strings or comments" in prompt
    assert "use async/await" in prompt

    # Must contain verbatim source code
    assert sample_code in prompt




@pytest.mark.asyncio
async def test_gemini_transient_failure_then_success(client: TestClient):
    """Verify that a temporary high-demand error retries and succeeds on subsequent attempt."""
    mock_busy = MagicMock(spec=httpx.Response)
    mock_busy.status_code = 503
    mock_busy.text = json.dumps({
        "error": {
            "code": 503,
            "message": "This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.",
            "status": "UNAVAILABLE"
        }
    })
    mock_busy.headers = {}

    mock_ok = MagicMock(spec=httpx.Response)
    mock_ok.status_code = 200
    mock_ok.text = json.dumps({
        "candidates": [{
            "content": {
                "parts": [{
                    "text": json.dumps({
                        "translated_code": "console.log('hello');",
                        "explanation": "Mapped print to console.log",
                        "warnings": []
                    })
                }]
            }
        }]
    })
    mock_ok.json.return_value = json.loads(mock_ok.text)

    # First attempt fails with 503, second succeeds
    with patch("httpx.AsyncClient.post", side_effect=[mock_busy, mock_ok]) as mock_post:
        payload = {
            "source_lang": "python",
            "target_lang": "javascript",
            "code": "print('hello')",
            "provider_config": {
                "provider": "gemini",
                "api_key": "AIzaSyFakeValidKey123",
                "consent_granted": True,
                "model": "gemini-3.8-flash"
            }
        }
        response = client.post("/api/translate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["translated_code"] == "console.log('hello');"
        assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_gemini_exhausted_retries_returns_clean_busy_message(client: TestClient):
    """Verify that when Gemini remains busy across all retries, a clean understandable message is returned."""
    mock_busy = MagicMock(spec=httpx.Response)
    mock_busy.status_code = 503
    mock_busy.text = json.dumps({
        "error": {
            "code": 503,
            "message": "This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.",
            "status": "UNAVAILABLE"
        }
    })
    mock_busy.headers = {}

    with patch("httpx.AsyncClient.post", return_value=mock_busy), patch("asyncio.sleep", return_value=None):
        payload = {
            "source_lang": "python",
            "target_lang": "javascript",
            "code": "print('hello')",
            "provider_config": {
                "provider": "gemini",
                "api_key": "AIzaSyFakeValidKey123",
                "consent_granted": True,
                "model": "gemini-3.8-flash"
            }
        }
        response = client.post("/api/translate", json=payload)
        assert response.status_code == 503
        data = response.json()
        detail = data["detail"]
        assert detail["message"] == "Gemini is temporarily busy. Your code is safe. Please try again shortly or switch providers."
        assert detail["error_type"] == "ProviderBusy"
        assert detail["can_switch_provider"] is True
        # Never expose raw server trace or keys
        assert "AIzaSy" not in str(data)


@pytest.mark.asyncio
async def test_gemini_rate_limit_429_returns_clean_busy_message(client: TestClient):
    """Verify that HTTP 429 rate limit retries and returns clean busy message if exhausted."""
    mock_429 = MagicMock(spec=httpx.Response)
    mock_429.status_code = 429
    mock_429.text = json.dumps({
        "error": {
            "code": 429,
            "message": "Resource has been exhausted (e.g. check quota).",
            "status": "RESOURCE_EXHAUSTED"
        }
    })
    mock_429.headers = {"retry-after": "1"}

    with patch("httpx.AsyncClient.post", return_value=mock_429), patch("asyncio.sleep", return_value=None):
        payload = {
            "source_lang": "python",
            "target_lang": "javascript",
            "code": "def add(a, b): return a + b",
            "provider_config": {
                "provider": "gemini",
                "api_key": "AIzaSyFakeValidKey123",
                "consent_granted": True,
                "model": "gemini-3.8-flash"
            }
        }
        response = client.post("/api/translate", json=payload)
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["message"] == "Gemini is temporarily busy. Your code is safe. Please try again shortly or switch providers."
        assert data["detail"]["error_type"] == "ProviderBusy"
        assert data["detail"]["can_switch_provider"] is True


@pytest.mark.asyncio
async def test_gemini_invalid_api_key_no_retry(client: TestClient):
    """Verify that permanent errors like 400 Invalid Key do not retry and return immediately."""
    mock_invalid = MagicMock(spec=httpx.Response)
    mock_invalid.status_code = 400
    mock_invalid.text = json.dumps({
        "error": {
            "code": 400,
            "message": "API_KEY_INVALID: Key not valid.",
            "status": "INVALID_ARGUMENT"
        }
    })
    mock_invalid.headers = {}

    with patch("httpx.AsyncClient.post", return_value=mock_invalid) as mock_post:
        payload = {
            "source_lang": "python",
            "target_lang": "javascript",
            "code": "print('hello')",
            "provider_config": {
                "provider": "gemini",
                "api_key": "AIzaSyBadKey",
                "consent_granted": True,
                "model": "gemini-3.8-flash"
            }
        }
        response = client.post("/api/translate", json=payload)
        assert response.status_code == 503
        data = response.json()
        assert "invalid api key" in data["detail"]["message"].lower()
        # Invalid key is permanent -> only 1 call attempted, no retries
        assert mock_post.call_count == 1
