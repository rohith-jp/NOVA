"""NOVA Prompt-Injection Firewall Module.

Inspects untrusted external content (from web search, browser automation, scraped pages,
or third-party APIs) before that content is passed to the planner or LLM.

Note: This classifier uses rule-based heuristic pattern matching and entropy checks.
It is an initial layer of defense and is not claimed to be 100% perfect.
"""
import re
import logging
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Models & Enums
# ---------------------------------------------------------------------------

class FirewallDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


class FirewallResult(BaseModel):
    decision: FirewallDecision
    allowed: bool
    reason: str
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Risk score from 0.0 (safe) to 1.0 (malicious)")
    matched_rules: List[str] = Field(default_factory=list)
    source: str = "external_tool"


class PromptInjectionBlockedError(Exception):
    """Raised when untrusted content is blocked by the firewall."""
    def __init__(self, result: FirewallResult):
        super().__init__(f"Prompt Injection Blocked [source={result.source}]: {result.reason}")
        self.result = result


# ---------------------------------------------------------------------------
# Suspicious Pattern Registry
# ---------------------------------------------------------------------------

# Patterns commonly used to hijack LLM system prompts or inject instructions
SUSPICIOUS_PATTERNS = [
    # 1. Instruction Overrides & Reset Attempts
    (r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", "INSTRUCTION_OVERRIDE", 0.9),
    (r"(?i)disregard\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?)", "INSTRUCTION_OVERRIDE", 0.9),
    (r"(?i)forget\s+(all\s+)?(previous|prior|system)\s+instructions?", "INSTRUCTION_OVERRIDE", 0.9),
    (r"(?i)override\s+(the\s+)?system\s+prompt", "SYSTEM_PROMPT_OVERRIDE", 0.95),
    (r"(?i)you\s+are\s+now\s+a\s+(new|different)\s+ai", "ROLE_HIJACK", 0.85),
    (r"(?i)you\s+are\s+now\s+in\s+(dan|jailbreak|developer)\s+mode", "JAILBREAK_ATTEMPT", 0.95),

    # 2. System Role & Delimiter Impersonation
    (r"(?i)<\|im_start\|>", "CHATML_DELIMITER_INJECTION", 0.95),
    (r"(?i)<\|im_end\|>", "CHATML_DELIMITER_INJECTION", 0.95),
    (r"(?i)\[SYSTEM\s+INSTRUCTION\]", "SYSTEM_HEADER_IMPERSONATION", 0.9),
    (r"(?i)<<<SYSTEM>>>", "SYSTEM_HEADER_IMPERSONATION", 0.9),
    (r"(?i)^system:", "SYSTEM_ROLE_IMPERSONATION", 0.85),

    # 3. Credential & Prompt Exfiltration
    (r"(?i)(output|print|reveal|display|show)\s+(your\s+|the\s+)?(system\s+prompt|initial\s+instructions)", "PROMPT_EXFILTRATION", 0.85),
    (r"(?i)(output|print|reveal|display|show)\s+(your\s+|the\s+)?([a-z0-9_]*key|[a-z0-9_]*secret|env|environment\s+variables?|password|token)", "CREDENTIAL_EXFILTRATION", 0.9),
    (r"(?i)(supabase_service_role_key|gemini_api_key|groq_api_key|anthropic_api_key)", "SPECIFIC_SECRET_EXFILTRATION", 0.95),


    # 4. Dangerous Code Execution Vectors
    (r"(?i)eval\s*\(\s*base64_decode", "MALICIOUS_CODE_EXEC", 0.9),
    (r"(?i)rm\s+-rf\s+/", "DESTRUCTIVE_COMMAND_INJECTION", 0.95),
]

# Zero-width / invisible characters used to hide prompt injection
ZERO_WIDTH_CHARS = ["\u200b", "\u200c", "\u200d", "\ufeff"]


# ---------------------------------------------------------------------------
# Firewall Classifier Engine
# ---------------------------------------------------------------------------

class PromptInjectionFirewall:
    """Prompt-Injection Firewall Classifier.

    Analyzes untrusted text from external sources for prompt injection attempts.
    """

    def __init__(self, risk_threshold: float = 0.5):
        self.risk_threshold = risk_threshold

    def inspect(self, text: str, source: str = "external_tool") -> FirewallResult:
        """Inspect untrusted text and return a structured FirewallResult.

        Args:
            text: Untrusted text string from web search, browser automation, etc.
            source: Label identifying content provenance.

        Returns:
            FirewallResult with decision (ALLOW/BLOCK), risk score, and matched rules.
        """
        if not text or not text.strip():
            return FirewallResult(
                decision=FirewallDecision.ALLOW,
                allowed=True,
                reason="Empty content.",
                risk_score=0.0,
                source=source,
            )

        matched_rules: List[str] = []
        max_pattern_score = 0.0

        # 1. Check for Zero-Width / Hidden Character Injections
        for zwc in ZERO_WIDTH_CHARS:
            if zwc in text:
                matched_rules.append("HIDDEN_ZERO_WIDTH_CHARS")
                max_pattern_score = max(max_pattern_score, 0.75)
                break

        # 2. Pattern Matching against Suspicious Injection Registry
        for pattern, rule_name, score in SUSPICIOUS_PATTERNS:
            if re.search(pattern, text):
                matched_rules.append(rule_name)
                max_pattern_score = max(max_pattern_score, score)

        # 3. Determine Final Decision
        final_risk = max_pattern_score

        if final_risk >= self.risk_threshold or len(matched_rules) > 0:
            reason = f"Suspicious prompt-injection patterns detected: {', '.join(set(matched_rules))}"
            logger.warning(f"[FIREWALL BLOCK] Source '{source}': {reason} (Risk: {final_risk})")
            return FirewallResult(
                decision=FirewallDecision.BLOCK,
                allowed=False,
                reason=reason,
                risk_score=final_risk,
                matched_rules=list(set(matched_rules)),
                source=source,
            )

        return FirewallResult(
            decision=FirewallDecision.ALLOW,
            allowed=True,
            reason="No prompt injection patterns detected.",
            risk_score=0.0,
            matched_rules=[],
            source=source,
        )


# Global singleton instance
_firewall = PromptInjectionFirewall()


def inspect_external_input(text: str, source: str = "external_tool") -> FirewallResult:
    """Inspect untrusted input text and return FirewallResult decision."""
    return _firewall.inspect(text, source=source)


def sanitize_or_reject_external_input(text: str, source: str = "external_tool") -> str:
    """Inspect untrusted text. If allowed, returns text. If blocked, raises PromptInjectionBlockedError.

    NEVER silently passes blocked content to the planner or LLM.
    """
    result = inspect_external_input(text, source=source)
    if not result.allowed:
        raise PromptInjectionBlockedError(result)
    return text
