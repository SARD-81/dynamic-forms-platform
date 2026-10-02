import logging
import re
import traceback

SENSITIVE_PATTERNS = [
    # 1. Authorization header bearer tokens (must run before general key-values)
    (
        re.compile(r"(?i)\b(bearer\s+)([A-Za-z0-9_\-\.]+)"),
        r"\1[REDACTED]",
    ),
    # 2. Credentials inside connection URIs (postgres://user:pass@host or redis://:pass@host)
    (
        re.compile(r"([a-zA-Z]+://[^:]+:)([^@]+)(@.+)"),
        r"\1[REDACTED]\3",
    ),
    # 3. Standalone numeric OTP codes (4 to 8 digits) when preceded by otp/code keywords
    (
        re.compile(r"(?i)(otp|verification[_\s-]?code)\s*[:=]?\s*(\b\d{4,8}\b)"),
        r"\1: [REDACTED]",
    ),
    # 4. Key-value assignments for sensitive terms (password, secret, token, api_key, etc.)
    (
        re.compile(
            r"""(?i)(["']?(?:password|pass|secret|token|otp|code|api_key|delivery_secret|smtp_password)["']?\s*[:=]\s*["']?(?:bearer\s+)?)(?!\[REDACTED\])([^"'\s,;]+)"""
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
    Handles parameterized logging messages and exception tracebacks safely.
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
