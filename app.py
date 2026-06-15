import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from werkzeug.security import generate_password_hash, check_password_hash

from stress_algorithm import QUESTIONS, calculate_stress_score, generate_insights, chatbot_reply

APP_TITLE = "AI Mental Stress Detector"
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "streamlit_database.db"
CSS_PATH = BASE_DIR / "static" / "css" / "style.css"

st.set_page_config(page_title=APP_TITLE, page_icon="🧠", layout="wide", initial_sidebar_state="expanded")


def inject_css():
    base_css = """
    <style>
    .stApp {background: radial-gradient(circle at top left,#eeeaff,transparent 28%),linear-gradient(135deg,#f7fbff,#eefcf8);}
    .main-card {background: rgba(255,255,255,.86); border: 1px solid rgba(255,255,255,.72); border-radius: 24px; padding: 24px; box-shadow: 0 18px 45px rgba(19,34,56,.10);}
    .metric-card {background: white; border-radius: 22px; padding: 20px; box-shadow: 0 12px 28px rgba(19,34,56,.08);}
    .pill {display:inline-block; padding:8px 13px; border-radius: 99px; font-weight:800;}
    .low {background:#dff8ef; color:#047857;} .medium {background:#fff3d6; color:#a16207;} .high {background:#ffe3e3; color:#b42318;}
    .muted {color:#667085;} .hero-title {font-size: 3.2rem; font-weight: 900; color:#071a33; line-height:1.05;}
    </style>
    """
    st.markdown(base_css, unsafe_allow_html=True)


