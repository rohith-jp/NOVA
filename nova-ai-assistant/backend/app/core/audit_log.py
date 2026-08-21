import hashlib
import json
import time
import uuid
from typing import List, Dict, Any, Tuple, Optional


class AuditLogEntry:
    def __init__(
        self,
        entry_id: str,
        timestamp: float,
        user_id: str,
        task_id: str,
        action_type: str,
        action_metadata: Dict[str, Any],
        prev_hash: str,
        curr_hash: str = ""
    ):
        self.entry_id = entry_id
        self.timestamp = timestamp
        self.user_id = user_id
        self.task_id = task_id
        self.action_type = action_type
        self.action_metadata = action_metadata
        self.prev_hash = prev_hash
        self.curr_hash = curr_hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "task_id": self.task_id,
            "action_type": self.action_type,
            "metadata": self.action_metadata,
            "prev_hash": self.prev_hash,
            "curr_hash": self.curr_hash
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditLogEntry":
        return cls(
            entry_id=data.get("entry_id", ""),
            timestamp=data.get("timestamp", 0.0),
            user_id=data.get("user_id", ""),
            task_id=data.get("task_id", ""),
            action_type=data.get("action_type", ""),
            action_metadata=data.get("metadata", {}),
            prev_hash=data.get("prev_hash", ""),
            curr_hash=data.get("curr_hash", "")
        )

    def compute_hash(self) -> str:
        """
        Computes the SHA-256 hash of the entry.
        Note: The curr_hash field itself is excluded from the computation.
        """
        data = self.to_dict()
        # Remove curr_hash for the calculation
        data.pop("curr_hash", None)
        
        # Serialize to JSON with sorted keys to ensure deterministic hashing
        serialized = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class AuditLogChain:
    """
    A tamper-evident append-only audit log chain.
    This provides hash-based chain verification (similar to a blockchain ledger).
    It is NOT a digital signature mechanism.
    """
    GENESIS_HASH = "0" * 64

    def __init__(self, existing_entries: Optional[List[AuditLogEntry]] = None):
        self.entries: List[AuditLogEntry] = existing_entries or []

    def add_entry(
        self,
        user_id: str,
        task_id: str,
        action_type: str,
        metadata: Dict[str, Any]
    ) -> AuditLogEntry:
        """Appends a new entry to the chain and computes its linked hash."""
        prev_hash = self.entries[-1].curr_hash if self.entries else self.GENESIS_HASH
        
        entry = AuditLogEntry(
            entry_id=str(uuid.uuid4()),
            timestamp=time.time(),
            user_id=user_id,
            task_id=task_id,
            action_type=action_type,
            action_metadata=metadata,
            prev_hash=prev_hash
        )
        
        entry.curr_hash = entry.compute_hash()
        self.entries.append(entry)
        return entry

    def verify_chain(self) -> Tuple[bool, str, int]:
        """
        Walks the chain to verify cryptographic integrity.
        Detects:
        1. Tampered payload data (curr_hash != recomputed hash)
        2. Deleted entries (prev_hash of entry i != curr_hash of entry i-1)
        3. Reordered entries (same as deleted/broken chain link)
        
        Returns:
            (is_valid, reason, index_of_failure)
        """
        if not self.entries:
            return True, "Chain is empty.", -1

        for i, entry in enumerate(self.entries):
            # 1. Verify intrinsic data integrity
            expected_hash = entry.compute_hash()
            if entry.curr_hash != expected_hash:
                return False, f"Tampered data detected: Hash mismatch at entry {entry.entry_id}.", i
            
            # 2. Verify chain linkage (prev_hash)
            if i == 0:
                if entry.prev_hash != self.GENESIS_HASH:
                    return False, f"Broken chain: Genesis entry {entry.entry_id} has invalid prev_hash.", i
            else:
                prev_entry = self.entries[i - 1]
                if entry.prev_hash != prev_entry.curr_hash:
                    return False, f"Broken chain link detected between {prev_entry.entry_id} and {entry.entry_id}.", i

        return True, "Chain is cryptographically intact.", -1
