import streamlit as st
import pandas as pd
import random
import json
import gspread
import altair as alt
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid
from question_generator import generate_quiz_questions
import google.generativeai as genai

questions, quiz_id = generate_quiz_questions(st.secrets["GEMINI_API_KEY"])

# --- GOOGLE SHEETS SETUP ---
SHEET_NAME = "AgenticAI_Quiz_Leaderboard"
WORKSHEET_NAME = "Responses"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)

# --- STREAMLIT SESSION STATE INIT ---
if "name" not in st.session_state:
    st.session_state.name = ""
if "score" not in st.session_state:
    st.session_state.score = 0
if "step" not in st.session_state:
    st.session_state.step = 0
if "feedback" not in st.session_state:
    st.session_state.feedback = ""
if "quiz_started" not in st.session_state:
    st.session_state.quiz_started = False
if "show_leaderboard" not in st.session_state:
    st.session_state.show_leaderboard = False
if "quiz_id" not in st.session_state:
    st.session_state.quiz_id = str(uuid.uuid4())[:8]

# --- QUIZ QUESTIONS ---
def get_fresh_questions():
    return [
        {
            "question": "What is a defining trait of an agentic AI?",
            "options": ["It responds only to direct prompts", "It follows pre-written scripts", "It autonomously sets and pursues goals", "It only processes data in real-time"],
            "answer": "It autonomously sets and pursues goals"
        },
        {
            "question": "Which ability is MOST aligned with agentic behavior?",
            "options": ["Predict next word", "Store user preferences", "Create and follow multi-step plans", "Display search results"],
            "answer": "Create and follow multi-step plans"
        },
        {
            "question": "True or False: Agentic AI can adapt its actions based on environmental feedback.",
            "options": ["True", "False"],
            "answer": "True"
        }
    ]

if "questions" not in st.session_state:
    st.session_state.questions = get_fresh_questions()

# --- AGENT FEEDBACK FUNCTION ---
def agent_feedback(question, user_answer, correct_answer):
    if user_answer == correct_answer:
        return "✅ Nice! That’s exactly what an agentic AI would expect you to know."
    else:
        return f"🤖 Hmm, not quite. Agentic AI means {correct_answer.lower()}—think autonomy and purposeful action."



# --- START PAGE ---
st.title("🤖 Agentic AI Quiz Challenge")
tab1, tab2 = st.tabs(["🎮 Quiz", "📊 Dashboard"])

