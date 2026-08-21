import os
from unittest.mock import patch, MagicMock
from app.services.memory import create_memory, store_memory
from app.core.encryption import decrypt_field


@patch("app.services.memory.SentenceTransformer")
def test_create_memory_embeds_and_encrypts(mock_st):
    print("\n=== TEST 1: Memory Creation ===")
    user_id = "test_user_123"
    content = "The user prefers concise summaries and loves Python."
    memory_type = "preference"
    source = "test_case"
    
    # Mock the SentenceTransformer instance and its encode method
    mock_model_instance = MagicMock()
    class MockOutput:
        def tolist(self):
            return [0.5] * 384
    mock_model_instance.encode.return_value = MockOutput()
    mock_st.return_value = mock_model_instance
    
    # Needs a fake encryption key in env if it's not set
    with patch.dict(os.environ, {"ENCRYPTION_SECRET_KEY": "fake_32_byte_secret_key_for_test!"}):
        memory = create_memory(user_id, content, memory_type, source)
        
        # 1. Metadata check
        assert memory["user_id"] == user_id
        assert memory["metadata"]["memory_type"] == memory_type
        assert memory["metadata"]["source"] == source
        
        # 2. Embedding check (all-MiniLM-L6-v2 produces 384 dims)
        assert "embedding" in memory
        assert len(memory["embedding"]) == 384
        assert isinstance(memory["embedding"][0], float)
        
        # 3. Encryption check
        assert memory["content"] != content
        assert "concise summaries" not in memory["content"]
        
        # 4. Verification that it can be decrypted
        decrypted = decrypt_field(memory["content"])
        assert decrypted == content
        
        print("[OK] create_memory() successfully generated 384-d embedding and encrypted content.")


@patch("app.services.memory.get_supabase_admin_client")
def test_store_memory(mock_get_client):
    print("\n=== TEST 2: Store Memory ===")
    
    # Setup mock Supabase client
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_insert = MagicMock()
    mock_execute = MagicMock()
    
    mock_get_client.return_value = mock_client
    mock_client.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value = mock_execute
    
    mock_execute.data = [{"id": "new-memory-uuid-1234"}]
    
    fake_payload = {
        "user_id": "test",
        "content": "encrypted_text",
        "metadata": {},
        "embedding": [0.1] * 384
    }
    
    result_id = store_memory(fake_payload)
    
    mock_client.table.assert_called_once_with("memory_vectors")
    mock_table.insert.assert_called_once_with(fake_payload)
    assert result_id == "new-memory-uuid-1234"
    print("[OK] store_memory() successfully interacted with Supabase mock.")


@patch("app.services.memory.get_supabase_admin_client")
@patch("app.services.memory.SentenceTransformer")
def test_search_memory(mock_st, mock_get_client):
    print("\n=== TEST 3: Search Memory ===")
    
    # 1. Reset global model to force new mock and return fixed embedding
    import app.services.memory
    app.services.memory._model = None
    mock_model_instance = MagicMock()
    class MockOutput:
        def tolist(self):
            return [0.1] * 384
    mock_model_instance.encode.return_value = MockOutput()
    mock_st.return_value = mock_model_instance
    
    # 2. Mock Supabase RPC call
    mock_client = MagicMock()
    mock_rpc = MagicMock()
    mock_execute = MagicMock()
    
    mock_get_client.return_value = mock_client
    mock_client.rpc.return_value = mock_rpc
    mock_rpc.execute.return_value = mock_execute
    
    # 3. Simulate database returning an encrypted memory
    from app.core.encryption import encrypt_field
    with patch.dict(os.environ, {"ENCRYPTION_SECRET_KEY": "fake_32_byte_secret_key_for_test!"}):
        encrypted_text = encrypt_field("The user prefers concise summaries.")
        
        mock_execute.data = [
            {
                "id": "uuid-1234",
                "content": encrypted_text,
                "metadata": {"memory_type": "preference", "source": "test_case"},
                "distance": 0.05
            }
        ]
        
        # Perform Search
        from app.services.memory import search_memory
        results = search_memory("test_user_123", "Does the user like summaries?")
        
        # Verify RPC Call
        mock_client.rpc.assert_called_once_with(
            "match_memories",
            {
                "query_embedding": [0.1] * 384,
                "match_threshold": 1.0,
                "match_count": 5,
                "p_user_id": "test_user_123"
            }
        )
        
        # Verify decryption and response formatting
        assert len(results) == 1
        assert results[0]["id"] == "uuid-1234"
        assert results[0]["distance"] == 0.05
        assert results[0]["content"] == "The user prefers concise summaries."
        assert results[0]["metadata"]["memory_type"] == "preference"
        
        print("[OK] search_memory() successfully queried pgvector and decrypted content.")


def main():
    test_create_memory_embeds_and_encrypts()
    test_store_memory()
    test_search_memory()
    print("\n==============================================")
    print(" ALL MEMORY MODULE TESTS PASSED! ")
    print("==============================================")


if __name__ == "__main__":
    main()
