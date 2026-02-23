import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import random
import re

load_dotenv()

# ── API CONFIG ──────────────────────────────────────────────────────────────
API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDbGcPr1EiJdjFWMhxcRJOv2sNq44ERWnk")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Skill Roadmap Generator",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main-header {
    font-size: 2.6rem; font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-align: center; margin-bottom: 0.3rem;
}
.sub-header {
    font-size: 1.1rem; color: #888; text-align: center; margin-bottom: 2rem;
}
.feature-card {
    background: linear-gradient(135deg, #1e1e2e, #2a2a3e);
    border: 1px solid #444; border-radius: 12px;
    padding: 1.2rem; margin-bottom: 1rem;
}
.badge {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 0.75rem; font-weight: 600; margin: 2px;
}
.badge-green  { background: #1a4731; color: #4ade80; }
.badge-blue   { background: #1e3a5f; color: #60a5fa; }
.badge-purple { background: #3b1f5e; color: #c084fc; }
.stProgress > div > div > div { background: linear-gradient(90deg, #667eea, #764ba2); }
.quiz-correct   { background: #1a4731; border-left: 4px solid #4ade80; padding: 1rem; border-radius: 8px; }
.quiz-incorrect { background: #4c1d1d; border-left: 4px solid #f87171; padding: 1rem; border-radius: 8px; }
.streak-box {
    background: linear-gradient(135deg, #f59e0b, #d97706);
    border-radius: 12px; padding: 1rem; text-align: center; color: white; font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE DEFAULTS ───────────────────────────────────────────────────
for key, default in {
    "roadmap_text": "",
    "structured_data": None,
    "quiz_questions": [],
    "quiz_index": 0,
    "quiz_score": 0,
    "quiz_done": False,
    "completed_topics": set(),
    "streak": 0,
    "xp": 0,
    "area_of_interest": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── HEADER ───────────────────────────────────────────────────────────────────
st.markdown('<h1 class="main-header">🎓 AI Skill Roadmap Generator</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Your Personalized, Interactive Learning Journey — 100% Free</p>', unsafe_allow_html=True)

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📝 Your Profile")

    qualification = st.selectbox("Current Qualification",
        ["10th Grade","12th Grade","Undergraduate","Graduate","Post Graduate","Other"])

    area_of_interest = st.text_input("Area of Interest",
        placeholder="e.g., Web Development, Data Science")

    time_available = st.slider("Hours Available Per Day", 0.5, 8.0, 2.0, 0.5)

    duration_preference = st.radio("Roadmap Duration",
        ["1 Month","3 Months","6 Months","1 Year"])

    experience_level = st.selectbox("Current Experience Level",
        ["Complete Beginner","Some Knowledge","Intermediate","Advanced"])

    learning_style = st.multiselect("Preferred Learning Style",
        ["Videos","Reading/Docs","Hands-on Projects","Quizzes","Community/Forums"],
        default=["Videos","Hands-on Projects"])

    goal = st.text_area("Your Goal (Optional)",
        placeholder="e.g., Get a job, Build a project, Freelance")

    st.markdown("---")
    generate_button = st.button("🚀 Generate My Roadmap", use_container_width=True, type="primary")

    # ── XP / Streak widget ──
    if st.session_state.xp > 0:
        st.markdown(f"""
        <div class="streak-box">
            🔥 Streak: {st.session_state.streak} days<br>
            ⭐ XP: {st.session_state.xp}
        </div>""", unsafe_allow_html=True)

# ── HELPER: CALL GEMINI ──────────────────────────────────────────────────────
def call_gemini(prompt: str) -> str:
    try:
        resp = model.generate_content(prompt)
        return resp.text
    except Exception as e:
        return f"ERROR: {e}"


# ── HELPER: GENERATE STRUCTURED JSON ─────────────────────────────────────────
def generate_structured_roadmap(area, qualification, time_available, duration, level, style, goal):
    prompt = f"""
You are an expert educational counselor. Return ONLY valid JSON (no markdown, no explanation).

Create a learning roadmap for:
- Area: {area}
- Qualification: {qualification}
- Daily Time: {time_available} hours
- Duration: {duration}
- Level: {level}
- Learning Style: {', '.join(style)}
- Goal: {goal or 'General learning'}

JSON schema (fill all fields with real content):
{{
  "overview": "2-3 sentence overview of the field",
  "career_paths": ["role1", "role2", "role3", "role4"],
  "avg_salary_range": "e.g. ₹4-12 LPA",
  "phases": [
    {{
      "phase": 1,
      "title": "Phase title",
      "duration": "e.g. 2 weeks",
      "topics": ["topic1","topic2","topic3"],
      "free_resources": [
        {{"name": "resource name", "url": "https://...", "type": "Video/Course/Docs"}}
      ],
      "project": "A concrete mini-project to build",
      "skills_gained": ["skill1","skill2"]
    }}
  ],
  "quiz": [
    {{
      "question": "Question text?",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "answer": "A) ...",
      "explanation": "Why this is correct"
    }}
  ],
  "daily_schedule": {{
    "morning": "30-min activity",
    "afternoon": "1-hour activity",
    "evening": "30-min activity"
  }},
  "motivational_quote": "An inspiring quote relevant to learning {area}"
}}

Return 4-6 phases and 5 quiz questions. All resources must be real and free.
"""
    raw = call_gemini(prompt)
    # Strip possible markdown fences
    raw = re.sub(r"^```json\s*", "", raw.strip())
    raw = re.sub(r"```$", "", raw.strip())
    try:
        return json.loads(raw)
    except Exception:
        return None


# ── HELPER: DRAW GANTT ────────────────────────────────────────────────────────
def draw_gantt(phases):
    today = datetime.today()
    rows = []
    start = today
    for p in phases:
        # parse duration weeks
        weeks = 2
        m = re.search(r"(\d+)\s*week", p.get("duration",""), re.I)
        if m:
            weeks = int(m.group(1))
        else:
            m2 = re.search(r"(\d+)\s*month", p.get("duration",""), re.I)
            if m2:
                weeks = int(m2.group(1)) * 4
        end = start + timedelta(weeks=weeks)
        rows.append(dict(
            Task=f"Phase {p['phase']}: {p['title']}",
            Start=start.strftime("%Y-%m-%d"),
            Finish=end.strftime("%Y-%m-%d"),
            Phase=p["phase"]
        ))
        start = end

    df = pd.DataFrame(rows)
    colors = px.colors.qualitative.Pastel
    fig = px.timeline(df, x_start="Start", x_end="Finish", y="Task",
                      color="Phase", color_discrete_sequence=colors,
                      title="📅 Your Learning Timeline")
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(showlegend=False, height=300,
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      font_color="white", title_font_size=16)
    return fig


# ── HELPER: SKILL RADAR ───────────────────────────────────────────────────────
def draw_skill_radar(phases, completed_topics):
    all_skills = []
    for p in phases:
        all_skills.extend(p.get("skills_gained", []))
    # Count unique skills
    skill_counts = {}
    for p in phases:
        for s in p.get("skills_gained", []):
            phase_topics = p.get("topics", [])
            done = sum(1 for t in phase_topics if t in completed_topics)
            ratio = done / max(len(phase_topics), 1)
            skill_counts[s] = skill_counts.get(s, 0) + ratio

    if not skill_counts:
        return None

    labels = list(skill_counts.keys())[:8]
    values = [min(skill_counts[l] * 100, 100) for l in labels]

    fig = go.Figure(go.Scatterpolar(
        r=values + [values[0]],
        theta=labels + [labels[0]],
        fill="toself",
        fillcolor="rgba(102,126,234,0.3)",
        line=dict(color="#667eea", width=2),
        name="Your Progress"
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], color="#888")),
        showlegend=False, height=350,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="white", title="🕸️ Skill Radar",
        title_font_size=16
    )
    return fig


# ── GENERATE BUTTON CLICKED ───────────────────────────────────────────────────
if generate_button:
    if not area_of_interest.strip():
        st.error("⚠️ Please enter your area of interest!")
    else:
        st.session_state.area_of_interest = area_of_interest
        with st.spinner("🤖 Building your personalized roadmap…"):
            data = generate_structured_roadmap(
                area_of_interest, qualification, time_available,
                duration_preference, experience_level, learning_style, goal
            )
            if data:
                st.session_state.structured_data = data
                st.session_state.quiz_questions = data.get("quiz", [])
                st.session_state.quiz_index = 0
                st.session_state.quiz_score = 0
                st.session_state.quiz_done = False
                st.session_state.completed_topics = set()
                st.session_state.xp += 50  # XP for generating
                st.success("✅ Roadmap ready! Explore the tabs below.")
            else:
                # Fallback to plain text
                plain_prompt = f"""
                Create a detailed learning roadmap for {area_of_interest}.
                Qualification: {qualification}, Level: {experience_level},
                Duration: {duration_preference}, Daily time: {time_available}h.
                Include phases, free resources, projects, and career paths.
                """
                st.session_state.roadmap_text = call_gemini(plain_prompt)
                st.warning("⚠️ Loaded in basic mode. All content is available in the Roadmap tab.")


# ── MAIN CONTENT ──────────────────────────────────────────────────────────────
data = st.session_state.structured_data

if data or st.session_state.roadmap_text:

    tabs = st.tabs([
        "🗺️ Roadmap",
        "📅 Timeline",
        "✅ Progress Tracker",
        "🧠 Quiz Yourself",
        "🕸️ Skill Radar",
        "⏰ Daily Planner",
        "📥 Export",
    ])

    # ── TAB 1: ROADMAP ────────────────────────────────────────────────────────
    with tabs[0]:
        if data:
            # Overview card
            st.markdown(f"""
            <div class="feature-card">
                <b>📖 Overview</b><br>{data.get('overview','')}
                <br><br>
                <b>💼 Career Paths:</b> {' '.join([f'<span class="badge badge-purple">{c}</span>' for c in data.get('career_paths',[])])}
                <br>
                <b>💰 Avg Salary:</b> <span class="badge badge-green">{data.get('avg_salary_range','')}</span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"> 💬 *\"{data.get('motivational_quote','')}\"*")
            st.markdown("---")

            # Phases
            for p in data.get("phases", []):
                with st.expander(f"🔷 Phase {p['phase']}: {p['title']}  —  ⏱ {p['duration']}", expanded=(p['phase']==1)):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**📚 Topics to Learn:**")
                        for t in p.get("topics", []):
                            st.markdown(f"- {t}")
                        st.markdown(f"**🛠️ Mini Project:** {p.get('project','')}")
                    with col_b:
                        st.markdown("**🔗 Free Resources:**")
                        for r in p.get("free_resources", []):
                            badge_class = "badge-blue" if r.get("type") == "Video" else "badge-green"
                            st.markdown(
                                f'<span class="badge {badge_class}">{r.get("type","")}</span> '
                                f'[{r.get("name","")}]({r.get("url","#")})',
                                unsafe_allow_html=True
                            )
                        st.markdown("**⚡ Skills Gained:**")
                        st.markdown(' '.join([f'<span class="badge badge-purple">{s}</span>' for s in p.get("skills_gained",[])]), unsafe_allow_html=True)
        else:
            st.markdown(st.session_state.roadmap_text)

    # ── TAB 2: TIMELINE ───────────────────────────────────────────────────────
    with tabs[1]:
        if data and data.get("phases"):
            st.plotly_chart(draw_gantt(data["phases"]), use_container_width=True)
            st.info("📌 This timeline is calculated from today's date based on each phase's duration.")
        else:
            st.info("Generate a roadmap first to see the timeline.")

    # ── TAB 3: PROGRESS TRACKER ───────────────────────────────────────────────
    with tabs[2]:
        if data and data.get("phases"):
            st.subheader("✅ Track Your Progress")
            total_topics = sum(len(p.get("topics",[])) for p in data["phases"])
            completed = st.session_state.completed_topics

            for p in data["phases"]:
                st.markdown(f"**Phase {p['phase']}: {p['title']}**")
                cols = st.columns(min(len(p.get("topics",[])), 3))
                for i, topic in enumerate(p.get("topics",[])):
                    with cols[i % 3]:
                        key = f"topic_{p['phase']}_{i}"
                        checked = topic in completed
                        if st.checkbox(topic, value=checked, key=key):
                            if topic not in completed:
                                st.session_state.completed_topics.add(topic)
                                st.session_state.xp += 10
                        else:
                            st.session_state.completed_topics.discard(topic)
                st.markdown("---")

            done_count = len(st.session_state.completed_topics)
            pct = int(done_count / max(total_topics, 1) * 100)
            st.markdown(f"### Overall Progress: {pct}% ({done_count}/{total_topics} topics)")
            st.progress(pct / 100)

            if pct == 100:
                st.balloons()
                st.success("🎉 Congratulations! You've completed the entire roadmap!")
            elif pct >= 50:
                st.success("🔥 You're halfway there — keep going!")
        else:
            st.info("Generate a roadmap first to track your progress.")

    # ── TAB 4: QUIZ ───────────────────────────────────────────────────────────
    with tabs[3]:
        st.subheader("🧠 Knowledge Quiz")
        questions = st.session_state.quiz_questions

        if not questions:
            st.info("Generate a roadmap first to unlock the quiz!")
        elif st.session_state.quiz_done:
            score = st.session_state.quiz_score
            total = len(questions)
            pct = int(score / total * 100)
            st.markdown(f"## 🎯 Your Score: {score}/{total} ({pct}%)")
            if pct >= 80:
                st.success("🏆 Excellent! You have a strong foundation!")
            elif pct >= 50:
                st.warning("👍 Good effort! Review the roadmap and retry.")
            else:
                st.error("💪 Keep learning! Revisit the basics and try again.")

            if st.button("🔄 Retry Quiz"):
                st.session_state.quiz_index = 0
                st.session_state.quiz_score = 0
                st.session_state.quiz_done = False
                st.rerun()
        else:
            idx = st.session_state.quiz_index
            if idx < len(questions):
                q = questions[idx]
                st.markdown(f"**Question {idx+1} of {len(questions)}**")
                st.progress((idx) / len(questions))
                st.markdown(f"### {q.get('question','')}")

                choice = st.radio("Choose your answer:", q.get("options",[]), key=f"quiz_{idx}")

                if st.button("Submit Answer ✔️"):
                    if choice == q.get("answer"):
                        st.markdown('<div class="quiz-correct">✅ Correct!</div>', unsafe_allow_html=True)
                        st.markdown(f"*{q.get('explanation','')}*")
                        st.session_state.quiz_score += 1
                        st.session_state.xp += 20
                    else:
                        st.markdown(f'<div class="quiz-incorrect">❌ Incorrect. Correct answer: **{q.get("answer","")}**</div>', unsafe_allow_html=True)
                        st.markdown(f"*{q.get('explanation','')}*")

                    st.session_state.quiz_index += 1
                    if st.session_state.quiz_index >= len(questions):
                        st.session_state.quiz_done = True
                    if st.button("Next ➡️"):
                        st.rerun()
                    else:
                        st.info("Click **Next ➡️** to continue or re-run the page.")

    # ── TAB 5: SKILL RADAR ───────────────────────────────────────────────────
    with tabs[4]:
        if data and data.get("phases"):
            fig = draw_skill_radar(data["phases"], st.session_state.completed_topics)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Radar updates as you tick off topics in the Progress Tracker.")

                # XP leaderboard (local session)
                st.markdown("---")
                st.markdown("### ⭐ Your Stats")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total XP", st.session_state.xp)
                c2.metric("Topics Done", len(st.session_state.completed_topics))
                c3.metric("Quiz Score", f"{st.session_state.quiz_score}/{len(st.session_state.quiz_questions)}")
        else:
            st.info("Generate a roadmap to see your skill radar.")

    # ── TAB 6: DAILY PLANNER ─────────────────────────────────────────────────
    with tabs[5]:
        st.subheader("⏰ Daily Study Planner")
        if data and data.get("daily_schedule"):
            sched = data["daily_schedule"]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("### 🌅 Morning")
                st.info(sched.get("morning", ""))
            with col2:
                st.markdown("### ☀️ Afternoon")
                st.info(sched.get("afternoon", ""))
            with col3:
                st.markdown("### 🌙 Evening")
                st.info(sched.get("evening", ""))

            st.markdown("---")
            st.markdown("### 📆 Weekly Habit Tracker")
            days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
            cols = st.columns(7)
            for i, day in enumerate(days):
                with cols[i]:
                    st.checkbox(day, key=f"habit_{day}")

            # Pomodoro timer hint
            st.markdown("---")
            st.markdown("""
            ### 🍅 Pomodoro Study Tips
            - **25 min** focused study → **5 min** break
            - After 4 rounds → **15–30 min** long break
            - Use [Pomofocus.io](https://pomofocus.io) (free, no signup)
            """)
        else:
            st.info("Generate a roadmap to see your daily planner.")

    # ── TAB 7: EXPORT ─────────────────────────────────────────────────────────
    with tabs[6]:
        st.subheader("📥 Export Your Roadmap")
        if data:
            # Build markdown export
            lines = [f"# {st.session_state.area_of_interest} Learning Roadmap\n"]
            lines.append(f"**Overview:** {data.get('overview','')}\n")
            lines.append(f"**Career Paths:** {', '.join(data.get('career_paths',[]))}\n")
            lines.append(f"**Salary Range:** {data.get('avg_salary_range','')}\n\n")
            for p in data.get("phases",[]):
                lines.append(f"## Phase {p['phase']}: {p['title']} ({p['duration']})\n")
                lines.append("### Topics\n" + "\n".join(f"- {t}" for t in p.get("topics",[])) + "\n")
                lines.append(f"### Mini Project\n{p.get('project','')}\n")
                lines.append("### Free Resources\n")
                for r in p.get("free_resources",[]):
                    lines.append(f"- [{r.get('name','')}]({r.get('url','')}) — {r.get('type','')}\n")
                lines.append("\n")
            md_content = "\n".join(lines)

            st.download_button(
                "📄 Download as Markdown",
                data=md_content,
                file_name=f"{st.session_state.area_of_interest.replace(' ','_')}_roadmap.md",
                mime="text/markdown",
                use_container_width=True,
            )

            # JSON export
            st.download_button(
                "🗂️ Download as JSON",
                data=json.dumps(data, indent=2),
                file_name=f"{st.session_state.area_of_interest.replace(' ','_')}_roadmap.json",
                mime="application/json",
                use_container_width=True,
            )
        else:
            st.info("Generate a roadmap first to export it.")

# ── LANDING (no roadmap yet) ──────────────────────────────────────────────────
else:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="feature-card">
        <h3>🗺️ Structured Phases</h3>
        Not just a list — a phased, week-by-week plan with real free resources linked directly.
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="feature-card">
        <h3>🧠 Built-in Quiz</h3>
        Test your knowledge with AI-generated quiz questions tailored to your chosen topic.
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="feature-card">
        <h3>✅ Progress Tracker</h3>
        Tick off topics as you learn, earn XP, and watch your skill radar grow.
        </div>""", unsafe_allow_html=True)

    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown("""
        <div class="feature-card">
        <h3>📅 Visual Timeline</h3>
        See your entire journey as an interactive Gantt chart from today's date.
        </div>""", unsafe_allow_html=True)
    with col5:
        st.markdown("""
        <div class="feature-card">
        <h3>⏰ Daily Planner</h3>
        Morning, afternoon, and evening schedule + weekly habit tracker built in.
        </div>""", unsafe_allow_html=True)
    with col6:
        st.markdown("""
        <div class="feature-card">
        <h3>📥 Export Anywhere</h3>
        Download your roadmap as Markdown or JSON to use offline or share.
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    ### 💡 Popular Topics to Try:
    `Web Development` · `Python Programming` · `Data Science` · `Digital Marketing`
    · `Graphic Design` · `Mobile App Development` · `Machine Learning` · `Cybersecurity`
    """)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align:center; color:#666; padding:1rem;'>
    Made with ❤️ for empowering learners everywhere &nbsp;|&nbsp; Powered by Google Gemini AI
</div>
""", unsafe_allow_html=True)