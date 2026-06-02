class APIError(Exception):
    def __init__(self, message: str, status_code: int = 500, error_code: str = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


class AuthenticationError(APIError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401, error_code="AUTH_001")


class AuthorizationError(APIError):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status_code=403, error_code="AUTHZ_001")


class RateLimitError(APIError):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429, error_code="RATE_001")


class ResourceNotFoundError(APIError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404, error_code="NOT_FOUND_001")


class ValidationError(APIError):
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, status_code=400, error_code="VALIDATE_001")
