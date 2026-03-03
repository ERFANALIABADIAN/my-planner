"""
My Planner - A clean, minimal task & time management app.
Run with: streamlit run app.py
"""

import streamlit as st
from database import init_db, update_user_theme
from auth import is_authenticated, render_login_page, logout_user
from pages_tasks import render_tasks_page, render_sidebar
from pages_timer import render_timer_page
from pages_analytics import render_analytics_page

# ─── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="My Planner",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Initialize Database (cached – runs once per server lifetime) ─
init_db()


# ─── Cached CSS Generator ────────────────────────────────────
# The ~500-line CSS block is expensive to re-inject on every rerun.
# By caching it keyed on theme, it's only rebuilt when the theme changes.
@st.cache_data(show_spinner=False)
def _build_theme_css(theme: str) -> str:
    """Return the full app CSS string for the given theme. Cached so it's
    only computed once per theme value instead of on every Streamlit rerun."""
    _dark = (theme == 'dark')
    if _dark:
        _bg = "#0F1117"; _surface = "#1E2130"; _surface2 = "#252840"
        _border = "#2D3150"; _text = "#374151"; _muted = "#9CA3AF"  # noqa: redefine ok
        _text = "#E5E7EB"; _head = "#FFFFFF"; _accent = "#4F8EF7"
        _sidebar = "#0F1117"; _input = "#1E2130"
    else:
        _bg = "#F5F7FA"; _surface = "#FFFFFF"; _surface2 = "#F9FAFB"
        _border = "#E5E7EB"; _text = "#374151"; _muted = "#6B7280"
        _head = "#1E1E2E"; _accent = "#4A90D9"; _sidebar = "#F8F9FA"
        _input = "#FFFFFF"

    return f"""<style>
    /* ── Override Streamlit CSS custom properties for theme ── */
    :root, .stApp {{
        --background-color: {_bg};
        --secondary-background-color: {_surface};
        --text-color: {_text};
        --font: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }}
    /* ── Global background fix: eliminate ALL white backgrounds ── */
    .stApp {{
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        background-color: {_bg} !important;
        color: {_text} !important;
        transition: background-color 0.3s ease, color 0.3s ease;
    }}
    .main .block-container {{ background-color: {_bg} !important; padding-top:0.4rem; }}
    /* Nuclear: force every structural Streamlit container to match theme */
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > div,
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"],
    [data-testid="stVerticalBlock"],
    [data-testid="stHorizontalBlock"],
    [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stColumn"],
    [data-testid="column"],
    section.main,
    section.main > div,
    section.main > div > div {{
        background-color: {_bg} !important;
        background: {_bg} !important;
    }}
    /* Header / toolbar - often white by default */
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    .stApp > header,
    header[data-testid="stHeader"] {{
        background-color: {_bg} !important;
        background: {_bg} !important;
    }}
    /* Bottom container */
    [data-testid="stBottom"],
    [data-testid="stBottom"] > div {{
        background-color: {_bg} !important;
        background: {_bg} !important;
    }}
    /* Sidebar structural containers */
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarUserContent"],
    [data-testid="stSidebarContent"] > div {{
        background-color: {_sidebar} !important;
        background: {_sidebar} !important;
    }}
    /* Dialog / Modal */
    [data-testid="stDialog"],
    [data-testid="stModal"],
    [data-testid="stDialog"] > div,
    [data-testid="stModal"] > div,
    div[role="dialog"] {{
        background-color: {_surface} !important;
        background: {_surface} !important;
        color: {_text} !important;
    }}
    /* Toast notifications */
    [data-testid="stToast"],
    [data-testid="stToast"] > div {{
        background-color: {_surface} !important;
        background: {_surface} !important;
        color: {_text} !important;
        border-color: {_border} !important;
    }}
    /* Alert / Info / Warning / Error boxes */
    .stAlert,
    [data-testid="stAlert"],
    [role="alert"] {{
        background-color: {_surface} !important;
        color: {_text} !important;
        border-color: {_border} !important;
    }}
    .stAlert p, [data-testid="stAlert"] p, [role="alert"] p {{
        color: {_text} !important;
    }}
    /* iframe containers (e.g. JS timer component) */
    iframe {{
        background-color: transparent !important;
        background: transparent !important;
    }}
    [data-testid="stIFrame"],
    [data-testid="stCustomComponentV1"],
    .stCustomComponentV1 {{
        background-color: {_bg} !important;
        background: {_bg} !important;
    }}
    /* Slider */
    .stSlider,
    .stSlider > div,
    [data-testid="stSlider"] {{
        background-color: transparent !important;
        color: {_text} !important;
    }}
    [data-testid="stSlider"] [data-testid="stTickBarMin"],
    [data-testid="stSlider"] [data-testid="stTickBarMax"] {{
        color: {_muted} !important;
    }}
    /* Color picker */
    [data-testid="stColorPicker"] > div {{
        background-color: {_input} !important;
    }}
    /* Spinner / progress containers */
    .stSpinner > div {{
        background-color: transparent !important;
    }}
    /* Fragment containers */
    [data-testid="stElementContainer"] {{
        background-color: transparent !important;
    }}
    h1,h2,h3,h4,h5,h6 {{ color: {_head} !important; }}
    .stMarkdown p, .stMarkdown span {{ color: {_text}; }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="collapsedControl"] svg {{
        width: 1.5rem !important; height: 1.5rem !important;
        color: {_muted} !important; transition: all 0.2s ease;
    }}
    [data-testid="stSidebarCollapseButton"]:hover svg,
    [data-testid="collapsedControl"]:hover svg {{
        color: {_accent} !important; transform: scale(1.1);
    }}
    section[data-testid="stSidebar"] {{
        background-color: {_sidebar} !important;
        border-right: 1px solid {_border} !important;
    }}
    [data-testid="stSidebar"] * {{ color: {_text} !important; }}
    [data-testid="stSidebar"] .stMarkdown h3 {{
        color: {_head} !important; font-size:1rem; font-weight:600; margin-top:1rem;
    }}
    [data-testid="stExpander"] {{
        background-color: {_surface} !important;
        border: 1px solid {_border} !important;
        border-radius: 12px; margin-bottom: 0.25rem; color: {_text} !important;
    }}
    [data-testid="stExpander"] summary {{
        color: {_head} !important;
        background-color: {_surface} !important;
        border-radius: 12px;
        padding: 0.35rem 0.7rem !important;
    }}
    [data-testid="stExpander"] details {{ background-color: {_surface} !important; }}
    [data-testid="stExpander"] details[open] > summary {{ border-radius: 12px 12px 0 0 !important; }}
    [data-testid="stExpander"] > div:first-child {{ background-color: {_surface} !important; }}
    [data-testid="stExpander"] details > div {{
        background-color: {_surface} !important;
        border-radius: 0 0 12px 12px;
    }}
    [data-testid="stExpander"] summary svg {{
        fill: {_text} !important; color: {_text} !important;
    }}
    .stRadio label, .stRadio span, .stRadio p,
    .stRadio div[role="radiogroup"] label, .stRadio > label,
    .stCheckbox label, .stCheckbox span,
    [data-testid="stRadio"] label, [data-testid="stRadio"] span, [data-testid="stRadio"] p,
    [role="radio"] + span, [role="radiogroup"] label {{
        color: {_text} !important; opacity: 1 !important;
    }}
    [data-testid="stRadio"] input[type="radio"] + div,
    [data-testid="stRadio"] input[type="radio"] ~ div {{
        border-color: {_text} !important;
    }}
    svg {{ fill: {_text} !important; color: {_text} !important; }}
    [data-baseweb="select"] > div {{
        background-color: {_input} !important;
        border-color: {_border} !important;
        color: {_text} !important;
    }}
    [data-baseweb="select"] [data-testid="stMarkdownContainer"],
    [data-baseweb="select"] span, [data-baseweb="select"] div {{
        color: {_text} !important;
    }}
    [data-baseweb="select"] svg path {{ fill: {_text} !important; }}
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
    .stButton > button {{
        border-radius: 8px; font-weight: 500; transition: all 0.2s ease;
    }}
    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,{'0.3' if _dark else '0.1'});
    }}
    .stButton > button:disabled, .stButton > button[disabled] {{
        background-color: {_surface2} !important;
        color: {_muted} !important;
        border: 1px solid {_border} !important;
        opacity: 0.6 !important;
        cursor: not-allowed !important;
        transform: none !important;
        box-shadow: none !important;
    }}
    .stButton > button[kind="tertiary"] {{
        background: transparent !important; border: none !important;
        box-shadow: none !important; padding: 0.2rem 0.4rem !important;
        color: {_muted} !important; font-size: 1.1rem !important;
    }}
    .stButton > button[kind="tertiary"]:hover {{
        color: #EF4444 !important; transform: scale(1.2) !important; box-shadow: none !important;
    }}
    .stButton > button[kind="secondary"] {{
        background-color: {_surface2} !important;
        border: 1px solid {_border} !important;
        color: {_text} !important;
    }}
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
    .stTabs [data-baseweb="tab-list"] {{ gap: 8px; background: transparent !important; }}
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
    .stTabs [data-baseweb="tab-panel"],
    .stTabs [role="tabpanel"],
    .stTabs > div:last-child {{
        background-color: {_bg} !important;
        background: {_bg} !important;
    }}
    [data-testid="stMetric"] {{
        background: {_surface} !important; padding: 0.6rem;
        border-radius: 12px; border: 1px solid {_border};
    }}
    [data-testid="stMetricLabel"] {{ font-size: 0.8rem !important; color: {_muted} !important; }}
    [data-testid="stMetricValue"] {{ font-size: 1.5rem !important; font-weight: 700 !important; color: {_head} !important; }}
    [data-testid="stForm"] {{
        border: none !important; padding: 0 !important;
        background: transparent !important;
    }}
    [data-testid="stFormSubmitButton"] {{
        background: transparent !important;
    }}
    [data-testid="stFormSubmitButton"] > button {{
        background-color: {_surface2} !important;
        color: {_text} !important;
        border: 1px solid {_border} !important;
        border-radius: 8px;
    }}
    [data-testid="stFormSubmitButton"] > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,{'0.3' if _dark else '0.1'});
    }}
    .stProgress > div > div > div {{ border-radius: 999px; }}
    hr {{ border: none; border-top: 1px solid {_border}; margin: 0.25rem 0; }}
    @media (max-width: 768px) {{
        .stColumns {{ flex-direction: column; }}
        [data-testid="stMetricValue"] {{ font-size: 1.2rem !important; }}
    }}
    html {{ scroll-behavior: smooth; }}
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {{
        background-color: {_input} !important; color: {_text} !important;
        border: 1px solid {_border} !important; border-radius: 8px;
        caret-color: {_text} !important;
    }}
    .stNumberInput [data-baseweb="input"],
    .stNumberInput [data-baseweb="base-input"],
    div[data-testid="stNumberInput"] > div,
    div[data-testid="stNumberInput"] > div > div {{
        background-color: {_input} !important;
        border-color: {_border} !important;
    }}
    div[data-testid="stNumberInput"] input {{
        background-color: {_input} !important; color: {_text} !important;
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
    .stNumberInput button {{ color: {_text} !important; background: {_input} !important; border-color: {_border} !important; }}
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
    [data-baseweb="calendar"], [data-baseweb="datepicker"] {{
        background-color: {_surface} !important;
        background: {_surface} !important;
        color: {_text} !important;
    }}
    [data-baseweb="calendar"] *,
    [data-baseweb="calendar"] *::before,
    [data-baseweb="calendar"] *::after {{
        background-color: transparent !important;
        background: transparent !important;
        color: {_text} !important;
    }}
    [data-baseweb="calendar"] [data-baseweb="calendar-header"],
    [data-baseweb="calendar"] > div:first-child {{
        background-color: {_surface} !important;
        background: {_surface} !important;
        color: {_text} !important;
    }}
    [data-baseweb="calendar"] select,
    [data-baseweb="calendar"] [data-baseweb="select"] > div {{
        background-color: {_surface2} !important;
        background: {_surface2} !important;
        color: {_text} !important;
        border-color: {_border} !important;
    }}
    [data-baseweb="calendar"] [data-baseweb="select"] span,
    [data-baseweb="calendar"] [data-baseweb="select"] div {{
        color: {_text} !important;
    }}
    [data-baseweb="calendar"] button {{
        color: {_text} !important;
        background-color: transparent !important;
        background: transparent !important;
    }}
    [data-baseweb="calendar"] button:hover {{
        background-color: {_surface2} !important;
        background: {_surface2} !important;
    }}
    [data-baseweb="calendar"] th,
    [data-baseweb="calendar"] [role="columnheader"] {{
        color: {_muted} !important;
    }}
    [data-baseweb="calendar"] [aria-selected="true"],
    [data-baseweb="calendar"] [aria-selected="true"] *,
    [data-baseweb="calendar"] [role="gridcell"][aria-selected="true"],
    [data-baseweb="calendar"] [role="gridcell"][aria-selected="true"] * {{
        background-color: {_accent} !important;
        background: {_accent} !important;
        color: #FFFFFF !important;
    }}
    [data-baseweb="calendar"] [role="gridcell"]:hover,
    [data-baseweb="calendar"] [role="gridcell"]:hover *,
    [data-baseweb="calendar"] td:hover,
    [data-baseweb="calendar"] td:hover * {{
        background-color: {_surface2} !important;
        background: {_surface2} !important;
        color: {_text} !important;
    }}
    [data-baseweb="calendar"] [aria-selected="true"]:hover,
    [data-baseweb="calendar"] [aria-selected="true"]:hover *,
    [data-baseweb="calendar"] [role="gridcell"][aria-selected="true"]:hover,
    [data-baseweb="calendar"] [role="gridcell"][aria-selected="true"]:hover * {{
        background-color: {_accent} !important;
        background: {_accent} !important;
        color: #FFFFFF !important;
    }}
    [data-baseweb="calendar"] [role="gridcell"][aria-disabled="true"],
    [data-baseweb="calendar"] [role="gridcell"][aria-disabled="true"] * {{
        color: {_muted} !important;
        opacity: 0.4;
        background-color: transparent !important;
        background: transparent !important;
    }}
    div[data-baseweb="popover"]:has([data-baseweb="calendar"]),
    div[data-baseweb="popover"]:has([data-baseweb="calendar"]) > div,
    div[data-baseweb="popover"]:has([data-baseweb="calendar"]) > div > div {{
        background-color: {_surface} !important;
        background: {_surface} !important;
    }}
    [data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"] {{
        background-color: {_input} !important;
        border-color: {_border} !important;
        color: {_text} !important;
    }}
    [data-baseweb="input"] input, [data-baseweb="base-input"] input,
    [data-baseweb="input"] textarea {{
        background-color: {_input} !important; color: {_text} !important;
    }}
    [data-baseweb="input"] input::placeholder,
    [data-baseweb="textarea"] textarea::placeholder {{
        color: {_muted} !important;
    }}
    [data-testid="stPopover"] button,
    [data-testid="stSidebar"] [data-testid="stPopover"] button,
    [data-testid="stPopover"] button[kind="secondary"] {{
        background-color: {_input} !important;
        color: {_text} !important;
        border: 1px solid {_border} !important;
        border-radius: 8px !important;
        width: 2.8rem !important; min-width: 2.8rem !important; max-width: 2.8rem !important;
        height: 2.8rem !important; min-height: 2.8rem !important;
        padding: 0 !important;
        display: flex !important; align-items: center !important; justify-content: center !important;
        font-size: 1.4rem !important;
        overflow: hidden !important; gap: 0 !important;
    }}
    [data-testid="stPopover"] button svg,
    [data-testid="stSidebar"] [data-testid="stPopover"] button svg {{
        display: none !important; visibility: hidden !important;
        width: 0 !important; height: 0 !important;
        position: absolute !important; overflow: hidden !important;
    }}
    [data-testid="stPopover"] button:hover,
    [data-testid="stSidebar"] [data-testid="stPopover"] button:hover {{
        border-color: {_accent} !important;
        box-shadow: 0 0 0 2px {_accent}33 !important;
        background-color: {_input} !important;
    }}
    div[data-baseweb="popover"], div[data-baseweb="popover"] > div,
    div[data-baseweb="popover"] > div > div,
    .stPopover > div, div[role="dialog"] {{
        background-color: {_surface} !important;
        color: {_text} !important;
        border-color: {_border} !important;
    }}
    [data-baseweb="popover"] button {{
        background-color: {_surface2} !important;
        color: {_text} !important;
        border: 1px solid {_border} !important;
        margin: 2px !important; transition: transform 0.1s;
    }}
    [data-baseweb="popover"] button:hover {{
        border-color: {_accent} !important;
        transform: scale(1.1); z-index: 10;
        background-color: {_input} !important;
        color: {_accent} !important;
    }}
    [data-baseweb="popover"] [data-testid="stMarkdownContainer"] p,
    [data-baseweb="popover"] h1, [data-baseweb="popover"] h2, [data-baseweb="popover"] h3 {{
        color: {_text} !important;
    }}
    @media (max-width: 768px) {{
        [data-testid="stMetricValue"] {{ font-size: 1.2rem !important; }}
    }}
    {'* { scrollbar-color: #3D4160 #1E2130; scrollbar-width: thin; }' if _dark else ''}
    {_dark_scrollbar_css() if _dark else ''}
</style>"""


