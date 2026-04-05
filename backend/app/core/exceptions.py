class EgrulAPIError(Exception):
    """Raised when the external EGRUL API returns an error or unexpected response."""


class OrganizationNotFoundError(Exception):
    """Raised when no organization is found for the given INN."""


class InvalidINNError(Exception):
    """Raised when the provided INN has an invalid format."""
