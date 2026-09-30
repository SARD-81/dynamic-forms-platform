import logging
import re

# Masking patterns for sensitive data
SENSITIVE_PATTERNS = [
    # Key-value assignments for sensitive terms (password, secret, token, otp, key)
    (
        re.compile(
            r"""(?i)(["']?(?:password|pass|secret|token|otp|code|api_key|delivery_secret|smtp_password)["']?\s*[:=]\s*["']?)([^"'\s,;]+)"""
        ),
        r"\1[REDACTED]",
    ),
    # Authorization header bearer tokens
    (
        re.compile(r"(?i)(bearer\s+)([A-Za-z0-9_\-\.]+)"),
        r"\1[REDACTED]",
    ),
    # Credentials inside connection URIs (postgres://user:pass@host or redis://:pass@host)
    (
        re.compile(r"([a-zA-Z]+://[^:]+:)([^@]+)(@.+)"),
        r"\1[REDACTED]\3",
    ),
    # Standalone numeric OTP codes (4 to 8 digits) when preceded by otp/code keywords
    (
        re.compile(r"(?i)(otp|verification[_\s-]?code)\s*[:=]?\s*(\b\d{4,8}\b)"),
        r"\1: [REDACTED]",
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
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = scrub_sensitive_text(record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: (scrub_sensitive_text(v) if isinstance(v, str) else v)
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    scrub_sensitive_text(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )

        return True
