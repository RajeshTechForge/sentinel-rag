import time
from datetime import datetime
from typing import Optional
from urllib.parse import quote

import streamlit as st

from api_client import SentinelRAGClient, APIError, UserInfo
from styles import (
    get_custom_css,
    get_header_html,
    get_user_profile_html,
    get_metric_card_html,
    get_document_card_html,
    get_result_card_html,
    get_status_indicator_html,
    get_alert_html,
)


# Configuration
# -------------

st.set_page_config(
    page_title="Sentinel RAG | Enterprise Document Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/yourusername/sentinel-rag",
        "Report a bug": "https://github.com/yourusername/sentinel-rag/issues",
        "About": "# Sentinel RAG\nEnterprise Document Intelligence Platform v1.0.0",
    },
)


# Session State Initialization
# ----------------------------


def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "authenticated": False,
        "token": None,
        "user": None,
        "api_url": "http://localhost:8000",
        "streamlit_url": "http://localhost:8501",
        "current_page": "dashboard",
        "query_history": [],
        "upload_success": None,
        "last_error": None,
        "auth_callback_processed": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


# API Client
# ----------


@st.cache_resource
def get_api_client() -> SentinelRAGClient:
    """Get or create cached API client."""
    return SentinelRAGClient(base_url=st.session_state.api_url)


def get_authenticated_client() -> Optional[SentinelRAGClient]:
    """Get authenticated API client or None."""
    if st.session_state.authenticated and st.session_state.token:
        client = get_api_client()
        client.set_token(st.session_state.token)
        return client
    return None


# Authentication Functions
# ------------------------


def handle_login(token: str) -> bool:
    """
    Handle user login with JWT token.

    Args:
        token: JWT access token

    Returns:
        True if login successful
    """
    client = get_api_client()
    client.set_token(token)

    try:
        user = client.get_current_user()
        st.session_state.authenticated = True
        st.session_state.token = token
        st.session_state.user = user
        st.session_state.last_error = None
        return True
    except APIError as e:
        st.session_state.last_error = str(e)
        return False


def handle_logout():
    """Handle user logout."""
    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.query_history = []
    st.cache_resource.clear()


# OAuth Callback Handler
# ----------------------


def check_auth_callback():
    """
    Check if we're receiving an OAuth callback with access_token.
    The FastAPI backend redirects here after successful OIDC authentication.
    """
    # Check query parameters for token (from callback redirect)
    query_params = st.query_params

    # Check for access_token in query params (callback from FastAPI)
    if "access_token" in query_params and not st.session_state.auth_callback_processed:
        token = query_params.get("access_token")
        if token and handle_login(token):
            st.session_state.auth_callback_processed = True
            # Clear the URL parameters
            st.query_params.clear()
            st.rerun()

    # Check for auth error
    if "auth_error" in query_params:
        error = query_params.get("auth_error", "Authentication failed")
        st.session_state.last_error = error
        st.query_params.clear()


# Run callback check on every page load
check_auth_callback()


# UI Components
# -------------


