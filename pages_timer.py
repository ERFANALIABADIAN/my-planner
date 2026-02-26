"""
Timer page - Stopwatch/Pomodoro timer with time logging.
Uses JavaScript-based timer for smooth live counting.
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, date
import database as db

# Helper to request confirmation before deleting items (local to timer page)
def request_delete(kind: str, obj_id: int, name: str = None):
    st.session_state['confirm_delete'] = {'kind': kind, 'id': obj_id, 'name': name}
    st.rerun()

# Keep the session alive every 3 minutes when the timer is running.
# streamlit-autorefresh is already in requirements.txt.
try:
    from streamlit_autorefresh import st_autorefresh
    _HAS_AUTOREFRESH = True
except ImportError:
    _HAS_AUTOREFRESH = False


def format_seconds(seconds: int) -> str:
    """Format seconds into MM:SS or HH:MM:SS."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def js_timer_component(elapsed_seconds: int, is_running: bool, mode: str = "stopwatch", total_seconds: int = 0):
    """Render a JavaScript-based live timer that counts without page refresh.
    Also embeds a silent keepalive fetch so the Streamlit session never idles out."""
    
    # Check theme for text color
    is_dark = st.session_state.get('theme', 'light') == 'dark'
    text_color = "#E0E0E0" if is_dark else "#1E1E2E"
    sub_text_color = "#A0A0A0" if is_dark else "#6B7280"

    keepalive_js = """
        // Keepalive: ping the health endpoint every 90s to prevent session timeout
        setInterval(function() {
            try { fetch('/_stcore/health', {cache:'no-store'}); } catch(e) {}
        }, 90000);
    """ if is_running else ""
    timer_html = f"""
    <div id="timer-container" style="text-align:center; padding:1.5rem 0;">
        <div id="timer-display" style="font-size:4rem; font-weight:800; color:{text_color};
             font-family:'Courier New', monospace; letter-spacing:0.2rem; user-select:none;">
            00:00
        </div>
        <div id="timer-status" style="margin-top:0.5rem; font-size:0.85rem; color:{sub_text_color};"></div>
    </div>
    <script>
        (function() {{
            var startElapsed = {elapsed_seconds};
            var isRunning = {'true' if is_running else 'false'};
            var mode = "{mode}";
            var totalSeconds = {total_seconds};
            var startTime = Date.now();
            var defaultTextColor = "{text_color}";

            function formatTime(sec) {{
                sec = Math.max(0, Math.floor(sec));
                var h = Math.floor(sec / 3600);
                var m = Math.floor((sec % 3600) / 60);
                var s = sec % 60;
                if (h > 0) {{
                    return String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
                }}
                return String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
            }}

            function update() {{
                var display = document.getElementById('timer-display');
                var status = document.getElementById('timer-status');
                if (!display) return;

                var current;
                if (isRunning) {{
                    current = startElapsed + Math.floor((Date.now() - startTime) / 1000);
                }} else {{
                    current = startElapsed;
                }}

                if (mode === 'pomodoro') {{
                    var remaining = Math.max(0, totalSeconds - current);
                    display.textContent = formatTime(remaining);
                    display.style.color = remaining === 0 ? '#EF4444' : defaultTextColor;
                    if (remaining === 0 && isRunning) {{
                        status.textContent = '🍅 Time is up!';
                        status.style.color = '#EF4444';
                    }}
                }} else {{
                    display.textContent = formatTime(current);
                    display.style.color = defaultTextColor;
                }}

                if (isRunning) {{
                    status.innerHTML = '<span style="animation:pulse 2s infinite;">🔴 Running...</span>';
                }} else if (current > 0) {{
                    status.textContent = '⏸ Paused';
                }} else {{
                    status.textContent = '';
                }}
            }}

            update();
            if (isRunning) {{
                setInterval(update, 200);
            }}
            {keepalive_js}
        }})();
    </script>
    <style>
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.4; }}
        }}
    </style>
    """
    components.html(timer_html, height=160)