def db_connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            age INTEGER,
            occupation TEXT,
            preferred_theme TEXT DEFAULT 'calm',
            notifications INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stress_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            mood TEXT NOT NULL,
            sleep_quality INTEGER NOT NULL,
            pressure_level INTEGER NOT NULL,
            anxiety_level INTEGER NOT NULL,
            feeling_text TEXT,
            score INTEGER NOT NULL,
            level TEXT NOT NULL,
            explanation TEXT NOT NULL,
            factors TEXT NOT NULL,
            recommendations TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS questionnaire_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stress_test_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer_value INTEGER NOT NULL,
            FOREIGN KEY(stress_test_id) REFERENCES stress_tests(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stress_test_id INTEGER NOT NULL,
            summary TEXT NOT NULL,
            emotional_pattern TEXT NOT NULL,
            sleep_pressure_analysis TEXT NOT NULL,
            risk_indicator TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(stress_test_id) REFERENCES stress_tests(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wellness_tips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            icon TEXT DEFAULT '🌿'
        )
    """)
    cur.execute("SELECT COUNT(*) AS total FROM wellness_tips")
    if cur.fetchone()["total"] == 0:
        tips = [
            ("Breathing Reset", "Anxiety", "Inhale for 4 seconds, hold for 4 seconds, and exhale for 6 seconds. Repeat five times.", "🌬️"),
            ("Sleep Routine", "Sleep", "Keep a fixed sleep and wake time. Avoid screens and caffeine close to bedtime.", "🌙"),
            ("Task Break", "Productivity", "Split big tasks into 25-minute focus blocks with 5-minute breaks.", "⏱️"),
            ("Grounding", "Calm", "Name 5 things you see, 4 things you feel, 3 things you hear, 2 smells, and 1 taste.", "🧘"),
            ("Talk to Someone", "Support", "Share how you feel with a trusted person when pressure feels too heavy.", "🤝"),
        ]
        cur.executemany("INSERT INTO wellness_tips(title, category, content, icon) VALUES (?,?,?,?)", tips)
    conn.commit()
    conn.close()


def query_one(sql, params=()):
    conn = db_connect()
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return row


def query_all(sql, params=()):
    conn = db_connect()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def execute(sql, params=()):
    conn = db_connect()
    cur = conn.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


def current_user():
    uid = st.session_state.get("user_id")
    if not uid:
        return None
    return query_one("SELECT * FROM users WHERE id=?", (uid,))


def require_login():
    if not current_user():
        st.warning("Please login or create an account to continue.")
        login_register_page()
        st.stop()


def level_class(level):
    if "Low" in level:
        return "low"
    if "Moderate" in level:
        return "medium"
    return "high"


def register_user(name, email, password):
    if query_one("SELECT id FROM users WHERE email=?", (email.lower(),)):
        return False, "This email is already registered."
    user_id = execute(
        "INSERT INTO users(name,email,password_hash,created_at) VALUES (?,?,?,?)",
        (name.strip(), email.strip().lower(), generate_password_hash(password), datetime.utcnow().isoformat()),
    )
    st.session_state.user_id = user_id
    return True, "Account created successfully."


def login_user(email, password):
    user = query_one("SELECT * FROM users WHERE email=?", (email.strip().lower(),))
    if user and check_password_hash(user["password_hash"], password):
        st.session_state.user_id = user["id"]
        return True
    return False


def landing_page():
    st.markdown('<div class="hero-title">AI Mental Stress Detector</div>', unsafe_allow_html=True)
    st.write("A calm healthcare-style web app that estimates stress level from mood, sleep, pressure, anxiety, questionnaire answers, and text input.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Stress Levels", "Low / Moderate / High")
    c2.metric("Tracking", "History + Reports")
    c3.metric("Support", "Wellness Chatbot")
    st.info("Use the sidebar to Login/Register and start your stress test.")


def login_register_page():
    st.header("Login / Register")
    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
        if submitted:
            if login_user(email, password):
                st.success("Welcome back.")
                st.rerun()
            else:
                st.error("Invalid email or password.")
    with tab2:
        with st.form("register_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email Address")
            password = st.text_input("Create Password", type="password")
            submitted = st.form_submit_button("Create Account")
        if submitted:
            if not name or not email or not password:
                st.error("Please complete all fields.")
            else:
                ok, msg = register_user(name, email, password)
                st.success(msg) if ok else st.error(msg)
                if ok:
                    st.rerun()


def dashboard_page():
    require_login()
    user = current_user()
    st.header(f"Welcome, {user['name']}")
    latest = query_one("SELECT * FROM stress_tests WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user["id"],))
    tests = query_all("SELECT * FROM stress_tests WHERE user_id=? ORDER BY created_at DESC LIMIT 5", (user["id"],))
    c1, c2, c3 = st.columns(3)
    c1.metric("Latest Score", f"{latest['score']}%" if latest else "No test")
    c2.metric("Latest Level", latest["level"] if latest else "Not available")
    c3.metric("Total Tests", len(query_all("SELECT id FROM stress_tests WHERE user_id=?", (user["id"],))))
    st.subheader("Recent Stress Tests")
    if tests:
        st.dataframe(pd.DataFrame([dict(t) for t in tests])[['created_at','mood','score','level']], use_container_width=True)
    else:
        st.info("No tests yet. Start your first stress test from the sidebar.")


def stress_test_page():
    require_login()
    st.header("Stress Test")
    with st.form("stress_form"):
        feeling_text = st.text_area("How are you feeling today?", height=120)
        mood = st.selectbox("Current mood", ["great", "good", "okay", "sad", "anxious", "angry"], index=2)
        sleep_quality = st.slider("Sleep quality", 1, 10, 5)
        pressure_level = st.slider("Work/study pressure", 1, 10, 5)
        anxiety_level = st.slider("Anxiety/restlessness level", 1, 10, 5)
        st.subheader("Questionnaire")
        answers = []
        for i, q in enumerate(QUESTIONS):
            answers.append(st.slider(q, 1, 5, 3, key=f"q_{i}"))
        submitted = st.form_submit_button("Generate AI Stress Result")
    if submitted:
        score = calculate_stress_score(mood, sleep_quality, pressure_level, anxiety_level, answers, feeling_text)
        insights = generate_insights(score, mood, sleep_quality, pressure_level, anxiety_level, answers, feeling_text)
        risk = "Low" if score <= 39 else "Medium" if score <= 69 else "High"
        user_id = st.session_state.user_id
        test_id = execute(
            """INSERT INTO stress_tests(user_id,mood,sleep_quality,pressure_level,anxiety_level,feeling_text,score,level,explanation,factors,recommendations,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, mood, sleep_quality, pressure_level, anxiety_level, feeling_text, score, insights['level'], insights['explanation'], '|'.join(insights['factors']), '|'.join(insights['recommendations']), datetime.utcnow().isoformat()),
        )
        for q, value in zip(QUESTIONS, answers):
            execute("INSERT INTO questionnaire_answers(stress_test_id,question,answer_value) VALUES (?,?,?)", (test_id, q, value))
        execute(
            "INSERT INTO reports(stress_test_id,summary,emotional_pattern,sleep_pressure_analysis,risk_indicator,created_at) VALUES (?,?,?,?,?,?)",
            (test_id, f"Your stress level is {insights['level']} with a score of {score}%.", f"Mood is {mood}; anxiety level is {anxiety_level}/10.", f"Sleep quality is {sleep_quality}/10 and pressure level is {pressure_level}/10.", risk, datetime.utcnow().isoformat()),
        )
        st.session_state.latest_test_id = test_id
        st.success("Stress result generated.")
        result_page(test_id)


