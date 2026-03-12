# PickyText — VPS Translation Backend

## Purpose

PickyText uses a **self-hosted LibreTranslate instance** on a VPS as its primary
translation backend. The client (`translation/libretranslate.py`) sends OCR text to
the API and gets back translated text. No cloud API key (e.g. Google, DeepL) is used.

---

## VPS Requirements

| Resource | Minimum | Recommended |
|---|---|---|
| RAM | 4 GB | 8 GB |
| CPU | 2 vCPU | 4 vCPU |
| Disk | 5 GB | 10 GB |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| Docker | 24.x | 24.x |
| Open port | 5000 (or 443 via nginx) | 443 (HTTPS via nginx) |

RAM breakdown: ~30–80 MB per language model. 20 languages ≈ 1–2 GB peak loading.
The remaining RAM budget is comfortable on an 8 GB VPS.

---

## Docker Container Setup

```bash
# Pull image
docker pull libretranslate/libretranslate

# Run (production)
docker run -d \
  --name libretranslate \
  -p 5000:5000 \
  --restart unless-stopped \
  -v lt-local:/home/libretranslate/.local \
  libretranslate/libretranslate \
  --load-only en,ar,zh,nl,fr,de,hi,id,it,ja,ko,pl,pt,ru,es,sv,th,tr,uk,vi \
  --disable-web-ui \
  --api-keys

# Check it's running
curl http://localhost:5000/languages
```

### Flag reference

| Flag | Purpose |
|---|---|
| `--load-only <codes>` | Comma-separated BCP-47 codes to load. Omit to load ALL (uses much more RAM). |
| `--disable-web-ui` | Disables the browser UI. API still works. Reduces attack surface. |
| `--api-keys` | Requires an API key on every request. Generate keys inside the container (see below). |
| `--req-limit <n>` | Max requests per minute per IP (rate-limiting). Default: unlimited. |
| `--threads <n>` | Translation threads. Default: 4. Match to vCPU count. |
| `--char-limit <n>` | Max chars per request. Default: unlimited. Recommended: 5000. |

### Generate API keys (when `--api-keys` is enabled)

```bash
# Enter the container
docker exec -it libretranslate bash

# Generate a key
ltmanage keys add --name pickytext

# Copy the printed key into PickyText Settings → Translation → API key
```

### Update the container

```bash
docker pull libretranslate/libretranslate
docker stop libretranslate
docker rm libretranslate
# Re-run the docker run command above — -v lt-local preserves downloaded models
```

---

## Nginx Reverse Proxy + HTTPS (recommended for production)

Without HTTPS, the API key and OCR text travel in plaintext. Configure nginx + Let's Encrypt:

```bash
# Install certbot + nginx (Ubuntu)
sudo apt install nginx certbot python3-certbot-nginx -y

# Register certificate
sudo certbot --nginx -d translate.yourdomain.com
```

`/etc/nginx/sites-available/libretranslate`:

```nginx
server {
    listen 443 ssl;
    server_name translate.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/translate.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/translate.yourdomain.com/privkey.pem;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;

    # Body size — OCR text can be long (separator-batched multi-region)
    client_max_body_size 512k;

    location / {
        proxy_pass         http://localhost:5000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_read_timeout 30s;
    }
}

# Redirect HTTP → HTTPS
server {
    listen 80;
    server_name translate.yourdomain.com;
    return 301 https://$host$request_uri;
}
```

```bash
sudo ln -s /etc/nginx/sites-available/libretranslate /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Set the PickyText endpoint to `https://translate.yourdomain.com`.

---

## API Endpoints Used by PickyText

| Method | Path | Used for |
|---|---|---|
| `POST` | `/translate` | Translate text |
| `GET` | `/languages` | Ping / latency check (Settings → Test Connection) |

### POST `/translate` — request body

```json
{
  "q": "text to translate\n|||REGION_SEP|||\nmore text",
  "source": "auto",
  "target": "en",
  "format": "text",
  "api_key": "your-key-here"
}
```

- `source`: BCP-47 code or `"auto"` (auto-detect). LibreTranslate supports `"auto"` natively.
- `format`: always `"text"` (PickyText does not send HTML).
- `api_key`: omit the field entirely if `--api-keys` is not enabled.

### POST `/translate` — response

```json
{
  "translatedText": "translated text\n|||REGION_SEP|||\ntranslated more text"
}
```

The separator (`\n|||REGION_SEP|||\n`) is passed through verbatim by LibreTranslate
in almost all language pairs. PickyText splits on it to recover per-region translations.

**Edge case**: very rarely a translation engine will mangle or drop the separator.
`translation/engine.py` handles this: if the split count mismatches the input count it
pads/trims to match rather than crashing.

---

## Multi-Region Separator Batching

PickyText sends all OCR regions in one HTTP request to minimize latency.

```
"Text from region 1."
\n|||REGION_SEP|||\n
"Text from region 2."
\n|||REGION_SEP|||\n
"Text from region 3."
```

Code location: `translation/engine.py` → `TranslationEngine.translate(texts, source, target)`

