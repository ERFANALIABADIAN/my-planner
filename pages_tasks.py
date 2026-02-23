"""
Tasks page - Category & Task management with subtasks.
"""

import streamlit as st
from datetime import date
import database as db

# ─── Icon picker options ────────────────────────────────────────────
ICONS = [
    "📁", "📂", "📋", "📌", "📍", "🗂", "🖥", "💻", "📱",
    "📚", "📖", "📧", "📦", "💰", "💳", "🏆", "🎯",
    "🚀", "⚡", "🔥", "💡", "⭐", "🌟", "🌱", "🎨",
    "🎵", "🎸", "🥋", "🏃", "💪", "🧠", "🔬",
    "🌍", "🏠", "🏫", "🏥", "🏭", "🔑", "🔧",
    "📊", "📈", "📉", "🤝", "👀", "✅", "📏",
]


def _subtask_toggle_cb(sub_id: int):
    """Callback executed when a subtask checkbox changes. No rerun needed."""
    db.toggle_subtask(sub_id)
    # Invalidate the subtask cache so the updated count is reflected
    try:
        db.get_subtasks.clear()
    except Exception:
        pass



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

    # ─── Sidebar: Category Management ─────────────────────────
    with st.sidebar:
        st.markdown("### 📁 Categories")

        with st.expander("➕ New Category", expanded=False):
            cat_name = st.text_input("Name", placeholder="e.g. Programming", key="new_cat_name")

            # Icon picker
            st.markdown("**Icon** – click to select:")
            picked = st.session_state.get('new_cat_icon', '📁')
            icon_cols = st.columns(9)
            for idx, ico in enumerate(ICONS):
                with icon_cols[idx % 9]:
                    btn_type = "primary" if ico == picked else "secondary"
                    if st.button(ico, key=f"ico_{idx}", type=btn_type):
                        st.session_state['new_cat_icon'] = ico
                        st.rerun()

            cat_color = st.color_picker("Color", value="#4A90D9", key="new_cat_color")
            if st.button("Create", use_container_width=True, type="primary", key="create_cat_btn"):
                if cat_name.strip():
                    try:
                        db.create_category(user_id, cat_name.strip(), cat_color, picked)
                        st.success(f"Created: {picked} {cat_name}")
                        st.session_state.pop('new_cat_name', None)
                        st.session_state['new_cat_icon'] = '📁'
                        st.rerun()
                    except Exception:
                        st.error("Category already exists!")
                else:
                    st.warning("Enter a name.")

        # Category list – click to filter, trash to delete
        if categories:
            filter_id = st.session_state.get('filter_cat_id', None)
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
                        # Toggle filter: click same category again to deselect
                        if is_active:
                            st.session_state.pop('filter_cat_id', None)
                        else:
                            st.session_state['filter_cat_id'] = cat['id']
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_cat_{cat['id']}", help="Delete", type="tertiary"):
                        db.delete_category(cat['id'])
                        if st.session_state.get('filter_cat_id') == cat['id']:
                            st.session_state.pop('filter_cat_id', None)
                        st.rerun()
        else:
            st.info("No categories yet. Create one above!")

    # ─── Main Content: Tasks ──────────────────────────────────
    st.markdown("## 📋 My Tasks")

    if not categories:
        st.info("👈 Start by creating a category in the sidebar.")
        return

    # ─ Filter bar (synced with sidebar category selection) ─
    # Sync sidebar selection => dropdown
    sidebar_cat_id = st.session_state.get('filter_cat_id', None)

    col_filter, col_status = st.columns([3, 2])
    with col_filter:
        cat_options = {"All Categories": None}
        for c in categories:
            cat_options[f"{c['icon']} {c['name']}"] = c['id']
        # Find the default index based on sidebar selection
        keys_list = list(cat_options.keys())
        vals_list = list(cat_options.values())
        default_idx = vals_list.index(sidebar_cat_id) if sidebar_cat_id in vals_list else 0
        selected_cat_name = st.selectbox(
            "Filter by Category",
            options=keys_list,
            index=default_idx,
            label_visibility="collapsed",
            key="main_cat_filter"
        )
        selected_cat_id = cat_options[selected_cat_name]
        # Keep sidebar in sync when dropdown changes
        if selected_cat_id != sidebar_cat_id:
            if selected_cat_id is None:
                st.session_state.pop('filter_cat_id', None)
            else:
                st.session_state['filter_cat_id'] = selected_cat_id
    with col_status:
        status_filter = st.selectbox(
            "Status",
            ["active", "completed", "all"],
            label_visibility="collapsed"
        )

    # Add new task
    with st.expander("➕ Add New Task", expanded=False):
        with st.form("new_task_form", clear_on_submit=True):
            task_title = st.text_input("Task Title", placeholder="What do you need to do?")
            task_desc = st.text_area("Description (optional)", placeholder="Details...", height=80)
            task_cat = st.selectbox(
                "Category",
                options=[c['id'] for c in categories],
                format_func=lambda x: next(
                    f"{c['icon']} {c['name']}" for c in categories if c['id'] == x
                )
            )
            if st.form_submit_button("Add Task", use_container_width=True, type="primary"):
                if task_title.strip():
                    db.create_task(user_id, task_cat, task_title.strip(), task_desc.strip())
                    st.success(f"Task added!")
                    st.rerun()
                else:
                    st.warning("Enter a task title.")

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

    for task in tasks:
        total_time = db.get_task_total_time(task['id'])
        subtasks = db.get_subtasks(task['id'])
        done_count = sum(1 for s in subtasks if s['is_done'])
        progress = done_count / len(subtasks) if subtasks else 0

        is_completed = task['status'] == 'completed'
        border_color = task['category_color']

        with st.container():
            st.markdown(
                f"""<div style='border-left: 4px solid {border_color}; padding: 0.5rem 1rem;
                     margin-bottom: 0.5rem; border-radius: 0 8px 8px 0;
                     background: {"#F0FFF4" if is_completed else "#FFFFFF"};
                     opacity: {"0.7" if is_completed else "1"};'>
                </div>""",
                unsafe_allow_html=True
            )

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
                if subtasks:
                    st.progress(progress, text=f"{done_count}/{len(subtasks)}")

            with col_actions:
                # All action buttons are borderless (icon-only)
                col_a1, col_a2, col_a3 = st.columns(3)
                with col_a1:
                    if not is_completed:
                        if st.button("✅", key=f"done_{task['id']}", help="Mark complete", type="tertiary"):
                            db.update_task(task['id'], status='completed')
                            st.rerun()
                    else:
                        if st.button("↩️", key=f"undo_{task['id']}", help="Reactivate", type="tertiary"):
                            db.update_task(task['id'], status='active')
                            st.rerun()
                with col_a2:
                    if st.button("✏️", key=f"edit_{task['id']}", help="Edit", type="tertiary"):
                        st.session_state[f'editing_task_{task["id"]}'] = True
                with col_a3:
                    if st.button("🗑️", key=f"del_task_{task['id']}", help="Delete", type="tertiary"):
                        db.delete_task(task['id'])
                        st.rerun()

            # Edit task inline
            if st.session_state.get(f'editing_task_{task["id"]}', False):
                with st.form(f"edit_form_{task['id']}"):
                    new_title = st.text_input("Title", value=task['title'])
                    new_desc = st.text_area("Description", value=task['description'] or "", height=60)
                    new_cat = st.selectbox(
                        "Category",
                        options=[c['id'] for c in categories],
                        index=next(i for i, c in enumerate(categories) if c['id'] == task['category_id']),
                        format_func=lambda x: next(
                            f"{c['icon']} {c['name']}" for c in categories if c['id'] == x
                        ),
                        key=f"edit_cat_{task['id']}"
                    )
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.form_submit_button("Save", type="primary", use_container_width=True):
                            db.update_task(task['id'], title=new_title, description=new_desc, category_id=new_cat)
                            st.session_state.pop(f'editing_task_{task["id"]}', None)
                            st.rerun()
                    with col_cancel:
                        if st.form_submit_button("Cancel", use_container_width=True):
                            st.session_state.pop(f'editing_task_{task["id"]}', None)
                            st.rerun()

            # ─── Subtasks ──────────────────────────────────
            sub_label = f"Subtasks ({done_count}/{len(subtasks)})" if subtasks else "Add Subtasks"
            with st.expander(sub_label, expanded=False):
                # Align checkbox with text at same vertical level
                st.markdown("""
                <style>
                [data-testid="stCheckbox"] { margin-bottom:0 !important; padding-bottom:0 !important; }
                [data-testid="stCheckbox"] > label { padding-top:0.3rem !important; }
                </style>""", unsafe_allow_html=True)

                for sub in subtasks:
                    col_check, col_name, col_sub_del = st.columns([0.5, 6, 0.5])
                    with col_check:
                        # on_change fires immediately – no manual comparison or rerun needed
                        st.checkbox(
                            "done", value=bool(sub['is_done']),
                            key=f"sub_{sub['id']}",
                            label_visibility="collapsed",
                            on_change=_subtask_toggle_cb,
                            args=(sub['id'],)
                        )
                    with col_name:
                        style = "text-decoration:line-through; color:#9CA3AF;" if sub['is_done'] else ""
                        st.markdown(
                            f"<p style='margin:0; padding-top:0.3rem; {style}'>{sub['title']}</p>",
                            unsafe_allow_html=True
                        )
                    with col_sub_del:
                        if st.button("🗑️", key=f"del_sub_{sub['id']}", help="Delete", type="tertiary"):
                            db.delete_subtask(sub['id'])
                            st.rerun()

                # Add subtask
                col_new_sub, col_add_sub = st.columns([5, 1])
                with col_new_sub:
                    new_sub_title = st.text_input(
                        "New subtask",
                        placeholder="Add a subtask...",
                        key=f"new_sub_{task['id']}",
                        label_visibility="collapsed"
                    )
                with col_add_sub:
                    if st.button("➕", key=f"add_sub_{task['id']}"):
                        if new_sub_title.strip():
                            db.create_subtask(task['id'], new_sub_title.strip())
                            st.rerun()

            # ─── Quick Time Log ────────────────────────────
            with st.expander("⏱ Log Time", expanded=False):
                col_dur, col_date, col_note, col_add = st.columns([2, 2, 3, 1])
                with col_dur:
                    log_mins = st.number_input(
                        "Minutes", min_value=1, value=25,
                        key=f"log_min_{task['id']}",
                        label_visibility="collapsed"
                    )
                with col_date:
                    log_date = st.date_input(
                        "Date", value=date.today(),
                        key=f"log_date_{task['id']}",
                        label_visibility="collapsed"
                    )
                with col_note:
                    log_note = st.text_input(
                        "Note", placeholder="What did you work on?",
                        key=f"log_note_{task['id']}",
                        label_visibility="collapsed"
                    )
                with col_add:
                    if st.button("💾", key=f"save_log_{task['id']}"):
                        db.add_time_log(
                            user_id, task['id'],
                            log_mins,
                            log_date.isoformat(),
                            log_note, "manual"
                        )
                        st.success(f"Logged {format_minutes(log_mins)}!")
                        st.rerun()

            st.divider()
