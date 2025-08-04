import streamlit as st
import pandas as pd
import random
import json
import gspread
import altair as alt
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid


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
if "questions" not in st.session_state:
    st.session_state.questions = get_fresh_questions()
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

# --- QUIZ QUESTIONS ---
def get_fresh_questions():
    return generate_quiz_questions(
        api_key=st.secrets["GEMINI_API_KEY"],
        topic="Agentic AI",
        num_questions=3
    )
# --- AGENT FEEDBACK FUNCTION ---
def agent_feedback(question, user_answer, correct_answer):
    if user_answer == correct_answer:
        return "✅ Nice! That’s exactly what an agentic AI would expect you to know."
    else:
        return f"🤖 Hmm, not quite. Agentic AI means {correct_answer.lower()}—think autonomy and purposeful action."

# --- QUIZ QUESTIONS ---
quiz_data = [
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

# --- START PAGE ---
st.title("🤖 Agentic AI Quiz Challenge")
st.markdown("Test your knowledge and learn how Agentic AI thinks!")
tab1, tab2 = st.tabs(["🎮 Quiz", "📊 Dashboard"])
with tab1:
    


    if not st.session_state.quiz_started:
       st.subheader("Enter your name to begin:")
       name = st.text_input("Your name")
       if st.button("Start Quiz") and name.strip():
           st.session_state.name = name.strip()
           st.session_state.quiz_started = True
           st.rerun()
       else:
            st.markdown(f"**👤 Player:** `{st.session_state.name}`")

            if st.session_state.step < len(quiz_data):
                current = quiz_data[st.session_state.step]
                st.subheader(f"Q{st.session_state.step + 1}: {current['question']}")
                user_answer = st.radio("Choose your answer:", current['options'])

            if st.button("Submit Answer"):
                if user_answer == current['answer']:
                    st.session_state.score += 1
            st.session_state.feedback = agent_feedback(current['question'], user_answer, current['answer'])
            st.session_state.step += 1
            st.rerun()
    else:
        st.success(f"🎉 You've completed the quiz! Your score: {st.session_state.score} / {len(quiz_data)}")





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

                        leaderboard['Avatar'] = leaderboard['Name'].apply(lambda x: random.choice(['🇵🇭','🇺🇸','🇯🇵','🇰🇷','🇮🇳','👽','🤖']))
                        leaderboard = leaderboard.sort_values(by="Score", ascending=False).reset_index(drop=True)
                        leaderboard.index += 1

                        leaderboard_placeholder.dataframe(
                            leaderboard[['Avatar', 'Name', 'Score', 'Timestamp']].style
                            .highlight_max(subset=["Score"], color="lightgreen")
                            .set_properties(**{"text-align": "left"})
                        )
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
            st.session_state.questions = get_fresh_questions()
            st.rerun()