The separator was chosen to be:
- Unlikely to appear in natural language text
- On its own line (so translation models don't attach it to adjacent sentences)
- Short enough not to inflate token/char counts significantly

---

## Client-Side Integration

**File**: `translation/libretranslate.py`

```python
class LibreTranslateClient:
    def __init__(self, endpoint: str, api_key: str = "") -> None: ...

    async def translate(self, text: str, source: str, target: str) -> str:
        # POST /translate, returns translatedText string
        # Raises httpx.HTTPStatusError on 4xx/5xx
        # Raises httpx.ConnectError / TimeoutException when VPS unreachable

    async def ping(self) -> float:
        # GET /languages, returns round-trip latency in ms
        # Used by Settings → Test Connection button
```

**Timeout**: 10 s for translation, 5 s for ping.

**Error routing** (`translation/engine.py`):
- `httpx.ConnectError` / `TimeoutException` / `NetworkError` / `RemoteProtocolError`
  → friendly message: *"Cannot connect to LibreTranslate at `<endpoint>`…"*
- `fallback = "argos"` in settings → try Argos Translate locally before raising
- All other HTTP errors (4xx, 5xx) → re-raised as-is

---

## Settings Keys (stored in `%APPDATA%\PickyText\settings.json`)

| Key | Type | Default | Description |
|---|---|---|---|
| `translation_endpoint` | `str` | `"http://localhost:5000"` | Full URL of LibreTranslate instance |
| `translation_api_key` | `str` | `""` | API key (leave empty if `--api-keys` not enabled) |
| `translation_source_language` | `str` | `"auto"` | BCP-47 or `"auto"` |
| `translation_target_language` | `str` | `"en"` | BCP-47 target |
| `translation_fallback` | `str` | `"none"` | `"none"` or `"argos"` |

These are editable in **Settings → Translation** inside the app.

---

## Language Codes Loaded on the VPS

These match what PickyText ships in its Settings language dropdown:

```
en  ar  zh  nl  fr  de  hi  id  it  ja  ko  pl  pt  ru  es  sv  th  tr  uk  vi
```

> **Chinese note**: LibreTranslate uses `zh` (Simplified). Traditional Chinese (`zh-Hant`)
> is not a separate model — avoid using `zh-Hant` as a LibreTranslate source/target;
> use `zh` instead. PickyText's UI labels it "Chinese (Simplified)".

---

## Argos Translate (Offline Fallback)

Argos is the same open-source engine that LibreTranslate uses internally.
When installed locally it allows translation without any network connection.

- **Install**: `pip install argostranslate` (or optional component in the PickyText installer)
- **Models**: downloaded at runtime via **Settings → Optional Features → Download Model**
  Stored in `%APPDATA%\argos-translate\` (Argos default; not under PickyText's folder)
- **"auto" source**: Argos does **not** support `source="auto"`. `translation/argos.py`
  converts `"auto"` → `"en"` before calling Argos. LibreTranslate handles `"auto"` natively.
- **Quality**: lower than LibreTranslate for CJK; acceptable for European languages.

---

## Security Considerations

| Concern | Mitigation |
|---|---|
| API key exposure | Key stored in `settings.json` (user-local, `%APPDATA%`). Password field in Settings UI. Never logged. |
| OCR text sent to VPS | All text is from the user's own screen. Still, use HTTPS to prevent interception on networks you don't control. |
| Open port 5000 | Block 5000 in the VPS firewall; expose only 443 via nginx. |
| DoS / abuse | Enable `--api-keys` and `--req-limit` on the container. |
| LibreTranslate web UI | Disable with `--disable-web-ui` — prevents unauthorized use of the server. |
| Unencrypted LAN use | If endpoint is `http://` on a non-localhost host, PickyText does not warn. AI assistant should flag this if it appears in settings. |

---

## Monitoring & Maintenance

```bash
# View live logs
docker logs -f libretranslate

# Check memory usage
docker stats libretranslate

# Restart after system reboot (--restart unless-stopped handles this automatically)
docker start libretranslate

# Test API from the VPS itself
curl -s -X POST http://localhost:5000/translate \
  -H "Content-Type: application/json" \
  -d '{"q":"Hello","source":"en","target":"it","format":"text"}' | python3 -m json.tool
```

---

## Development / Local Testing (no VPS)

Run LibreTranslate locally with Docker Desktop:

```bash
docker run -d -p 5000:5000 --name lt-dev \
  libretranslate/libretranslate \
  --load-only en,it,fr,de \
  --disable-web-ui
```

Then in PickyText Settings set endpoint to `http://localhost:5000` and leave API key blank.

The `--load-only en,it,fr,de` keeps startup fast and RAM usage under 400 MB for dev.

---

## AI Assistant Notes

When working on translation-related code in this project:

- **`translation/libretranslate.py`** — sole HTTP client. Do not add retry logic here;
  retries are the responsibility of `engine.py`.
- **`translation/engine.py`** — router. Primary → Argos fallback → raise. All error
  message formatting lives here, not in the UI.
- **`translation/argos.py`** — must convert `source="auto"` to `"en"` before calling
  Argos. This is already done; do not remove it.
- **Separator constant** `_REGION_SEP = "\n|||REGION_SEP|||\n"` is defined once in
  `engine.py`. Do not redefine it elsewhere; import if needed.
- **UI language combos** in `ui/overlay.py` (`_TRANS_LANGS`) and `ui/settings_window.py`
  (`_LANGUAGES`) must stay in sync. Both use BCP-47 codes. The overlay combos are the
  *active* source/target used for the current capture; settings are the *defaults*.
- **`source="auto"`** is valid to send to LibreTranslate. Never strip it before the LT
  call. Only strip/replace it when falling through to Argos.
- **Test Connection** in Settings hits `GET /languages` (the ping endpoint), not
  `/translate`. A successful ping proves the server is reachable but does not prove a
  specific language pair works.
- When the VPS is down, `httpx.ConnectError` is the most common exception class.
  `httpx.TimeoutException` fires after 10 s. Both are handled in `engine.py`.
- The settings key `translation_fallback` defaults to `"none"`. If a user hasn't
  explicitly set it to `"argos"`, Argos is never tried even if it's installed.
  This is intentional — Argos quality may be lower and the user should opt in.
