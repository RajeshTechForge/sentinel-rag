"""
Sentinel RAG - Custom Styling Module

Professional CSS styling for the Streamlit application.
Designed to create a polished, enterprise-grade UI.
"""


def get_custom_css() -> str:
    """
    Returns custom CSS for the Streamlit application.

    Design Principles:
    - Clean, modern enterprise aesthetic
    - Consistent color palette with accessibility in mind
    - Smooth animations for better UX
    - Responsive layout components
    """
    return """
    <style>
        /* ================================
           ROOT VARIABLES & THEME
           ================================ */
        :root {
            --primary-color: #6366f1;
            --primary-hover: #4f46e5;
            --secondary-color: #0ea5e9;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --error-color: #ef4444;
            --background-dark: #0f172a;
            --background-card: #1e293b;
            --background-elevated: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --border-color: #334155;
            --border-radius: 12px;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
            --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
            --transition-normal: 250ms cubic-bezier(0.4, 0, 0.2, 1);
        }

        /* ================================
           GLOBAL STYLES
           ================================ */
        .stApp {
            background: linear-gradient(135deg, var(--background-dark) 0%, #1a1a2e 100%);
        }

        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* ================================
           HEADER COMPONENT
           ================================ */
        .app-header {
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            padding: 2rem 2.5rem;
            border-radius: var(--border-radius);
            margin-bottom: 2rem;
            box-shadow: var(--shadow-lg);
            position: relative;
            overflow: hidden;
        }

        .app-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
            opacity: 0.5;
        }

        .app-header h1 {
            color: white;
            font-size: 2.5rem;
            font-weight: 700;
            margin: 0;
            position: relative;
            z-index: 1;
        }

        .app-header p {
            color: rgba(255, 255, 255, 0.9);
            font-size: 1.1rem;
            margin: 0.5rem 0 0 0;
            position: relative;
            z-index: 1;
        }

        /* ================================
           CARD COMPONENTS
           ================================ */
        .card {
            background: var(--background-card);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            padding: 1.5rem;
            margin-bottom: 1rem;
            transition: all var(--transition-normal);
            box-shadow: var(--shadow-md);
        }

        .card:hover {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 1px var(--primary-color), var(--shadow-lg);
            transform: translateY(-2px);
        }

        .card-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
        }

        .card-title {
            color: var(--text-primary);
            font-size: 1.25rem;
            font-weight: 600;
            margin: 0;
        }

        .card-icon {
            font-size: 1.5rem;
        }

        /* ================================
           METRIC CARDS
           ================================ */
        .metric-card {
            background: linear-gradient(135deg, var(--background-card) 0%, var(--background-elevated) 100%);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            padding: 1.5rem;
            text-align: center;
            transition: all var(--transition-normal);
        }

        .metric-card:hover {
            transform: scale(1.02);
            box-shadow: var(--shadow-lg);
        }

        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .metric-label {
            color: var(--text-secondary);
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 0.5rem;
        }

        /* ================================
           USER PROFILE CARD
           ================================ */
        .user-profile-card {
            background: linear-gradient(135deg, var(--background-card) 0%, rgba(99, 102, 241, 0.1) 100%);
            border: 1px solid var(--primary-color);
            border-radius: var(--border-radius);
            padding: 2rem;
            margin-bottom: 1.5rem;
        }

        .user-avatar {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            color: white;
            margin: 0 auto 1rem;
            box-shadow: var(--shadow-lg);
        }

        .user-info {
            text-align: center;
        }

        .user-name {
            color: var(--text-primary);
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }

        .user-email {
            color: var(--text-secondary);
            font-size: 0.95rem;
        }

        .user-badges {
            display: flex;
            justify-content: center;
            gap: 0.75rem;
            margin-top: 1rem;
        }

        /* ================================
           BADGES & TAGS
           ================================ */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 0.375rem;
            padding: 0.375rem 0.875rem;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.025em;
        }

        .badge-primary {
            background: rgba(99, 102, 241, 0.15);
            color: var(--primary-color);
            border: 1px solid rgba(99, 102, 241, 0.3);
        }

        .badge-success {
            background: rgba(16, 185, 129, 0.15);
            color: var(--success-color);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .badge-warning {
            background: rgba(245, 158, 11, 0.15);
            color: var(--warning-color);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }

        .badge-error {
            background: rgba(239, 68, 68, 0.15);
            color: var(--error-color);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .badge-info {
            background: rgba(14, 165, 233, 0.15);
            color: var(--secondary-color);
            border: 1px solid rgba(14, 165, 233, 0.3);
        }

        /* Classification badges */
        .classification-public {
            background: rgba(16, 185, 129, 0.15);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .classification-internal {
            background: rgba(14, 165, 233, 0.15);
            color: #0ea5e9;
            border: 1px solid rgba(14, 165, 233, 0.3);
        }

        .classification-confidential {
            background: rgba(245, 158, 11, 0.15);
            color: #f59e0b;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }

        .classification-restricted {
            background: rgba(239, 68, 68, 0.15);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        /* ================================
           DOCUMENT CARDS
           ================================ */
        .document-card {
            background: var(--background-card);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            padding: 1.25rem 1.5rem;
            margin-bottom: 0.75rem;
            transition: all var(--transition-normal);
            display: flex;
            align-items: flex-start;
            gap: 1rem;
        }

        .document-card:hover {
            border-color: var(--primary-color);
            background: var(--background-elevated);
        }

        .document-icon {
            font-size: 2rem;
            flex-shrink: 0;
        }

        .document-details {
            flex-grow: 1;
            min-width: 0;
        }

        .document-title {
            color: var(--text-primary);
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .document-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin-top: 0.5rem;
        }

        .document-meta-item {
            display: flex;
            align-items: center;
            gap: 0.25rem;
            color: var(--text-muted);
            font-size: 0.85rem;
        }

        /* ================================
           QUERY RESULTS
           ================================ */
        .result-card {
            background: var(--background-card);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            padding: 1.5rem;
            margin-bottom: 1rem;
            position: relative;
            overflow: hidden;
        }

        .result-card::before {
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 4px;
            background: linear-gradient(180deg, var(--primary-color) 0%, var(--secondary-color) 100%);
        }

        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }

        .result-content {
            color: var(--text-primary);
            line-height: 1.7;
            font-size: 0.95rem;
        }

        .result-content mark {
            background: rgba(99, 102, 241, 0.3);
            color: var(--text-primary);
            padding: 0.125rem 0.25rem;
            border-radius: 4px;
        }

        .result-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border-color);
        }

        /* ================================
           STATUS INDICATORS
           ================================ */
        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }

        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        .status-dot.healthy {
            background: var(--success-color);
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
        }

        .status-dot.warning {
            background: var(--warning-color);
            box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.2);
        }

        .status-dot.error {
            background: var(--error-color);
            box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.2);
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }

        /* ================================
           UPLOAD SECTION
           ================================ */
        .upload-zone {
            border: 2px dashed var(--border-color);
            border-radius: var(--border-radius);
            padding: 3rem 2rem;
            text-align: center;
            transition: all var(--transition-normal);
            background: rgba(99, 102, 241, 0.02);
        }

        .upload-zone:hover {
            border-color: var(--primary-color);
            background: rgba(99, 102, 241, 0.05);
        }

        .upload-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }

        .upload-text {
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
        }

        .upload-hint {
            color: var(--text-muted);
            font-size: 0.85rem;
        }

        /* ================================
           FORM ELEMENTS
           ================================ */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div > div {
            background: var(--background-elevated) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 8px !important;
            color: var(--text-primary) !important;
        }

        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {
            border-color: var(--primary-color) !important;
            box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
        }

        /* ================================
           BUTTONS
           ================================ */
        .stButton > button {
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-hover) 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.625rem 1.5rem !important;
            font-weight: 600 !important;
            transition: all var(--transition-fast) !important;
            box-shadow: var(--shadow-md) !important;
        }

        .stButton > button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 8px 25px -5px rgba(99, 102, 241, 0.4) !important;
        }

        .stButton > button:active {
            transform: translateY(0) !important;
        }

        /* Secondary button style */
        .secondary-btn > button {
            background: transparent !important;
            border: 1px solid var(--border-color) !important;
            color: var(--text-primary) !important;
        }

        .secondary-btn > button:hover {
            border-color: var(--primary-color) !important;
            background: rgba(99, 102, 241, 0.1) !important;
        }

        /* ================================
           SIDEBAR
           ================================ */
        .css-1d391kg, [data-testid="stSidebar"] {
            background: var(--background-card) !important;
            border-right: 1px solid var(--border-color) !important;
        }

        .sidebar-header {
            padding: 1.5rem;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 1rem;
        }

        .sidebar-logo {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .sidebar-nav-item {
            padding: 0.75rem 1rem;
            border-radius: 8px;
            color: var(--text-secondary);
            transition: all var(--transition-fast);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .sidebar-nav-item:hover {
            background: var(--background-elevated);
            color: var(--text-primary);
        }

        .sidebar-nav-item.active {
            background: rgba(99, 102, 241, 0.15);
            color: var(--primary-color);
        }

        /* ================================
           TABS
           ================================ */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            background: var(--background-card);
            padding: 0.5rem;
            border-radius: var(--border-radius);
            border: 1px solid var(--border-color);
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            color: var(--text-secondary);
            padding: 0.75rem 1.5rem;
            font-weight: 500;
        }

        .stTabs [aria-selected="true"] {
            background: var(--primary-color) !important;
            color: white !important;
        }

        /* ================================
           EXPANDERS
           ================================ */
        .streamlit-expanderHeader {
            background: var(--background-card) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: var(--border-radius) !important;
            color: var(--text-primary) !important;
        }

        .streamlit-expanderContent {
            background: var(--background-card) !important;
            border: 1px solid var(--border-color) !important;
            border-top: none !important;
            border-radius: 0 0 var(--border-radius) var(--border-radius) !important;
        }

        /* ================================
           ALERT COMPONENTS
           ================================ */
        .alert {
            padding: 1rem 1.25rem;
            border-radius: var(--border-radius);
            margin-bottom: 1rem;
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
        }

        .alert-success {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: var(--success-color);
        }

        .alert-warning {
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.3);
            color: var(--warning-color);
        }

        .alert-error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: var(--error-color);
        }

        .alert-info {
            background: rgba(14, 165, 233, 0.1);
            border: 1px solid rgba(14, 165, 233, 0.3);
            color: var(--secondary-color);
        }

        /* ================================
           LOADING STATES
           ================================ */
        .skeleton {
            background: linear-gradient(
                90deg,
                var(--background-card) 0%,
                var(--background-elevated) 50%,
                var(--background-card) 100%
            );
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
            border-radius: 8px;
        }

        @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }

        /* ================================
           SCROLLBAR
           ================================ */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: var(--background-dark);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--text-muted);
        }

        /* ================================
           UTILITIES
           ================================ */
        .text-center { text-align: center; }
        .text-muted { color: var(--text-muted); }
        .text-secondary { color: var(--text-secondary); }
        .text-primary-color { color: var(--primary-color); }
        .font-semibold { font-weight: 600; }
        .mt-1 { margin-top: 0.25rem; }
        .mt-2 { margin-top: 0.5rem; }
        .mt-3 { margin-top: 1rem; }
        .mt-4 { margin-top: 1.5rem; }
        .mb-1 { margin-bottom: 0.25rem; }
        .mb-2 { margin-bottom: 0.5rem; }
        .mb-3 { margin-bottom: 1rem; }
        .mb-4 { margin-bottom: 1.5rem; }

        /* ================================
           RESPONSIVE
           ================================ */
        @media (max-width: 768px) {
            .app-header h1 {
                font-size: 1.75rem;
            }
            .metric-value {
                font-size: 1.75rem;
            }
        }
    </style>
    """