def render_sidebar():
    """Render the sidebar navigation and user info."""
    with st.sidebar:
        # Logo and branding
        st.markdown(
            """
        <div style="padding: 1rem 0; border-bottom: 1px solid #334155; margin-bottom: 1.5rem;">
            <div style="font-size: 1.75rem; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 0.5rem;">
                🛡️ <span style="background: linear-gradient(135deg, #6366f1, #0ea5e9); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Sentinel</span>
            </div>
            <div style="color: #64748b; font-size: 0.85rem; margin-top: 0.25rem;">Enterprise RAG Platform</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if st.session_state.authenticated and st.session_state.user:
            user: UserInfo = st.session_state.user

            # User info card
            st.markdown(
                f"""
            <div style="background: linear-gradient(135deg, #1e293b, rgba(99, 102, 241, 0.1)); border: 1px solid #334155; border-radius: 12px; padding: 1rem; margin-bottom: 1.5rem;">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <div style="width: 45px; height: 45px; border-radius: 50%; background: linear-gradient(135deg, #6366f1, #0ea5e9); display: flex; align-items: center; justify-content: center; font-size: 1.25rem; color: white; font-weight: 600;">
                        {user.email[0].upper()}
                    </div>
                    <div>
                        <div style="color: #f8fafc; font-weight: 600; font-size: 0.95rem;">{user.email.split("@")[0].replace(".", " ").title()}</div>
                        <div style="color: #64748b; font-size: 0.75rem;">{user.role} • {user.department}</div>
                    </div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Navigation
            st.markdown("### Navigation")

            nav_items = [
                ("dashboard", "📊", "Dashboard"),
                ("query", "🔍", "Query Documents"),
                ("upload", "📤", "Upload Document"),
                ("documents", "📁", "My Documents"),
                ("settings", "⚙️", "Settings"),
            ]

            for page_id, icon, label in nav_items:
                is_active = st.session_state.current_page == page_id
                if st.button(
                    f"{icon}  {label}",
                    key=f"nav_{page_id}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state.current_page = page_id
                    st.rerun()

            st.divider()

            # Logout button
            if st.button("🚪 Logout", use_container_width=True, type="secondary"):
                handle_logout()
                st.rerun()

        else:
            # Not authenticated - show login prompt
            st.info("Please authenticate to access the platform.")

        # Footer
        st.markdown(
            """
        <div style="position: fixed; bottom: 1rem; left: 1rem; right: 1rem; max-width: 230px;">
            <div style="border-top: 1px solid #334155; padding-top: 1rem; color: #64748b; font-size: 0.75rem; text-align: center;">
                Sentinel RAG v1.0.0<br>
                <span style="color: #94a3b8;">Enterprise Edition</span>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )


def render_login_page():
    """Render the login/authentication page."""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown(get_header_html(), unsafe_allow_html=True)

        # Main login card
        st.markdown(
            """
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 2.5rem; margin-top: 2rem; text-align: center;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">🔐</div>
            <h2 style="color: #f8fafc; margin-bottom: 0.5rem;">Welcome to Sentinel RAG</h2>
            <p style="color: #94a3b8; margin-bottom: 2rem;">Sign in to access the Enterprise Document Intelligence Platform</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Show any auth errors
        if st.session_state.last_error:
            st.markdown(
                get_alert_html(st.session_state.last_error, "error"),
                unsafe_allow_html=True,
            )
            st.session_state.last_error = None

        st.markdown("<br>", unsafe_allow_html=True)

        # Primary SSO Login Button
        # Build login URL with redirect back to Streamlit
        streamlit_callback = st.session_state.streamlit_url
        login_url = f"{st.session_state.api_url}/auth/login?redirect_uri={quote(streamlit_callback)}"
        # Create a styled button that redirects to the OIDC login
        st.markdown(
            f"""
        <div style="text-align: center; margin: 1.5rem 0;">
            <a href="{login_url}" target="_self" style="
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 0.75rem;
                background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
                color: white;
                text-decoration: none;
                padding: 1rem 2.5rem;
                border-radius: 12px;
                font-size: 1.1rem;
                font-weight: 600;
                box-shadow: 0 4px 15px -3px rgba(99, 102, 241, 0.4);
                transition: all 0.2s ease;
            " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 8px 25px -5px rgba(99, 102, 241, 0.5)';"
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px -3px rgba(99, 102, 241, 0.4)';">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
                    <polyline points="10 17 15 12 10 7"/>
                    <line x1="15" y1="12" x2="3" y2="12"/>
                </svg>
                Sign in with SSO
            </a>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
        <p style="text-align: center; color: #64748b; font-size: 0.85rem; margin-top: 1rem;">
            You will be redirected to your organization's identity provider
        </p>
        """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Divider
        st.markdown(
            """
        <div style="display: flex; align-items: center; margin: 2rem 0;">
            <div style="flex: 1; height: 1px; background: #334155;"></div>
            <span style="padding: 0 1rem; color: #64748b; font-size: 0.85rem;">OR</span>
            <div style="flex: 1; height: 1px; background: #334155;"></div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Developer Options (collapsed by default)
        with st.expander("🔧 Developer Options", expanded=False):
            st.markdown(
                """
            <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 1rem;">
                For developers and testing: manually enter a JWT access token
            </p>
            """,
                unsafe_allow_html=True,
            )

            # API URL Configuration
            col_dev1, col_dev2 = st.columns(2)

            with col_dev1:
                api_url = st.text_input(
                    "API Base URL",
                    value=st.session_state.api_url,
                    help="The base URL of the Sentinel RAG API server",
                )
                if api_url != st.session_state.api_url:
                    st.session_state.api_url = api_url
                    st.cache_resource.clear()

            with col_dev2:
                streamlit_url = st.text_input(
                    "Streamlit Callback URL",
                    value=st.session_state.streamlit_url,
                    help="The URL where Streamlit is running (for OAuth callback)",
                )
                if streamlit_url != st.session_state.streamlit_url:
                    st.session_state.streamlit_url = streamlit_url

            # Token input
            token = st.text_area(
                "Access Token (JWT)",
                height=100,
                placeholder="Paste your JWT access token here...",
                help="Obtain your token from the /auth/callback endpoint or your administrator",
            )

            if st.button("🔑 Connect with Token", use_container_width=True):
                if token.strip():
                    with st.spinner("Authenticating..."):
                        if handle_login(token.strip()):
                            st.success("✅ Authentication successful!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(
                                f"❌ Authentication failed: {st.session_state.last_error}"
                            )
                else:
                    st.warning("⚠️ Please enter a valid token")

        # Health check section
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("---")

        col_a, col_b = st.columns([1, 1])

        with col_a:
            st.markdown("### 🏥 API Status")
            try:
                client = get_api_client()
                health = client.health_check()
                st.markdown(
                    f"""
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="width: 12px; height: 12px; border-radius: 50%; background: #10b981; display: inline-block;"></span>
                    <span style="color: #10b981; font-weight: 500;">Connected</span>
                    <span style="color: #64748b; font-size: 0.85rem;">v{health.version}</span>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            except Exception:
                st.markdown(
                    """
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="width: 12px; height: 12px; border-radius: 50%; background: #ef4444; display: inline-block;"></span>
                    <span style="color: #ef4444; font-weight: 500;">Disconnected</span>
                </div>
                """,
                    unsafe_allow_html=True,
                )

        with col_b:
            if st.button("🔄 Check Connection", use_container_width=True):
                try:
                    client = get_api_client()
                    health = client.health_check()
                    st.success(f"✅ API is healthy (v{health.version})")
                except APIError as e:
                    st.error(f"❌ API Error: {e.message}")
                except Exception as e:
                    st.error(f"❌ Connection Error: {str(e)}")

        # Help section
        st.markdown(
            """
        <div style="margin-top: 2rem; padding: 1.5rem; background: rgba(99, 102, 241, 0.05); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 12px;">
            <h4 style="color: #f8fafc; margin-bottom: 0.75rem;">💡 Need Help?</h4>
            <div style="color: #94a3b8; font-size: 0.9rem;">
                <p style="margin-bottom: 0.5rem;"><strong>First time user?</strong> Click "Sign in with SSO" to authenticate with your organization's identity provider.</p>
                <p style="margin-bottom: 0;"><strong>Having issues?</strong> Ensure the FastAPI server is running and OIDC is properly configured.</p>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )


def render_dashboard():
    """Render the main dashboard page."""
    st.markdown(
        get_header_html("Dashboard", "Welcome back! Here's your activity overview"),
        unsafe_allow_html=True,
    )

    client = get_authenticated_client()
    user: UserInfo = st.session_state.user

    # User profile section
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown(
            get_user_profile_html(user.email, user.role, user.department),
            unsafe_allow_html=True,
        )

        # Quick actions
        st.markdown(
            """
        <div class="card">
            <div class="card-header">
                <span class="card-icon">⚡</span>
                <h3 class="card-title">Quick Actions</h3>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if st.button("🔍 New Query", use_container_width=True, type="primary"):
            st.session_state.current_page = "query"
            st.rerun()

        if st.button("📤 Upload Document", use_container_width=True):
            st.session_state.current_page = "upload"
            st.rerun()

        if st.button("📁 View My Documents", use_container_width=True):
            st.session_state.current_page = "documents"
            st.rerun()

    with col2:
        # Metrics row
        st.markdown("### 📊 Your Statistics")

        try:
            documents = client.get_user_documents()
            doc_count = len(documents)
        except APIError:
            documents = []
            doc_count = 0

        query_count = len(st.session_state.query_history)

        metric_cols = st.columns(4)

        with metric_cols[0]:
            st.markdown(
                get_metric_card_html(str(doc_count), "Documents", "📄"),
                unsafe_allow_html=True,
            )

        with metric_cols[1]:
            st.markdown(
                get_metric_card_html(str(query_count), "Queries Today", "🔍"),
                unsafe_allow_html=True,
            )

        with metric_cols[2]:
            # Calculate unique departments from documents
            unique_depts = (
                len(set(doc.department for doc in documents)) if documents else 0
            )
            st.markdown(
                get_metric_card_html(str(unique_depts), "Departments", "🏢"),
                unsafe_allow_html=True,
            )

        with metric_cols[3]:
            st.markdown(
                get_metric_card_html(user.role.upper(), "Access Level", "🔐"),
                unsafe_allow_html=True,
            )

        # Recent documents
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📁 Recent Documents")

        if documents:
            for doc in documents[:5]:  # Show last 5
                st.markdown(
                    get_document_card_html(
                        title=doc.title,
                        doc_id=doc.doc_id,
                        classification=doc.classification,
                        department=doc.department,
                        created_at=doc.created_at,
                    ),
                    unsafe_allow_html=True,
                )

            if len(documents) > 5:
                st.markdown(
                    f"""
                <div style="text-align: center; padding: 1rem; color: #64748b;">
                    <em>+ {len(documents) - 5} more documents</em>
                </div>
                """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                get_alert_html(
                    "No documents found. Upload your first document to get started!",
                    "info",
                ),
                unsafe_allow_html=True,
            )

    # System status section
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🏥 System Status")

    try:
        health = client.readiness_check()
        status_cols = st.columns(4)

        with status_cols[0]:
            st.markdown(
                f"""
            <div class="card" style="text-align: center;">
                {get_status_indicator_html(health.status, "Overall Status")}
            </div>
            """,
                unsafe_allow_html=True,
            )

        if health.components:
            for i, (name, details) in enumerate(health.components.items()):
                if i < 3:  # Show up to 3 components
                    with status_cols[i + 1]:
                        st.markdown(
                            f"""
                        <div class="card" style="text-align: center;">
                            {get_status_indicator_html(details.get("status", "unknown"), name.title())}
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

    except APIError as e:
        st.markdown(
            get_alert_html(f"Unable to fetch system status: {e.message}", "warning"),
            unsafe_allow_html=True,
        )


def render_query_page():
    """Render the document query page."""
    st.markdown(
        get_header_html(
            "Query Documents", "Semantic search across your authorized documents"
        ),
        unsafe_allow_html=True,
    )

    client = get_authenticated_client()

    # Query input section
    st.markdown(
        """
    <div class="card">
        <div class="card-header">
            <span class="card-icon">🔍</span>
            <h3 class="card-title">Enter Your Query</h3>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([3, 1])

    with col1:
        query_text = st.text_area(
            "Search Query",
            placeholder="Enter your question or search terms...\n\nExample: What are the security policies for handling customer data?",
            height=120,
            label_visibility="collapsed",
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        k = st.slider(
            "Results Count",
            min_value=1,
            max_value=20,
            value=5,
            help="Number of document chunks to retrieve",
        )

        search_button = st.button("🚀 Search", use_container_width=True, type="primary")

    # Execute query
    if search_button and query_text.strip():
        with st.spinner("🔍 Searching documents..."):
            start_time = time.time()

            try:
                results = client.query(query_text.strip(), k=k)
                elapsed_time = (time.time() - start_time) * 1000

                # Store in history
                st.session_state.query_history.append(
                    {
                        "query": query_text,
                        "results_count": len(results),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

                # Display results
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(
                    f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <h3 style="color: #f8fafc; margin: 0;">📋 Search Results</h3>
                    <div style="color: #64748b; font-size: 0.9rem;">
                        Found {len(results)} results in {elapsed_time:.0f}ms
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                if results:
                    for i, result in enumerate(results, 1):
                        with st.expander(
                            f"📄 Result {i} — {result.title or 'Untitled'}",
                            expanded=i <= 3,
                        ):
                            st.markdown(
                                get_result_card_html(
                                    content=result.content,
                                    doc_title=result.title,
                                    classification=result.classification,
                                    chunk_id=result.chunk_id,
                                ),
                                unsafe_allow_html=True,
                            )

                            # Metadata details
                            st.markdown("**Metadata:**")
                            st.json(result.metadata)
                else:
                    st.markdown(
                        get_alert_html(
                            "No results found. Try a different query or check your access permissions.",
                            "info",
                        ),
                        unsafe_allow_html=True,
                    )

            except APIError as e:
                st.markdown(
                    get_alert_html(f"Query failed: {e.message}", "error"),
                    unsafe_allow_html=True,
                )

    elif search_button:
        st.warning("⚠️ Please enter a search query")

    # Query history section
    if st.session_state.query_history:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📜 Recent Queries")

        history_df_data = []
        for item in reversed(st.session_state.query_history[-10:]):
            history_df_data.append(
                {
                    "Query": item["query"][:50]
                    + ("..." if len(item["query"]) > 50 else ""),
                    "Results": item["results_count"],
                    "Time": item["timestamp"].split("T")[1].split(".")[0],
                }
            )

        st.dataframe(
            history_df_data,
            use_container_width=True,
            hide_index=True,
        )


def render_upload_page():
    """Render the document upload page."""
    st.markdown(
        get_header_html("Upload Document", "Add new documents to the knowledge base"),
        unsafe_allow_html=True,
    )

    client = get_authenticated_client()
    user: UserInfo = st.session_state.user

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(
            """
        <div class="card">
            <div class="card-header">
                <span class="card-icon">📤</span>
                <h3 class="card-title">Document Upload</h3>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["pdf", "txt", "md", "doc", "docx"],
            help="Supported formats: PDF, TXT, MD, DOC, DOCX",
        )

        if uploaded_file:
            st.markdown(
                f"""
            <div class="alert alert-info">
                <span>📎</span>
                <div>
                    <strong>File selected:</strong> {uploaded_file.name}<br>
                    <span style="font-size: 0.85rem;">Size: {uploaded_file.size / 1024:.1f} KB | Type: {uploaded_file.type}</span>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # Document metadata form
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Document Details")

        doc_title = st.text_input(
            "Document Title*",
            placeholder="Enter a descriptive title for the document",
        )

        doc_description = st.text_area(
            "Description*",
            placeholder="Provide a brief description of the document content...",
            height=100,
        )

        col_a, col_b = st.columns(2)

        with col_a:
            doc_department = st.selectbox(
                "Department*",
                options=client.get_department_options(),
                format_func=lambda x: x.replace("_", " ").title(),
            )

        with col_b:
            doc_classification = st.selectbox(
                "Classification Level*",
                options=client.get_classification_options(),
                format_func=lambda x: x.title(),
            )

        # Classification info
        classification_info = {
            "public": ("🟢", "Accessible to all users within the organization"),
            "internal": ("🔵", "Accessible to employees within specific departments"),
            "confidential": (
                "🟡",
                "Restricted access, requires explicit authorization",
            ),
            "restricted": ("🔴", "Highly sensitive, strict access controls apply"),
        }

        icon, desc = classification_info.get(doc_classification, ("", ""))
        st.markdown(
            f"""
        <div style="padding: 0.75rem; background: rgba(99, 102, 241, 0.05); border-radius: 8px; margin-top: 0.5rem;">
            <span style="font-size: 1.25rem;">{icon}</span>
            <span style="color: #94a3b8; font-size: 0.9rem; margin-left: 0.5rem;">{desc}</span>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Upload button
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("📤 Upload Document", use_container_width=True, type="primary"):
            # Validation
            if not uploaded_file:
                st.error("❌ Please select a file to upload")
            elif not doc_title.strip():
                st.error("❌ Please enter a document title")
            elif not doc_description.strip():
                st.error("❌ Please enter a document description")
            else:
                with st.spinner("📤 Uploading and processing document..."):
                    try:
                        result = client.upload_document(
                            file=uploaded_file.getvalue(),
                            filename=uploaded_file.name,
                            title=doc_title.strip(),
                            description=doc_description.strip(),
                            department=doc_department,
                            classification=doc_classification,
                        )

                        st.session_state.upload_success = result

                        st.markdown(
                            f"""
                        <div class="alert alert-success">
                            <span>✅</span>
                            <div>
                                <strong>Document uploaded successfully!</strong><br>
                                <span style="font-size: 0.85rem;">
                                    Document ID: <code>{result.doc_id}</code><br>
                                    Processing time: {result.processing_time_ms:.0f}ms
                                </span>
                            </div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

                        st.balloons()

                    except APIError as e:
                        st.markdown(
                            get_alert_html(f"Upload failed: {e.message}", "error"),
                            unsafe_allow_html=True,
                        )

    with col2:
        # Upload guidelines
        st.markdown(
            """
        <div class="card">
            <div class="card-header">
                <span class="card-icon">📋</span>
                <h3 class="card-title">Upload Guidelines</h3>
            </div>
            <div style="color: #94a3b8; font-size: 0.9rem;">
                <ul style="padding-left: 1.25rem; margin: 0;">
                    <li style="margin-bottom: 0.5rem;">Ensure documents are properly classified</li>
                    <li style="margin-bottom: 0.5rem;">Use descriptive titles for easy discovery</li>
                    <li style="margin-bottom: 0.5rem;">Max file size: 10MB</li>
                    <li style="margin-bottom: 0.5rem;">Documents are automatically chunked and indexed</li>
                    <li style="margin-bottom: 0.5rem;">PII is automatically detected and protected</li>
                </ul>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Current user context
        st.markdown(
            f"""
        <div class="card">
            <div class="card-header">
                <span class="card-icon">👤</span>
                <h3 class="card-title">Upload Context</h3>
            </div>
            <div style="color: #94a3b8; font-size: 0.9rem;">
                <p><strong>Uploading as:</strong> {user.email}</p>
                <p><strong>Role:</strong> {user.role}</p>
                <p><strong>Department:</strong> {user.department}</p>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )


def render_documents_page():
    """Render the documents list page."""
    st.markdown(
        get_header_html("My Documents", "View and manage your uploaded documents"),
        unsafe_allow_html=True,
    )

    client = get_authenticated_client()

    # Filters
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        search_filter = st.text_input(
            "🔍 Search documents",
            placeholder="Filter by title...",
            label_visibility="collapsed",
        )

    with col2:
        classification_filter = st.selectbox(
            "Classification",
            options=["All"] + [c.title() for c in client.get_classification_options()],
            label_visibility="collapsed",
        )

    with col3:
        department_filter = st.selectbox(
            "Department",
            options=["All"]
            + [d.replace("_", " ").title() for d in client.get_department_options()],
            label_visibility="collapsed",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Fetch and display documents
    try:
        with st.spinner("Loading documents..."):
            documents = client.get_user_documents()

        # Apply filters
        filtered_docs = documents

        if search_filter:
            filtered_docs = [
                d for d in filtered_docs if search_filter.lower() in d.title.lower()
            ]

        if classification_filter != "All":
            filtered_docs = [
                d
                for d in filtered_docs
                if d.classification.lower() == classification_filter.lower()
            ]

        if department_filter != "All":
            dept_value = department_filter.lower().replace(" ", "_")
            filtered_docs = [
                d for d in filtered_docs if d.department.lower() == dept_value
            ]

        # Stats
        st.markdown(
            f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <span style="color: #f8fafc; font-size: 1.1rem;">📁 Showing {len(filtered_docs)} of {len(documents)} documents</span>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if filtered_docs:
            # Display as grid
            cols = st.columns(2)

            for i, doc in enumerate(filtered_docs):
                with cols[i % 2]:
                    st.markdown(
                        get_document_card_html(
                            title=doc.title,
                            doc_id=doc.doc_id,
                            classification=doc.classification,
                            department=doc.department,
                            created_at=doc.created_at,
                        ),
                        unsafe_allow_html=True,
                    )

        else:
            st.markdown(
                get_alert_html("No documents match your filters.", "info"),
                unsafe_allow_html=True,
            )

    except APIError as e:
        st.markdown(
            get_alert_html(f"Failed to load documents: {e.message}", "error"),
            unsafe_allow_html=True,
        )


def render_settings_page():
    """Render the settings page."""
    st.markdown(
        get_header_html(
            "Settings", "Configure your preferences and view system information"
        ),
        unsafe_allow_html=True,
    )

    client = get_authenticated_client()
    user: UserInfo = st.session_state.user

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
        <div class="card">
            <div class="card-header">
                <span class="card-icon">👤</span>
                <h3 class="card-title">Account Information</h3>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown(f"""
        | Property | Value |
        |----------|-------|
        | **User ID** | `{user.user_id}` |
        | **Email** | {user.email} |
        | **Role** | {user.role} |
        | **Department** | {user.department} |
        """)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            """
        <div class="card">
            <div class="card-header">
                <span class="card-icon">🔗</span>
                <h3 class="card-title">API Configuration</h3>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        new_api_url = st.text_input(
            "API Base URL",
            value=st.session_state.api_url,
        )

        if new_api_url != st.session_state.api_url:
            if st.button("Update API URL"):
                st.session_state.api_url = new_api_url
                st.cache_resource.clear()
                st.success("✅ API URL updated")
                st.rerun()

    with col2:
        st.markdown(
            """
        <div class="card">
            <div class="card-header">
                <span class="card-icon">🏥</span>
                <h3 class="card-title">System Health</h3>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        try:
            health = client.readiness_check()

            st.markdown(
                f"**Overall Status:** {get_status_indicator_html(health.status, health.status.title())}",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Version:** {health.version}")
            st.markdown(f"**Environment:** {health.environment}")
            st.markdown(
                f"**Audit Logging:** {'Enabled' if health.audit_enabled else 'Disabled'}"
            )

            if health.components:
                st.markdown("<br>**Components:**", unsafe_allow_html=True)
                for name, details in health.components.items():
                    status = details.get("status", "unknown")
                    st.markdown(
                        get_status_indicator_html(status, f"{name.title()}: {status}"),
                        unsafe_allow_html=True,
                    )

        except APIError as e:
            st.error(f"Failed to fetch health status: {e.message}")

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            """
        <div class="card">
            <div class="card-header">
                <span class="card-icon">📊</span>
                <h3 class="card-title">Session Statistics</h3>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown(f"**Queries this session:** {len(st.session_state.query_history)}")
        st.markdown(f"**Session started:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🗑️ Clear Session Data", use_container_width=True):
            st.session_state.query_history = []
            st.session_state.upload_success = None
            st.success("✅ Session data cleared")


# Main Application
# ----------------


def main():
    """Main application entry point."""
    # Apply custom CSS
    st.markdown(get_custom_css(), unsafe_allow_html=True)

    # Render sidebar
    render_sidebar()

    # Route to appropriate page
    if not st.session_state.authenticated:
        render_login_page()
    else:
        page = st.session_state.current_page

        if page == "dashboard":
            render_dashboard()
        elif page == "query":
            render_query_page()
        elif page == "upload":
            render_upload_page()
        elif page == "documents":
            render_documents_page()
        elif page == "settings":
            render_settings_page()
        else:
            render_dashboard()


if __name__ == "__main__":
    main()
