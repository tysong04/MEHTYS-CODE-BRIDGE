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

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
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
        assert response.status_code == 502
        data = response.json()
        assert "rate limit or quota" in data["detail"]["message"].lower()


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


