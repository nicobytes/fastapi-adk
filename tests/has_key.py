from __future__ import annotations

import os


def has_gemini_key() -> bool:
    return bool(os.environ.get("GOOGLE_API_KEY", "").strip())


def has_whatsapp_creds() -> bool:
    return bool(
        os.environ.get("WHATSAPP_TOKEN", "").strip()
        and os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    )
