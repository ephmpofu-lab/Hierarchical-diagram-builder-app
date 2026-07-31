"""Standalone Validator (doc section 4.5) -- deliberately not merged into the Decomposition
Engine (backend/decompose/). Runs 3 categories against every frozen tree, in order (spec
section 7): structural principles P1-P8, reference-architecture conformance (TDSP stage
mapping + C4 nesting depth), then the domain-specific checklist. Nothing reaches a renderer
without passing all three -- the tree is never partially accepted."""

from ..models import DomainChecklist, DomainTaskTree, ValidationResult
from .principles import (
    STRUCTURAL_CHECKS,
    check_p7_coverage_checklist,
    check_reference_architecture_conformance,
)


def validate_tree(tree: DomainTaskTree, checklist: DomainChecklist) -> ValidationResult:
    violations = []
    for check in STRUCTURAL_CHECKS:  # category 1: P1-P8
        violations.extend(check(tree))
    violations.extend(check_reference_architecture_conformance(tree, checklist))  # category 2
    violations.extend(check_p7_coverage_checklist(tree, checklist))  # category 3
    return ValidationResult(passed=len(violations) == 0, violations=violations)
