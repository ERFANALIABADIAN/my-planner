"""
Timer page - Stopwatch/Pomodoro timer with time logging.
Uses JavaScript-based timer for smooth live counting.
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, date
import database as db


def format_seconds(seconds: int) -> str:
    """Format seconds into MM:SS or HH:MM:SS."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def js_timer_component(elapsed_seconds: int, is_running: bool, mode: str = "stopwatch", total_seconds: int = 0):
    """Render a JavaScript-based live timer that counts without page refresh."""
    timer_html = f"""
    <div id="timer-container" style="text-align:center; padding:1.5rem 0;">
        <div id="timer-display" style="font-size:4rem; font-weight:800; color:#1E1E2E;
             font-family:'Courier New', monospace; letter-spacing:0.2rem; user-select:none;">
            00:00
        </div>
        <div id="timer-status" style="margin-top:0.5rem; font-size:0.85rem; color:#6B7280;"></div>
    </div>
    <script>
        (function() {{
            var startElapsed = {elapsed_seconds};
            var isRunning = {'true' if is_running else 'false'};
            var mode = "{mode}";
            var totalSeconds = {total_seconds};
            var startTime = Date.now();

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
                    display.style.color = remaining === 0 ? '#EF4444' : '#1E1E2E';
                    if (remaining === 0 && isRunning) {{
                        status.textContent = '🍅 Time is up!';
                        status.style.color = '#EF4444';
                    }}
                }} else {{
                    display.textContent = formatTime(current);
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
    user_id = st.session_state['user_id']
    categories = db.get_categories(user_id)
    tasks = db.get_tasks(user_id, status='active')

    st.markdown("## ⏱ Focus Timer")

    if not tasks:
        st.info("You need active tasks to use the timer. Go to Tasks page to create some!")
        return

    # ─── Timer Configuration ──────────────────────────────────
    col_config, col_timer = st.columns([1, 1])

    with col_config:
        st.markdown("### 🎯 Select Task")

        # Group tasks by category  
        task_options = {}
        for t in tasks:
            label = f"{t['category_icon']} {t['title']} ({t['category_name']})"
            task_options[label] = t['id']

        selected_task_label = st.selectbox(
            "Task",
            options=list(task_options.keys()),
            label_visibility="collapsed"
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
                    options=list(sub_options.keys())
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

            pomodoro_min = st.number_input(
                "Custom (minutes)",
                min_value=1, max_value=240,
                value=st.session_state.get('pomodoro_minutes', 25)
            )
            st.session_state['pomodoro_minutes'] = pomodoro_min

    with col_timer:
        st.markdown("### 🕐 Timer")
        
        # Initialize timer state
        if 'timer_running' not in st.session_state:
            st.session_state['timer_running'] = False
        if 'timer_start' not in st.session_state:
            st.session_state['timer_start'] = None
        if 'timer_elapsed' not in st.session_state:
            st.session_state['timer_elapsed'] = 0
        if 'timer_paused_elapsed' not in st.session_state:
            st.session_state['timer_paused_elapsed'] = 0

        # Calculate elapsed time
        if st.session_state['timer_running'] and st.session_state['timer_start']:
            elapsed = st.session_state['timer_paused_elapsed'] + \
                      (datetime.now() - st.session_state['timer_start']).total_seconds()
        else:
            elapsed = st.session_state.get('timer_paused_elapsed', 0)

        elapsed = int(elapsed)

        # Display timer using JavaScript component (smooth, no lag)
        if "🍅" in timer_mode:
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
        col_start, col_pause, col_stop = st.columns(3)

        with col_start:
            if not st.session_state['timer_running']:
                if st.button("▶ Start", use_container_width=True, type="primary"):
                    st.session_state['timer_running'] = True
                    st.session_state['timer_start'] = datetime.now()
                    st.session_state['timer_task_id'] = selected_task_id
                    st.session_state['timer_subtask_id'] = selected_subtask_id
                    st.rerun()

        with col_pause:
            if st.session_state['timer_running']:
                if st.button("⏸ Pause", use_container_width=True):
                    st.session_state['timer_running'] = False
                    st.session_state['timer_paused_elapsed'] = elapsed
                    st.session_state['timer_start'] = None
                    st.rerun()

        with col_stop:
            if elapsed > 0:
                if st.button("⏹ Stop & Save", use_container_width=True, type="primary"):
                    # Save the time log
                    minutes_spent = max(1, elapsed / 60)
                    task_id = st.session_state.get('timer_task_id', selected_task_id)
                    subtask_id = st.session_state.get('timer_subtask_id', selected_subtask_id)

                    db.add_time_log(
                        user_id=user_id,
                        task_id=task_id,
                        duration_minutes=round(minutes_spent, 1),
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

                    st.success(f"✅ Saved {int(minutes_spent)} min!")
                    st.rerun()

        # Reset button
        if elapsed > 0 and not st.session_state['timer_running']:
            if st.button("🔄 Reset", use_container_width=True):
                st.session_state['timer_paused_elapsed'] = 0
                st.session_state['timer_elapsed'] = 0
                st.rerun()

    # No auto-refresh needed - JavaScript timer handles live display

    # ─── Today's Sessions ─────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Today's Sessions")

    today_logs = db.get_time_logs(user_id, start_date=date.today().isoformat(),
                                  end_date=date.today().isoformat())
    if today_logs:
        total_today = sum(log['duration_minutes'] for log in today_logs)
        st.metric("Total Today", f"{int(total_today // 60)}h {int(total_today % 60)}m")

        for log in today_logs:
            col_info, col_dur, col_del = st.columns([5, 2, 1])
            with col_info:
                st.markdown(
                    f"{log['category_icon']} **{log['task_title']}** "
                    f"<small style='color:#6B7280;'>({log['category_name']})</small>",
                    unsafe_allow_html=True
                )
                if log['note']:
                    st.caption(log['note'])
            with col_dur:
                source_icon = "⏱" if log['source'] == 'timer' else "✏️"
                st.markdown(f"{source_icon} **{int(log['duration_minutes'])} min**")
            with col_del:
                if st.button("✕", key=f"del_log_{log['id']}"):
                    db.delete_time_log(log['id'])
                    st.rerun()
    else:
        st.markdown(
            """<div style='text-align:center; padding:2rem; color:#9CA3AF;'>
                <p>No sessions logged today. Start the timer!</p>
            </div>""",
            unsafe_allow_html=True
        )
