"""Tool Registry (Tool Engineering Architecture, ADR-006) -- WP16.

Per ADR-006: agents orchestrate, tools carry the specialised, evidence-grounded domain
logic. This registry is the inspectable data half of that split -- one entry per tool
named in the initial Tool Registry, honestly marked with its real status against WP1-13c
and WP0a/WP0b rather than assumed complete. `status="built"` means the cited
`implementation` module is real, tested, and already grounded in the named evidence base's
actual rules (not just an LLM prompt referencing the domain by name). `status="partial"`
means real code exists at `implementation` but is still prompt-driven rather than a
deterministic/rule-based engine grounded in the evidence base. `status="not_built"` means
no implementation exists yet -- these are the candidates for future one-tool-per-WP work,
per the same separation-of-concerns rule WP11/WP13's ADR-003/ADR-004 splits established.

This is the framework only (ADR-006's own split): registering a tool here does not
implement its logic. Orchestrator dispatch is deliberately NOT wired to this registry yet
-- most entries have no real implementation to dispatch to, and wiring it now would be
premature per the same discipline WP11's switcher used (register the shape, add real
content one WP at a time)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Tool:
    name: str
    operating_model_activity: str  # which WP0a Operating Model part this tool serves
    needs_tool: str  # "No" | "Partial" | "Yes" -- the initial Tool Registry's own column
    evidence_base: str  # research/standards/theories/regulations it must be traceable to
    status: str  # "built" | "partial" | "not_built"
    implementation: str  # module path if built/partial, "" if not_built


CONVERSATION_ENGINE = Tool(
    name="Conversation Engine",
    operating_model_activity="Capture Objective",
    needs_tool="No",
    evidence_base="NLP",
    status="built",
    implementation="backend.intelligence (objective intake, WP5)",
)
REQUIREMENT_ANALYSIS_TOOL = Tool(
    name="Requirement Analysis Tool",
    operating_model_activity="Discover Constraints",
    needs_tool="Partial",
    evidence_base="Requirements Engineering",
    status="built",
    implementation="backend.tools.requirement_analysis (deterministic INCOSE Guide for "
    "Writing Requirements / IEEE 830 weak-word and completeness checks; explain() "
    "optionally phrases the result via the AI Service but never adds/removes a finding) "
    "-- WP16d. The interactive discovery loop itself (asking follow-up questions until "
    "sufficient understanding, WP0a Part 04) remains unbuilt -- this tool assesses "
    "requirement text quality, it does not elicit requirements.",
)
AI_SUITABILITY_ASSESSMENT_TOOL = Tool(
    name="AI Suitability Assessment Tool",
    operating_model_activity="AI Suitability Assessment",
    needs_tool="Yes",
    evidence_base="AI Engineering, NIST AI RMF, ISO/IEC 42001, Decision Theory",
    status="built",
    implementation="backend.tools.ai_suitability (deterministic decision tree; explain() "
    "optionally phrases the result via the AI Service but never decides it) -- WP16a",
)
BUSINESS_ARCHITECTURE_TOOL = Tool(
    name="Business Architecture Tool",
    operating_model_activity="Generate Business Architecture",
    needs_tool="Yes",
    evidence_base="TOGAF, ArchiMate, Business Architecture",
    status="partial",
    implementation="backend.intelligence.stages (business_analysis/capability_analysis), "
    "backend.decomposition.strategies.BUSINESS -- prompt-driven, not yet ArchiMate-grounded",
)
DATA_ARCHITECTURE_TOOL = Tool(
    name="Data Architecture Tool",
    operating_model_activity="Generate Data Architecture",
    needs_tool="Yes",
    evidence_base="TOGAF, Data Modelling, ER Theory",
    status="partial",
    implementation="backend.decomposition.strategies.DATA -- prompt-driven, not ER-theory-grounded",
)
APPLICATION_ARCHITECTURE_TOOL = Tool(
    name="Application Architecture Tool",
    operating_model_activity="Generate Application Architecture",
    needs_tool="Yes",
    evidence_base="TOGAF, SOA, Microservices",
    status="partial",
    implementation="backend.decomposition.strategies.APPLICATION -- prompt-driven",
)
TECHNOLOGY_ARCHITECTURE_TOOL = Tool(
    name="Technology Architecture Tool",
    operating_model_activity="Generate Technology Architecture",
    needs_tool="Yes",
    evidence_base="TOGAF, Cloud Architecture",
    status="partial",
    implementation="backend.decomposition.strategies.TECHNOLOGY -- prompt-driven",
)
RECURSIVE_DECOMPOSITION_ENGINE = Tool(
    name="Recursive Decomposition Engine",
    operating_model_activity="Recursive Decomposition",
    needs_tool="Yes",
    evidence_base="Systems Engineering, Functional Decomposition",
    status="built",
    implementation="backend.decomposition.selector (deterministic strategy selection), "
    "backend.decomposition.stopping (deterministic stopping criteria)",
)
WORKFLOW_VERIFICATION_TOOL = Tool(
    name="Workflow Verification Tool",
    operating_model_activity="Workflow Validation",
    needs_tool="Yes",
    evidence_base="BPMN, Workflow Theory",
    status="not_built",
    implementation="",
)
ENGINEERING_STANDARDS_TOOL = Tool(
    name="Engineering Standards Tool",
    operating_model_activity="Repository Generation",
    needs_tool="Yes",
    evidence_base="Clean Architecture, DDD, SOLID",
    status="not_built",
    implementation="",
)
DATABASE_DESIGN_TOOL = Tool(
    name="Database Design Tool",
    operating_model_activity="Database Design",
    needs_tool="Yes",
    evidence_base="Codd's Relational Model, Normalization",
    status="built",
    implementation="backend.tools.database_design (deterministic 1NF/2NF/3NF check over "
    "explicit key-structure signals; explain() optionally phrases the result via the AI "
    "Service but never decides it) -- WP16f",
)
API_DESIGN_TOOL = Tool(
    name="API Design Tool",
    operating_model_activity="API Design",
    needs_tool="Yes",
    evidence_base="REST, OpenAPI, API Design Guidelines",
    status="not_built",
    implementation="",
)
RISK_ASSESSMENT_TOOL = Tool(
    name="Risk Assessment Tool",
    operating_model_activity="Risk Assessment",
    needs_tool="Yes",
    evidence_base="ISO 31000, COSO, NIST RMF",
    status="built",
    implementation="backend.tools.risk_assessment (deterministic likelihood x impact "
    "matrix; explain() optionally phrases the result via the AI Service but never "
    "decides it) -- WP16b. WP5's risk_reasoning stage remains prompt-driven and is not "
    "yet wired to call this tool.",
)
SECURITY_ARCHITECTURE_TOOL = Tool(
    name="Security Architecture Tool",
    operating_model_activity="Security Design",
    needs_tool="Yes",
    evidence_base="NIST CSF, OWASP, Zero Trust",
    status="built",
    implementation="backend.tools.security_assessment (deterministic NIST CSF "
    "five-function checklist -- Identify/Protect/Detect/Respond/Recover; explain() "
    "optionally phrases the result via the AI Service but never decides it) -- WP16e",
)
GOVERNANCE_ASSESSMENT_TOOL = Tool(
    name="Governance Assessment Tool",
    operating_model_activity="Governance",
    needs_tool="Yes",
    evidence_base="COBIT, TOGAF Governance, ISO 38500",
    status="built",
    implementation="backend.tools.governance_assessment (deterministic ISO 38500 "
    "six-principle assessment, Conformance as a hard gate; explain() optionally phrases "
    "the result via the AI Service but never decides it) -- WP16c, alongside "
    "backend.governance.validation's existing structural/policy checks (untouched, not "
    "duplicated)",
)
TEST_DESIGN_TOOL = Tool(
    name="Test Design Tool",
    operating_model_activity="Testing Strategy",
    needs_tool="Yes",
    evidence_base="ISTQB, Test Pyramid",
    status="not_built",
    implementation="",
)
DEPLOYMENT_ARCHITECTURE_TOOL = Tool(
    name="Deployment Architecture Tool",
    operating_model_activity="Deployment Strategy",
    needs_tool="Yes",
    evidence_base="DevOps, CI/CD, Platform Engineering",
    status="not_built",
    implementation="",
)

ALL_TOOLS = [
    CONVERSATION_ENGINE,
    REQUIREMENT_ANALYSIS_TOOL,
    AI_SUITABILITY_ASSESSMENT_TOOL,
    BUSINESS_ARCHITECTURE_TOOL,
    DATA_ARCHITECTURE_TOOL,
    APPLICATION_ARCHITECTURE_TOOL,
    TECHNOLOGY_ARCHITECTURE_TOOL,
    RECURSIVE_DECOMPOSITION_ENGINE,
    WORKFLOW_VERIFICATION_TOOL,
    ENGINEERING_STANDARDS_TOOL,
    DATABASE_DESIGN_TOOL,
    API_DESIGN_TOOL,
    RISK_ASSESSMENT_TOOL,
    SECURITY_ARCHITECTURE_TOOL,
    GOVERNANCE_ASSESSMENT_TOOL,
    TEST_DESIGN_TOOL,
    DEPLOYMENT_ARCHITECTURE_TOOL,
]
