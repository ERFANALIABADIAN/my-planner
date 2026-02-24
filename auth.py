"""
Authentication module for My Planner.
Handles user login, registration, and session management.
"""

import bcrypt
import streamlit as st
from database import get_user_by_username, create_user
import database as _db


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def login_user(username: str, password: str) -> bool:
    """Attempt to login a user. Returns True if successful."""
    user = get_user_by_username(username)
    if user and verify_password(password, user['password_hash']):
        st.session_state['authenticated'] = True
        st.session_state['user_id'] = user['id']
        st.session_state['username'] = user['username']
        st.session_state['display_name'] = user['display_name']
        st.session_state['theme'] = user.get('theme', 'light') or 'light'
        # Persist session: store token in DB and add to URL so refresh works
        try:
            token = _db.create_session_token(user['id'])
            st.session_state['_session_token'] = token
            st.query_params['_s'] = token
        except Exception:
            pass
        return True
    return False


def register_user(username: str, password: str, display_name: str = None) -> tuple:
    """Register a new user. Returns (success: bool, message: str)."""
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."
    existing = get_user_by_username(username)
    if existing:
        return False, "Username already exists."
    try:
        pw_hash = hash_password(password)
        user_id = create_user(username, pw_hash, display_name)
        st.session_state['authenticated'] = True
        st.session_state['user_id'] = user_id
        st.session_state['username'] = username
        st.session_state['display_name'] = display_name or username
        # Persist session
        try:
            token = _db.create_session_token(user_id)
            st.session_state['_session_token'] = token
            st.query_params['_s'] = token
        except Exception:
            pass
        return True, "Account created successfully!"
    except Exception as e:
        return False, f"Error: {str(e)}"


def logout_user():
    """Clear session state to logout."""
    # Delete token from DB
    token = st.session_state.get('_session_token')
    if token:
        try:
            _db.delete_session_token(token)
        except Exception:
            pass
    # Clear URL token so refresh shows login
    try:
        st.query_params.clear()
    except Exception:
        pass
    for key in ['authenticated', 'user_id', 'username', 'display_name',
                'timer_running', 'timer_start', 'timer_task_id', '_session_token']:
        st.session_state.pop(key, None)


def is_authenticated() -> bool:
    """Check if user is currently authenticated. Also restores session from URL token on refresh."""
    if st.session_state.get('authenticated', False):
        return True
    # Try to restore from persistent URL token (survives browser refresh)
    token = st.query_params.get('_s', None)
    if token:
        try:
            user = _db.get_session_user(token)
            if user:
                st.session_state['authenticated'] = True
                st.session_state['user_id'] = user['id']
                st.session_state['username'] = user['username']
                st.session_state['display_name'] = user['display_name']
                # Restore saved theme preference when restoring session from token
                st.session_state['theme'] = user.get('theme', 'light') or 'light'
                st.session_state['_session_token'] = token
                return True
        except Exception:
            pass
    return False


def get_current_user_id() -> int:
    """Get current logged-in user's ID."""
    return st.session_state.get('user_id')


def render_login_page():
    """Render the login/register page."""
    
    # Check theme state from session to determine colors
    import streamlit as st
    theme = st.session_state.get('theme', 'light')
    is_dark = (theme == 'dark')

    # Define colors based on theme
    bg_color = "#0F1117" if is_dark else "#F5F7FA"
    text_color = "#FFFFFF" if is_dark else "#1E1E2E"
    subtitle_color = "#9CA3AF" if is_dark else "#6B7280"

    st.markdown(f"""
    <style>
        /* ── Full-screen login overlay ─────────────────────────── */
        /* Covers any stale app content that might show through    */
        [data-testid="stAppViewContainer"]::before {{
            content: '';
            position: fixed;
            inset: 0;
            background: {bg_color};
            z-index: 100;
        }}
        /* Bring the main block above the overlay                  */
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"] {{
            position: relative;
            z-index: 200;
        }}
        /* ── Kill ALL page-enter animations ────────────────────── */
        .stApp, .stApp > *, .main, .main > *,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        section.main > div {{
            animation: none !important;
            transition: none !important;
            transform: none !important;
            filter: none !important;
            opacity: 1 !important;
        }}
        /* ── Hide sidebar on login ──────────────────────────────── */
        section[data-testid="stSidebar"] {{ display: none !important; }}
        [data-testid="collapsedControl"]  {{ display: none !important; }}
        /* ── Login card styling ─────────────────────────────────── */
        .login-title {{
            text-align: center; font-size: 2.5rem;
            font-weight: 700; color: {text_color}; margin-bottom: 0.5rem;
        }}
        .login-subtitle {{
            text-align: center; color: {subtitle_color};
            margin-bottom: 2rem; font-size: 1rem;
        }}
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown('<div class="login-title">📋 My Planner</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Track your tasks, manage your time</div>', unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register"])

        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Login", use_container_width=True, type="primary")

                if submitted:
                    if username and password:
                        if login_user(username, password):
                            st.rerun()
                        else:
                            st.error("Invalid username or password.")
                    else:
                        st.warning("Please enter both username and password.")

        with tab_register:
            with st.form("register_form", clear_on_submit=False):
                new_username = st.text_input("Username", placeholder="Choose a username")
                new_display = st.text_input("Display Name", placeholder="Your name (optional)")
                new_password = st.text_input("Password", type="password", placeholder="Choose a password")
                new_password2 = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
                reg_submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")

                if reg_submitted:
                    if new_password != new_password2:
                        st.error("Passwords do not match.")
                    elif new_username and new_password:
                        success, msg = register_user(new_username, new_password, new_display)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("Please fill in all required fields.")