def result_page(test_id=None):
    require_login()
    test_id = test_id or st.session_state.get("latest_test_id")
    if not test_id:
        tests = query_all("SELECT * FROM stress_tests WHERE user_id=? ORDER BY created_at DESC", (st.session_state.user_id,))
        if not tests:
            st.info("No result found. Please complete a stress test first.")
            return
        test_id = tests[0]["id"]
    test = query_one("SELECT * FROM stress_tests WHERE id=? AND user_id=?", (test_id, st.session_state.user_id))
    if not test:
        st.error("Result not found.")
        return
    st.header("AI Stress Result")
    st.markdown(f"<span class='pill {level_class(test['level'])}'>{test['level']}</span>", unsafe_allow_html=True)
    st.metric("Stress Score", f"{test['score']}%")
    st.write(test["explanation"])
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Detected Factors")
        for item in test["factors"].split("|"):
            st.write(f"• {item}")
    with c2:
        st.subheader("Recommendations")
        for item in test["recommendations"].split("|"):
            st.write(f"• {item}")
    report_text = make_report_text(test)
    st.download_button("Download Report", report_text, file_name=f"stress_report_{test['id']}.txt", mime="text/plain")


def make_report_text(test):
    return f"""AI Mental Stress Detector Report
Date: {test['created_at']}
Score: {test['score']}%
Level: {test['level']}
Mood: {test['mood']}
Sleep Quality: {test['sleep_quality']}/10
Pressure Level: {test['pressure_level']}/10
Anxiety Level: {test['anxiety_level']}/10

Explanation:
{test['explanation']}

Factors:
{test['factors'].replace('|', ', ')}

Recommendations:
{test['recommendations'].replace('|', '; ')}
"""


def history_page():
    require_login()
    st.header("Stress History")
    tests = query_all("SELECT * FROM stress_tests WHERE user_id=? ORDER BY created_at ASC", (st.session_state.user_id,))
    if not tests:
        st.info("No history available yet.")
        return
    df = pd.DataFrame([dict(t) for t in tests])
    df["created_at"] = pd.to_datetime(df["created_at"])
    st.line_chart(df.set_index("created_at")["score"])
    st.dataframe(df[["created_at", "mood", "sleep_quality", "pressure_level", "anxiety_level", "score", "level"]], use_container_width=True)


def reports_page():
    require_login()
    st.header("Reports")
    tests = query_all("SELECT * FROM stress_tests WHERE user_id=? ORDER BY created_at DESC", (st.session_state.user_id,))
    if not tests:
        st.info("No reports found.")
        return
    labels = [f"#{t['id']} | {t['created_at'][:10]} | {t['level']} | {t['score']}%" for t in tests]
    choice = st.selectbox("Select report", labels)
    selected_id = int(choice.split(" | ")[0].replace("#", ""))
    result_page(selected_id)


