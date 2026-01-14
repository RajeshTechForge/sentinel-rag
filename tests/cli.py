"""
Command Line Interface for Sentinel RAG System.

This module provides an interactive CLI for testing the Sentinel-RAG system locally.
Designed for developers to test functions by bypassing auth checks.

No Error Handling or Input Validation. So that you can see Raw Exceptions
directly for Better Debugging.

"""

import os
import sys
import logging
from typing import NoReturn, Optional
from pathlib import Path

from sentinel_rag.config import get_settings
from sentinel_rag.core import SentinelEngine
from sentinel_rag.services.database import DatabaseManager


#       ANSI COLOR CODES
# -----------------------------
class Colors:
    """ANSI color codes for terminal output."""

    # Basic colors
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"

    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


#   Styled Print Functions
# ---------------------------


def print_header(text: str) -> None:
    """Print a styled header."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}{'─' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}  {text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{'─' * 60}{Colors.RESET}\n")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{Colors.BRIGHT_GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str, details: Optional[str] = None) -> None:
    """Print an error message with optional details."""
    print(f"\n{Colors.BRIGHT_RED}✗ Error: {message}{Colors.RESET}")
    if details:
        print(f"{Colors.RED}  → {details}{Colors.RESET}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{Colors.BRIGHT_YELLOW}⚠ {message}{Colors.RESET}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"{Colors.BRIGHT_BLUE}ℹ {message}{Colors.RESET}")


def print_divider() -> None:
    """Print a simple divider."""
    print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")


def print_prompt(text: str) -> str:
    """Print a styled input prompt and return user input."""
    return input(f"{Colors.BRIGHT_MAGENTA}▸ {text}{Colors.RESET} ").strip()


#   Info & Input Config
# -----------------------

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


#  Starting Display
# -------------------


def display_banner() -> None:
    """Display the application banner."""
    banner = f"""
{Colors.BOLD}{Colors.BRIGHT_CYAN}
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        🛡️  SENTINEL RAG SYSTEM - DEVELOPER CLI            ║
║                                                           ║
║        Advanced RAG Framework Testing Interface           ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
{Colors.RESET}
    """
    print(banner)


def display_menu() -> None:
    """Display the main menu options."""
    print(
        f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}╭─ Main Menu ─────────────────────────────────────────────╮{Colors.RESET}"
    )
    print(f"{Colors.BRIGHT_CYAN}│{Colors.RESET}")
    print(
        f"{Colors.BRIGHT_CYAN}│{Colors.RESET}  {Colors.BOLD}1{Colors.RESET}  📄  Ingest Documents"
    )
    print(
        f"{Colors.BRIGHT_CYAN}│{Colors.RESET}  {Colors.BOLD}2{Colors.RESET}  💬  Chat Interface"
    )
    print(
        f"{Colors.BRIGHT_CYAN}│{Colors.RESET}  {Colors.BOLD}3{Colors.RESET}  👤  Create User"
    )
    print(
        f"{Colors.BRIGHT_CYAN}│{Colors.RESET}  {Colors.BOLD}4{Colors.RESET}  🚪  Exit"
    )
    print(f"{Colors.BRIGHT_CYAN}│{Colors.RESET}")
    print(
        f"{Colors.BOLD}{Colors.BRIGHT_CYAN}╰─────────────────────────────────────────────────────────╯{Colors.RESET}\n"
    )


#   Usage Functions
# -------------------


def handle_ingest(rag: SentinelEngine, db: DatabaseManager) -> None:
    """Handle document ingestion with enhanced UX."""
    print_header("📄 Document Ingestion")

    # Get file path
    path = print_prompt("File or directory path:")
    if not path:
        print_error("Path cannot be empty")
        return

    # Validate path exists
    if not Path(path).exists():
        print_error("Path does not exist", f"Cannot find: {path}")
        return

    # Get metadata
    title = print_prompt("Document title (optional, press Enter to skip):")
    description = print_prompt("Document description (optional, press Enter to skip):")

    # Get user
    email = print_prompt("User email for attribution:")
    if not email:
        print_error("User email is required for document attribution")
        return

    user = db.get_user_by_email(email)
    if not user:
        print_error("User not found", f"No user exists with email: {email}")
        print_info("Tip: Use option 3 to create a new user")
        return

    user_id = str(user["user_id"])
    user_name = user.get("full_name", email)
    print_success(f"User verified: {user_name}")

    # Get department
    department_name = print_prompt("Department name:").lower()
    if not department_name:
        print_error("Department name is required")
        return

    department_id = db.get_department_id_by_name(department_name)
    if not department_id:
        print_error(
            "Department not found",
            f"'{department_name}' does not exist in the system",
        )
        print_info("Available departments can be queried through the database")
        return

    # Get classification
    classification = print_prompt(
        "Classification (public/internal/confidential):"
    ).lower()
    valid_classifications = ["public", "internal", "confidential"]

    if classification not in valid_classifications:
        print_error(
            "Invalid classification",
            f"Must be one of: {', '.join(valid_classifications)}",
        )
        return

    # Confirm and ingest
    print_divider()
    print_info("Starting document ingestion...")
    print(f"{Colors.DIM}  Path: {path}")
    print(f"  Department: {department_name}")
    print(f"  Classification: {classification}")
    print(f"  Attributed to: {user_name}{Colors.RESET}")
    print_divider()

    rag.ingest_documents(
        source=path,
        title=title or None,
        description=description or None,
        user_id=user_id,
        department_id=department_id,
        classification=classification,
    )

    print_success("Documents ingested successfully!")


def handle_create_user(db: DatabaseManager) -> None:
    """Handle user creation with enhanced validation."""
    print_header("👤 Create New User")

    # Get user details
    email = print_prompt("Email address:").lower()
    if not email:
        print_error("Email is required")
        return

    # Check if user already exists
    existing_user = db.get_user_by_email(email)
    if existing_user:
        print_warning("User already exists with this email")
        print_info(f"Existing user: {existing_user.get('full_name', 'N/A')}")
        return

    name = print_prompt("Full name:")
    if not name:
        print_error("Full name is required")
        return

    department = print_prompt("Department name:").lower()
    if not department:
        print_error("Department name is required")
        return

    # Check available roles
    available_roles = db.get_roles_by_department(department)
    if not available_roles:
        print_error(
            "Department not found or has no roles",
            f"Department '{department}' does not exist or has no configured roles",
        )
        return

    print_info(f"Available roles in '{department}': {', '.join(available_roles)}")

    role = print_prompt("Role name:").lower()
    if not role:
        print_error("Role name is required")
        return

    if role not in available_roles:
        print_error(
            "Invalid role",
            f"Role '{role}' is not available in department '{department}'",
        )
        print_info(f"Choose from: {', '.join(available_roles)}")
        return

    # Confirm creation
    print_divider()
    print_info("Creating user with the following details:")
    print(f"{Colors.DIM}  Email: {email}")
    print(f"  Name: {name}")
    print(f"  Department: {department}")
    print(f"  Role: {role}{Colors.RESET}")
    print_divider()

    # Create user
    uid = db.create_user(email, name)
    db.assign_role(uid, role, department)

    print_success("User created successfully!")
    print(f"{Colors.GREEN}  User ID: {uid}")
    print(f"  Role '{role}' assigned in department '{department}'{Colors.RESET}")


def handle_chat(rag: SentinelEngine, db: DatabaseManager) -> None:
    """Handle chat session with enhanced interaction."""
    print_header("💬 Chat Interface")

    # Authenticate user
    email = print_prompt("Email to login:")
    if not email:
        print_error("Email is required")
        return

    user = db.get_user_by_email(email)

    if not user:
        print_error("User not found", f"No user exists with email: {email}")
        print_info("Tip: Use option 3 to create a new user")
        return
    user_id = str(user["user_id"])
    user_name = user.get("full_name", email)

    print_success(f"Logged in as: {user_name}")
    print_info(f"Type '{EXIT_COMMAND}' to return to main menu")
    print_divider()

    # Chat loop
    while True:
        query = input(
            f"\n{Colors.BOLD}{Colors.BRIGHT_GREEN}You:{Colors.RESET} "
        ).strip()

        if not query:
            continue

        if query.lower() == EXIT_COMMAND:
            print_info("Ending chat session...")
            break

        # Query the RAG system
        results = rag.query(query, user_id=user_id)

        # Display results
        print(f"\n{Colors.BOLD}{Colors.BRIGHT_BLUE}Sentinel:{Colors.RESET}")

        if not results:
            print(
                f"{Colors.YELLOW}  No relevant documents found or access denied.{Colors.RESET}"
            )
            print_info("This could mean:")
            print(f"{Colors.DIM}    • No documents match your query")
            print(
                f"    • You don't have permission to access matching documents{Colors.RESET}"
            )
        else:
            print(
                f"{Colors.GREEN}  Found {len(results)} relevant document(s):{Colors.RESET}\n"
            )

            for i, doc in enumerate(results, 1):
                score = doc.metadata.get("score", 0)
                source = doc.metadata.get("source", "Unknown")
                content_preview = doc.page_content[:200].replace("\n", " ")

                # Score-based coloring
                if score >= 0.8:
                    score_color = Colors.BRIGHT_GREEN
                elif score >= 0.6:
                    score_color = Colors.BRIGHT_YELLOW
                else:
                    score_color = Colors.BRIGHT_RED

                print(
                    f"{Colors.BOLD}  [{i}]{Colors.RESET} {Colors.CYAN}{source}{Colors.RESET}"
                )
                print(f"      {score_color}Score: {score:.4f}{Colors.RESET}")
                print(f"      {Colors.DIM}{content_preview}...{Colors.RESET}\n")


# ---------------------------


def main() -> NoReturn:
    """Main application entry point."""
    # Clear screen (cross-platform)
    os.system("clear" if os.name != "nt" else "cls")

    # Display banner
    display_banner()

    # Load configuration
    config = os.getenv("SENTINEL_CONFIG_PATH")
    if config:
        print_info(f"Using config: {config}")
    else:
        print_warning("SENTINEL_CONFIG_PATH not set, using defaults")

    # Initialize system
    print_info("Initializing Sentinel RAG System...")
    settings = get_settings()
    db = DatabaseManager(database_url=settings.database.dsn)
    engine = SentinelEngine(
        db=db,
        rbac_config=settings.rbac.as_dict,
        max_retrieved_docs=settings.doc_retrieval.max_retrieved_docs,
        similarity_threshold=settings.doc_retrieval.similarity_threshold,
        rrf_constant=settings.doc_retrieval.rrf_constant,
    )
    print_success("System initialized successfully\n")

    # Main loop
    while True:
        display_menu()
        choice = print_prompt("Select an option [1-4]:")

        if choice == OPTION_INGEST:
            handle_ingest(engine, db)
        elif choice == OPTION_CHAT:
            handle_chat(engine, db)
        elif choice == OPTION_CREATE_USER:
            handle_create_user(db)
        elif choice == OPTION_EXIT:
            print(
                f"\n{Colors.BRIGHT_CYAN}Thanks for using Sentinel RAG! 👋{Colors.RESET}\n"
            )
            sys.exit(0)
        else:
            print_warning(f"Invalid choice: '{choice}'. Please enter 1-4.")


if __name__ == "__main__":
    main()
