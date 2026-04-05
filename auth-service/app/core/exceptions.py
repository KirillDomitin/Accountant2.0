class InvalidCredentialsError(Exception):
    pass


class InvalidTokenError(Exception):
    pass


class RateLimitError(Exception):
    pass


class UserAlreadyExistsError(Exception):
    pass


class UserNotFoundError(Exception):
    pass
