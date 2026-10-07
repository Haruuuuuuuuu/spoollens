"""SpoolLens: auditable fixed-width text report extraction."""
from .engine import (
    VERSION as __version__, ExportBlocked, InputError, LoadedRule, Result, RuleError,
    SpoolLensError, canonical_rule_bytes, empty_rule, execute, export_result,
    load_rule, rule_issues, validate_rule, write_json_artifact,
)

__all__ = ["__version__", "ExportBlocked", "InputError", "LoadedRule", "Result",
           "RuleError", "SpoolLensError", "canonical_rule_bytes", "empty_rule",
           "execute", "export_result", "load_rule", "rule_issues", "validate_rule", "write_json_artifact"]
