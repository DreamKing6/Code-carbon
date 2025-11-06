# app.py
"""
EcoSaver — Student Resource Dashboard (Eco Nature theme)

"""
# app.py (top of file) - REPLACE your current imports with this block
import os
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import date, timedelta, datetime
import plotly.express as px
import statsmodels.api as sm

custom_css = """
<style>
/* Page background */
body {
    background-color: #0b1416;
    color: #ffffff;
}

/* Headings */
h1, h2, h3, h4 {
    color: #6aff6a; /* Neon green */
}

/* Cards / containers */
.stApp {
    background-color: #0b1416;
    color: white;
}

div[data-testid="stMetric"] {
    background-color: #111b1d;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #1f2f30;
    margin-bottom: 10px;
}

/* Buttons */
button[kind="primary"] {
    background-color: #6aff6a !important;
    color: #000 !important;
    border-radius: 8px;
    font-weight: 600;
}
button[kind="secondary"] {
    background-color: #1f2f30 !important;
    color: white !important;
    border-radius: 8px;
}

/* Text Inputs and Selectbox */
.stTextInput > div > div > input,
.stSelectbox > div,
.stNumberInput input {
    background-color: #111b1d;
    color: white;
    border-radius: 8px;
    border: 1px solid #1f2f30;
}

/* Success / info boxes */
.stAlert {
    background-color: #102b10 !important;
    color: #79ff81 !important;
    border-left: 4px solid #00ff44 !important;
}

/* Tables */
tbody, thead {
    background-color: #111b1d !important;
    color: white !important;
}

/* Progress bar dark theme */
.stProgress > div > div > div > div {
    background-color: #6aff6a !important; /* Neon green progress fill */
}

/* Specific sidebar input styling for dark theme */
.stSidebar .stTextInput > div > div > input,
.stSidebar .stSelectbox > div,
.stSidebar .stNumberInput input {
    border: 1px solid #6aff6a; /* Green border for contrast */
}

/* Titles and subtitles in dark theme */
.big-title { 
    font-size:30px; 
    font-weight:700; 
    color:#6aff6a; 
}

.subtle { 
    color:#9eff9e; 
    font-size:16px;
}

</style>
"""
# ---------------------------
# Config & constants
# ---------------------------
APP_NAME = "EcoSaver"
DB_DIR = "data"
DB_FILE = os.path.join(DB_DIR, "techforge_eco.db")
CO2_PER_KWH = 0.82          # kg CO2 per kWh (example factor)
CO2_PER_LITER_WATER = 0.00035  # kg CO2 per liter (1000 L -> 0.35 kg)
DATE_FMT = "%Y-%m-%d"
DEFAULT_HISTORY_DAYS = 30 # For default filtering after date range removal

# Streamlit page config (eco-nature vibe)
st.set_page_config(page_title=f"{APP_NAME} — Eco Dashboard", layout="wide",
                    initial_sidebar_state="expanded")

# Apply the custom dark CSS theme
st.markdown(custom_css, unsafe_allow_html=True)


# ---------------------------
# Database helpers
# ---------------------------
def ensure_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        created_at TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        electricity_units REAL NOT NULL,
        water_liters INTEGER NOT NULL,
        household_size INTEGER NOT NULL,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    conn.commit()
    conn.close()

def get_conn():
    ensure_db()
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def add_user_if_not_exists(conn, username: str):
    username = username.strip().lower()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("INSERT INTO users (username, created_at) VALUES (?, ?)", (username, datetime.utcnow().isoformat()))
    conn.commit()
    return cur.lastrowid

def add_usage(conn, user_id: int, date_str: str, elec: float, water: int, hh_size: int):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO usage (user_id, date, electricity_units, water_liters, household_size, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, date_str, elec, water, hh_size, datetime.utcnow().isoformat()))
    conn.commit()

