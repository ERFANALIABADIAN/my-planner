"""
Tasks page - Category & Task management with subtasks.
"""

import streamlit as st
from datetime import date
import database as db
import time

# Helper to request confirmation before deleting items
def request_delete(kind: str, obj_id: int, name: str = None):
    st.session_state['confirm_delete'] = {'kind': kind, 'id': obj_id, 'name': name}
    st.rerun()
# ─── Icon picker options ────────────────────────────────────────────
ICONS = [
    "📁", "📂", "📋", "📌", "📍", "🗂", "🖥", "💻", "📱",
    "📚", "📖", "📧", "📦", "💰", "💳", "🏆", "🎯",
    "🚀", "⚡", "🔥", "💡", "⭐", "🌟", "🌱", "🎨",
    "🎵", "🎸", "🥋", "🏃", "💪", "🧠", "🔬",
    "🌍", "🏠", "🏫", "🏥", "🏭", "🔑", "🔧",
    "📊", "📈", "📉", "🤝", "👀", "✅", "📏",
]


def _subtask_toggle_cb(sub_id: int, task_id: int):
    """Callback executed when a subtask checkbox changes. Reset activity timer."""
    db.toggle_subtask(sub_id)
    # Invalidate caches
    try:
        db.get_subtasks.clear()
        # Also force parent task to refresh total_time/progress if dependent
        db.get_task_by_id.clear() 
    except Exception:
        pass
    
    # Reset the auto-close timer when user interacts
    st.session_state[f'subtask_timer_{task_id}'] = time.time()



@st.fragment
def _render_sidebar_new_category(user_id, text_col):
    """Fragment for New Category form to allow fast toggling without full app rerun."""
    if 'new_cat_open' not in st.session_state:
        st.session_state['new_cat_open'] = False
    _nc_open = st.session_state['new_cat_open']

    # Toggle button - NO explicit rerun needed for fragment update
    if st.button(
        "▼ ➕ New Category" if _nc_open else "➕ New Category",
        key="btn_toggle_new_cat",
        use_container_width=True,
        type="secondary"
    ):
        st.session_state['new_cat_open'] = not _nc_open
        st.rerun()  # Fragment rerun

    if st.session_state['new_cat_open']:
        with st.container():
            cat_name = st.text_input("Name", placeholder="e.g. Programming", key="new_cat_name")

            # Compact layout: Icon Popover + Color Picker side-by-side
            col_icon, col_color = st.columns([1, 4], gap="small")

            picked = st.session_state.get('new_cat_icon', '📁')

            with col_icon:
                st.markdown(
                    f"<p style='font-size:0.875rem; color:{text_col}; "
                    f"font-weight:400; margin-bottom:4px; line-height:1.4;'>Icon</p>",
                    unsafe_allow_html=True
                )
                popover = st.popover(picked)
                with popover:
                    st.markdown("### Choose Icon")
                    cols = st.columns(5)
                    for i, icon in enumerate(ICONS):
                        with cols[i % 5]:
                            if st.button(icon, key=f"icon_select_{i}", use_container_width=True):
                                st.session_state['new_cat_icon'] = icon
                                st.rerun()  # Fragment rerun

            with col_color:
                cat_color = st.color_picker("Color", value="#4A90D9", key="new_cat_color")

            st.write("")  # Spacer

            if st.button("Create", use_container_width=True, type="primary", key="create_cat_btn"):
                if cat_name.strip():
                    try:
                        db.create_category(user_id, cat_name.strip(), cat_color, picked)
                        st.success(f"Created: {picked} {cat_name}")
                        st.session_state.pop('new_cat_name', None)
                        st.session_state['new_cat_icon'] = '📁'
                        st.session_state['new_cat_open'] = False  # auto-close
                        st.rerun()  # FULL App rerun needed to update category list
                    except Exception:
                        st.error("Category already exists!")
                else:
                    st.warning("Enter a name.")


