import logging
import re
import traceback

SENSITIVE_KEY = (
    # The lookahead finds a sensitive label once; consuming the whole key then
    # avoids repeatedly rescanning suffixes of long attacker-controlled words.
    r"(?:(?=[\w-]*(?:password|passwd|secret|token|api[_-]?key|credential))[\w-]+|"
    r"smtp[_-]?(?:user|username)|django_email_host_user|"
    r"pass|otp|code|verification[_\s-]?code)"
)

SENSITIVE_PATTERNS = [
    # Usernames can also be credentials, particularly in SMTP connection URIs.
    (
        re.compile(
            r"(?<![\w+.-])([a-zA-Z][a-zA-Z0-9+.-]*://)([^/:\s\"']+):"
            r"([^\s\"']*)(@[^\"'\s,;]+)"
        ),
        r"\1[REDACTED]:[REDACTED]\4",
    ),
    # Some API clients embed a token as URI userinfo without a password delimiter.
    (
        re.compile(r"(?<![\w+.-])([a-zA-Z][a-zA-Z0-9+.-]*://)([^/:\s@\"']+)(@)"),
        r"\1[REDACTED]\3",
    ),
    # Quoted and bytes-rendered authorization values occur in exception/debug logs.
    (
        re.compile(r"(?i)(\bbearer\s+)(?:[bu])?([\"'])(.*?)\2", re.DOTALL),
        r"\1\2[REDACTED]\2",
    ),
    # 1. Authorization header bearer tokens
    (
        re.compile(r"(?i)\b(bearer\s+)([^\s,;\"'}]+)"),
        r"\1[REDACTED]",
    ),
    # 2. Quoted sensitive key-values (handles spaces e.g. password="secret phrase")
    (
        re.compile(
            rf"(?i)(?<![\w-])([\"']?{SENSITIVE_KEY}[\"']?\s*[:=]\s*)"
            r"(?:[bu])?([\"'])(.*?)\2",
            re.DOTALL,
        ),
        r"\1\2[REDACTED]\2",
    ),
    # 3. Connection URIs with or without user (e.g. redis://:pass@host)
    (
        re.compile(
            r"(?<![\w+.-])([a-zA-Z][a-zA-Z0-9+.-]*://[^/@:\s]*:)"
            r"([^\s\"']+)"
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
            rf"(?i)(?<![\w-])([\"']?{SENSITIVE_KEY}[\"']?\s*[:=]\s*(?:bearer\s+)?)"
            r"(?!\[REDACTED\])[^\"'\s,;&}]+"
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
            rendered = "Log message unavailable (formatting failed)"

        record.msg = scrub_sensitive_text(rendered)
        record.args = ()

        if record.exc_info and not record.exc_text:
            try:
                record.exc_text = "".join(traceback.format_exception(*record.exc_info))
            except Exception:
                record.exc_text = "Exception details unavailable"

        if record.exc_text:
            record.exc_text = scrub_sensitive_text(record.exc_text)

        # Every formatter must use the sanitized exception text, including later
        # handlers that otherwise regenerate a traceback from exc_info.
        record.exc_info = None

        if getattr(record, "stack_info", None):
            record.stack_info = scrub_sensitive_text(record.stack_info)

        return True
