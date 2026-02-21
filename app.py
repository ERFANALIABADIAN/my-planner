"""
My Planner - A clean, minimal task & time management app.
Run with: streamlit run app.py
"""

import streamlit as st
from database import init_db
from auth import is_authenticated, render_login_page, logout_user
from pages_tasks import render_tasks_page
from pages_timer import render_timer_page
from pages_analytics import render_analytics_page

# ─── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="My Planner",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Initialize Database ─────────────────────────────────────
init_db()

# ─── Custom Styling ──────────────────────────────────────────
st.markdown("""
<style>
    /* Clean, minimal look */
    .stApp {
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }

    /* Hide Streamlit branding but keep sidebar toggle */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {
        visibility: visible !important;
        background: transparent !important;
        height: auto !important;
    }

    /* Hide Streamlit decoration/toolbar, but DO NOT hide the sidebar toggle */
    [data-testid="stDecoration"],
    [data-testid="stToolbar"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }

    /* Sidebar collapse/expand toggle: handle multiple Streamlit versions */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    header[data-testid="stHeader"] button[aria-label*="sidebar" i],
    button[aria-label*="Open sidebar" i],
    button[aria-label*="Close sidebar" i] {
        visibility: visible !important;
        display: flex !important;
        opacity: 1 !important;
        position: fixed !important;
        top: 0.5rem !important;
        left: 0.5rem !important;
        z-index: 999999 !important;
        background: white !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
        padding: 0.5rem !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        pointer-events: all !important;
        touch-action: manipulation !important;
    }
    
    [data-testid="collapsedControl"]:hover,
    [data-testid="stSidebarCollapsedControl"]:hover,
    header[data-testid="stHeader"] button[aria-label*="sidebar" i]:hover,
    button[aria-label*="Open sidebar" i]:hover,
    button[aria-label*="Close sidebar" i]:hover {
        background: #F3F4F6 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
        transform: scale(1.05) !important;
    }

    /* Always keep toggle in top-left (don’t move it into the sidebar) */
    section[data-testid="stSidebar"] [data-testid="collapsedControl"] {
        position: fixed !important;
        top: 0.5rem !important;
        left: 0.5rem !important;
        right: auto !important;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #F8F9FA !important;
        border-right: 1px solid #E5E7EB !important;
    }
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #374151;
        font-size: 1rem;
        font-weight: 600;
        margin-top: 1rem;
    }

    /* Card-like containers */
    [data-testid="stExpander"] {
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }

    /* Clean buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 16px;
        font-weight: 500;
    }

    /* Metric styling */
    [data-testid="stMetric"] {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid #E5E7EB;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        color: #6B7280 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #1E1E2E !important;
    }

    /* Forms */
    [data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
    }

    /* Progress bars */
    .stProgress > div > div > div {
        border-radius: 999px;
    }

    /* Navigation buttons */
    .nav-container {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }

    /* Dividers */
    hr {
        border: none;
        border-top: 1px solid #F0F0F0;
        margin: 0.5rem 0;
    }

    /* Mobile responsive */
    @media (max-width: 768px) {
        .stColumns {
            flex-direction: column;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.2rem !important;
        }
    }

    /* Smooth scrolling */
    html {
        scroll-behavior: smooth;
    }

    /* Input styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 8px;
        border: 1px solid #E5E7EB;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #4A90D9;
        box-shadow: 0 0 0 2px rgba(74, 144, 217, 0.15);
    }
</style>
""", unsafe_allow_html=True)

# ─── Authentication Gate ──────────────────────────────────────
if not is_authenticated():
    render_login_page()
    st.stop()

# ─── Main App (Authenticated) ────────────────────────────────

# Sidebar navigation
with st.sidebar:
    st.markdown(
        f"""<div style='padding: 0.5rem 0; margin-bottom: 1rem;'>
            <div style='font-size: 1.3rem; font-weight: 700; color: #1E1E2E;'>
                📋 My Planner
            </div>
            <div style='font-size: 0.85rem; color: #6B7280;'>
                Welcome, {st.session_state.get('display_name', 'User')}
            </div>
        </div>""",
        unsafe_allow_html=True
    )

    # Navigation
    nav_options = {
        "📋 Tasks": "tasks",
        "⏱ Timer": "timer",
        "📊 Analytics": "analytics"
    }

    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 'tasks'

    for label, page_key in nav_options.items():
        btn_type = "primary" if st.session_state['current_page'] == page_key else "secondary"
        if st.button(label, key=f"nav_{page_key}", use_container_width=True, type=btn_type):
            st.session_state['current_page'] = page_key

    st.markdown("---")

    # Logout
    if st.button("🚪 Logout", use_container_width=True):
        logout_user()


# ─── Page Router ──────────────────────────────────────────────
current_page = st.session_state.get('current_page', 'tasks')

if current_page == 'tasks':
    render_tasks_page()
elif current_page == 'timer':
    render_timer_page()
elif current_page == 'analytics':
    render_analytics_page()