def render_sidebar(user_id):
    """Render the Categories area in the sidebar. This is called from app.py so the sidebar
    is present across all pages (Tasks, Timer, Analytics)."""
    # Theme-aware colors
    _dark = st.session_state.get('theme', 'light') == 'dark'
    _text_col = "#E5E7EB" if _dark else "#374151"

    st.markdown("### 📁 Categories")
    _render_sidebar_new_category(user_id, _text_col)

    categories = db.get_categories(user_id)
    if categories:
        cat_options = {f"{c['icon']} {c['name']}": c['id'] for c in categories}
        main_cat = st.session_state.get('main_cat_filter', "All Categories")
        filter_id = cat_options.get(main_cat, None) if main_cat != "All Categories" else None
        for cat in categories:
            col_cat, col_del = st.columns([0.85, 0.15])
            with col_cat:
                is_active = filter_id == cat['id']
                btn_style = "primary" if is_active else "secondary"
                if st.button(
                    f"{cat['icon']} {cat['name']}",
                    key=f"sidebar_cat_{cat['id']}",
                    use_container_width=True,
                    type=btn_style
                ):
                    if is_active:
                        st.session_state.pop('filter_cat_id', None)
                        st.session_state['main_cat_filter'] = "All Categories"
                    else:
                        st.session_state['filter_cat_id'] = cat['id']
                        st.session_state['main_cat_filter'] = f"{cat['icon']} {cat['name']}"
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"del_cat_{cat['id']}", help="Delete", type="tertiary"):
                    request_delete('category', cat['id'], cat.get('name') or '')
    else:
        st.info("No categories yet. Create one above!")


def _render_subtask_section(task_id, subtasks, text_col, muted_col):
    """Subtasks panel helper (called within task fragment)."""
    sub_label = f"Subtasks ({sum(1 for s in subtasks if s['is_done'])}/{len(subtasks)})" if subtasks else "Add Subtasks"
    _sub_key = f'sub_open_{task_id}'
    if _sub_key not in st.session_state:
        st.session_state[_sub_key] = False
    _sub_open = st.session_state[_sub_key]

    with st.container():
        if st.button(
            ("▼ " if _sub_open else "") + sub_label,
            key=f"btn_toggle_sub_{task_id}",
            use_container_width=True,
            type="secondary"
        ):
            st.session_state[_sub_key] = not _sub_open
            st.rerun()  # Fragment rerun

        if _sub_open:
            st.markdown("""
            <style>
            div[data-testid="stCheckbox"] { padding: 0 !important; margin: 0 !important; }
            div[data-testid="stCheckbox"] > label {
                display: flex !important; align-items: center !important;
                gap: 0.5rem !important; padding: 0 !important; min-height: 1.8rem !important;
            }
            div[data-testid="column"]:has(div[data-testid="stCheckbox"]) {
                display: flex !important; align-items: center !important;
            }
            </style>""", unsafe_allow_html=True)

            # Separate undone and completed subtasks so we can hide completed ones by default
            undone_subs = [s for s in subtasks if not s['is_done']]
            done_subs = [s for s in subtasks if s['is_done']]

            # Render undone subtasks as before
            for sub in undone_subs:
                col_check, col_name, col_sub_del = st.columns([0.5, 6, 0.5])
                with col_check:
                    st.checkbox(
                        "done", value=False,
                        key=f"sub_{sub['id']}",
                        label_visibility="collapsed",
                        on_change=_subtask_toggle_cb,
                        args=(sub['id'], task_id)
                    )
                with col_name:
                    st.markdown(
                        f"<div style='display:flex; align-items:center; min-height:1.8rem; color:{text_col};'>{sub['title']}</div>",
                        unsafe_allow_html=True
                    )
                with col_sub_del:
                    if st.button("🗑️", key=f"del_sub_{sub['id']}", help="Delete", type="tertiary"):
                        request_delete('subtask', sub['id'], sub.get('title') or '')

            # Completed subtasks: hidden by default, toggle to reveal
            comp_key = f'completed_sub_open_{task_id}'
            if comp_key not in st.session_state:
                st.session_state[comp_key] = False
            comp_open = st.session_state[comp_key]

            if done_subs:
                if st.button(("▼ " if comp_open else "") + f"Completed Subtasks ({len(done_subs)})",
                             key=f"btn_toggle_comp_{task_id}", use_container_width=True, type="secondary"):
                    st.session_state[comp_key] = not comp_open
                    st.rerun()

                if st.session_state[comp_key]:
                    for sub in done_subs:
                        col_check, col_name, col_actions = st.columns([0.5, 6, 1])
                        with col_check:
                            # Show checked box that can be toggled to mark undone
                            st.checkbox("done", value=True, key=f"sub_done_{sub['id']}", label_visibility="collapsed",
                                        on_change=_subtask_toggle_cb, args=(sub['id'], task_id))
                        with col_name:
                            st.markdown(
                                f"<div style='display:flex; align-items:center; min-height:1.8rem; text-decoration:line-through; color:{muted_col};'>{sub['title']}</div>",
                                unsafe_allow_html=True
                            )
                        with col_actions:
                            # Only show delete for completed subtasks
                            if st.button("🗑️", key=f"del_done_sub_{sub['id']}", help="Delete", type="tertiary"):
                                request_delete('subtask', sub['id'], sub.get('title') or '')

            col_new_sub, col_add_sub = st.columns([5, 1])
            with col_new_sub:
                # Use a rotating counter in the widget key so we can force a fresh widget instance
                ctr_key = f'new_sub_ctr_{task_id}'
                if ctr_key not in st.session_state:
                    st.session_state[ctr_key] = 0
                ctr = st.session_state[ctr_key]
                rotating_key = f"new_sub_{task_id}_{ctr}"
                new_sub_title = st.text_input(
                    "New subtask", placeholder="Add a subtask...",
                    key=rotating_key, label_visibility="collapsed"
                )
            with col_add_sub:
                if st.button("➕", key=f"add_sub_{task_id}"):
                    if new_sub_title.strip():
                        db.create_subtask(task_id, new_sub_title.strip())
                        # Advance counter so next render creates a new widget instance (cleared)
                        st.session_state[ctr_key] = ctr + 1
                        st.rerun()  # Fragment rerun


