"""
Sentinel RAG - Professional Streamlit Interface
Enterprise-Grade RAG with Document Management and Intelligent Search
"""

import os
import sys
import tempfile
import streamlit as st
from pathlib import Path

# Add src to path (go up one level from app folder, then into src)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sentinel_rag.config.config import get_settings
from sentinel_rag.services.database.database import DatabaseManager
from sentinel_rag.core.engine import SentinelEngine


# Page configuration
st.set_page_config(
    page_title="Sentinel RAG",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for professional styling
st.markdown(
    """
<style>
    /* Main container styling */
    .main {
        padding: 0rem 1rem;
    }
    
    /* Header styling */
    .header-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .header-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        padding: 0;
    }
    
    .header-subtitle {
        font-size: 1.1rem;
        opacity: 0.9;
        margin-top: 0.5rem;
    }
    
    /* Card styling */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
    
    /* Document card styling */
    .doc-card {
        background: #f8f9fa;
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border-left: 3px solid #667eea;
        transition: transform 0.2s;
    }
    
    .doc-card:hover {
        transform: translateX(5px);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    /* Result card styling */
    .result-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        border-left: 4px solid #48bb78;
    }
    
    /* Button styling */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 5px;
        font-weight: 600;
        transition: transform 0.2s;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background: #f8f9fa;
    }
    
    /* Success/Error message styling */
    .stSuccess, .stError, .stWarning, .stInfo {
        border-radius: 8px;
    }
    
    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 1rem 2rem;
        font-weight: 600;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def initialize_system():
    """Initialize database and engine (cached for performance)"""
    try:
        settings = get_settings()
        db = DatabaseManager(settings.database.dsn)
        engine = SentinelEngine(
            db=db,
            rbac_config=settings.rbac.as_dict,
            max_retrieved_docs=settings.doc_retrieval.max_retrieved_docs,
            similarity_threshold=settings.doc_retrieval.similarity_threshold,
            rrf_constant=settings.doc_retrieval.rrf_constant,
        )
        return settings, db, engine
    except Exception as e:
        st.error(f"⚠️ System initialization failed: {str(e)}")
        st.stop()


def render_header():
    """Render professional header"""
    st.markdown(
        """
    <div class="header-container">
        <h1 class="header-title">🛡️ Sentinel RAG</h1>
        <p class="header-subtitle">Enterprise-Grade RAG with Intelligent Document Management & Semantic Search</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_sidebar(settings):
    """Render sidebar with user selection and stats"""
    with st.sidebar:
        st.markdown("### 👤 User Profile")

        # Get all users from database
        _, db, _ = initialize_system()

        try:
            with db._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT u.user_id, u.email, u.full_name,
                               STRING_AGG(DISTINCT d.department_name, ', ') as departments,
                               STRING_AGG(DISTINCT r.role_name, ', ') as roles
                        FROM users u
                        LEFT JOIN user_access ua ON u.user_id = ua.user_id
                        LEFT JOIN departments d ON ua.department_id = d.department_id
                        LEFT JOIN roles r ON ua.role_id = r.role_id
                        GROUP BY u.user_id, u.email, u.full_name
                        ORDER BY u.email
                    """)
                    users = cur.fetchall()
        except Exception as e:
            st.error(f"Error loading users: {e}")
            users = []

        if not users:
            st.warning("No users found in the system")
            return None

        # Create user selection dropdown
        user_options = {f"{u[1]} ({u[2] or 'No name'})": u[0] for u in users}
        selected_user_display = st.selectbox(
            "Select User",
            options=list(user_options.keys()),
            help="Choose a user to perform operations",
        )

        selected_user_id = user_options[selected_user_display]

        # Display user info
        selected_user = next(u for u in users if u[0] == selected_user_id)

        st.markdown("---")
        st.markdown("**User Details:**")
        st.markdown(f"**Email:** {selected_user[1]}")
        st.markdown(f"**Name:** {selected_user[2] or 'Not set'}")
        st.markdown(f"**Departments:** {selected_user[3] or 'None'}")
        st.markdown(f"**Roles:** {selected_user[4] or 'None'}")

        st.markdown("---")
        st.markdown("### ⚙️ System Configuration")
        st.markdown(f"**Environment:** {settings.environment}")
        st.markdown(f"**Embedding:** {settings.embeddings.provider}")
        st.markdown(f"**Max Results:** {settings.doc_retrieval.max_retrieved_docs}")
        st.markdown(f"**Similarity:** {settings.doc_retrieval.similarity_threshold}")

        st.markdown("---")
        st.markdown("### 📊 Quick Stats")

        try:
            with db._get_connection() as conn:
                with conn.cursor() as cur:
                    # Total documents
                    cur.execute("SELECT COUNT(*) FROM documents")
                    total_docs = cur.fetchone()[0]

                    # Total chunks
                    cur.execute("SELECT COUNT(*) FROM chunks")
                    total_chunks = cur.fetchone()[0]

                    # User's documents
                    cur.execute(
                        "SELECT COUNT(*) FROM documents WHERE uploaded_by = %s",
                        (selected_user_id,),
                    )
                    user_docs = cur.fetchone()[0]

            st.metric("Total Documents", total_docs)
            st.metric("Total Chunks", total_chunks)
            st.metric("Your Documents", user_docs)

        except Exception as e:
            st.error(f"Error loading stats: {e}")

        return selected_user_id


def render_upload_tab(user_id: str, engine: SentinelEngine, settings):
    """Render document upload interface"""
    st.markdown("## 📤 Upload Documents")
    st.markdown(
        "Upload documents to the knowledge base with metadata and access controls."
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["pdf", "docx", "txt", "md", "html", "xlsx", "pptx"],
            help="Supported formats: PDF, DOCX, TXT, MD, HTML, XLSX, PPTX",
        )

    with col2:
        use_hierarchical = st.checkbox(
            "Use Hierarchical Chunking",
            value=False,
            help="Enable parent-document retrieval for better context",
        )

    if uploaded_file:
        st.markdown("### 📋 Document Metadata")

        col1, col2 = st.columns(2)

        with col1:
            doc_title = st.text_input(
                "Document Title*",
                value=uploaded_file.name,
                help="Descriptive title for the document",
            )

            doc_department = st.selectbox(
                "Department*",
                options=settings.rbac.departments,
                help="Department that owns this document",
            )

        with col2:
            doc_description = st.text_area(
                "Description*",
                help="Brief description of the document content",
                height=100,
            )

            doc_classification = st.selectbox(
                "Classification Level*",
                options=["public", "internal", "confidential"],
                help="Access level for this document",
            )

        st.markdown("---")

        if st.button(
            "🚀 Upload & Process Document", type="primary", use_container_width=True
        ):
            if not doc_title or not doc_description:
                st.error("❌ Please fill in all required fields (marked with *)")
                return

            with st.spinner("Processing document... This may take a moment."):
                try:
                    # Create a temporary file
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=Path(uploaded_file.name).suffix
                    ) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name

                    # Process document
                    doc_id = engine.ingest_documents(
                        source=tmp_path,
                        title=doc_title,
                        description=doc_description,
                        user_id=user_id,
                        department_id=doc_department,
                        classification=doc_classification,
                        use_hierarchical=use_hierarchical,
                    )

                    # Clean up
                    os.unlink(tmp_path)

                    st.success(
                        f"✅ Document successfully uploaded! Document ID: `{doc_id}`"
                    )
                    st.balloons()

                except Exception as e:
                    st.error(f"❌ Upload failed: {str(e)}")
                    if "tmp_path" in locals() and os.path.exists(tmp_path):
                        os.unlink(tmp_path)


def render_search_tab(user_id: str, engine: SentinelEngine):
    """Render intelligent search interface"""
    st.markdown("## 🔍 Intelligent Search")
    st.markdown(
        "Search across documents you have access to with semantic understanding."
    )

    col1, col2 = st.columns([4, 1])

    with col1:
        query = st.text_input(
            "Enter your question",
            placeholder="e.g., What are the company's remote work policies?",
            label_visibility="collapsed",
        )

    with col2:
        use_parent = st.checkbox(
            "Parent Retrieval",
            value=False,
            help="Use parent document retrieval for better context",
        )

    if st.button("🔎 Search", type="primary", use_container_width=True) or (
        query and len(query) > 3
    ):
        if not query or len(query) < 3:
            st.warning("⚠️ Please enter a query with at least 3 characters")
            return

        with st.spinner("Searching knowledge base..."):
            try:
                results = engine.query(
                    question=query, user_id=user_id, use_parent_retrieval=use_parent
                )

                if not results:
                    st.info(
                        "ℹ️ No results found. Try a different query or check your access permissions."
                    )
                    return

                st.markdown(f"### 📚 Found {len(results)} relevant results")

                for idx, doc in enumerate(results, 1):
                    with st.container():
                        st.markdown(
                            f"""
                        <div class="result-card">
                            <h4>📄 Result {idx}: {doc.metadata.get("title", "Untitled")}</h4>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

                        # Create columns for metadata and content
                        meta_col, content_col = st.columns([1, 2])

                        with meta_col:
                            st.markdown("**Metadata:**")
                            st.markdown(
                                f"- **Department:** {doc.metadata.get('department_id', 'N/A')}"
                            )
                            st.markdown(
                                f"- **Classification:** {doc.metadata.get('classification', 'N/A')}"
                            )
                            st.markdown(
                                f"- **Similarity:** {doc.metadata.get('similarity_score', 0):.2%}"
                            )

                            if "chunk_id" in doc.metadata:
                                st.markdown(
                                    f"- **Chunk ID:** `{doc.metadata['chunk_id']}`"
                                )
                            if "parent_chunk_id" in doc.metadata:
                                st.markdown(
                                    f"- **Parent ID:** `{doc.metadata['parent_chunk_id']}`"
                                )

                        with content_col:
                            st.markdown("**Content:**")
                            st.markdown(f"```\n{doc.page_content}\n```")

                        st.markdown("---")

            except Exception as e:
                st.error(f"❌ Search failed: {str(e)}")


def render_documents_tab(user_id: str, db: DatabaseManager):
    """Render document management interface"""
    st.markdown("## 📚 Document Library")
    st.markdown("View and manage your uploaded documents.")

    try:
        docs = db.get_document_uploads_by_user(user_id)

        if not docs:
            st.info(
                "ℹ️ You haven't uploaded any documents yet. Go to the Upload tab to add documents."
            )
            return

        st.markdown(f"### You have uploaded **{len(docs)}** document(s)")

        # Create search filter
        search_filter = st.text_input(
            "🔍 Filter documents", placeholder="Search by title or description..."
        )

        filtered_docs = docs
        if search_filter:
            filtered_docs = [
                d
                for d in docs
                if search_filter.lower() in d["title"].lower()
                or search_filter.lower() in (d["description"] or "").lower()
            ]

        for doc in filtered_docs:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.markdown(
                        f"""
                    <div class="doc-card">
                        <h4>📄 {doc["title"]}</h4>
                        <p style="color: #666; margin: 0.5rem 0;">{doc["description"] or "No description"}</p>
                        <small style="color: #999;">Uploaded: {doc["created_at"].strftime("%Y-%m-%d %H:%M")}</small>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                with col2:
                    st.markdown("**Department:**")
                    st.markdown(doc["department_name"])

                with col3:
                    classification_colors = {
                        "public": "🟢",
                        "internal": "🟡",
                        "confidential": "🔴",
                    }
                    st.markdown("**Classification:**")
                    st.markdown(
                        f"{classification_colors.get(doc['classification'], '⚪')} {doc['classification']}"
                    )

                # Get chunk count for this document
                with db._get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT COUNT(*) FROM chunks WHERE doc_id = %s",
                            (doc["doc_id"],),
                        )
                        chunk_count = cur.fetchone()[0]

                st.markdown(f"*Contains {chunk_count} chunks*")
                st.markdown("---")

    except Exception as e:
        st.error(f"❌ Error loading documents: {str(e)}")


def render_analytics_tab(db: DatabaseManager):
    """Render analytics dashboard"""
    st.markdown("## 📊 Analytics Dashboard")
    st.markdown("System-wide statistics and insights.")

    try:
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                # Get various statistics
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT doc_id) as total_docs,
                        COUNT(*) as total_chunks,
                        AVG(LENGTH(content)) as avg_chunk_size
                    FROM chunks
                """)
                stats = cur.fetchone()

                cur.execute("SELECT COUNT(*) FROM users")
                total_users = cur.fetchone()[0]

                cur.execute("SELECT COUNT(DISTINCT department_id) FROM documents")
                active_departments = cur.fetchone()[0]

        # Display metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("📚 Total Documents", stats[0] if stats else 0)

        with col2:
            st.metric("📝 Total Chunks", stats[1] if stats else 0)

        with col3:
            st.metric("👥 Total Users", total_users)

        with col4:
            st.metric("🏢 Active Departments", active_departments)

        st.markdown("---")

        # Document distribution by classification
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT classification, COUNT(*) as count
                    FROM documents
                    GROUP BY classification
                    ORDER BY count DESC
                """)
                classification_data = cur.fetchall()

        if classification_data:
            st.markdown("### 📊 Documents by Classification")

            col1, col2 = st.columns([2, 1])

            with col1:
                for classification, count in classification_data:
                    percentage = (
                        (count / stats[0] * 100) if stats and stats[0] > 0 else 0
                    )
                    st.progress(
                        percentage / 100,
                        f"{classification.upper()}: {count} documents ({percentage:.1f}%)",
                    )

            with col2:
                for classification, count in classification_data:
                    st.markdown(f"**{classification}:** {count}")

        # Recent uploads
        st.markdown("### 📅 Recent Uploads")
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT d.title, d.created_at, u.email, dept.department_name, d.classification
                    FROM documents d
                    JOIN users u ON d.uploaded_by = u.user_id
                    JOIN departments dept ON d.department_id = dept.department_id
                    ORDER BY d.created_at DESC
                    LIMIT 10
                """)
                recent_docs = cur.fetchall()

        if recent_docs:
            for doc in recent_docs:
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"**{doc[0]}**")
                with col2:
                    st.markdown(f"*{doc[2]}*")
                with col3:
                    st.markdown(f"_{doc[1].strftime('%Y-%m-%d %H:%M')}_")
        else:
            st.info("No recent uploads")

    except Exception as e:
        st.error(f"❌ Error loading analytics: {str(e)}")


def main():
    """Main application"""
    # Initialize system
    settings, db, engine = initialize_system()

    # Render header
    render_header()

    # Render sidebar and get selected user
    user_id = render_sidebar(settings)

    if not user_id:
        st.error("⚠️ No user selected. Please create users first.")
        return

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(
        ["🔍 Search", "📤 Upload", "📚 My Documents", "📊 Analytics"]
    )

    with tab1:
        render_search_tab(user_id, engine)

    with tab2:
        render_upload_tab(user_id, engine, settings)

    with tab3:
        render_documents_tab(user_id, db)

    with tab4:
        render_analytics_tab(db)


if __name__ == "__main__":
    main()
