class AccountServiceError(Exception):
    public_message = "Unable to complete the account operation."

    def __init__(self, message=None):
        super().__init__(message or self.public_message)


class AccountValidationError(AccountServiceError):
    public_message = "Please correct the account information."

    def __init__(self, errors):
        self.errors = errors
        super().__init__(self.public_message)


class OTPUnavailableError(AccountServiceError):
    public_message = "No usable verification code is available for this account."


class OTPExpiredError(AccountServiceError):
    public_message = "This verification code has expired. Request a new code."


class OTPInvalidCodeError(AccountServiceError):
    public_message = "The verification code is incorrect."


class OTPAttemptsExceededError(AccountServiceError):
    public_message = "Too many incorrect verification attempts. Request a new code."


class OTPAlreadyVerifiedError(AccountServiceError):
    public_message = "This account is already verified."


class OTPThrottleError(AccountServiceError):
    def __init__(self, message, retry_after):
        self.retry_after = max(1, int(retry_after))
        super().__init__(message)


class OTPCooldownError(OTPThrottleError):
    def __init__(self, retry_after):
        super().__init__(
            "Please wait before requesting another verification code.",
            retry_after,
        )


class OTPRateLimitError(OTPThrottleError):
    def __init__(self, retry_after):
        super().__init__(
            "Too many verification codes were requested. Try again later.",
            retry_after,
        )


class OTPEmailDeliveryError(AccountServiceError):
    public_message = (
        "The account state was saved, but the verification email could not be delivered."
    )


class AuthenticationFailedError(AccountServiceError):
    public_message = "The username or password is incorrect."


class InactiveAccountError(AccountServiceError):
    public_message = "Verify your email before signing in."