def _dark_scrollbar_css() -> str:
    """Return dark-mode scrollbar CSS rules (extracted to avoid f-string nesting)."""
    return """
    [data-baseweb="popover"] ul::-webkit-scrollbar,
    [data-baseweb="popover"] div::-webkit-scrollbar,
    [data-baseweb="menu"] ::-webkit-scrollbar,
    [data-baseweb="select"] ::-webkit-scrollbar,
    [role="listbox"]::-webkit-scrollbar { width: 8px !important; }
    [data-baseweb="popover"] ul::-webkit-scrollbar-track,
    [data-baseweb="popover"] div::-webkit-scrollbar-track,
    [data-baseweb="menu"] ::-webkit-scrollbar-track,
    [data-baseweb="select"] ::-webkit-scrollbar-track,
    [role="listbox"]::-webkit-scrollbar-track { background: #1E2130 !important; border-radius: 4px; }
    [data-baseweb="popover"] ul::-webkit-scrollbar-thumb,
    [data-baseweb="popover"] div::-webkit-scrollbar-thumb,
    [data-baseweb="menu"] ::-webkit-scrollbar-thumb,
    [data-baseweb="select"] ::-webkit-scrollbar-thumb,
    [role="listbox"]::-webkit-scrollbar-thumb { background: #3D4160 !important; border-radius: 4px; }
    [data-baseweb="popover"] ul::-webkit-scrollbar-thumb:hover,
    [data-baseweb="popover"] div::-webkit-scrollbar-thumb:hover,
    [data-baseweb="menu"] ::-webkit-scrollbar-thumb:hover,
    [data-baseweb="select"] ::-webkit-scrollbar-thumb:hover,
    [role="listbox"]::-webkit-scrollbar-thumb:hover { background: #4F5380 !important; }
    [data-baseweb="popover"] ul,
    [data-baseweb="popover"] div[style*="overflow"],
    [data-baseweb="menu"], [role="listbox"] {{
        scrollbar-color: #3D4160 #1E2130 !important;
        scrollbar-width: thin !important;
    }}
    /* ── Smooth page transition animation ── */
    @keyframes pageFadeSlideIn {{
        from {{ opacity: 0; transform: translateY(14px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    [data-testid="stMainBlockContainer"] > div {{
        animation: pageFadeSlideIn 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
    }}
    /* Sidebar also gets a subtle fade */
    @keyframes sidebarFadeIn {{
        from {{ opacity: 0; }}
        to   {{ opacity: 1; }}
    }}
    [data-testid="stSidebarUserContent"] > div {{
        animation: sidebarFadeIn 0.3s ease both;
    }}
    """

