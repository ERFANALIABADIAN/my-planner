"""
Analytics page - Daily, Weekly, Monthly reports with charts.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
import database as db


def _inject_datepicker_css():
    """Inject per-page CSS to ensure the datepicker/calendar is readable in dark theme."""
    dark = st.session_state.get('theme', 'light') == 'dark'
    if dark:
        surface = "#1E2130"
        surface2 = "#252840"
        text = "#E5E7EB"
        head = "#FFFFFF"
        accent = "#4F8EF7"
        muted = "#9CA3AF"
    else:
        surface = "#FFFFFF"
        surface2 = "#F9FAFB"
        text = "#374151"
        head = "#1E1E2E"
        accent = "#4A90D9"
        muted = "#6B7280"

    css = f"""
    <style>
    /* Analytics page: datepicker/calendar fallback styles */
    div[data-baseweb="popover"] .DayPicker,
    div[data-baseweb="popover"] .react-calendar,
    div[role="dialog"] .DayPicker,
    div[role="dialog"] .react-calendar {{
        background-color: {surface} !important;
        color: {text} !important;
    }}
    div[data-baseweb="popover"] .DayPicker-Day,
    div[data-baseweb="popover"] .react-calendar__tile {{
        color: {text} !important;
        background: transparent !important;
        opacity: 1 !important;
    }}
    div[data-baseweb="popover"] .DayPicker-Day:hover,
    div[data-baseweb="popover"] .react-calendar__tile:hover {{
        background-color: {surface2} !important;
        color: {head} !important;
    }}
    div[data-baseweb="popover"] .DayPicker-Day--selected,
    div[data-baseweb="popover"] .react-calendar__tile--active {{
        background-color: {accent} !important;
        color: #ffffff !important;
    }}
    div[data-baseweb="popover"] .DayPicker-Day--disabled,
    div[data-baseweb="popover"] .react-calendar__tile--disabled {{
        color: {muted} !important; opacity: 0.9 !important;
    }}
    /* Ensure month/year header is visible */
    div[data-baseweb="popover"] .DayPicker-Caption,
    div[data-baseweb="popover"] .react-calendar__navigation {{
        color: {text} !important; background: transparent !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


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


def render_analytics_page():
    # Ensure Tasks page will reset its panels when user navigates back
    st.session_state['_tasks_initialized'] = False
    user_id = st.session_state['user_id']

    # Per-page fallback CSS for datepicker/calendar
    _inject_datepicker_css()

    st.markdown("## 📊 Analytics & Reports") 

    # ─── Period Selection ─────────────────────────────────────
    tab_daily, tab_weekly, tab_monthly, tab_trend = st.tabs([
        "📅 Today", "📆 This Week", "📆 This Month", "📈 Trend"
    ])

    # ─── DAILY TAB (Fragment) ─────────────────────────────────
    with tab_daily:
        _render_daily_tab(user_id)

    # ─── WEEKLY TAB (Fragment) ────────────────────────────────
    with tab_weekly:
        _render_weekly_tab(user_id)

    # ─── MONTHLY TAB (Fragment) ───────────────────────────────
    with tab_monthly:
        _render_monthly_tab(user_id)

    # ─── TREND TAB (Fragment) ─────────────────────────────────
    with tab_trend:
        _render_trend_tab(user_id)


@st.fragment
def _render_daily_tab(user_id):
    target_date = st.date_input("Select Date", value=date.today(), key="daily_date")
    daily = db.get_daily_summary(user_id, target_date.isoformat())
    
    if daily:
        total_min = sum(row['total_minutes'] for row in daily)

        # Top metrics
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("Total Time", format_minutes(total_min))
        with col_m2:
            st.metric("Tasks Worked", len(daily))
        with col_m3:
            categories_today = len(set(row['category_name'] for row in daily))
            st.metric("Categories", categories_today)

        # Pie chart
        df_daily = pd.DataFrame([dict(row) for row in daily])
        df_daily['label'] = df_daily.apply(
            lambda r: f"{r['icon']} {r['task_title']}", axis=1
        )
        df_daily['hours'] = df_daily['total_minutes'] / 60
        df_daily['pct'] = (df_daily['total_minutes'] / total_min * 100).round(1)

        fig_pie = px.pie(
            df_daily, values='total_minutes', names='label',
            color_discrete_sequence=df_daily['color'].tolist(),
            hole=0.4
        )
        fig_pie.update_traces(
            textposition='inside',
            textinfo='label+percent',
            textfont_size=12
        )
        fig_pie.update_layout(
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            height=350,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_pie, use_container_width=True)

        # Detailed table
        for row in daily:
            pct = row['total_minutes'] / total_min * 100
            col_name, col_time, col_pct = st.columns([4, 2, 2])
            with col_name:
                st.markdown(
                    f"{row['icon']} **{row['task_title']}** "
                    f"<small style='color:{row['color']};'>({row['category_name']})</small>",
                    unsafe_allow_html=True
                )
            with col_time:
                st.markdown(f"**{format_minutes(row['total_minutes'])}**")
            with col_pct:
                st.markdown(f"**{pct:.1f}%**")
            st.progress(pct / 100)
    else:
        _empty_state("No data for this date")


@st.fragment
def _render_weekly_tab(user_id):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    
    col_nav1, col_nav2, col_nav3 = st.columns([1, 3, 1])
    with col_nav1:
        if st.button("◀ Prev Week", key="prev_week"):
            st.session_state['week_offset'] = st.session_state.get('week_offset', 0) - 1
            st.rerun() # Fragment update only
    with col_nav3:
        if st.button("Next Week", key="next_week"):
            st.session_state['week_offset'] = min(0, st.session_state.get('week_offset', 0) + 1)
            st.rerun() # Fragment update only

    offset = st.session_state.get('week_offset', 0)
    current_week_start = week_start + timedelta(weeks=offset)
    current_week_end = current_week_start + timedelta(days=6)

    with col_nav2:
        st.markdown(
            f"<div style='text-align:center;'><strong>"
            f"{current_week_start.strftime('%b %d')} — {current_week_end.strftime('%b %d, %Y')}"
            f"</strong></div>",
            unsafe_allow_html=True
        )

    weekly = db.get_weekly_summary(user_id, current_week_start.isoformat())

    if weekly:
        total_min = sum(row['total_minutes'] for row in weekly)

        col_w1, col_w2, col_w3 = st.columns(3)
        with col_w1:
            st.metric("Total This Week", format_minutes(total_min))
        with col_w2:
            avg_daily = total_min / 7
            st.metric("Daily Average", format_minutes(avg_daily))
        with col_w3:
            st.metric("Categories Active", len(weekly))

        # Bar chart by category
        df_weekly = pd.DataFrame([dict(row) for row in weekly])
        df_weekly['hours'] = (df_weekly['total_minutes'] / 60).round(1)
        df_weekly['label'] = df_weekly.apply(
            lambda r: f"{r['icon']} {r['category_name']}", axis=1
        )
        df_weekly['pct'] = (df_weekly['total_minutes'] / total_min * 100).round(1)

        fig_bar = px.bar(
            df_weekly, x='label', y='hours',
            color='category_name',
            color_discrete_sequence=df_weekly['color'].tolist(),
            text=df_weekly.apply(
                lambda r: f"{r['hours']}h ({r['pct']}%)", axis=1
            )
        )
        fig_bar.update_traces(textposition='outside')
        fig_bar.update_layout(
            xaxis_title="", yaxis_title="Hours",
            showlegend=False,
            margin=dict(t=10, b=10),
            height=350,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # Details
        for row in weekly:
            pct = row['total_minutes'] / total_min * 100
            col_name, col_time, col_days, col_pct = st.columns([4, 2, 1, 1])
            with col_name:
                st.markdown(f"{row['icon']} **{row['category_name']}**")
            with col_time:
                st.markdown(f"**{format_minutes(row['total_minutes'])}**")
            with col_days:
                st.markdown(f"{row['active_days']}d")
            with col_pct:
                st.markdown(f"**{pct:.1f}%**")
            st.progress(pct / 100)
    else:
        _empty_state("No data for this week")


@st.fragment
def _render_monthly_tab(user_id):
    today = date.today()
    col_year, col_month = st.columns(2)
    with col_year:
        sel_year = st.number_input("Year", min_value=2020, max_value=2030,
                                   value=today.year, key="m_year")
    with col_month:
        sel_month = st.number_input("Month", min_value=1, max_value=12,
                                     value=today.month, key="m_month")

    monthly = db.get_monthly_summary(user_id, int(sel_year), int(sel_month))

    if monthly:
        total_min = sum(row['total_minutes'] for row in monthly)

        col_mt1, col_mt2, col_mt3 = st.columns(3)
        with col_mt1:
            st.metric("Total This Month", format_minutes(total_min))
        with col_mt2:
            import calendar
            days_in_month = calendar.monthrange(int(sel_year), int(sel_month))[1]
            avg = total_min / days_in_month
            st.metric("Daily Average", format_minutes(avg))
        with col_mt3:
            st.metric("Categories", len(monthly))

        # Donut chart
        df_monthly = pd.DataFrame([dict(row) for row in monthly])
        df_monthly['hours'] = (df_monthly['total_minutes'] / 60).round(1)
        df_monthly['label'] = df_monthly.apply(
            lambda r: f"{r['icon']} {r['category_name']}", axis=1
        )

        fig_donut = px.pie(
            df_monthly, values='total_minutes', names='label',
            color_discrete_sequence=df_monthly['color'].tolist(),
            hole=0.5
        )
        fig_donut.update_traces(textposition='inside', textinfo='label+percent')
        fig_donut.update_layout(
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            height=350,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_donut, use_container_width=True)

        # Monthly breakdown table
        st.markdown("#### Breakdown")
        for row in monthly:
            pct = row['total_minutes'] / total_min * 100
            col_name, col_time, col_days, col_pct = st.columns([4, 2, 1, 1])
            with col_name:
                st.markdown(f"{row['icon']} **{row['category_name']}**")
            with col_time:
                st.markdown(f"**{format_minutes(row['total_minutes'])}**")
            with col_days:
                st.markdown(f"{row['active_days']}d")
            with col_pct:
                st.markdown(f"**{pct:.1f}%**")
            st.progress(pct / 100)
    else:
        _empty_state("No data for this month")


@st.fragment
def _render_trend_tab(user_id):
    days_range = st.slider("Show last N days", 7, 90, 30, key="trend_days")
    trend_data = db.get_daily_trend(user_id, days_range)

    if trend_data:
        df_trend = pd.DataFrame([dict(row) for row in trend_data])
        df_trend['hours'] = (df_trend['total_minutes'] / 60).round(2)
        df_trend['log_date'] = pd.to_datetime(df_trend['log_date'])

        # Stacked area chart
        fig_trend = px.area(
            df_trend, x='log_date', y='hours',
            color='category_name',
            color_discrete_map=dict(zip(df_trend['category_name'], df_trend['color'])),
            labels={'log_date': 'Date', 'hours': 'Hours', 'category_name': 'Category'}
        )
        fig_trend.update_layout(
            margin=dict(t=10, b=10),
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation="h", yanchor="bottom", y=-0.3)
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        # Total summary
        total_hours = df_trend['hours'].sum()
        active_days_count = df_trend['log_date'].nunique()
        st.markdown(
            f"**Total: {total_hours:.1f} hours** over **{active_days_count} active days** "
            f"(avg {total_hours / max(active_days_count, 1):.1f} h/day)"
        )
    else:
        _empty_state("No data for this period")


def _empty_state(message: str):
    st.markdown(
        f"""<div style='text-align:center; padding:3rem; color:#9CA3AF;'>
            <p style='font-size:3rem;'>📊</p>
            <p>{message}</p>
            <p style='font-size:0.85rem;'>Start logging time on your tasks!</p>
        </div>""",
        unsafe_allow_html=True
    )
