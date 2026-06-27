import httpx
import pytest

from stock_agent.app.providers.server_chan import ServerChanProvider


def test_server_chan_posts_title_and_markdown_content():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"code": 0, "message": "success"})

    provider = ServerChanProvider(send_key="SCT123", client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = provider.send(title="早报", content="# 早报")
    assert result.success is True
    assert str(requests[0].url) == "https://sctapi.ftqq.com/SCT123.send"
    assert b"title=" in requests[0].content


def test_server_chan_requires_send_key():
    with pytest.raises(ValueError, match="SERVER_CHAN_SEND_KEY"):
        ServerChanProvider(send_key="")


def test_server_chan_returns_failure_for_nonzero_code():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 1024, "message": "bad key"})

    provider = ServerChanProvider(send_key="SCT123", client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = provider.send(title="早报", content="# 早报")
    assert result.success is False
    assert result.error_message == "bad key"


def test_server_chan_returns_failure_for_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "server error"})

    provider = ServerChanProvider(send_key="SCT123", client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = provider.send(title="早报", content="# 早报")
    assert result.success is False
    assert result.error_message == "HTTP 500"