def render_timer_page():
    # Ensure Tasks page will reset its panels when user navigates back
    st.session_state['_tasks_initialized'] = False
    user_id = st.session_state['user_id']
    categories = db.get_categories(user_id)
    tasks = db.get_tasks(user_id, status='active')

    st.markdown("## ⏱ Focus Timer")

    if not tasks:
        st.info("You need active tasks to use the timer. Go to Tasks page to create some!")
        return

    # ─── Build task options BEFORE columns so we can use them for sync ───
    task_options = {}
    for t in tasks:
        label = f"{t['category_icon']} {t['title']} ({t['category_name']})"
        task_options[label] = t['id']

    # ─── Initialize session state ─────────────────────────────────────────
    if 'timer_running' not in st.session_state:
        st.session_state['timer_running'] = False
    if 'timer_start' not in st.session_state:
        st.session_state['timer_start'] = None
    if 'timer_elapsed' not in st.session_state:
        st.session_state['timer_elapsed'] = 0
    if 'timer_paused_elapsed' not in st.session_state:
        st.session_state['timer_paused_elapsed'] = 0

    # ─── Load + sync from DB (must run before columns so selectbox is correct) ──
    active_timer_db = db.get_active_timer(user_id)
    if active_timer_db and not st.session_state.get('db_synced'):
        db_running = bool(active_timer_db['is_running'])
        db_start = (datetime.fromisoformat(active_timer_db['start_time'])
                    if active_timer_db['start_time'] else None)
        st.session_state['timer_running']        = db_running
        st.session_state['timer_start']          = db_start
        st.session_state['timer_paused_elapsed'] = active_timer_db['paused_elapsed']
        st.session_state['timer_task_id']        = active_timer_db['task_id']
        st.session_state['timer_subtask_id']     = active_timer_db['subtask_id']
        st.session_state['pomodoro_minutes']     = active_timer_db['pomodoro_minutes']
        st.session_state['db_synced'] = True

    # ─── Sync selectbox key → active task (timer running or paused) ─────────
    # This must happen BEFORE st.selectbox() renders so the widget shows correctly.
    active_task_id = st.session_state.get('timer_task_id')
    if active_task_id and (st.session_state['timer_running']
                           or st.session_state.get('timer_paused_elapsed', 0) > 0):
        correct_label = next(
            (lbl for lbl, tid in task_options.items() if tid == active_task_id), None
        )
        if correct_label:
            st.session_state['timer_task_select'] = correct_label

    # ─── Sync subtask selectbox ───────────────────────────────────────────────
    active_subtask_id = st.session_state.get('timer_subtask_id')
    if active_task_id and active_subtask_id:
        _active_subs = db.get_subtasks(active_task_id)
        correct_sub_label = next(
            (s['title'] for s in _active_subs if s['id'] == active_subtask_id), None
        )
        if correct_sub_label:
            st.session_state['timer_subtask_select'] = correct_sub_label

    # Render the interactive timer dashboard as a fragment for high performance
    # If a delete confirmation was requested elsewhere, show a modal here
    if st.session_state.get('confirm_delete'):
        cd = st.session_state['confirm_delete']
        # Scroll to top so the confirmation modal is visible without manual scrolling
        try:
            components.html("<script>window.scrollTo({top:0,behavior:'smooth'});</script>", height=1)
        except Exception:
            pass
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
                        if st.button("Yes, delete", key="__timer_confirm_delete_yes__", type="primary"):
                            try:
                                if kind == 'timelog':
                                    db.delete_time_log(cd['id'])
                                elif kind == 'task':
                                    db.delete_task(cd['id'])
                                elif kind == 'subtask':
                                    db.delete_subtask(cd['id'])
                                elif kind == 'category':
                                    db.delete_category(cd['id'])
                            finally:
                                st.session_state.pop('confirm_delete', None)
                                st.rerun()
                    with col_no:
                        if st.button("Cancel", key="__timer_confirm_delete_cancel__"):
                            st.session_state.pop('confirm_delete', None)
                            st.rerun()
            except Exception:
                modal_shown = False

        # Fallback inline confirmation if modal isn't supported
        if not modal_shown:
            box = st.container()
            with box:
                kind = cd.get('kind')
                name = cd.get('name') or ''
                st.markdown(f"### Confirm delete: {kind} — {name}")
                st.markdown("This action cannot be undone.")
                col_yes, col_no = st.columns([1, 1])
                with col_yes:
                    if st.button("Yes, delete", key="__timer_confirm_delete_yes_fb__", type="primary"):
                        try:
                            if kind == 'timelog':
                                db.delete_time_log(cd['id'])
                            elif kind == 'task':
                                db.delete_task(cd['id'])
                            elif kind == 'subtask':
                                db.delete_subtask(cd['id'])
                            elif kind == 'category':
                                db.delete_category(cd['id'])
                        finally:
                            st.session_state.pop('confirm_delete', None)
                            st.rerun()
                with col_no:
                    if st.button("Cancel", key="__timer_confirm_delete_cancel_fb__"):
                        st.session_state.pop('confirm_delete', None)
                        st.rerun()

    _render_timer_dashboard(user_id, tasks, task_options)

    # ─── Today's Sessions ─────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Today's Sessions")


