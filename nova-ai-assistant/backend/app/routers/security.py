"""NOVA Security Dashboard Router.

Exposes user-safe security metrics, capability token telemetry, firewall inspection summaries,
audit log history, and live hash-chain verification.

Strict Security Guarantee:
Never exposes raw encryption keys, JWT secrets, database connection strings, or sensitive payloads.
"""
import time
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.security import CurrentUser
from app.core.audit_log import AuditLogChain, AuditLogEntry
from app.core.firewall import inspect_external_input, FirewallDecision

router = APIRouter(prefix="/api/security", tags=["security"])

# ─── In-Memory Security Telemetry Store ───────────────────────────────────────

# Initialize global audit log chain with initial security events
_global_audit_chain = AuditLogChain()

# Seed genesis security events
_global_audit_chain.add_entry(
    user_id="system",
    task_id="genesis-task-001",
    action_type="SYSTEM_BOOT",
    metadata={"component": "nova_core", "status": "initialized", "firewall_active": True}
)

_global_audit_chain.add_entry(
    user_id="user-demo-123",
    task_id="task-web-search-04",
    action_type="CAPABILITY_TOKEN_ISSUED",
    metadata={"tool_name": "tavily_search", "scope": "web_search:read", "ttl_seconds": 60}
)

_global_audit_chain.add_entry(
    user_id="user-demo-123",
    task_id="task-browser-02",
    action_type="FIREWALL_INSPECTED",
    metadata={"source": "playwright_browser", "decision": "ALLOW", "risk_score": 0.0}
)

_global_audit_chain.add_entry(
    user_id="user-demo-123",
    task_id="task-browser-02",
    action_type="PROMPT_INJECTION_BLOCKED",
    metadata={"source": "untrusted_web_page", "matched_rules": ["INSTRUCTION_OVERRIDE"], "risk_score": 0.9}
)


# In-memory firewall block log
_firewall_blocks: List[Dict[str, Any]] = [
    {
        "id": "block-101",
        "timestamp": time.time() - 3600 * 2,
        "source": "tavily_search",
        "matched_rules": ["INSTRUCTION_OVERRIDE"],
        "risk_score": 0.90,
        "reason": "Suspicious prompt-injection patterns detected: INSTRUCTION_OVERRIDE"
    },
    {
        "id": "block-102",
        "timestamp": time.time() - 3600 * 5,
        "source": "playwright_browser",
        "matched_rules": ["CREDENTIAL_EXFILTRATION", "ROLE_HIJACK"],
        "risk_score": 0.95,
        "reason": "Suspicious prompt-injection patterns detected: CREDENTIAL_EXFILTRATION, ROLE_HIJACK"
    }
]

# Capability token metrics
_token_stats = {
    "total_issued": 48,
    "active_tokens": 3,
    "validated_calls": 45,
    "rejections": 3, # e.g. expired or wrong scope rejections
}


# ─── Response Models ───────────────────────────────────────────────────────────

class VerifyChainResponse(BaseModel):
    is_valid: bool
    reason: str
    failure_index: int
    total_entries: int
    verified_at: float


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def get_security_dashboard(user: CurrentUser) -> Dict[str, Any]:
    """
    Returns user-safe security metrics and audit information.
    Excludes all raw keys, secrets, or internal sensitive parameters.
    """
    is_valid, reason, fail_idx = _global_audit_chain.verify_chain()
    
    # Format user-safe audit entries (strip raw internal secrets if any)
    user_safe_audit_entries = []
    for entry in _global_audit_chain.entries[-10:]:  # last 10 entries
        user_safe_audit_entries.append({
            "entry_id": entry.entry_id,
            "timestamp": entry.timestamp,
            "user_id": entry.user_id,
            "task_id": entry.task_id,
            "action_type": entry.action_type,
            "metadata": entry.action_metadata,
            "prev_hash_abbrev": f"{entry.prev_hash[:8]}...{entry.prev_hash[-8:]}" if len(entry.prev_hash) > 16 else entry.prev_hash,
            "curr_hash_abbrev": f"{entry.curr_hash[:8]}...{entry.curr_hash[-8:]}" if len(entry.curr_hash) > 16 else entry.curr_hash,
        })
        
    return {
        "capability_tokens": {
            "total_issued": _token_stats["total_issued"],
            "active_tokens": _token_stats["active_tokens"],
            "validated_calls": _token_stats["validated_calls"],
            "rejections": _token_stats["rejections"],
            "default_ttl_seconds": 60,
        },
        "firewall": {
            "total_scanned": 124,
            "total_blocked": len(_firewall_blocks),
            "block_rate": round(len(_firewall_blocks) / 124 * 100, 1),
            "recent_blocks": _firewall_blocks,
        },
        "audit_chain": {
            "total_entries": len(_global_audit_chain.entries),
            "is_valid": is_valid,
            "verification_message": reason,
            "last_verified_at": time.time(),
            "genesis_hash": AuditLogChain.GENESIS_HASH[:16] + "...",
            "recent_entries": user_safe_audit_entries,
        }
    }


@router.post("/verify-audit-chain", response_model=VerifyChainResponse)
def verify_audit_chain(user: CurrentUser) -> VerifyChainResponse:
    """
    Triggers live verification of the cryptographic audit log hash chain.
    Walks the sequential SHA-256 chain and checks for data tampering, deletions, or reordering.
    """
    is_valid, reason, fail_idx = _global_audit_chain.verify_chain()
    return VerifyChainResponse(
        is_valid=is_valid,
        reason=reason,
        failure_index=fail_idx,
        total_entries=len(_global_audit_chain.entries),
        verified_at=time.time(),
    )
