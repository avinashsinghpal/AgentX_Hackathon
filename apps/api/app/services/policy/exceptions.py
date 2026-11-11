class PolicyError(Exception):
    """Base class for deterministic policy-engine failures."""


class PolicyNotFoundError(PolicyError):
    """The seller has no active policy."""


class PolicyValidationError(PolicyError):
    """The seller's stored policy document is invalid."""


class OwnershipError(PolicyError):
    """Case, order, seller or buyer do not agree on ownership."""


class DuplicateClaimError(PolicyError):
    """A conflicting claim already exists for the same order."""


class AuthorizationError(PolicyError):
    """An action was requested without a valid authorization."""