def load_usage_df(conn, start_date=None, end_date=None):
    q = "SELECT u.id as usage_id, us.username, us.id as user_id, u.date, u.electricity_units, u.water_liters, u.household_size FROM usage u JOIN users us ON u.user_id = us.id"
    params = []
    
    # If a specific date range is provided, use it. Otherwise, load all data.
    if start_date and end_date:
        q += " WHERE date(u.date) BETWEEN date(?) AND date(?)"
        params = [start_date, end_date]
        
    q += " ORDER BY date(u.date) ASC"
    df = pd.read_sql_query(q, conn, params=params, parse_dates=["date"])
    
    if not df.empty:
        df["username"] = df["username"].str.strip().str.lower()
        
        # Apply default history filter if no dates were provided to load_usage_df
        if not start_date and not end_date:
            latest_date = df['date'].max()
            start_date_limit = latest_date - timedelta(days=DEFAULT_HISTORY_DAYS)
            df = df[df['date'] >= start_date_limit]
            
    return df

def get_user_list(conn):
    df = pd.read_sql_query("SELECT username FROM users ORDER BY username", conn)
    return df["username"].tolist()

# ---------------------------
# Demo data on first run
# ---------------------------
def populate_demo_if_empty(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    if count > 0:
        return
    # create demo users and 10 days of data
    demo_users = ["arya", "dev", "mira"]
    start = date.today() - timedelta(days=9)
    np.random.seed(1)
    for u in demo_users:
        uid = add_user_if_not_exists(conn, u)
        hh = 3 if u != "mira" else 1
        for i in range(10):
            d = (start + timedelta(days=i)).strftime(DATE_FMT)
            # sample values (vary per user)
            base_elec = 2.5 if u=="mira" else 3.5 if u=="arya" else 5.0
            elec = max(0.5, float(np.round(np.random.normal(base_elec, 0.8),2)))
            water = int(max(40, np.random.normal(120 if u=="arya" else 180 if u=="dev" else 80, 25)))
            add_usage(conn, uid, d, elec, water, hh)

# ---------------------------
# Prediction & scoring (Statsmodels)
# ---------------------------
def fit_linear_trend(df_user, value_col="electricity_units"):
    if df_user.shape[0] < 3:
        return None, None
    df_user = df_user.sort_values("date").copy()
    df_user["day_index"] = (df_user["date"] - df_user["date"].min()).dt.days.astype(int)
    X = sm.add_constant(df_user["day_index"].values)
    y = df_user[value_col].values
    try:
        model = sm.OLS(y, X).fit()
        next_index = df_user["day_index"].max() + 1
        pred = model.predict(sm.add_constant([next_index]))[0]
        return float(pred), model
    except Exception:
        return None, None

def global_trend_predict(df_all, value_col="electricity_units"):
    if df_all.shape[0] < 3:
        return float(df_all[value_col].mean()) if df_all.shape[0] > 0 else None
    df2 = df_all.sort_values("date").copy()
    df2["day_index"] = (df2["date"] - df2["date"].min()).dt.days.astype(int)
    X = sm.add_constant(df2["day_index"].values)
    y = df2[value_col].values
    try:
        model = sm.OLS(y, X).fit()
        next_index = df2["day_index"].max() + 1
        pred = model.predict(sm.add_constant([next_index]))[0]
        return float(pred)
    except Exception:
        return float(df2[value_col].mean())

def eco_score(latest, predicted):
    if predicted is None or predicted == 0:
        return 50
    diff = predicted - latest
    pct = diff / predicted
    s = 50 + (pct * 50)
    return int(round(max(0, min(100, s))))

# ---------------------------
# Patterns & Suggestions
# ---------------------------
# Removed the body of this function as "Detected Patterns" is being removed
def detect_patterns(df_user):
    # Function kept but returns empty list since "Detected Patterns" section is removed
    return []

def generate_suggestions(latest, predicted, df_user):
    suggestions = []
    if predicted is None:
        suggestions.append("Insufficient history to predict — add more daily records.")
    else:
        if latest > predicted:
            excess = latest - predicted
            suggestions.append(f"You used {excess:.2f} kWh more than predicted. Try reducing AC/heavy loads by 30 min to save approx {excess*0.15:.2f} kWh.")
        else:
            suggestions.append(f"Good work — you're {(predicted-latest):.2f} kWh under prediction. Keep that habit!")
    hh = int(df_user.iloc[-1].get("household_size", 1) or 1)
    per_person = df_user.iloc[-1]["water_liters"] / hh
    if per_person > 150:
        suggestions.append("Shorten showers by 2-3 mins or install a low-flow head — saves 20-40 L/day per person.")
    elif per_person > 100:
        suggestions.append("Fix small leaks and try one short shower a day to cut water use.")
    suggestions.append("Unplug chargers at night. Replace bulbs with LEDs. Use natural light where possible.")
    return suggestions

# ---------------------------
# UI: Sidebar - Login & Input
# ---------------------------
conn = get_conn()
ensure_db()
populate_demo_if_empty(conn)  # auto-populate demo rows for quick demo

# Sidebar Title and User Management
st.sidebar.markdown(f"<div class='big-title'>Eco Saver</div>", unsafe_allow_html=True)
st.sidebar.markdown("**User Management**")

# Login Form (Kept)
with st.sidebar.form("login_form", clear_on_submit=False):
    username = st.text_input("Enter your username (no password)", value="", help="A quick unique id, e.g., rahul123").strip().lower()
    login_btn = st.form_submit_button("Create / Use user")
    if login_btn:
        if username == "":
            st.warning("Please enter a username.")
        else:
            uid = add_user_if_not_exists(conn, username)
            st.success(f"Logged in as **{username}**")

st.sidebar.markdown("---")

# NEW DROPDOWN: CHOOSE HOME/SCHOOL
st.sidebar.header("Data Source")
st.sidebar.selectbox(
    "CHOOSE HOME/SCHOOL", 
    options=["Home", "School"],
    help="This selection could be used to load different data sets or benchmark usage.",
    index=0
)


# ---------------------------
# Main layout
# ---------------------------
st.markdown(f"<div class='big-title'>{APP_NAME} — Eco Dashboard</div>", unsafe_allow_html=True) 
st.markdown("<div class='subtle'>Predictive student dashboard for electricity & water with CO₂ estimation and friendly suggestions.</div>", unsafe_allow_html=True)
st.markdown("---")

# MOVED FILTERS TO MAIN PAGE (and removed date range)
users = ["All users"] + get_user_list(conn)
selected_user = st.selectbox("View user", options=users, index=0, label_visibility="visible")

# Load data based on current requirements (No specific start/end date now)
df_all = load_usage_df(conn) 
df_filtered = df_all.copy()
if selected_user != "All users":
    df_filtered = df_all[df_all["username"] == selected_user].copy()

st.markdown("---") # Separator after the main filter

col_main, col_side = st.columns([2,1])

# LEFT: Trends & analysis
with col_main:
    st.header("Usage Trends & Prediction")
    if df_filtered.empty:
        st.info("No data for selection. Add entries from the sidebar to begin.")
    else:
        if selected_user != "All users":
            df_user = df_filtered.sort_values("date").copy()
            st.subheader(f"User — {selected_user}")
            fig = px.line(df_user, x="date", y="electricity_units", markers=True, title="Electricity (kWh) over time")
            st.plotly_chart(fig, use_container_width=True)
            fig2 = px.bar(df_user, x="date", y="water_liters", title="Water (L) over time")
            st.plotly_chart(fig2, use_container_width=True)

            latest = df_user.iloc[-1]
            st.metric("Latest electricity (kWh)", f"{latest['electricity_units']:.2f}")
            st.metric("Latest water (L)", f"{int(latest['water_liters']):,}")

            pred, model = fit_linear_trend(df_user, "electricity_units")
            if pred is None:
                pred = global_trend_predict(df_all, "electricity_units")
                st.info(f"Not enough user history for per-user model. Using global trend: {pred:.2f} kWh (next-day estimate).")
            else:
                st.success(f"Per-user trend prediction (next day): {pred:.2f} kWh")

            score = eco_score(latest["electricity_units"], pred)
            st.write("EcoScore (higher is better):")
            st.progress(score/100)
            st.write(f"**{score}/100**")

            latest_co2 = latest["electricity_units"] * CO2_PER_KWH + latest["water_liters"] * CO2_PER_LITER_WATER
            st.write(f"Estimated CO₂ footprint (latest day): **{latest_co2:.3f} kg CO₂**")
            st.caption(f"Factors: {CO2_PER_KWH} kgCO₂/kWh, {CO2_PER_LITER_WATER} kgCO₂/L")

            # Removed: st.subheader("Detected Patterns") block
            
            st.subheader("Personalized Suggestions")
            # Note: Since detect_patterns is now empty, generate_suggestions is simplified
            suggestions = generate_suggestions(latest["electricity_units"], pred, df_user)
            for s in suggestions:
                st.write("•", s)

            st.subheader("What-If: Estimate quick savings")
            with st.form("whatif_form", clear_on_submit=False):
                ac_reduce = st.slider("Reduce AC / heavy load (hours/day)", 0.0, 4.0, 0.5, step=0.25)
                shower_reduce = st.slider("Shorter shower (mins/day)", 0, 10, 2, step=1)
                change_led = st.checkbox("Switch 3 incandescent bulbs -> LED (daily effect)")
                submit_whatif = st.form_submit_button("Estimate savings")
                if submit_whatif:
                    est_elec_save = ac_reduce * 0.8 + (0.5 if change_led else 0.0)
                    est_water_save = shower_reduce * 10
                    est_co2_save = est_elec_save * CO2_PER_KWH + est_water_save * CO2_PER_LITER_WATER
                    st.write(f"Estimated electricity saved/day: **{est_elec_save:.2f} kWh**")
                    st.write(f"Estimated water saved/day: **{est_water_save:.0f} L**")
                    st.write(f"Estimated CO₂ reduction/day: **{est_co2_save:.3f} kg CO₂**")

        else:
            st.subheader("All users — aggregated")
            agg = df_filtered.groupby("date").agg({"electricity_units":"mean","water_liters":"mean"}).reset_index()
            fig_all_e = px.line(agg, x="date", y="electricity_units", title="Average electricity (kWh) — all users")
            st.plotly_chart(fig_all_e, use_container_width=True)
            fig_all_w = px.line(agg, x="date", y="water_liters", title="Average water (L) — all users")
            st.plotly_chart(fig_all_w, use_container_width=True)
            pred_global = global_trend_predict(df_filtered, "electricity_units")
            st.write(f"Global next-day electricity estimate (average users): **{pred_global:.2f} kWh**")

# RIGHT: Leaderboard & admin
with col_side:
    st.header("Leaderboard (last 7 days)")
    # Since date range is removed, we hardcode the leaderboard to the last 7 days
    last7_start = (date.today() - timedelta(days=7)).strftime(DATE_FMT)
    last7_df = load_usage_df(conn, last7_start, date.today().strftime(DATE_FMT))
    users_scores = []
    for u in last7_df["username"].unique().tolist():
        du = last7_df[last7_df["username"] == u].sort_values("date")
        if du.empty:
            continue
        latest_val = du.iloc[-1]["electricity_units"]
        pred_u, _ = fit_linear_trend(du, "electricity_units")
        if pred_u is None:
            pred_u = global_trend_predict(last7_df, "electricity_units") or latest_val
        score = eco_score(latest_val, pred_u)
        users_scores.append({"username": u, "score": score, "latest_kWh": float(latest_val), "pred": round(float(pred_u),2)})
    if users_scores:
        lb = pd.DataFrame(users_scores).sort_values("score", ascending=False).reset_index(drop=True)
        st.table(lb)
    else:
        st.info("No data in last 7 days to show leaderboard.")

    st.markdown("---")
    st.subheader("Quick stats")
    for u in get_user_list(conn):
        # We use df_all here, which defaults to the last 30 days of data in the new setup
        du = df_all[df_all["username"] == u] 
        if du.empty:
            continue
        st.write(f"**{u}** — records: {len(du)} | avg kWh: {du['electricity_units'].mean():.2f} | avg water L: {du['water_liters'].mean():.0f}")

    st.markdown("---")
    st.subheader("Admin")
    if st.checkbox("Reset DB (danger!)"):
        if st.button("Confirm reset"):
            try:
                conn.close()
            except Exception:
                pass
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
            ensure_db()
            st.experimental_rerun()

st.markdown("---")
st.caption("EcoSaver — built for student hackathons. Trend prediction uses simple OLS (statsmodels). CO₂ factors are illustrative approximations.")