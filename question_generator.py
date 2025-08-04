# question_generator.py
import google.generativeai as genai
import json
import uuid
from datetime import datetime
import gspread

def generate_quiz_questions(api_key, topic="Agentic AI", num_questions=3):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-pro")

    prompt = (
        f"Generate {num_questions} multiple-choice questions about {topic}.\n"
        "Format as JSON:\n"
        "[{\"question\": \"...\", \"options\": [...], \"answer\": \"...\"}]"
    )

    try:
        response = model.generate_content(prompt)
        content = response.text.strip("```json\n").strip("```")
        questions = json.loads(content)

        # Save to Google Sheet
        creds = Credentials.from_service_account_info(st.secrets["GOOGLE_CREDENTIALS"], scopes=SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open("AgenticAI_Quiz_Leaderboard").worksheet("QuestionsLog")

        quiz_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for q in questions:
            row = [quiz_id, timestamp, q["question"], "; ".join(q["options"]), q["answer"]]
            sheet.append_row(row)

        return questions, quiz_id

    except Exception as e:
        print("❌ Error generating or saving questions:", e)
        return [], None
