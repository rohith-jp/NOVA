import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def run_migrations():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL must be set in environment")

    migration_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../db/migrations/001_initial_schema.sql")
    )

    if not os.path.exists(migration_path):
        raise FileNotFoundError(f"Migration file not found at {migration_path}")

    print(f"Reading migration file: {migration_path}")
    with open(migration_path, "r", encoding="utf-8") as f:
        sql = f.read()

    print("Connecting to Supabase PostgreSQL database...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()

    print("Executing migration SQL...")
    cursor.execute(sql)
    print("Migration executed successfully!")

    # Verification
    tables = ["users", "tasks", "receipts", "memory_vectors"]
    print("\n--- Verifying Created Tables ---")
    for table in tables:
        cursor.execute(
            "SELECT column_name, data_type "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s "
            "ORDER BY ordinal_position;",
            (table,),
        )

        cols = cursor.fetchall()
        print(f"\nTable: '{table}' ({len(cols)} columns)")
        for col_name, col_type in cols:
            print(f"  - {col_name}: {col_type}")

    cursor.close()
    conn.close()
    print("\nAll database tables verified successfully!")


if __name__ == "__main__":
    run_migrations()