def wellness_page():
    require_login()
    st.header("Wellness Tips")
    tips = query_all("SELECT * FROM wellness_tips ORDER BY id ASC")
    cols = st.columns(2)
    for i, tip in enumerate(tips):
        with cols[i % 2]:
            st.markdown(f"### {tip['icon']} {tip['title']}")
            st.caption(tip["category"])
            st.write(tip["content"])


def assistant_page():
    require_login()
    st.header("AI Mental Wellness Chatbot")
    messages = query_all("SELECT * FROM chat_messages WHERE user_id=? ORDER BY created_at ASC", (st.session_state.user_id,))
    for msg in messages:
        with st.chat_message("user" if msg["sender"] == "user" else "assistant"):
            st.write(msg["message"])
    prompt = st.chat_input("Share how you feel...")
    if prompt:
        reply = chatbot_reply(prompt)
        execute("INSERT INTO chat_messages(user_id,sender,message,created_at) VALUES (?,?,?,?)", (st.session_state.user_id, "user", prompt, datetime.utcnow().isoformat()))
        execute("INSERT INTO chat_messages(user_id,sender,message,created_at) VALUES (?,?,?,?)", (st.session_state.user_id, "bot", reply, datetime.utcnow().isoformat()))
        st.rerun()


def profile_page():
    require_login()
    user = current_user()
    st.header("Profile")
    with st.form("profile_form"):
        name = st.text_input("Name", user["name"])
        age = st.number_input("Age", min_value=0, max_value=120, value=int(user["age"] or 0))
        occupation = st.text_input("Occupation", user["occupation"] or "")
        submitted = st.form_submit_button("Save Profile")
    if submitted:
        execute("UPDATE users SET name=?, age=?, occupation=? WHERE id=?", (name, age or None, occupation, user["id"]))
        st.success("Profile updated.")
        st.rerun()


def settings_page():
    require_login()
    user = current_user()
    st.header("Settings")
    with st.form("settings_form"):
        theme = st.selectbox("Preferred theme", ["calm", "blue", "mint", "lavender"], index=["calm", "blue", "mint", "lavender"].index(user["preferred_theme"] or "calm"))
        notifications = st.checkbox("Enable wellness reminders", value=bool(user["notifications"]))
        submitted = st.form_submit_button("Save Settings")
    if submitted:
        execute("UPDATE users SET preferred_theme=?, notifications=? WHERE id=?", (theme, int(notifications), user["id"]))
        st.success("Settings saved.")


def emergency_page():
    st.header("Emergency Support")
    st.error("This app is not a medical emergency service. If you feel unsafe or at risk of self-harm, contact local emergency services or a trusted person immediately.")
    st.write("Try to stay near someone you trust, move away from harmful objects, and call emergency support in your area.")


def sidebar():
    st.sidebar.title("🧠 AI Stress Detector")
    user = current_user()
    if user:
        st.sidebar.success(f"Logged in as {user['name']}")
        pages = ["Dashboard", "Stress Test", "Latest Result", "History", "Reports", "Wellness Tips", "Chatbot", "Profile", "Settings", "Emergency"]
        page = st.sidebar.radio("Navigation", pages)
        if st.sidebar.button("Logout"):
            st.session_state.pop("user_id", None)
            st.session_state.pop("latest_test_id", None)
            st.rerun()
    else:
        page = st.sidebar.radio("Navigation", ["Home", "Login/Register", "Emergency"])
    return page


def main():
    inject_css()
    init_db()
    page = sidebar()
    if page == "Home": landing_page()
    elif page == "Login/Register": login_register_page()
    elif page == "Dashboard": dashboard_page()
    elif page == "Stress Test": stress_test_page()
    elif page == "Latest Result": result_page()
    elif page == "History": history_page()
    elif page == "Reports": reports_page()
    elif page == "Wellness Tips": wellness_page()
    elif page == "Chatbot": assistant_page()
    elif page == "Profile": profile_page()
    elif page == "Settings": settings_page()
    elif page == "Emergency": emergency_page()


if __name__ == "__main__":
    main()
