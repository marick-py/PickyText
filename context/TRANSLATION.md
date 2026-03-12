# PickyText — Translation

## Backend Priority

```
LibreTranslate (self-hosted VPS)  ←  Primary
        ↓ unreachable / timeout
Argos Translate (local)           ←  Optional fallback (installed separately)
        ↓ not installed
Graceful error with message
```

---

## LibreTranslate (Primary)

### Setup — VPS Side (Docker)

```bash
docker run -d \
  --name libretranslate \
  -p 5000:5000 \
  --restart unless-stopped \
  -v lt-local:/home/libretranslate/.local \
  libretranslate/libretranslate \
  --load-only en,it,fr,de,es,pt,ja,zh,ko,ar,ru,nl,pl,sv,tr,uk,hi,vi,th,id \
  --disable-web-ui
```

- VPS: 8GB RAM, 4 CPUs (Riccardo's existing VPS)
- `--load-only` restricts loaded models to save RAM (~300–600MB total for listed languages)
- `--disable-web-ui` for security (API only)
- Reverse proxy recommended (nginx + HTTPS) for secure access from client

RAM estimate per language model: ~30–80MB. 20 languages ≈ 1–2GB peak, well within VPS budget.

### Nginx Reverse Proxy (recommended)

```nginx
server {
    listen 443 ssl;
    server_name translate.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
    }
}
```

Configure endpoint in PickyText settings as `https://translate.yourdomain.com`.

### Client Integration (`translation/libretranslate.py`) — ✅ Implemented

```python
class LibreTranslateClient:
    async def translate(self, text, source, target) -> str: ...
    async def ping(self) -> float:  # returns latency in ms — used by Settings Test Connection button
        ...
```

Uses `httpx` async client with 10s timeout. `ping()` hits `/languages` endpoint.

---

## Multi-Region Batching (Separator Trick)

To minimize API calls while keeping translations context-independent:

### Strategy
Combine all region texts into a single request, separated by a unique delimiter:

```
REGION_SEPARATOR = "\n|||REGION_SEP|||\n"
```

Batch payload:
```
"Text from region 1 here."
|||REGION_SEP|||
"Text from region 2 here."
|||REGION_SEP|||
"Text from region 3 here."
```

After translation, split the response on the same delimiter → each part maps back to its region.

### Why This Works
- LibreTranslate translates each "paragraph" somewhat independently
- The separator is unlikely to appear in natural text
- Single HTTP round-trip regardless of region count
- If the separator gets mangled by translation (rare edge case): fall back to individual requests

### Implementation — ✅ Implemented (`translation/engine.py`)

`TranslationEngine.translate(texts, source, target)` is an `async` method:
- Joins with `REGION_SEP`, calls LibreTranslate, splits result
- If separator count mismatches (mangled by engine): pads/trims to match input length
- On LibreTranslate failure: routes to Argos fallback (if configured) or raises

`translation/argos.py` ✅ — wraps `argostranslate.translate` (requires `pip install argostranslate` + language models)

---

## Argos Translate (Optional Local Fallback)

### When Used
- VPS unreachable (no internet, VPS down)
- User preference for fully offline operation
- Installed as optional component during setup

### Installation
Optional component in Inno Setup installer:
- Installs `argostranslate` Python package
- User selects language pairs to pre-download (~100MB per pair)
- Language pairs stored in `%APPDATA%\PickyText\argos_packages\`

### Integration (`translation/argos.py`)

```python
import argostranslate.package
import argostranslate.translate

def translate(text: str, source: str, target: str) -> str:
    return argostranslate.translate.translate(text, source, target)
```

Note: Argos Translate quality is lower than LibreTranslate for non-European languages. For CJK, prefer LibreTranslate.

---

## Translation Router (`translation/engine.py`)

```python
class TranslationEngine:
    def translate_regions(
        self,
        texts: list[str],   # one string per region (joined words)
        source: str,         # BCP-47 or "auto"
        target: str          # BCP-47
    ) -> list[str]:
        """
        Attempts LibreTranslate batch → Argos fallback → raises TranslationUnavailableError
        """
```

---

## Language Support

### Supported Languages (LibreTranslate)
| Code | Language |
|------|----------|
| `en` | English |
| `it` | Italian |
| `fr` | French |
| `de` | German |
| `es` | Spanish |
| `pt` | Portuguese |
| `ja` | Japanese |
| `zh` | Chinese (Simplified) |
| `ko` | Korean |
| `ar` | Arabic |
| `ru` | Russian |
| `nl` | Dutch |
| `pl` | Polish |
| `sv` | Swedish |
| `tr` | Turkish |
| `uk` | Ukrainian |
| `hi` | Hindi |
| `vi` | Vietnamese |
| `th` | Thai |
| `id` | Indonesian |

Source can be `"auto"` for language auto-detection (LibreTranslate supports this).

### CJK Notes
- Japanese vertical text: OCR handles orientation; translation input is horizontal unicode — no special handling needed
- Chinese: LibreTranslate uses `zh` for Simplified; Traditional (`zh-Hant`) may require separate model
- Korean: fully supported

---

## Error Handling

| Error | Behavior |
|---|---|
| VPS timeout (>10s) | Fallback to Argos if installed, else tray warning |
| VPS returns 5xx | Same fallback logic |
| Language pair not supported | Show inline error per region |
| Translation mangled separator | Silent per-region fallback |
| No translation backend available | "Translation unavailable" shown in region, copy still works |
