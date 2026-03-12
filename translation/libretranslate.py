"""LibreTranslate HTTP client (self-hosted VPS)."""
import httpx


class LibreTranslateClient:
    def __init__(self, endpoint: str, api_key: str = "") -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key

    async def translate(self, text: str, source: str, target: str) -> str:
        payload: dict = {
            "q": text,
            "source": source,
            "target": target,
            "format": "text",
        }
        if self.api_key:
            payload["api_key"] = self.api_key

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{self.endpoint}/translate", json=payload)
            response.raise_for_status()
            return response.json()["translatedText"]

    async def ping(self) -> float:
        """Return latency in ms, or raise on failure."""
        import time
        async with httpx.AsyncClient(timeout=5.0) as client:
            t0 = time.perf_counter()
            await client.get(f"{self.endpoint}/languages")
            return (time.perf_counter() - t0) * 1000