# --- TAB 1: QUIZ ---
with tab1:
    if not st.session_state.quiz_started:
        st.subheader("Enter your name to begin:")
        name = st.text_input("Your name")
        if st.button("Start Quiz") and name.strip():
            st.session_state.name = name.strip().title()
            st.session_state.quiz_started = True
            st.rerun()
    else:
        st.markdown(f"**👤 Player:** `{st.session_state.name}`")

        if st.session_state.step < len(st.session_state.questions):
            current = st.session_state.questions[st.session_state.step]
            st.subheader(f"Q{st.session_state.step + 1}: {current['question']}")
            user_answer = st.radio("Choose your answer:", current['options'])

            if st.button("Submit Answer"):
                is_correct = user_answer == current['answer']
                if is_correct:
                    st.session_state.score += 1
                st.session_state.feedback = agent_feedback(current['question'], user_answer, current['answer'])
                st.session_state.step += 1

                # Save response to ResponsesLog
                try:
                    response_log = client.open(SHEET_NAME).worksheet("ResponsesLog")
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    response_log.append_row([
                        st.session_state.name,
                        st.session_state.quiz_id,
                        current['question'],
                        user_answer,
                        current['answer'],
                        "✅" if is_correct else "❌",
                        timestamp
                    ])
                except Exception as e:
                    st.warning(f"⚠️ Could not log response: {e}")
                st.rerun()
        else:
            st.success(f"🎉 You've completed the quiz! Your score: {st.session_state.score} / {len(st.session_state.questions)}")

            # --- SAVE TO GOOGLE SHEET ---
            if not st.session_state.show_leaderboard:
                try:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    sheet.append_row([st.session_state.name, str(st.session_state.score), timestamp], value_input_option="USER_ENTERED")
                    st.success("✅ Score submitted to leaderboard!")
                    st.session_state.show_leaderboard = True
                except Exception as e:
                    st.error(f"❌ Failed to submit score: {e}")

            # --- CUSTOM LEADERBOARD VIEW ---
            st.markdown("### 🏆 Top Performers")
            leaderboard_placeholder = st.empty()

            def render_leaderboard():
                try:
                    records = sheet.get_all_values()
                    if len(records) < 2:
                        leaderboard_placeholder.warning("Leaderboard is empty.")
                    else:
                        headers = records[0]
                        values = records[1:]
                        leaderboard = pd.DataFrame(values, columns=headers)

                        leaderboard.columns = leaderboard.columns.str.strip()
                        if 'Score' not in leaderboard.columns:
                            leaderboard_placeholder.warning("Leaderboard format invalid: missing 'Score' column.")
                        else:
                            leaderboard['Score'] = pd.to_numeric(leaderboard['Score'], errors='coerce')
                            leaderboard['Timestamp'] = pd.to_datetime(leaderboard['Timestamp'], errors='coerce')
                            leaderboard = leaderboard.dropna(subset=['Score', 'Timestamp'])

                            leaderboard = leaderboard.sort_values(by='Timestamp', ascending=False)
                            leaderboard = leaderboard.drop_duplicates(subset='Name', keep='first')

                            #leaderboard['Avatar'] = leaderboard['Name'].apply(lambda x: random.choice(['🇵🇭','🇺🇸','🇯🇵','🇰🇷','🇮🇳','👽','🤖']))
                            leaderboard = leaderboard.sort_values(by="Score", ascending=False).reset_index(drop=True)
                            leaderboard.index += 1

                            # Sentence-case all names
                            leaderboard['Name'] = leaderboard['Name'].astype(str).str.title()

                            # Styling: Highlight Top 10
                            def highlight_top_10(row):
                                return ['background-color: #d1e7dd'] * len(row) if row.name < 11 else [''] * len(row)

                            styled_df = leaderboard[['Name', 'Score', 'Timestamp']].style \
                                .apply(highlight_top_10, axis=1) \
                                .set_properties(**{'text-align': 'left'})  # 👈 This aligns all cells to the left

                            # Display
                            leaderboard_placeholder.dataframe(styled_df, use_container_width=True)

                except Exception as e:
                    leaderboard_placeholder.error(f"❌ Failed to load leaderboard: {e}")

            render_leaderboard()

            if st.button("🔄 Refresh Leaderboard"):
                render_leaderboard()

            if st.button("🎮 Play Again"):
                st.session_state.score = 0
                st.session_state.step = 0
                st.session_state.feedback = ""
                st.session_state.show_leaderboard = False
                st.session_state.quiz_id = str(uuid.uuid4())[:8]
                # Keep name and skip intro
                st.session_state.questions = get_fresh_questions()  # Gemini re-generation
                st.rerun()


        if st.session_state.feedback and st.session_state.step <= len(st.session_state.questions):
            st.info(st.session_state.feedback)

# --- TAB 2: DASHBOARD ---
with tab2:
    st.subheader("📊 Quiz Insights Dashboard")
    try:
        dashboard_sheet = client.open(SHEET_NAME).worksheet("ResponsesLog")
        response_data = dashboard_sheet.get_all_records()
        df = pd.DataFrame(response_data)

        if df.empty:
            st.info("No quiz responses recorded yet.")
        else:
            for question in df["Question"].unique():
                q_df = df[df["Question"] == question]
                chart = alt.Chart(q_df).mark_bar().encode(
                    y=alt.X("Chosen Answer", sort="-y", title="Answer"),
                    x=alt.Y("count()", title="Responses"),
                    color=alt.Color("Is Correct?", scale=alt.Scale(domain=["✅", "❌"], range=["green", "red"]))
                ).properties(title=question, height=300)
                st.altair_chart(chart, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Failed to load dashboard data: {e}")