def _render_log_time_section(user_id, task_id, task_title):
    """Log Time panel helper (called within task fragment)."""
    _log_key = f'log_open_{task_id}'
    if _log_key not in st.session_state:
        st.session_state[_log_key] = False
    _log_open = st.session_state[_log_key]

    with st.container():
        if st.button(
            "▼ ⏱ Log Time" if _log_open else "⏱ Log Time",
            key=f"btn_toggle_log_{task_id}",
            use_container_width=True,
            type="secondary"
        ):
            st.session_state[_log_key] = not _log_open
            # Ensure immediate UI update so single click opens/closes reliably
            st.rerun()

        if _log_open:
            # Use local variables for log time fields to avoid rerun issues
            if f'_log_min_local_{task_id}' not in st.session_state:
                st.session_state[f'_log_min_local_{task_id}'] = 25
            if f'_log_date_local_{task_id}' not in st.session_state:
                st.session_state[f'_log_date_local_{task_id}'] = date.today()
            if f'_log_note_local_{task_id}' not in st.session_state:
                st.session_state[f'_log_note_local_{task_id}'] = ""

            col_dur, col_date, col_note, col_add = st.columns([2, 2, 3, 1])
            with col_dur:
                log_mins = st.number_input(
                    "Minutes", min_value=1, value=st.session_state[f'_log_min_local_{task_id}'],
                    key=f"log_min_input_{task_id}", label_visibility="collapsed"
                )
                st.session_state[f'_log_min_local_{task_id}'] = log_mins
            with col_date:
                log_date = st.date_input(
                    "Date", value=st.session_state[f'_log_date_local_{task_id}'],
                    key=f"log_date_input_{task_id}", label_visibility="collapsed"
                )
                st.session_state[f'_log_date_local_{task_id}'] = log_date
            with col_note:
                log_note = st.text_input(
                    "Note", placeholder="What did you work on?",
                    value=st.session_state[f'_log_note_local_{task_id}'],
                    key=f"log_note_input_{task_id}", label_visibility="collapsed"
                )
                st.session_state[f'_log_note_local_{task_id}'] = log_note
            with col_add:
                # Use tertiary button with inline saving
                if st.button("💾", key=f"save_log_{task_id}"):
                    minutes = st.session_state[f'_log_min_local_{task_id}']
                    db.add_time_log(
                        user_id, task_id, minutes,
                        st.session_state[f'_log_date_local_{task_id}'].isoformat(),
                        st.session_state[f'_log_note_local_{task_id}'], "manual"
                    )
                    # Close panel and show success message
                    st.session_state[_log_key] = False
                    # Reset local fields
                    st.session_state[f'_log_min_local_{task_id}'] = 25
                    st.session_state[f'_log_date_local_{task_id}'] = date.today()
                    st.session_state[f'_log_note_local_{task_id}'] = ""
                    # Queue toast to show after rerun so it's always visible (no seconds)
                    # Format minutes without seconds for cleaner toasts
                    def _fmt_min_no_secs(m):
                        try:
                            total_min = int(round(float(m)))
                        except Exception:
                            total_min = int(m)
                        hrs = total_min // 60
                        mins = total_min % 60
                        return f"{hrs}h {mins}m" if hrs > 0 else f"{mins}m"

                    st.session_state[f'_pending_log_toast_{task_id}'] = (
                        f"✅ Logged {_fmt_min_no_secs(minutes)} for '{task_title}'"
                    )
                    st.rerun() # Ensure UI reflects saved data immediately

        

