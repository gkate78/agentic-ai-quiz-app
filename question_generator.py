# question_generator.py
import google.generativeai as genai
import json

def generate_quiz_questions(api_key, topic="Agentic AI", num_questions=3):
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-pro")

    prompt = (
        f"Generate {num_questions} multiple-choice questions about {topic}.\n"
        "Format the response as JSON like this:\n"
        "[\n"
        "  {\n"
        '    "question": "What is ...?",\n'
        '    "options": ["A", "B", "C", "D"],\n'
        '    "answer": "Correct option"\n'
        "  },\n"
        "  ...\n"
        "]"
    )

    try:
        response = model.generate_content(prompt)
        content = response.text.strip("```json\n").strip("```")
        questions = json.loads(content)
        return questions
    except Exception as e:
        print("Error:", e)
        return []
