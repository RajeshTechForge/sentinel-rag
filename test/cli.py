"""
Command Line Interface for Sentinel RAG System.

This module provides an interactive CLI for testing the Sentinel-RAG system locally.
For production use, see app.py (FastAPI server).

"""

import os
import sys
import logging
from typing import NoReturn

from sentinel_rag import SentinelEngine
from sentinel_rag import DatabaseManager


# Configure logging to suppress verbose output
logging.basicConfig(level=logging.WARNING, force=True)
logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)

# Menu options
OPTION_INGEST = "1"
OPTION_CHAT = "2"
OPTION_CREATE_USER = "3"
OPTION_EXIT = "4"

# Commands
EXIT_COMMAND = "exit"


def display_menu() -> None:
    """Display the main menu options."""
    print("\n" + "=" * 40)
    print("Options:")
    print("  1. Ingest Documents")
    print("  2. Chat")
    print("  3. Create User")
    print("  4. Exit")
    print("=" * 40)


def handle_ingest(rag: SentinelEngine, db: DatabaseManager) -> None:
    """Handle document ingestion."""

    print("\n--- Ingest Documents ---")
    path = input("Enter file or directory path: ").strip()
    if not path:
        print("Path is required.")
        return

    title = input("Enter document title (optional): ").strip()
    description = input("Enter document description (optional): ").strip()
    email = input("Enter user email for attribution: ").strip()
    user_id = None
    if email:
        user = db.get_user_by_email(email)
        if user:
            user_id = str(user["user_id"])
            print(f"Found user: {user.get('full_name', email)}")
        else:
            print("User not found. User is Required.")
            return

    print("\nIngesting documents...")
    department_name = input("Enter document department: ").strip().lower()

    department_id = db.get_department_id_by_name(department_name)
    if not department_id:
        print(f"Department '{department_name}' not found. Please create it first.")
        return

    classification = (
        input("Enter document classification (public/internal/confidential): ")
        .strip()
        .lower()
    )

    rag.ingest_documents(
        source=path,
        title=title,
        description=description,
        user_id=user_id,
        department_id=department_id,
        classification=classification,
    )
    print("Documents ingested successfully!")


def handle_create_user(db: SentinelEngine) -> None:
    print("\n--- Create User ---")
    email = input("Enter email: ").strip().lower()
    name = input("Enter full name: ").strip()
    department = input("Enter department name: ").strip().lower()
    role = input("Enter role name: ").strip().lower()

    if not email:
        print("Email is required.")
        return
    try:
        available_roles = db.get_roles_by_department(department)
        if not available_roles:
            print(
                f"No roles found for department '{department}' or department does not exist."
            )
            return

        if role not in available_roles:
            print(f"Role '{role}' not found in department '{department}'.")
            print(f"Available roles: {', '.join(available_roles)}")
            return

        uid = db.create_user(email, name)
        db.assign_role(uid, role, department)
        print(f"User created with ID: {uid}")
        print(f"Role '{role}' assigned to user {email} in department {department}.")

    except Exception as e:
        print(f"Error creating user: {e}")


def handle_chat(rag: SentinelEngine, db: DatabaseManager) -> None:
    """Handle chat session with the RAG system."""

    email = input("Enter your email to login: ").strip()
    user = db.get_user_by_email(email)
    if not user:
        print("User not found.")
        return
    user_id = str(user["user_id"])

    print("\nStarting Chat Session")
    print(f"(type '{EXIT_COMMAND}' to return to menu)")
    print("-" * 40)

    while True:
        query = input("\nYou: ").strip()

        if not query:
            continue

        if query.lower() == EXIT_COMMAND:
            print("Ending chat session...")
            break

        # try:
        results = rag.query(query, user_id=user_id)
        print("\nRelevant Documents:")
        if not results:
            print("No relevant documents found or access denied.")
        for i, doc in enumerate(results):
            print(
                f"{i + 1}. {doc.metadata.get('source')} (Score: {doc.metadata.get('score', 0):.4f})"
            )
            print(f"   Content: {doc.page_content[:200]}...\n")
        # except Exception as e:
        #     print(f"\n❌ Error: {e}")


def main() -> NoReturn:
    # Load config file
    config = os.getenv("SENTINEL_CONFIG_PATH")

    print("=" * 40)
    print("  Sentinel RAG System - CLI Interface")
    print("=" * 40)

    db = DatabaseManager()
    engine = SentinelEngine(db=db, config_file=config)

    while True:
        display_menu()
        choice = input("Enter your choice (1-4): ").strip()

        if choice == OPTION_INGEST:
            handle_ingest(engine, db)
        elif choice == OPTION_CHAT:
            handle_chat(engine, db)
        elif choice == OPTION_CREATE_USER:
            handle_create_user(db)
        elif choice == OPTION_EXIT:
            print("\nGoodbye! 👋")
            sys.exit(0)
        else:
            print("\n⚠️  Invalid choice. Please enter 1-4.")


if __name__ == "__main__":
    main()