@st.fragment
def _render_task_item(task, user_id, categories, text_col, muted_col, card_bg, done_bg, subtasks=None):
    """Fragment for a single task row. Accepts a pre-fetched `task` dict and optional `subtasks` list
    to avoid N+1 database queries when rendering task lists.
    """
    if not task:
        return

    # Use provided subtasks mapping/list if available, otherwise fetch for this task
    if subtasks is None:
        subtasks = db.get_subtasks(task['id'])

    # Calculate progress
    total_time = task.get('total_time', 0)
    done_count = sum(1 for s in subtasks if s['is_done'])
    progress = done_count / len(subtasks) if subtasks else 0

    is_completed = task['status'] == 'completed'
    border_color = task['category_color']
    goal_minutes = task.get('goal_minutes') or 0

    with st.container():
        col_main, col_time, col_actions = st.columns([5, 2, 2])

        with col_main:
            title_style = "text-decoration: line-through; color: #9CA3AF;" if is_completed else ""
            st.markdown(
                f"**<span style='{title_style}'>{task['category_icon']} {task['title']}</span>**"
                f" <small style='color:{border_color};'>({task['category_name']})</small>",
                unsafe_allow_html=True
            )
            if task['description']:
                st.caption(task['description'])

        with col_time:
            st.markdown(f"⏱ **{format_minutes(total_time)}**")
            
            # Progress bar
            if goal_minutes > 0:
                raw_pct = total_time / goal_minutes
                bar_pct = min(raw_pct, 1.0)
                pct_display = int(raw_pct * 100)
                
                goal_h = goal_minutes / 60.0
                color = "#EF4444" if raw_pct > 1.0 else muted_col
                st.markdown(f"""
                <div style="font-size:0.75rem; color:{color}; margin-bottom:2px;">
                    Goal: <b>{goal_h:g}h</b> &nbsp;•&nbsp; {pct_display}%
                </div>
                """, unsafe_allow_html=True)
                st.progress(bar_pct)
            
            # Show subtask progress independently (stacked if both exist)
            if subtasks:
                sub_pct = done_count / len(subtasks) if subtasks else 0
                # Use custom div to control spacing tightly like the goal bar
                st.markdown(f"""
                <div style="font-size:0.75rem; color:{muted_col}; margin-bottom:2px; margin-top:4px;">
                    {done_count}/{len(subtasks)} subtasks
                </div>
                """, unsafe_allow_html=True)
                st.progress(sub_pct)

        with col_actions:
            col_a1, col_a2, col_a3 = st.columns(3)
            with col_a1:
                if not is_completed:
                    if st.button("✅", key=f"done_{task['id']}", help="Mark complete", type="tertiary"):
                        db.update_task(task['id'], status='completed')
                        st.rerun() # Fragment rerun
                else:
                    if st.button("↩️", key=f"undo_{task['id']}", help="Reactivate", type="tertiary"):
                        db.update_task(task['id'], status='active')
                        st.rerun() # Fragment rerun
            with col_a2:
                if st.button("✏️", key=f"edit_{task['id']}", help="Edit", type="tertiary"):
                    st.session_state[f'editing_task_{task["id"]}'] = True
                    st.rerun()
            with col_a3:
                # Delete triggers a full app rerun because the list structure changes
                if st.button("🗑️", key=f"del_task_{task['id']}", help="Delete", type="tertiary"):
                    request_delete('task', task['id'], task.get('title') or '')
                    # The modal will run at top-level and perform the actual delete if confirmed.

        # Edit task inline
        if st.session_state.get(f'editing_task_{task["id"]}', False):
            with st.form(f"edit_form_{task['id']}"):
                new_title = st.text_input("Title", value=task['title'])
                new_desc = st.text_area("Description", value=task['description'] or "", height=60)
                new_cat = st.selectbox(
                    "Category",
                    options=[c['id'] for c in categories],
                    index=next((i for i, c in enumerate(categories) if c['id'] == task['category_id']), 0),
                    format_func=lambda x: next(
                        (f"{c['icon']} {c['name']}" for c in categories if c['id'] == x), "Unknown"
                    ),
                    key=f"edit_cat_{task['id']}"
                )
                curr_goal_h = (task.get('goal_minutes') or 0) / 60
                new_goal_h = st.number_input(
                    "Goal Hours (0 = no goal)",
                    min_value=0.0, max_value=10000.0, value=float(curr_goal_h), step=0.5
                )
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.form_submit_button("Save", type="primary", use_container_width=True):
                        db.update_task(task['id'], title=new_title, description=new_desc,
                                       category_id=new_cat, goal_minutes=new_goal_h * 60)
                        st.session_state.pop(f'editing_task_{task["id"]}', None)
                        st.rerun()
                with col_cancel:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        st.session_state.pop(f'editing_task_{task["id"]}', None)
                        st.rerun()

    # Subtasks & Log Time (rendered within the fragment so updates propagate)
    _render_subtask_section(task['id'], subtasks, text_col, muted_col)
    _render_log_time_section(user_id, task['id'], task['title'])

    st.divider()


