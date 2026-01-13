"""
Example: Parent-Document Retrieval Comparison

This script demonstrates the difference between traditional flat chunking
and Parent-Document Retrieval in terms of context quality and search precision.
"""

from sentinel_rag.core.engine import SentinelEngine
from sentinel_rag.services.database import DatabaseManager


def compare_retrieval_strategies():
    """Compare flat vs hierarchical chunking with sample queries."""

    # Initialize
    db = DatabaseManager()
    engine = SentinelEngine(db=db)

    # Sample document content
    sample_doc = """
    # Enterprise Password Security Policy
    
    ## Overview
    This document outlines the comprehensive password security requirements
    for all employees and contractors of ACME Corporation. These policies
    are designed to protect company assets and ensure compliance with
    industry standards.
    
    ## Password Requirements
    
    ### Complexity Rules
    All passwords must meet the following minimum requirements:
    - Minimum length of 12 characters
    - Must contain at least one uppercase letter (A-Z)
    - Must contain at least one lowercase letter (a-z)
    - Must contain at least one number (0-9)
    - Must contain at least one special character (!@#$%^&*)
    - Cannot contain your username or email address
    - Cannot contain common dictionary words
    - Cannot repeat the same character more than 3 times consecutively
    
    ### Password Rotation
    Passwords must be changed every 90 days. The system will send reminders
    starting 14 days before expiration. Users cannot reuse any of their
    last 12 passwords. Emergency password resets require manager approval
    for elevated access accounts.
    
    ### Multi-Factor Authentication
    All employees must enable MFA on their accounts within 7 days of hire.
    Supported methods include:
    - Authenticator apps (Google Authenticator, Microsoft Authenticator)
    - Hardware security keys (YubiKey, Titan)
    - SMS verification (for backup only)
    
    ## Account Lockout Policy
    
    After 5 failed login attempts, accounts will be locked for 30 minutes.
    After 10 failed attempts in 24 hours, accounts require IT support to unlock.
    Suspicious activity may result in immediate account suspension.
    
    ## Exceptions and Waivers
    
    Service accounts and API keys follow different policies outlined in the
    Technical Operations Manual. Requests for policy exceptions must be
    submitted through the Security Exception Request form and approved by
    the CISO.
    """

    # Create temporary file
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(sample_doc)
        temp_path = f.name

    try:
        print("=" * 80)
        print("PARENT-DOCUMENT RETRIEVAL COMPARISON")
        print("=" * 80)

        # Get test user
        user = db.get_user_by_email("alice@company.com")
        dept_id = db.get_department_id_by_name("Engineering")

        #    Test 1: Traditional Flat Chunking
        # ------------------------------------------
        print("\n" + "-" * 80)
        print("TEST 1: Traditional Flat Chunking")
        print("-" * 80)

        doc_id_flat = engine.ingest_documents(
            source=temp_path,
            title="Password Policy (Flat)",
            description="Test document with flat chunking",
            user_id=str(user["user_id"]),
            department_id=str(dept_id),
            classification="public",
            use_hierarchical=False,  # Traditional approach
        )

        print(f"✓ Ingested document (flat): {doc_id_flat}\n")

        # Query with flat chunks
        print("Query: 'What are the password length requirements?'\n")
        results_flat = engine.query(
            question="What are the password length requirements?",
            user_id=str(user["user_id"]),
            k=3,
            use_parent_retrieval=False,
        )

        print(f"Found {len(results_flat)} results:\n")
        for i, doc in enumerate(results_flat, 1):
            print(f"Result {i} (Score: {doc.metadata.get('score', 0)})")
            print(f"Length: {len(doc.page_content)} chars")
            print(f"Retrieval Type: {doc.metadata.get('retrieval_type', 'direct')}")
            print(f"Preview: {doc.page_content[:200]}...")
            print()

        #   Test 2: Parent-Document Retrieval
        # -------------------------------------
        print("-" * 80)
        print("TEST 2: Parent-Document Retrieval (Hierarchical)")
        print("-" * 80)

        doc_id_hier = engine.ingest_documents(
            source=temp_path,
            title="Password Policy (Hierarchical)",
            description="Test document with hierarchical chunking",
            user_id=str(user["user_id"]),
            department_id=str(dept_id),
            classification="internal",
            use_hierarchical=True,  # Parent-Document Retrieval
        )

        print(f"✓ Ingested document (hierarchical): {doc_id_hier}\n")

        # Query with parent retrieval
        print("Query: 'What are the password length requirements?'\n")
        results_hier = engine.query(
            question="What are the password length requirements?",
            user_id=str(user["user_id"]),
            k=3,
            use_parent_retrieval=True,
        )

        print(f"Found {len(results_hier)} results:\n")
        for i, doc in enumerate(results_hier, 1):
            print(f"Result {i} (Score: {doc.metadata.get('score', 0)})")
            print(f"Length: {len(doc.page_content)} chars")
            print(f"Retrieval Type: {doc.metadata.get('retrieval_type', 'direct')}")
            print(f"Preview: {doc.page_content[:300]}...")
            print()

        #   Analysis
        # -------------
        print("-" * 80)
        print("ANALYSIS")
        print("-" * 80)

        if results_flat and results_hier:
            avg_len_flat = sum(len(d.page_content) for d in results_flat) / len(
                results_flat
            )
            avg_len_hier = sum(len(d.page_content) for d in results_hier) / len(
                results_hier
            )

            print("\nAverage chunk length:")
            print(f"  Flat chunking:        {int(avg_len_flat):,} characters")
            print(f"  Parent-Doc Retrieval: {int(avg_len_hier):,} characters")
            print(
                f"  Context improvement:  {((avg_len_hier / avg_len_flat - 1) * 100):.1f}%"
            )

            print("\nContext Quality:")
            print("  Flat chunking:        ⭐⭐⭐ (May miss surrounding context)")
            print(
                "  Parent-Doc Retrieval: ⭐⭐⭐⭐⭐ (Complete sections with full context)"
            )

            print("\nSearch Precision:")
            print("  Flat chunking:        ⭐⭐⭐⭐ (Moderate precision)")
            print(
                "  Parent-Doc Retrieval: ⭐⭐⭐⭐⭐ (High precision from small child chunks)"
            )

        #    Database Statistics
        # --------------------------
        print("\n" + "-" * 80)
        print("DATABASE STATISTICS")
        print("-" * 80)

        with db._get_connection() as conn:
            with conn.cursor() as cur:
                # Chunk type distribution
                cur.execute(
                    """
                    SELECT 
                        COALESCE(chunk_type, 'legacy') as type,
                        COUNT(*) as count,
                        ROUND(AVG(LENGTH(content))) as avg_length,
                        COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as with_embedding
                    FROM document_chunks
                    WHERE doc_id IN (%s, %s)
                    GROUP BY chunk_type
                    ORDER BY chunk_type;
                """,
                    (doc_id_flat, doc_id_hier),
                )

                print("\nChunk Distribution:")
                print(
                    f"{'Type':<15} {'Count':<10} {'Avg Length':<15} {'Embeddings':<15}"
                )
                print("-" * 60)

                for row in cur.fetchall():
                    chunk_type, count, avg_len, with_emb = row
                    print(
                        f"{chunk_type:<15} {count:<10} {int(avg_len or 0):<15} {with_emb:<15}"
                    )

        #   Recommendations
        # -------------------
        print("\n" + "=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)

        print("""
Use Parent-Document Retrieval when:
  ✓ Documents have complex, nested structure (reports, manuals, legal docs)
  ✓ Context preservation is critical for LLM understanding
  ✓ Users expect complete, coherent answers
  ✓ Storage is not a primary constraint
  
Use Traditional Flat Chunking when:
  ✓ Documents are simple, flat text (emails, chat logs, tweets)
  ✓ Fast ingestion is priority
  ✓ Storage/cost is a concern
  ✓ Chunks are naturally self-contained
  
Best Practice:
  → Start with Parent-Document Retrieval for production systems
  → Fine-tune chunk sizes based on your document characteristics
  → Monitor retrieval quality metrics and adjust accordingly
        """)

    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

        print("\n" + "=" * 80)


def show_chunk_examples():
    """Display example of how documents are chunked."""

    print("\n" + "=" * 80)
    print("CHUNK HIERARCHY VISUALIZATION")
    print("=" * 80)

    sample_text = """
# Employee Handbook

## Section 1: Code of Conduct
All employees must adhere to our core values of integrity, respect, and 
excellence. This includes professional behavior, ethical decision-making, 
and maintaining confidentiality of sensitive information.

### Dress Code
Business casual attire is required in the office. This includes collared 
shirts, slacks or skirts, and closed-toe shoes. Jeans are permitted on 
Fridays. Remote workers should maintain professional appearance during 
video calls.

### Working Hours
Standard hours are 9 AM to 5 PM Monday through Friday. Flexible arrangements 
are available with manager approval. All employees must log their time 
accurately in the time tracking system.

## Section 2: Benefits
We offer comprehensive benefits including health insurance, 401(k) matching, 
unlimited PTO, and professional development stipends.
    """

    from sentinel_rag.core.document_processor import DocumentProcessor

    processor = DocumentProcessor()
    hierarchy = processor.hierarchical_chunks(sample_text)

    print(f"\nParent Chunks: {len(hierarchy['parent_chunks'])}")
    print(f"Child Chunks:  {len(hierarchy['child_chunks'])}")
    print(f"Relationships: {len(hierarchy['relationships'])}")

    print("\nHierarchy Structure:")
    print("-" * 80)

    for i, parent in enumerate(hierarchy["parent_chunks"]):
        print(f"\n📄 Parent Chunk {i + 1} ({len(parent.page_content)} chars)")
        print(f"   {parent.page_content[:100]}...")

        # Find children of this parent
        children = [
            (idx, child)
            for idx, child in enumerate(hierarchy["child_chunks"])
            if child.metadata.get("parent_index") == i
        ]

        print(f"\n   └─ {len(children)} child chunks:")
        for child_idx, child in children[:3]:  # Show first 3
            print(f"      ├─ Child {child_idx + 1} ({len(child.page_content)} chars)")
            print(f"      │  {child.page_content[:80]}...")

        if len(children) > 3:
            print(f"      └─ ... and {len(children) - 3} more")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    import sys

    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--visualize":
            show_chunk_examples()
        else:
            compare_retrieval_strategies()

            print("\nRun with --visualize to see chunk hierarchy examples")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
