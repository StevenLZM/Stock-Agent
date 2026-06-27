from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class PushSendResult:
    success: bool
    error_message: str = ""


class ServerChanProvider:
    def __init__(self, send_key: str, client: httpx.Client | None = None):
        if not send_key:
            raise ValueError("SERVER_CHAN_SEND_KEY is required")
        self.send_key = send_key
        self.client = client or httpx.Client(timeout=10)

    def send(self, title: str, content: str) -> PushSendResult:
        response = self.client.post(
            f"https://sctapi.ftqq.com/{self.send_key}.send",
            data={"title": title, "desp": content},
        )
        if response.status_code < 200 or response.status_code >= 300:
            return PushSendResult(success=False, error_message=f"HTTP {response.status_code}")
        payload = response.json()
        if payload.get("code") != 0:
            return PushSendResult(success=False, error_message=str(payload.get("message", "ServerChan send failed")))
        return PushSendResult(success=True)