@st.fragment
def _render_timer_dashboard(user_id, tasks, task_options):
    """Fragment-based timer dashboard for snappy UI updates without full page refreshes."""
    
    # ─── Timer Configuration ──────────────────────────────────
    col_config, col_timer = st.columns([1, 1])

    with col_config:
        st.markdown("### 🎯 Select Task")

        selected_task_label = st.selectbox(
            "Task",
            options=list(task_options.keys()),
            label_visibility="collapsed",
            key="timer_task_select"
        )
        selected_task_id = task_options[selected_task_label]

        # Optional subtask selection
        subtasks = db.get_subtasks(selected_task_id)
        selected_subtask_id = None
        if subtasks:
            undone_subtasks = [s for s in subtasks if not s['is_done']]
            if undone_subtasks:
                sub_options = {"None": None}
                for s in undone_subtasks:
                    sub_options[s['title']] = s['id']
                selected_sub_label = st.selectbox(
                    "Subtask (optional)",
                    options=list(sub_options.keys()),
                    key="timer_subtask_select"
                )
                selected_subtask_id = sub_options[selected_sub_label]

        st.markdown("---")
        st.markdown("### ⏰ Timer Mode")

        timer_mode = st.radio(
            "Mode",
            ["⏱ Stopwatch (Count Up)", "🍅 Pomodoro (Count Down)"],
            label_visibility="collapsed",
            horizontal=True
        )

        if "🍅" in timer_mode:
            preset_col1, preset_col2, preset_col3 = st.columns(3)
            with preset_col1:
                # Type primary if minutes match
                if st.button("25 min", use_container_width=True,
                             type="primary" if st.session_state.get('pomodoro_minutes', 25) == 25 else "secondary"):
                    st.session_state['pomodoro_minutes'] = 25
            with preset_col2:
                if st.button("45 min", use_container_width=True,
                             type="primary" if st.session_state.get('pomodoro_minutes') == 45 else "secondary"):
                    st.session_state['pomodoro_minutes'] = 45
            with preset_col3:
                if st.button("60 min", use_container_width=True,
                             type="primary" if st.session_state.get('pomodoro_minutes') == 60 else "secondary"):
                    st.session_state['pomodoro_minutes'] = 60

            # Use a separate key for the number input to avoid session/theme issues
            if 'custom_pomodoro_minutes' not in st.session_state:
                st.session_state['custom_pomodoro_minutes'] = st.session_state.get('pomodoro_minutes', 25)

            custom_min = st.number_input(
                "Custom (minutes)",
                min_value=1, max_value=240,
                value=st.session_state['custom_pomodoro_minutes'],
                key='custom_pomodoro_minutes',
                step=1
            )

            # Only update pomodoro_minutes if the value changed
            if custom_min != st.session_state.get('pomodoro_minutes', 25):
                st.session_state['pomodoro_minutes'] = custom_min
                # If there's an active timer saved in DB, update its pomodoro_minutes
                try:
                    if st.session_state.get('timer_task_id') is not None or st.session_state.get('db_synced'):
                        start_iso = st.session_state['timer_start'].isoformat() if st.session_state.get('timer_start') else ""
                        db.save_active_timer(
                            user_id,
                            st.session_state.get('timer_task_id', selected_task_id),
                            start_iso,
                            st.session_state.get('timer_paused_elapsed', 0),
                            bool(st.session_state.get('timer_running', False)),
                            'pomodoro',
                            custom_min,
                            st.session_state.get('timer_subtask_id', selected_subtask_id)
                        )
                except Exception:
                    pass

    with col_timer:
        # Calculate elapsed time
        if st.session_state['timer_running'] and st.session_state['timer_start']:
            elapsed = st.session_state['timer_paused_elapsed'] + \
                      (datetime.now() - st.session_state['timer_start']).total_seconds()
        else:
            elapsed = st.session_state.get('timer_paused_elapsed', 0)

        elapsed = int(elapsed)

        # Centered Header
        st.markdown("<h3 style='text-align: center;'>🕐 Timer</h3>", unsafe_allow_html=True)
        
        # Show what task is running if loaded from DB separate from selection
        if st.session_state.get('timer_running') and st.session_state.get('timer_task_id'):
            # Find task name
            active_t_name = next((t['title'] for t in tasks if t['id'] == st.session_state['timer_task_id']), "Unknown Task")
            st.markdown(f"<div style='text-align:center; color:#9CA3AF; font-size:0.9rem;'>Running: <b>{active_t_name}</b></div>", unsafe_allow_html=True)

        # Display timer using JavaScript component (smooth, no lag)
        mode_str = "pomodoro" if "🍅" in timer_mode else "stopwatch"
        if mode_str == "pomodoro":
            total_seconds = st.session_state.get('pomodoro_minutes', 25) * 60
            js_timer_component(
                elapsed_seconds=elapsed,
                is_running=st.session_state['timer_running'],
                mode="pomodoro",
                total_seconds=total_seconds
            )
        else:
            js_timer_component(
                elapsed_seconds=elapsed,
                is_running=st.session_state['timer_running'],
                mode="stopwatch"
            )

        # Timer Controls
        do_save = False
        final_elapsed = 0
        pom_mins = st.session_state.get('pomodoro_minutes', 25)

        st.write("") # Spacer

        if not st.session_state['timer_running']:
            if elapsed == 0:
                # State 1: Not started - Centered Start Button
                _, col_center, _ = st.columns([1, 2, 1])
                with col_center:
                    if st.button("Start", use_container_width=True, type="primary"):
                        st.session_state['timer_running'] = True
                        st.session_state['timer_start'] = datetime.now()
                        st.session_state['timer_task_id'] = selected_task_id
                        st.session_state['timer_subtask_id'] = selected_subtask_id
                        # Save to DB
                        db.save_active_timer(
                            user_id, selected_task_id, 
                            st.session_state['timer_start'].isoformat(), 
                            0, True, mode_str, pom_mins, selected_subtask_id
                        )
                        st.session_state['db_synced'] = True
                        st.rerun()  # Force rerun so timer UI updates instantly
            else:
                # State 3: Paused - Resume | Stop | Reset
                col_resume, col_stop, col_reset = st.columns(3)
                with col_resume:
                    if st.button("Resume", use_container_width=True, type="primary"):
                        st.session_state['timer_running'] = True
                        st.session_state['timer_start'] = datetime.now()
                        
                        # Update DB
                        db.save_active_timer(
                            user_id, st.session_state.get('timer_task_id', selected_task_id), 
                            st.session_state['timer_start'].isoformat(), 
                            st.session_state['timer_paused_elapsed'], 
                            True, mode_str, pom_mins, 
                            st.session_state.get('timer_subtask_id')
                        )
                        st.session_state['db_synced'] = True
                        # Ensure UI switches to running immediately
                        st.rerun()
                with col_stop:
                    if st.button("⏹ Stop & Save", use_container_width=True, key="stop_paused"):
                        final_elapsed = st.session_state.get('timer_paused_elapsed', 0)
                        do_save = True
                with col_reset:
                    if st.button("Reset", use_container_width=True):
                        st.session_state['timer_paused_elapsed'] = 0
                        st.session_state['timer_elapsed'] = 0
                        db.delete_active_timer(user_id) # Clear DB
                        st.session_state['db_synced'] = False
                        st.rerun() 
        else:
            # State 2: Running - Pause | Stop
            col_pause, col_stop = st.columns(2)
            with col_pause:
                if st.button("⏸ Pause", use_container_width=True):
                    # Recalculate elapsed at pause moment for accuracy
                    if st.session_state['timer_start']:
                        current_elapsed = st.session_state['timer_paused_elapsed'] + \
                                        (datetime.now() - st.session_state['timer_start']).total_seconds()
                    else:
                        current_elapsed = st.session_state.get('timer_paused_elapsed', 0)
                    st.session_state['timer_running'] = False
                    st.session_state['timer_paused_elapsed'] = current_elapsed
                    st.session_state['timer_start'] = None
                    
                    # Update DB (save pause state)
                    db.save_active_timer(
                        user_id, st.session_state.get('timer_task_id', selected_task_id), 
                        "", # No start time because paused
                        current_elapsed, 
                        False, mode_str, pom_mins, 
                        st.session_state.get('timer_subtask_id')
                    )
                    # Ensure UI shows paused state immediately
                    st.rerun()

            with col_stop:
                if st.button("⏹ Stop & Save", use_container_width=True, type="primary", key="stop_running"):
                    # CRITICAL: Recalculate elapsed time RIGHT NOW for accuracy
                    if st.session_state['timer_start']:
                        final_elapsed = st.session_state['timer_paused_elapsed'] + \
                                       (datetime.now() - st.session_state['timer_start']).total_seconds()
                    else:
                        final_elapsed = st.session_state.get('timer_paused_elapsed', 0)
                    do_save = True

        if do_save:
            # Clean up DB
            db.delete_active_timer(user_id)
            st.session_state['db_synced'] = False
            
            # Save the time log with exact duration
            minutes_spent = final_elapsed / 60
            task_id = st.session_state.get('timer_task_id', selected_task_id)
            subtask_id = st.session_state.get('timer_subtask_id', selected_subtask_id)

            db.add_time_log(
                user_id=user_id,
                task_id=task_id,
                duration_minutes=round(minutes_spent, 2),  # 2 decimal places = 1-second precision
                log_date=date.today().isoformat(),
                note=f"Timer session",
                source="timer",
                subtask_id=subtask_id
            )

            # Reset timer
            st.session_state['timer_running'] = False
            st.session_state['timer_start'] = None
            st.session_state['timer_paused_elapsed'] = 0
            st.session_state['timer_elapsed'] = 0

            # Feedback - include seconds (restore full HH:MM:SS or MM:SS)
            hrs = int(final_elapsed // 3600)
            ms = int((final_elapsed % 3600) // 60)
            ss = int(final_elapsed % 60)
            t_str = f"{hrs}h {ms}m {ss}s" if hrs > 0 else (f"{ms}m {ss}s" if ms > 0 else f"{ss}s")
            st.toast(f"✅ Saved {t_str}!", icon="⏱️")

            # FULL RERUN to update the Today's Sessions list below the fragment
            st.rerun()


    # No auto-refresh needed - JavaScript timer handles live display

    # ─── Today's Sessions ─────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Today's Sessions")

    today_logs = db.get_time_logs(user_id, start_date=date.today().isoformat(),
                                  end_date=date.today().isoformat())
    if today_logs:
        total_today_minutes = sum(log['duration_minutes'] for log in today_logs)
        total_seconds = int(total_today_minutes * 60)
        hours = total_seconds // 3600
        mins = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        
        if hours > 0:
            total_str = f"{hours}h {mins}m {secs}s"
        elif mins > 0:
            total_str = f"{mins}m {secs}s"
        else:
            total_str = f"{secs}s"
            
        st.metric("Total Today", total_str)

        for log in today_logs:
            col_info, col_dur, col_del = st.columns([5, 2, 1])
            with col_info:
                subtask_badge = ""
                if log.get('subtask_title'):
                    subtask_badge = f" <small style='color:#60A5FA;'>↳ {log['subtask_title']}</small>"
                st.markdown(
                    f"{log['category_icon']} **{log['task_title']}**{subtask_badge} "
                    f"<small style='color:#6B7280;'>({log['category_name']})</small>",
                    unsafe_allow_html=True
                )
                if log['note']:
                    st.caption(log['note'])
            with col_dur:
                source_icon = "⏱"  # always use timer icon
                # Display full time including seconds
                total_seconds = int(log['duration_minutes'] * 60)
                hours = total_seconds // 3600
                mins = (total_seconds % 3600) // 60
                secs = total_seconds % 60
                if hours > 0:
                    time_display = f"{hours}h {mins}m {secs}s"
                elif mins > 0:
                    time_display = f"{mins}m {secs}s"
                else:
                    time_display = f"{secs}s"
                st.markdown(f"{source_icon} **{time_display}**")
            with col_del:
                if st.button("🗑️", key=f"del_log_{log['id']}", help="Delete session", type="tertiary"):
                    # Request confirmation first
                    request_delete('timelog', log['id'], f"{log.get('task_title')} ({log.get('duration_minutes')}m)")
    else:
        st.markdown(
            """<div style='text-align:center; padding:2rem; color:#9CA3AF;'>
                <p>No sessions logged today. Start the timer!</p>
            </div>""",
            unsafe_allow_html=True
        )
