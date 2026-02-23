"""
My Planner - A clean, minimal task & time management app.
Run with: streamlit run app.py
"""

import streamlit as st
from database import init_db, update_user_theme
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

# ─── Theme Initialization ────────────────────────────────────
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'light'

_dark = (st.session_state['theme'] == 'dark')

# Color tokens per theme
if _dark:
    _bg = "#0F1117"; _surface = "#1E2130"; _surface2 = "#252840"
    _border = "#2D3150"; _text = "#E5E7EB"; _muted = "#9CA3AF"
    _head = "#FFFFFF"; _accent = "#4F8EF7"; _sidebar = "#151722"
    _input = "#1E2130"
else:
    _bg = "#F5F7FA"; _surface = "#FFFFFF"; _surface2 = "#F9FAFB"
    _border = "#E5E7EB"; _text = "#374151"; _muted = "#6B7280"
    _head = "#1E1E2E"; _accent = "#4A90D9"; _sidebar = "#F8F9FA"
    _input = "#FFFFFF"

# ─── Custom Styling ──────────────────────────────────────────
st.markdown(f"""
<style>
    /* Clean, minimal look */
    .stApp {{
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        background-color: {_bg} !important;
        transition: background-color 0.3s ease, color 0.3s ease;
    }}
    .main .block-container {{ background-color: {_bg} !important; padding-top:1.5rem; }}
    h1,h2,h3,h4,h5,h6 {{ color: {_head} !important; }}
    .stMarkdown p, .stMarkdown span {{ color: {_text}; }}

    /* Hide Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    /* Sidebar toggle */
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="collapsedControl"] svg {{
        width: 1.5rem !important; height: 1.5rem !important;
        color: {_muted} !important; transition: all 0.2s ease;
    }}
    [data-testid="stSidebarCollapseButton"]:hover svg,
    [data-testid="collapsedControl"]:hover svg {{
        color: {_accent} !important; transform: scale(1.1);
    }}
    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: {_sidebar} !important;
        border-right: 1px solid {_border} !important;
    }}
    [data-testid="stSidebar"] * {{ color: {_text} !important; }}
    [data-testid="stSidebar"] .stMarkdown h3 {{
        color: {_head} !important; font-size:1rem; font-weight:600; margin-top:1rem;
    }}

    /* Card-like containers */
    [data-testid="stExpander"] {{
        background-color: {_surface} !important;
        border: 1px solid {_border} !important;
        border-radius: 12px; margin-bottom: 0.5rem; color: {_text} !important;
    }}
    [data-testid="stExpander"] summary {{
        color: {_head} !important;
        background-color: {_surface} !important;
        border-radius: 12px;
        padding: 0.6rem 1rem !important;
    }}
    [data-testid="stExpander"] details {{ background-color: {_surface} !important; }}
    [data-testid="stExpander"] details[open] > summary {{ border-radius: 12px 12px 0 0 !important; }}
    [data-testid="stExpander"] > div:first-child {{ background-color: {_surface} !important; }}
    /* Expander inner content area */
    [data-testid="stExpander"] details > div {{
        background-color: {_surface} !important;
        border-radius: 0 0 12px 12px;
    }}
    
    /* Expander arrow icon */
    [data-testid="stExpander"] summary svg {{
        fill: {_text} !important; color: {_text} !important;
    }}
    /* Radio buttons & Checkboxes - all possible selectors */
    .stRadio label,
    .stRadio span,
    .stRadio p,
    .stRadio div[role="radiogroup"] label,
    .stRadio > label,
    .stCheckbox label,
    .stCheckbox span,
    [data-testid="stRadio"] label,
    [data-testid="stRadio"] span,
    [data-testid="stRadio"] p,
    [role="radio"] + span,
    [role="radiogroup"] label {{
        color: {_text} !important;
        opacity: 1 !important;
    }}
    /* Fix the radio button circle border so it's visible */
    [data-testid="stRadio"] input[type="radio"] + div,
    [data-testid="stRadio"] input[type="radio"] ~ div {{
        border-color: {_text} !important;
    }}
    /* All SVG icons: arrows, chevrons, dropdowns, selects */
    svg {{ fill: {_text} !important; color: {_text} !important; }}
    /* Selectbox dropdown text and arrow */
    [data-baseweb="select"] > div {{
        background-color: {_input} !important;
        border-color: {_border} !important;
        color: {_text} !important;
    }}
    [data-baseweb="select"] [data-testid="stMarkdownContainer"],
    [data-baseweb="select"] span, [data-baseweb="select"] div {{
        color: {_text} !important;
    }}
    [data-baseweb="select"] svg path {{
        fill: {_text} !important;
    }}
    /* Selectbox popup/menu */
    [data-baseweb="popover"] ul {{
        background-color: {_surface} !important;
        border-color: {_border} !important;
    }}
    [data-baseweb="popover"] li {{
        background-color: {_surface} !important;
        color: {_text} !important;
    }}
    [data-baseweb="popover"] li:hover {{
        background-color: {_surface2} !important;
    }}
    /* Buttons */
    .stButton > button {{
        border-radius: 8px; font-weight: 500; transition: all 0.2s ease;
    }}
    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,{'0.3' if _dark else '0.1'});
    }}
    /* Tertiary = icon-only, borderless */
    .stButton > button[kind="tertiary"] {{
        background: transparent !important; border: none !important;
        box-shadow: none !important; padding: 0.2rem 0.4rem !important;
        color: {_muted} !important; font-size: 1.1rem !important;
    }}
    .stButton > button[kind="tertiary"]:hover {{
        color: #EF4444 !important; transform: scale(1.2) !important; box-shadow: none !important;
    }}
    /* Secondary */
    .stButton > button[kind="secondary"] {{
        background-color: {_surface2} !important;
        border: 1px solid {_border} !important;
        color: {_text} !important;
    }}
    /* Sidebar secondary buttons – override Streamlit's sidebar default white */
    section[data-testid="stSidebar"] button[kind="secondary"],
    section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {{
        background-color: {_surface2} !important;
        background: {_surface2} !important;
        border: 1px solid {_border} !important;
        color: {_text} !important;
        box-shadow: none !important;
    }}
    section[data-testid="stSidebar"] button[kind="secondary"] p,
    section[data-testid="stSidebar"] .stButton > button[kind="secondary"] p {{
        color: {_text} !important;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px; background: transparent !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px 8px 0 0; padding: 8px 16px;
        font-weight: 500; color: {_muted} !important;
        background: {_surface2} !important;
    }}
    .stTabs [aria-selected="true"] {{
        color: {_accent} !important;
        background: {_surface} !important;
        border-bottom: 2px solid {_accent} !important;
    }}

    /* Metrics */
    [data-testid="stMetric"] {{
        background: {_surface} !important; padding: 1rem;
        border-radius: 12px; border: 1px solid {_border};
    }}
    [data-testid="stMetricLabel"] {{ font-size: 0.8rem !important; color: {_muted} !important; }}
    [data-testid="stMetricValue"] {{ font-size: 1.5rem !important; font-weight: 700 !important; color: {_head} !important; }}

    /* Forms */
    [data-testid="stForm"] {{
        border: none !important; padding: 0 !important;
        background: transparent !important;
    }}

    /* Progress bars */
    .stProgress > div > div > div {{
        border-radius: 999px;
    }}

    /* Dividers */
    hr {{ border: none; border-top: 1px solid {_border}; margin: 0.5rem 0; }}

    /* Mobile responsive */
    @media (max-width: 768px) {{
        .stColumns {{
            flex-direction: column;
        }}
        [data-testid="stMetricValue"] {{
            font-size: 1.2rem !important;
        }}
    }}

    /* Smooth scrolling */
    html {{
        scroll-behavior: smooth;
    }}

    /* Inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {{
        background-color: {_input} !important; color: {_text} !important;
        border: 1px solid {_border} !important; border-radius: 8px;
        caret-color: {_text} !important;
    }}
    /* Number input wrapper container (baseweb) */
    .stNumberInput [data-baseweb="input"],
    .stNumberInput [data-baseweb="base-input"],
    div[data-testid="stNumberInput"] > div,
    div[data-testid="stNumberInput"] > div > div {{
        background-color: {_input} !important;
        border-color: {_border} !important;
    }}
    div[data-testid="stNumberInput"] input {{
        background-color: {_input} !important;
        color: {_text} !important;
    }}
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {{
        color: {_muted} !important;
    }}
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: {_accent} !important;
        box-shadow: 0 0 0 2px {_accent}33 !important;
    }}
    /* Number input +/- buttons */
    .stNumberInput button {{ color: {_text} !important; background: {_input} !important; border-color: {_border} !important; }}
    /* All form field labels (text input, number input, selectbox, etc.) */
    .stTextInput label, .stTextArea label, .stNumberInput label,
    .stSelectbox label, .stDateInput label, .stColorPicker label,
    div[data-testid="stNumberInput"] label,
    div[data-testid="stTextInput"] label,
    div[data-testid="stSelectbox"] label,
    div[data-testid="column"] label,
    .stForm label,
    label[data-testid="stWidgetLabel"] p,
    label[data-testid="stWidgetLabel"] {{
        color: {_text} !important;
    }}
    /* Date input - all layers */
    .stDateInput > div > div > input,
    div[data-testid="stDateInput"] input {{
        background-color: {_input} !important; color: {_text} !important; border-color: {_border} !important;
    }}
    div[data-testid="stDateInput"] > div,
    div[data-testid="stDateInput"] [data-baseweb="input"],
    div[data-testid="stDateInput"] [data-baseweb="base-input"] {{
        background-color: {_input} !important;
        border-color: {_border} !important;
    }}
    /* Universal baseweb input fix for all fields in dark mode */
    [data-baseweb="input"],
    [data-baseweb="base-input"],
    [data-baseweb="textarea"] {{
        background-color: {_input} !important;
        border-color: {_border} !important;
        color: {_text} !important;
    }}
    [data-baseweb="input"] input,
    [data-baseweb="base-input"] input,
    [data-baseweb="input"] textarea {{
        background-color: {_input} !important;
        color: {_text} !important;
    }}
    [data-baseweb="input"] input::placeholder,
    [data-baseweb="textarea"] textarea::placeholder {{
        color: {_muted} !important;
    }}
    
    /* ── Icon Picker Popover Button ───────────────────────────────────── */
    /* Target both global and sidebar contexts, all override levels */
    [data-testid="stPopover"] button,
    [data-testid="stSidebar"] [data-testid="stPopover"] button,
    [data-testid="stPopover"] button[kind="secondary"] {{
        background-color: {_input} !important;
        color: {_text} !important;
        border: 1px solid {_border} !important;
        border-radius: 8px !important;
        width: 2.8rem !important;
        min-width: 2.8rem !important;
        max-width: 2.8rem !important;
        height: 2.8rem !important;
        min-height: 2.8rem !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 1.4rem !important;
        overflow: hidden !important;
        gap: 0 !important;
    }}
    /* Completely kill the chevron arrow SVG */
    [data-testid="stPopover"] button svg,
    [data-testid="stSidebar"] [data-testid="stPopover"] button svg {{
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        position: absolute !important;
        overflow: hidden !important;
    }}
    /* Hover */
    [data-testid="stPopover"] button:hover,
    [data-testid="stSidebar"] [data-testid="stPopover"] button:hover {{
        border-color: {_accent} !important;
        box-shadow: 0 0 0 2px {_accent}33 !important;
        background-color: {_input} !important;
    }}

    /* 2. The popover container (content window) - multiple layers needed */
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] > div,
    div[data-baseweb="popover"] > div > div,    
    .stPopover > div,
    div[role="dialog"] {{
        background-color: {_surface} !important;
        color: {_text} !important;
        border-color: {_border} !important;
    }}

    /* 3. The icon buttons grid inside the popover */
    [data-baseweb="popover"] button {{
        background-color: {_surface2} !important;
        color: {_text} !important; 
        border: 1px solid {_border} !important;
        margin: 2px !important;
        transition: transform 0.1s;
    }}
    [data-baseweb="popover"] button:hover {{
        border-color: {_accent} !important;
        transform: scale(1.1);
        z-index: 10;
        background-color: {_input} !important;
        color: {_accent} !important;
    }}
    [data-baseweb="popover"] [data-testid="stMarkdownContainer"] p,
    [data-baseweb="popover"] h1, [data-baseweb="popover"] h2, [data-baseweb="popover"] h3 {{
        color: {_text} !important;
    }}

    /* Mobile */
    @media (max-width: 768px) {{
        [data-testid="stMetricValue"] {{ font-size: 1.2rem !important; }}
    }}
    html {{ scroll-behavior: smooth; }}
    /* Scrollbar dark */
    {'* { scrollbar-color: #3D4160 #1E2130; }' if _dark else ''}
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
        f"""<div style='padding:0.5rem 0; margin-bottom:0.75rem;'>
            <div style='font-size:1.3rem; font-weight:700; color:{_head};'>
                📋 My Planner
            </div>
            <div style='font-size:0.85rem; color:{_muted};'>
                Welcome, {st.session_state.get('display_name', 'User')}
            </div>
        </div>""",
        unsafe_allow_html=True
    )

    # ── Dark / Light toggle
    _toggle_label = "☀️ Light Mode" if _dark else "🌙 Dark Mode"
    if st.button(_toggle_label, use_container_width=True, type="secondary", key="theme_toggle"):
        new_theme = 'light' if _dark else 'dark'
        st.session_state['theme'] = new_theme
        if is_authenticated():
            update_user_theme(st.session_state['user_id'], new_theme)
        st.rerun()

    st.markdown("---")

    # Navigation
    nav_options = {
        "📋 Tasks": "tasks",
        "⏱ Timer": "timer",
        "📊 Analytics": "analytics"
    }

    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 'tasks'

    for label, page_key in nav_options.items():
        btn_type = "primary" if st.session_state.get('current_page', 'tasks') == page_key else "secondary"
        if st.button(label, key=f"nav_{page_key}", use_container_width=True, type=btn_type):
            st.session_state['current_page'] = page_key
            st.rerun()

    # Smaller separator before content
    st.write("")


# ─── Page Router ──────────────────────────────────────────────
current_page = st.session_state.get('current_page', 'tasks')

if current_page == 'tasks':
    render_tasks_page()
elif current_page == 'timer':
    render_timer_page()
elif current_page == 'analytics':
    render_analytics_page()

# ─── Sidebar Footer (Refresh / Logout) ───────────────────────
with st.sidebar:
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    st.markdown("---")

    col_refresh, col_logout = st.sidebar.columns(2)
    with col_refresh:
        if st.button("🔄 Refresh", use_container_width=True, type="secondary", help="Reload data"):
            st.rerun()
    with col_logout:
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            logout_user()
            st.rerun()