@st.fragment
def _render_add_task_form(user_id, categories, selected_cat_id):
    """Fragment for Add Task form to allow fast toggling."""
    if 'add_task_open' not in st.session_state:
        st.session_state['add_task_open'] = False
    _at_open = st.session_state['add_task_open']

    # Toggle button - NO explicit rerun needed for fragment update
    if st.button(
        "▼ ➕ Add New Task" if _at_open else "➕ Add New Task",
        key="btn_toggle_add_task",
        use_container_width=True,
        type="secondary"
    ):
        st.session_state['add_task_open'] = not _at_open
        st.rerun()  # Fragment rerun

    if st.session_state['add_task_open']:
        with st.form("new_task_form", clear_on_submit=True):
            task_title = st.text_input("Task Title", placeholder="What do you need to do?")
            task_desc = st.text_area("Description (optional)", placeholder="Details...", height=80)

            # If a category filter is active, use it; otherwise show dropdown
            preselected_cat_id = selected_cat_id

            if preselected_cat_id:
                task_cat = preselected_cat_id
                col_goal_only = st.columns([1])[0]
                with col_goal_only:
                    task_goal = st.number_input("Goal Hours (Optional)", min_value=0.0, step=0.5, value=0.0)
            else:
                col_cat, col_goal = st.columns([2, 1])
                with col_cat:
                    task_cat = st.selectbox(
                        "Category",
                        options=[c['id'] for c in categories],
                        format_func=lambda x: next(
                            f"{c['icon']} {c['name']}" for c in categories if c['id'] == x
                        )
                    )
                with col_goal:
                    task_goal = st.number_input("Goal Hours (Optional)", min_value=0.0, step=0.5, value=0.0)

            if st.form_submit_button("Add Task", use_container_width=True, type="primary"):
                if task_title.strip():
                    db.create_task(
                        user_id, task_cat, task_title.strip(),
                        task_desc.strip(), goal_minutes=task_goal*60
                    )
                    st.success(f"Task added!")
                    st.session_state['add_task_open'] = False  # auto-close
                    st.rerun()  # FULL App rerun needed to update task list
                else:
                    st.warning("Enter a task title.")


