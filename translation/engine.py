"""
Translation router — LibreTranslate (primary) → Argos (fallback).
"""
from __future__ import annotations

_REGION_SEP = "\n|||REGION_SEP|||\n"


class TranslationEngine:
    def __init__(self, settings: dict) -> None:
        self._settings = settings

    async def translate(
        self,
        texts: list[str],
        source: str,
        target: str,
    ) -> list[str]:
        """
        Translate a list of per-region strings.
        Batches them into one request using the separator trick.
        Returns a list of translated strings (same length as input).
        """
        if not texts:
            return []

        batched = _REGION_SEP.join(texts)
        endpoint = self._settings.get("translation_endpoint", "http://localhost:5000")
        try:
            from translation.libretranslate import LibreTranslateClient
            client = LibreTranslateClient(
                endpoint=endpoint,
                api_key=self._settings.get("translation_api_key", ""),
            )
            result = await client.translate(batched, source, target)
        except Exception as lt_exc:
            fallback = self._settings.get("translation_fallback", "none")
            if fallback == "argos":
                try:
                    from translation.argos import translate_sync
                    result = translate_sync(batched, source, target)
                except RuntimeError:
                    raise RuntimeError(
                        f"LibreTranslate at {endpoint} is unreachable and "
                        "Argos Translate is not installed.\n"
                        "\u2022 Start your LibreTranslate server, or\n"
                        "\u2022 Install Argos: pip install argostranslate"
                    ) from None
            else:
                import httpx
                if isinstance(lt_exc, (httpx.ConnectError, httpx.TimeoutException,
                                       httpx.NetworkError, httpx.RemoteProtocolError)):
                    raise RuntimeError(
                        f"Cannot connect to LibreTranslate at {endpoint}.\n"
                        "Make sure your translation server is running, or update "
                        "the endpoint in Settings \u2192 Translation."
                    ) from lt_exc
                raise

        parts = result.split(_REGION_SEP)
        # Guard against separator being mangled by the translation engine
        if len(parts) != len(texts):
            return parts[:len(texts)] + [""] * max(0, len(texts) - len(parts))
        return parts