# ─── Restore session BEFORE theme init so saved theme is available ──
_is_auth = is_authenticated()

# ─── Theme Initialization ────────────────────────────────────
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'light'

_dark = (st.session_state['theme'] == 'dark')

# Color tokens per theme (kept for sidebar/footer HTML snippets below)
if _dark:
    _bg = "#0F1117"; _surface = "#1E2130"; _surface2 = "#252840"
    _border = "#2D3150"; _text = "#E5E7EB"; _muted = "#9CA3AF"
    _head = "#FFFFFF"; _accent = "#4F8EF7"; _sidebar = "#0F1117"
    _input = "#1E2130"
else:
    _bg = "#F5F7FA"; _surface = "#FFFFFF"; _surface2 = "#F9FAFB"
    _border = "#E5E7EB"; _text = "#374151"; _muted = "#6B7280"
    _head = "#1E1E2E"; _accent = "#4A90D9"; _sidebar = "#F8F9FA"
    _input = "#FFFFFF"

# ─── Custom Styling (cached – only re-computed on theme change) ──
st.markdown(_build_theme_css(st.session_state['theme']), unsafe_allow_html=True)

# ─── Authentication Gate ──────────────────────────────────────
if not _is_auth:
    render_login_page()
    st.stop()

# ─── Main App (Authenticated) ────────────────────────────────

# Sidebar navigation
with st.sidebar:
    st.markdown(
        f"""<div style='padding:0.25rem 0; margin-bottom:0.5rem;'>
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
    pass

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

    # Render the categories area (kept consistent across pages)
    render_sidebar(st.session_state['user_id'])


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

    # Theme toggle placed above refresh/logout (keeps same style as before)
    _toggle_label = "☀️ Light Mode" if _dark else "🌙 Dark Mode"
    if st.button(_toggle_label, use_container_width=True, type="secondary", key="theme_toggle"):
        new_theme = 'light' if _dark else 'dark'
        st.session_state['theme'] = new_theme
        if is_authenticated():
            update_user_theme(st.session_state['user_id'], new_theme)
        st.rerun()

    col_refresh, col_logout = st.sidebar.columns(2)
    with col_refresh:
        if st.button("🔄 Refresh", use_container_width=True, type="secondary", help="Reload data"):
            st.rerun()
    with col_logout:
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            logout_user()
            st.rerun()