def format_minutes(minutes: float) -> str:
    """Format minutes to a human-readable string with hours, minutes, and seconds."""
    total_seconds = int(minutes * 60)
    hours = total_seconds // 3600
    mins = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    
    if hours > 0:
        return f"{hours}h {mins}m {secs}s"
    elif mins > 0:
        return f"{mins}m {secs}s"
    else:
        return f"{secs}s"


def render_tasks_page():
    user_id = st.session_state['user_id']
    categories = db.get_categories(user_id)
    # ── Theme-aware colors ──────────────────────────────────
    _dark = st.session_state.get('theme', 'light') == 'dark'
    _card_bg   = "#1E2130" if _dark else "#FFFFFF"
    _done_bg   = "#0C2D21" if _dark else "#F0FFF4"
    _text_col  = "#E5E7EB" if _dark else "#374151"
    _muted_col = "#9CA3AF"
    # Render any queued toasts (ensures message shows after rerun)
    for k in list(st.session_state.keys()):
        if k.startswith('_pending_log_toast_'):
            st.toast(st.session_state[k], icon="⏱")
            st.session_state.pop(k, None)
    # If we're entering the Tasks page from another page, reset any open panels
    if not st.session_state.get('_tasks_initialized', False):
        for k in list(st.session_state.keys()):
            if k.startswith('sub_open_') or k.startswith('log_open_'):
                st.session_state[k] = False
        # Also ensure the Add Task fragment is closed when returning to Tasks
        st.session_state['add_task_open'] = False
        st.session_state['_tasks_initialized'] = True
    
    # If a delete confirmation was requested elsewhere, show a modal here
    if st.session_state.get('confirm_delete'):
        cd = st.session_state['confirm_delete']
        modal_shown = False
        if hasattr(st, 'modal'):
            try:
                with st.modal("Confirm Deletion"):
                    modal_shown = True
                    kind = cd.get('kind')
                    name = cd.get('name') or ''
                    st.markdown(f"Are you sure you want to delete **{kind}**: **{name}**? This action cannot be undone.")
                    col_yes, col_no = st.columns([1, 1])
                    with col_yes:
                        if st.button("Yes, delete", key="__confirm_delete_yes__", type="primary"):
                            try:
                                if kind == 'category':
                                    db.delete_category(cd['id'])
                                    if st.session_state.get('filter_cat_id') == cd['id']:
                                        st.session_state.pop('filter_cat_id', None)
                                elif kind == 'task':
                                    db.delete_task(cd['id'])
                                elif kind == 'subtask':
                                    db.delete_subtask(cd['id'])
                                elif kind == 'timelog':
                                    db.delete_time_log(cd['id'])
                            finally:
                                st.session_state.pop('confirm_delete', None)
                                st.rerun()
                    with col_no:
                        if st.button("Cancel", key="__confirm_delete_cancel__"):
                            st.session_state.pop('confirm_delete', None)
                            st.rerun()
            except Exception:
                modal_shown = False

        # Fallback UI if st.modal is not available or failed: render an inline confirmation box
        if not modal_shown:
            box = st.container()
            with box:
                kind = cd.get('kind')
                name = cd.get('name') or ''
                st.markdown(f"### Confirm delete: {kind} — {name}")
                st.markdown("This action cannot be undone.")
                col_yes, col_no = st.columns([1, 1])
                with col_yes:
                    if st.button("Yes, delete", key="__confirm_delete_yes_fb__", type="primary"):
                        try:
                            if kind == 'category':
                                db.delete_category(cd['id'])
                                if st.session_state.get('filter_cat_id') == cd['id']:
                                    st.session_state.pop('filter_cat_id', None)
                            elif kind == 'task':
                                db.delete_task(cd['id'])
                            elif kind == 'subtask':
                                db.delete_subtask(cd['id'])
                            elif kind == 'timelog':
                                db.delete_time_log(cd['id'])
                        finally:
                            st.session_state.pop('confirm_delete', None)
                            st.rerun()
                with col_no:
                    if st.button("Cancel", key="__confirm_delete_cancel_fb__"):
                        st.session_state.pop('confirm_delete', None)
                        st.rerun()
    
    # Fix dark mode styles for expanders inside tasks
    st.markdown(f"""
    <style>
    div[data-testid="stExpander"] {{
        background-color: {_card_bg} !important;
        border: 1px solid {_muted_col}40 !important;
        color: {_text_col} !important;
    }}
    div[data-testid="stExpander"] > details > summary {{
        color: {_text_col} !important;
    }}
    div[data-testid="stExpander"] > details > summary svg {{
        fill: {_text_col} !important; color: {_text_col} !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    # Sidebar rendering is moved to render_sidebar(user_id) so it can be shown on all pages.

    # ─── Main Content: Tasks ──────────────────────────────────
    st.markdown("## 📋 My Tasks")

    if not categories:
        st.info("👈 Start by creating a category in the sidebar.")
        return

    # ─ Filter bar (synced with sidebar category selection) ─
    sidebar_cat_id = st.session_state.get('filter_cat_id', None)

    col_filter, col_status = st.columns([3, 2])
    with col_filter:
        cat_options = {"All Categories": None}
        for c in categories:
            cat_options[f"{c['icon']} {c['name']}"] = c['id']
        
        # Ensure 'main_cat_filter' in session_state matches sidebar_cat_id
        if 'main_cat_filter' not in st.session_state:
            st.session_state['main_cat_filter'] = "All Categories"
        
        # Callback to update filter_cat_id BEFORE restart
        def on_cat_change():
            sel = st.session_state['main_cat_filter']
            st.session_state['filter_cat_id'] = cat_options.get(sel)

        selected_cat_name = st.selectbox(
            "Filter by Category",
            options=list(cat_options.keys()),
            label_visibility="collapsed",
            key="main_cat_filter",
            on_change=on_cat_change
        )
        selected_cat_id = cat_options[selected_cat_name] # Already synced via on_change


    with col_status:
        status_filter = st.selectbox(
            "Status",
            ["active", "completed", "all"],
            label_visibility="collapsed"
        )

    # Add new task (Fragment)
    _render_add_task_form(user_id, categories, selected_cat_id)

    # Task list
    status_param = None if status_filter == "all" else status_filter
    tasks = db.get_tasks(user_id, category_id=selected_cat_id, status=status_param)

    if not tasks:
        st.markdown(
            """<div style='text-align:center; padding:3rem; color:#9CA3AF;'>
                <p style='font-size:3rem;'>📝</p>
                <p>No tasks found. Create one above!</p>
            </div>""",
            unsafe_allow_html=True
        )
        return

    # Sidebar-to-main immediate sync is handled in the button click handler;
    # remove any unconditional rerun to avoid double-rerun behavior.

    # Prefetch subtasks for all tasks to avoid N+1 queries
    task_ids = [t['id'] for t in tasks]
    subtasks_map = db.get_subtasks_for_tasks(task_ids)

    for task in tasks:
        # Render each task as an isolated fragment for high performance
        _render_task_item(
            task, user_id, categories, _text_col, _muted_col, _card_bg, _done_bg,
            subtasks=subtasks_map.get(task['id'], [])
        )
