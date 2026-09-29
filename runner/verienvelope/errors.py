"""Errors that must not be turned into a passing result."""


class VeriEnvelopeError(Exception):
    """Base error for a run that does not have a trustworthy result."""


class PolicyError(VeriEnvelopeError):
    """Execution was refused, or the caller asked for something the policy forbids."""


class SchemaError(VeriEnvelopeError):
    """An object does not match the published schema."""


class MethodError(VeriEnvelopeError):
    """The method spec is unusable, or it disagrees with this runner."""
