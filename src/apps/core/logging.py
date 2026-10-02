import logging
import re
import traceback

SENSITIVE_PATTERNS = [
    # 1. Authorization header bearer tokens
    (
        re.compile(r"(?i)\b(bearer\s+)([A-Za-z0-9_\-\.]+)"),
        r"\1[REDACTED]",
    ),
    # 2. Quoted sensitive key-values (handles spaces e.g. password="secret phrase")
    (
        re.compile(
            r"(?i)([\"']?(?:password|pass|secret|token|otp|code|api_key|"
            r"delivery_secret|smtp_password)[\"']?\s*[:=]\s*)([\"'])(.*?)\2"
        ),
        r"\1\2[REDACTED]\2",
    ),
    # 3. Connection URIs with or without user (e.g. redis://:pass@host)
    (
        re.compile(
            r"([a-zA-Z]+://[^/@:\s]*:)"
            r"([^@\s\"']+)"
            r"(@[^\"'\s,;]+)"
        ),
        r"\1[REDACTED]\3",
    ),
    # 4. Standalone numeric OTP codes (4 to 8 digits)
    (
        re.compile(r"(?i)(otp|verification[_\s-]?code)\s*[:=]?\s*(\b\d{4,8}\b)"),
        r"\1: [REDACTED]",
    ),
    # 5. Unquoted sensitive key-values
    (
        re.compile(
            r"(?i)([\"']?(?:password|pass|secret|token|otp|code|api_key|"
            r"delivery_secret|smtp_password)[\"']?\s*[:=]\s*(?:bearer\s+)?)"
            r"(?!\[REDACTED\])[^\"'\s,;]+"
        ),
        r"\1[REDACTED]",
    ),
]


def scrub_sensitive_text(text: str) -> str:
    """Masks known sensitive patterns from the input string."""
    if not isinstance(text, str):
        return text
    for pattern, replacement in SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that sanitizes log records to prevent leaking passwords,
    OTP codes, tokens, and infrastructure secrets in production logs.
    Handles parameterized logging messages, quoted secrets, and tracebacks safely.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            rendered = record.getMessage()
        except Exception:
            rendered = str(record.msg)

        record.msg = scrub_sensitive_text(rendered)
        record.args = ()

        if record.exc_info and not record.exc_text:
            try:
                record.exc_text = "".join(traceback.format_exception(*record.exc_info))
            except Exception:
                pass

        if record.exc_text:
            record.exc_text = scrub_sensitive_text(record.exc_text)

        if getattr(record, "stack_info", None):
            record.stack_info = scrub_sensitive_text(record.stack_info)

        return True
