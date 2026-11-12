from scripts.list_gemini_models import (
    LIST_MODELS_URL,
    list_available_models,
    models_supporting_generate_content,
    parse_model_list,
)


def test_parse_model_list_keeps_only_names_and_generation_methods():
    payload = {
        "models": [
            {
                "name": "models/gemini-example",
                "supportedGenerationMethods": ["generateContent", "countTokens"],
                "description": "ignored",
                "inputTokenLimit": 1000,
            },
            {
                "name": "models/embedding-example",
                "supportedGenerationMethods": ["embedContent"],
            },
            {"name": "malformed", "supportedGenerationMethods": "generateContent"},
            None,
        ]
    }

    assert parse_model_list(payload) == [
        {
            "name": "models/gemini-example",
            "supportedGenerationMethods": ["generateContent", "countTokens"],
        },
        {
            "name": "models/embedding-example",
            "supportedGenerationMethods": ["embedContent"],
        },
    ]


def test_parse_model_list_rejects_missing_models_array():
    try:
        parse_model_list({"other": []})
    except ValueError as error:
        assert "models list" in str(error)
    else:
        raise AssertionError("Expected malformed ListModels response to be rejected")


def test_identifies_only_models_supporting_generate_content():
    models = parse_model_list({
        "models": [
            {
                "name": "models/text-model",
                "supportedGenerationMethods": ["generateContent", "countTokens"],
            },
            {
                "name": "models/embedding-model",
                "supportedGenerationMethods": ["embedContent"],
            },
        ]
    })

    assert models_supporting_generate_content(models) == [models[0]]


def test_list_models_uses_v1beta_endpoint_and_api_key_header():
    captured = {}

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "models": [{
                    "name": "models/text-model",
                    "supportedGenerationMethods": ["generateContent"],
                }]
            }

    def mock_get(url, headers, timeout):
        captured.update(url=url, headers=headers, timeout=timeout)
        return MockResponse()

    models = list_available_models("mock-secret-key", http_get=mock_get)

    assert captured["url"] == LIST_MODELS_URL
    assert captured["headers"] == {"x-goog-api-key": "mock-secret-key"}
    assert "mock-secret-key" not in captured["url"]
    assert models[0]["name"] == "models/text-model"
