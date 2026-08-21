import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def setup_rpc():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Skipping RPC setup because DATABASE_URL is not set.")
        return

    sql = """
    CREATE OR REPLACE FUNCTION match_memories (
      query_embedding vector(384),
      match_threshold float,
      match_count int,
      p_user_id uuid
    )
    RETURNS TABLE (
      id uuid,
      content text,
      metadata jsonb,
      distance float
    )
    LANGUAGE plpgsql
    AS $$
    BEGIN
      RETURN QUERY
      SELECT
        memory_vectors.id,
        memory_vectors.content,
        memory_vectors.metadata,
        (memory_vectors.embedding <-> query_embedding) AS distance
      FROM memory_vectors
      WHERE memory_vectors.user_id = p_user_id
        AND (memory_vectors.embedding <-> query_embedding) < match_threshold
      ORDER BY memory_vectors.embedding <-> query_embedding
      LIMIT match_count;
    END;
    $$;
    """

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Ensure the column is 384 since the initial schema was 1536
        cursor.execute("ALTER TABLE memory_vectors ALTER COLUMN embedding TYPE vector(384);")
        
        cursor.execute(sql)
        print("Successfully created match_memories RPC function.")
    except Exception as e:
        print(f"Failed to setup RPC: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    setup_rpc()
