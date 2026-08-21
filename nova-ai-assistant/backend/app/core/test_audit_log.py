from app.core.audit_log import AuditLogChain


def test_normal_chain():
    print("\n=== TEST 1: Normal Chain ===")
    chain = AuditLogChain()
    
    chain.add_entry("usr_1", "task_1", "CREATE_PLAN", {"step": "test"})
    chain.add_entry("usr_1", "task_1", "EXECUTE_TOOL", {"tool": "web_search"})
    chain.add_entry("usr_1", "task_1", "VERIFY_RESULT", {"success": True})
    
    assert len(chain.entries) == 3
    is_valid, reason, index = chain.verify_chain()
    assert is_valid is True, f"Chain should be valid, but failed: {reason}"
    print("[OK] Normal chain verified successfully!")


def test_modified_entry():
    print("\n=== TEST 2: Modified Entry (Tampered Payload) ===")
    chain = AuditLogChain()
    
    chain.add_entry("usr_1", "task_1", "CREATE_PLAN", {"step": "test"})
    entry2 = chain.add_entry("usr_1", "task_1", "EXECUTE_TOOL", {"tool": "web_search"})
    chain.add_entry("usr_1", "task_1", "VERIFY_RESULT", {"success": True})
    
    # Tamper with the metadata of entry2
    entry2.action_metadata["tool"] = "malicious_tool_execution"
    
    is_valid, reason, index = chain.verify_chain()
    assert is_valid is False
    assert index == 1
    assert "Tampered data detected" in reason
    print(f"[OK] Caught tampered entry at index {index}: {reason}")


def test_deleted_entry():
    print("\n=== TEST 3: Deleted Entry (Broken Link) ===")
    chain = AuditLogChain()
    
    chain.add_entry("usr_1", "task_1", "CREATE_PLAN", {"step": "test"})
    chain.add_entry("usr_1", "task_1", "EXECUTE_TOOL", {"tool": "web_search"})
    chain.add_entry("usr_1", "task_1", "VERIFY_RESULT", {"success": True})
    
    # Secretly delete the middle entry
    del chain.entries[1]
    
    is_valid, reason, index = chain.verify_chain()
    assert is_valid is False
    assert index == 1  # The new index 1 (which was originally 2) will fail linkage
    assert "Broken chain link detected" in reason
    print(f"[OK] Caught deleted entry (broken chain link) at index {index}: {reason}")


def test_reordered_entry():
    print("\n=== TEST 4: Reordered Entries (Broken Links) ===")
    chain = AuditLogChain()
    
    chain.add_entry("usr_1", "task_1", "CREATE_PLAN", {"step": "test"})
    chain.add_entry("usr_1", "task_1", "EXECUTE_TOOL", {"tool": "web_search"})
    chain.add_entry("usr_1", "task_1", "VERIFY_RESULT", {"success": True})
    
    # Swap entries 1 and 2
    chain.entries[1], chain.entries[2] = chain.entries[2], chain.entries[1]
    
    is_valid, reason, index = chain.verify_chain()
    assert is_valid is False
    assert index == 1
    assert "Broken chain link detected" in reason
    print(f"[OK] Caught reordered entry at index {index}: {reason}")


def main():
    test_normal_chain()
    test_modified_entry()
    test_deleted_entry()
    test_reordered_entry()
    print("\n==============================================")
    print(" ALL TAMPER-EVIDENT AUDIT LOG TESTS PASSED! ")
    print("==============================================")


if __name__ == "__main__":
    main()