def get_header_html(
    title: str = "Sentinel RAG",
    subtitle: str = "Enterprise Document Intelligence Platform",
) -> str:
    """Generate the app header HTML."""
    return f"""
    <div class="app-header">
        <h1>🛡️ {title}</h1>
        <p>{subtitle}</p>
    </div>
    """


def get_user_profile_html(email: str, role: str, department: str) -> str:
    """Generate user profile card HTML."""
    initials = "".join([part[0].upper() for part in email.split("@")[0].split(".")[:2]])
    return f"""
    <div class="user-profile-card">
        <div class="user-avatar">{initials}</div>
        <div class="user-info">
            <div class="user-name">{email.split("@")[0].replace(".", " ").title()}</div>
            <div class="user-email">{email}</div>
            <div class="user-badges">
                <span class="badge badge-primary">🎯 {role}</span>
                <span class="badge badge-info">🏢 {department}</span>
            </div>
        </div>
    </div>
    """


def get_metric_card_html(value: str, label: str, icon: str = "📊") -> str:
    """Generate a metric card HTML."""
    return f"""
    <div class="metric-card">
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">{icon}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """


def get_document_card_html(
    title: str,
    doc_id: str,
    classification: str,
    department: str,
    created_at: str = None,
) -> str:
    """Generate a document card HTML."""
    # Map classification to CSS class
    classification_class = f"classification-{classification.lower()}"

    # Icon based on classification
    icons = {"public": "📄", "internal": "📋", "confidential": "🔒", "restricted": "🛡️"}
    icon = icons.get(classification.lower(), "📄")

    date_html = (
        f'<span class="document-meta-item">📅 {created_at}</span>' if created_at else ""
    )

    return f"""
    <div class="document-card">
        <div class="document-icon">{icon}</div>
        <div class="document-details">
            <div class="document-title">{title}</div>
            <div class="document-meta">
                <span class="badge {classification_class}">{classification}</span>
                <span class="document-meta-item">🏢 {department}</span>
                {date_html}
            </div>
            <div class="document-meta-item mt-2" style="font-size: 0.75rem;">ID: {doc_id[:16]}...</div>
        </div>
    </div>
    """


