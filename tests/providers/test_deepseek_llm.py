import httpx
import pytest

from stock_agent.app.providers.deepseek_llm import DeepSeekLLMProvider


def test_deepseek_provider_sends_flash_or_pro_model():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"title":"早报","summary":"摘要","key_points":["点"],"evidence_refs":["600519"],"watch_items":["观察"],"risk_note":"仅为信息整理，不构成投资建议。"}'
                        }
                    }
                ]
            },
        )

    provider = DeepSeekLLMProvider(
        api_key="sk-test",
        base_url="https://api.deepseek.com",
        pro_model="deepseek-v4-pro",
        flash_model="deepseek-v4-flash",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    report = provider.generate_morning_report([], quality="pro")
    assert report.title == "早报"
    assert b"deepseek-v4-pro" in requests[0].content
    assert requests[0].headers["Authorization"] == "Bearer sk-test"


def test_deepseek_provider_uses_flash_model_for_flash_quality():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"title":"快报","summary":"摘要","key_points":["点"],"evidence_refs":[],"watch_items":[],"risk_note":"仅为信息整理，不构成投资建议。"}'
                        }
                    }
                ]
            },
        )

    provider = DeepSeekLLMProvider(
        api_key="sk-test",
        base_url="https://api.deepseek.com",
        pro_model="deepseek-v4-pro",
        flash_model="deepseek-v4-flash",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    provider.generate_morning_report([], quality="flash")
    assert b"deepseek-v4-flash" in requests[0].content


def test_deepseek_provider_rejects_non_json_model_content():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "not-json"}}]})

    provider = DeepSeekLLMProvider(
        api_key="sk-test",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(ValueError, match="valid JSON"):
        provider.generate_morning_report([])


def test_deepseek_provider_requires_api_key():
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        DeepSeekLLMProvider(api_key="")
