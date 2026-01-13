"""
Migration script to add Parent-Document Retrieval support to existing database.

This script:
1. Adds new columns to document_chunks table
2. Creates indexes for parent-child relationships
3. Maintains backward compatibility with existing data

Usage:
    python migrate_parent_document.py
"""

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()


def get_connection():
    """Get database connection."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "sample_db"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
    )


def migrate_schema():
    """Add Parent-Document Retrieval columns and indexes."""

    migration_sql = """
    -- Add parent-document retrieval columns
    DO $$ 
    BEGIN
        -- Add parent_chunk_id column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'document_chunks' AND column_name = 'parent_chunk_id'
        ) THEN
            ALTER TABLE document_chunks 
            ADD COLUMN parent_chunk_id UUID REFERENCES document_chunks(chunk_id) ON DELETE CASCADE;
        END IF;

        -- Add is_parent column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'document_chunks' AND column_name = 'is_parent'
        ) THEN
            ALTER TABLE document_chunks 
            ADD COLUMN is_parent BOOLEAN DEFAULT FALSE;
        END IF;

        -- Add chunk_type column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'document_chunks' AND column_name = 'chunk_type'
        ) THEN
            ALTER TABLE document_chunks 
            ADD COLUMN chunk_type VARCHAR(20) DEFAULT 'child';
        END IF;
    END $$;

    -- Create indexes for parent-child relationships
    CREATE INDEX IF NOT EXISTS idx_document_chunks_parent_id 
        ON document_chunks(parent_chunk_id);
    
    CREATE INDEX IF NOT EXISTS idx_document_chunks_type 
        ON document_chunks(chunk_type, is_parent);

    -- Update existing chunks to be compatible (mark as 'direct' type for backward compat)
    UPDATE document_chunks 
    SET chunk_type = 'direct', is_parent = TRUE 
    WHERE chunk_type IS NULL AND embedding IS NOT NULL;
    """

    print("Starting Parent-Document Retrieval migration...")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(migration_sql)
        conn.commit()
        print("✓ Migration completed successfully!")
        print("✓ Added columns: parent_chunk_id, is_parent, chunk_type")
        print("✓ Created indexes for parent-child relationships")
        print("✓ Updated existing chunks for backward compatibility")

        # Show statistics
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    chunk_type, 
                    COUNT(*) as count,
                    ROUND(AVG(LENGTH(content))) as avg_length
                FROM document_chunks
                GROUP BY chunk_type
                ORDER BY chunk_type;
            """)

            results = cur.fetchall()
            if results:
                print("\nChunk Statistics:")
                print("-" * 50)
                print(f"{'Type':<15} {'Count':<10} {'Avg Length':<15}")
                print("-" * 50)
                for row in results:
                    chunk_type = row[0] or "NULL"
                    count = row[1]
                    avg_len = row[2] or 0
                    print(f"{chunk_type:<15} {count:<10} {int(avg_len):<15}")

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def verify_migration():
    """Verify the migration was successful."""
    print("\nVerifying migration...")

    verification_sql = """
    SELECT 
        column_name, 
        data_type, 
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_name = 'document_chunks'
      AND column_name IN ('parent_chunk_id', 'is_parent', 'chunk_type')
    ORDER BY column_name;
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(verification_sql)
            columns = cur.fetchall()

            if len(columns) == 3:
                print("✓ All columns created successfully")
                print("\nColumn Details:")
                print("-" * 70)
                print(f"{'Column':<20} {'Type':<15} {'Nullable':<10} {'Default':<20}")
                print("-" * 70)
                for col in columns:
                    print(
                        f"{col[0]:<20} {col[1]:<15} {col[2]:<10} {col[3] or 'NULL':<20}"
                    )
            else:
                print(f"✗ Expected 3 columns, found {len(columns)}")

            # Check indexes
            cur.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'document_chunks' 
                  AND indexname IN ('idx_document_chunks_parent_id', 'idx_document_chunks_type');
            """)
            indexes = cur.fetchall()

            print(f"\n✓ Created {len(indexes)} indexes")
            for idx in indexes:
                print(f"  - {idx[0]}")

    except Exception as e:
        print(f"✗ Verification failed: {e}")
        raise
    finally:
        conn.close()


def rollback_migration():
    """Rollback the migration (use with caution!)."""
    print("\n⚠️  WARNING: This will remove Parent-Document Retrieval support!")
    response = input("Are you sure you want to rollback? (yes/no): ")

    if response.lower() != "yes":
        print("Rollback cancelled.")
        return

    rollback_sql = """
    -- Drop indexes
    DROP INDEX IF EXISTS idx_document_chunks_parent_id;
    DROP INDEX IF EXISTS idx_document_chunks_type;
    
    -- Remove columns
    ALTER TABLE document_chunks DROP COLUMN IF EXISTS parent_chunk_id;
    ALTER TABLE document_chunks DROP COLUMN IF EXISTS is_parent;
    ALTER TABLE document_chunks DROP COLUMN IF EXISTS chunk_type;
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(rollback_sql)
        conn.commit()
        print("✓ Rollback completed successfully")
    except Exception as e:
        print(f"✗ Rollback failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback_migration()
    else:
        migrate_schema()
        verify_migration()

        print("\n" + "=" * 70)
        print("Migration Complete!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Test hierarchical ingestion with use_hierarchical=True")
        print("2. Test queries with use_parent_retrieval=True")
        print("3. Monitor chunk statistics and query performance")
        print("\nFor rollback, run: python migrate_parent_document.py --rollback")
