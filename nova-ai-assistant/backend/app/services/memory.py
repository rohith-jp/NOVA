import os
import logging
from typing import Dict, Any
from sentence_transformers import SentenceTransformer
from app.db.supabase import get_supabase_admin_client
from app.core.encryption import encrypt_field

logger = logging.getLogger(__name__)

# Lazy initialization of the SentenceTransformer model
_model = None

def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        # all-MiniLM-L6-v2 produces 384-dimensional embeddings
        logger.info("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def create_memory(user_id: str, content: str, memory_type: str, source: str) -> Dict[str, Any]:
    """
    Creates a memory dictionary:
    1. Generates a 384-dim semantic embedding using Sentence Transformers.
    2. Encrypts the plaintext sensitive memory content using AES-256-GCM.
    3. Bundles metadata (user, type, source) into a payload ready for database insertion.
    """
    model = get_embedding_model()
    
    # Generate 384-dimensional semantic embedding
    embedding = model.encode(content).tolist()
    
    # Encrypt the plaintext memory content
    encrypted_content = encrypt_field(content)
    
    metadata = {
        "memory_type": memory_type,
        "source": source
    }
    
    memory_payload = {
        "user_id": user_id,
        "content": encrypted_content,
        "metadata": metadata,
        "embedding": embedding
    }
    
    return memory_payload

def store_memory(memory_payload: Dict[str, Any]) -> str:
    """
    Stores the compiled memory vector dictionary in the Supabase pgvector table.
    Returns the ID of the newly inserted memory.
    """
    client = get_supabase_admin_client()
    
    try:
        response = client.table("memory_vectors").insert(memory_payload).execute()
        if not response.data:
            raise Exception("No data returned after memory insertion.")
        
        memory_id = response.data[0]["id"]
        logger.info(f"Stored memory {memory_id} successfully in pgvector table.")
        return memory_id
        
    except Exception as e:
        logger.error(f"Failed to store memory in database: {e}")
        raise Exception(f"Memory storage failed: {e}")


def search_memory(user_id: str, query: str, match_threshold: float = 1.0, match_count: int = 5) -> list[Dict[str, Any]]:
    """
    Searches for relevant memories using pgvector similarity search (<->).
    Applies user isolation (p_user_id) and decrypts authorized sensitive fields.
    """
    model = get_embedding_model()
    
    # Generate embedding for the search query
    query_embedding = model.encode(query).tolist()
    
    client = get_supabase_admin_client()
    
    try:
        # Call the match_memories RPC function
        response = client.rpc(
            "match_memories",
            {
                "query_embedding": query_embedding,
                "match_threshold": match_threshold,
                "match_count": match_count,
                "p_user_id": user_id
            }
        ).execute()
        
        results = []
        for row in response.data:
            # Decrypt the authorized sensitive content retrieved from the database
            from app.core.encryption import decrypt_field
            decrypted_content = decrypt_field(row["content"])
            
            results.append({
                "id": row["id"],
                "content": decrypted_content,
                "metadata": row["metadata"],
                "distance": row["distance"]
            })
            
        return results
    except Exception as e:
        logger.error(f"Failed to search memories: {e}")
        raise Exception(f"Memory search failed: {e}")


def list_memories(user_id: str) -> list[Dict[str, Any]]:
    """
    Lists all memories for a user, decrypting content for authorized access.
    """
    client = get_supabase_admin_client()
    try:
        response = client.table("memory_vectors").select("id, user_id, content, metadata, created_at").eq("user_id", user_id).order("created_at", desc=True).execute()
        results = []
        from app.core.encryption import decrypt_field
        for row in response.data:
            try:
                decrypted_content = decrypt_field(row["content"])
            except Exception:
                decrypted_content = "[Encrypted Content]"
            results.append({
                "id": row["id"],
                "user_id": row["user_id"],
                "content": decrypted_content,
                "metadata": row.get("metadata") or {},
                "created_at": row.get("created_at")
            })
        return results
    except Exception as e:
        logger.error(f"Failed to list memories: {e}")
        return []