def get_result_card_html(
    content: str,
    doc_title: str = None,
    classification: str = None,
    score: float = None,
    chunk_id: str = None,
) -> str:
    """Generate a query result card HTML."""
    classification_class = (
        f"classification-{classification.lower()}" if classification else "badge-info"
    )

    header_html = ""
    if doc_title:
        header_html = f"""
        <div class="result-header">
            <div>
                <div style="color: var(--text-primary); font-weight: 600;">{doc_title}</div>
                {f'<span class="badge {classification_class}" style="margin-top: 0.5rem;">{classification}</span>' if classification else ""}
            </div>
            {f'<div class="badge badge-success">Score: {score:.2f}</div>' if score else ""}
        </div>
        """

    return f"""
    <div class="result-card">
        {header_html}
        <div class="result-content">{content}</div>
        {f'<div class="result-footer"><span class="text-muted" style="font-size: 0.75rem;">Chunk: {chunk_id}</span></div>' if chunk_id else ""}
    </div>
    """


def get_status_indicator_html(status: str, label: str) -> str:
    """Generate a status indicator HTML."""
    status_class = (
        "healthy"
        if status == "healthy"
        else ("warning" if status == "degraded" else "error")
    )
    return f"""
    <div class="status-indicator">
        <span class="status-dot {status_class}"></span>
        <span style="color: var(--text-primary);">{label}</span>
    </div>
    """


def get_alert_html(message: str, alert_type: str = "info", icon: str = None) -> str:
    """Generate an alert HTML."""
    icons = {"success": "✅", "warning": "⚠️", "error": "❌", "info": "ℹ️"}
    icon = icon or icons.get(alert_type, "ℹ️")
    return f"""
    <div class="alert alert-{alert_type}">
        <span>{icon}</span>
        <span>{message}</span>
    </div>
    """
