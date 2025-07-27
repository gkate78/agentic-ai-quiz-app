# question_generator.py

import streamlit as st
import google.generativeai as genai
import json
import uuid
from datetime import datetime
import gspread
import random
from google.oauth2.service_account import Credentials

# Load Gemini API Key
GEMINI_API_KEY = st.secrets["api_keys"]["gemini"]
genai.configure(api_key=GEMINI_API_KEY)

# Define the required scope for Google Sheets API
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def generate_quiz_questions(api_key, topic="Agentic AI", num_questions=3):
    # Instantiate the model
    model = genai.GenerativeModel("gemini-pro")

    # Prompt to generate questions in JSON format
    prompt = (
        f"Generate {num_questions} beginner-friendly multiple-choice questions about {topic}.\n"
        "Output JSON only in this format:\n"
        "[{\"question\": \"...\", \"options\": [\"...\", \"...\", \"...\", \"...\"], \"answer\": \"...\"}]\n"
        "Ensure the correct answer is one of the options."
    )

    try:
        # Call Gemini API
        response = model.generate_content(prompt)

        # Parse Gemini response
        raw_content = response.text.strip().strip("```json").strip("```")
        questions = json.loads(raw_content)

        # Authenticate with Google Sheets
        creds = Credentials.from_service_account_info(
            st.secrets["GOOGLE_CREDENTIALS"], scopes=SCOPES
        )
        client = gspread.authorize(creds)
        sheet = client.open("AgenticAI_Quiz_Leaderboard").worksheet("QuestionsLog")

        # Create unique quiz ID and timestamp
        quiz_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Log questions to Google Sheet
        for q in questions:
            row = [
                quiz_id,
                timestamp,
                q["question"],
                "; ".join(q["options"]),
                q["answer"],
            ]
            sheet.append_row(row)

        return questions, quiz_id

    except Exception as e:
        st.error(f"❌ Error generating or saving questions: {e}")
        return [], None
