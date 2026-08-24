import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def test_schema():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 1. Insert test user
        cur.execute(
            "INSERT INTO users (email, full_name) VALUES ('test@nova.ai', 'Test User') RETURNING id;"
        )
        user_id = cur.fetchone()[0]
        print(f"[OK] Inserted test user (ID: {user_id})")

        # 2. Insert test task
        cur.execute(
            "INSERT INTO tasks (user_id, title, status) VALUES (%s, 'Test Task', 'pending') RETURNING id;",
            (user_id,),
        )
        task_id = cur.fetchone()[0]
        print(f"[OK] Inserted test task (ID: {task_id})")

        # 3. Insert test receipt
        cur.execute(
            """
            INSERT INTO receipts (user_id, task_id, action_type, tokens_used, cost_usd) 
            VALUES (%s, %s, 'agent_run', 150, 0.002) RETURNING id;
            """,
            (user_id, task_id),
        )
        receipt_id = cur.fetchone()[0]
        print(f"[OK] Inserted test receipt (ID: {receipt_id})")

        # 4. Insert test memory vector (1536 dims)
        fake_vector = "[" + ",".join(["0.1"] * 1536) + "]"
        cur.execute(
            "INSERT INTO memory_vectors (user_id, content, embedding) VALUES (%s, 'Sample memory', %s::vector) RETURNING id;",
            (user_id, fake_vector),
        )
        vector_id = cur.fetchone()[0]
        print(f"[OK] Inserted test memory_vector (ID: {vector_id})")

        # Clean rollback so DB stays clean
        conn.rollback()
        print("[OK] Rollback successful — test data cleared cleanly!")
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Schema test failed: {e}")
        raise e

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    test_schema()
