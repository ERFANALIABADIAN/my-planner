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

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {
        visibility: hidden !important;
        height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* HIDE sidebar collapse/expand buttons completely - sidebar stays fixed */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    button[kind="header"] {
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }
    
    /* Force sidebar to always stay open */
    [data-testid="stSidebar"] {
        position: relative !important;
        transform: none !important;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #F8F9FA;
        border-right: 1px solid #E5E7EB;
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
            st.rerun()

    st.markdown("---")

    # Logout
    if st.button("🚪 Logout", use_container_width=True):
        logout_user()
        st.rerun()

# ─── Page Router ──────────────────────────────────────────────
current_page = st.session_state.get('current_page', 'tasks')

if current_page == 'tasks':
    render_tasks_page()
elif current_page == 'timer':
    render_timer_page()
elif current_page == 'analytics':
    render_analytics_page()
