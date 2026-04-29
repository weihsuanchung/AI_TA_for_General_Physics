import base64
import hashlib
import json
import os
import re
import threading
from datetime import datetime, timezone, timedelta

import google.generativeai as genai
import gspread
import streamlit as st


st.set_page_config(layout="wide")
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])


SHEET_URL = "https://docs.google.com/spreadsheets/d/1BP0F_gTlwAJkcYFRqDDAnX3O4utJdnKg3pCthVBlHiI/edit?usp=sharing"

CHAPTERS = {
    "Electrostatic Field": "Electric charge, Coulomb's law, electric field, field lines, superposition",
    "Gauss's Law": "Electric flux, symmetry, Gaussian surfaces, conductors, enclosed charge",
    "Electric Potential": "Potential energy, electric potential, potential difference, gradients, equipotentials",
    "Capacitance": "Capacitors, dielectric materials, energy storage, series and parallel capacitance",
    "DC Circuit": "Current, resistance, Ohm's law, Kirchhoff rules, RC circuits, power",
    "Magnetostatics": "Magnetic fields, Lorentz force, Biot-Savart law, Ampere's law, magnetic force on currents",
    "Electromagnetic Induction": "Faraday's law, Lenz's law, motional emf, induced electric fields, generators",
    "Inductance": "Self-inductance, mutual inductance, RL circuits, magnetic energy, inductors",
}

CHAPTER_ORDER = list(CHAPTERS.keys())


def clean_pdf_chapter_name(filename):
    return os.path.splitext(filename)[0].strip()


def available_review_chapters():
    chapters = {}
    static_dir = "static"

    if os.path.isdir(static_dir):
        pdf_chapters = [
            clean_pdf_chapter_name(filename)
            for filename in os.listdir(static_dir)
            if filename.lower().endswith(".pdf")
        ]

        for known_chapter in CHAPTER_ORDER:
            normalized_known = known_chapter.casefold().replace(" ", "")
            match = next(
                (
                    chapter for chapter in pdf_chapters
                    if normalized_known in chapter.casefold().replace(" ", "")
                    or ("gauss" in normalized_known and "gauss" in chapter.casefold())
                ),
                None,
            )
            if match:
                chapters[known_chapter] = CHAPTERS[known_chapter]

        for chapter in sorted(pdf_chapters):
            if not any(chapter.casefold().replace(" ", "") in key.casefold().replace(" ", "") for key in chapters):
                chapters[chapter] = f"Key concepts from the {chapter} lecture notes"

    return chapters or CHAPTERS


def anonymize_student_id(raw_id):
    clean_id = str(raw_id).strip().lower()
    salted_id = clean_id + st.secrets["ID_SALT"]
    hash_object = hashlib.sha256(salted_id.encode("utf-8"))
    return str(int(hash_object.hexdigest()[:8], 16))


def get_google_client():
    credentials_dict = dict(st.secrets["connections"]["gsheets"])
    return gspread.service_account_from_dict(credentials_dict)


def log_to_sheets(anonymous_id, current_time, safe_text):
    try:
        gc = get_google_client()
        sh = gc.open_by_url(SHEET_URL)
        worksheet = sh.sheet1
        worksheet.append_row([anonymous_id, current_time, "Physics Review Zone", safe_text])
    except Exception as e:
        print(f"Logging failed silently: {e}")


def run_login_gate():
    if "student_id" not in st.session_state:
        st.title("🌟 Luminer: Physics Review Zone")
        st.info("Please enter your student ID to get started.")

        st.write(
            "**Important:** Your student ID will be anonymized and stored securely. "
            "We only use it to track your progress and analyze for our research."
        )

        with st.form("login_form"):
            student_id_input = st.text_input("Student ID:")
            submitted = st.form_submit_button("Log in")

            if submitted:
                if student_id_input.strip() == "":
                    st.error("Student ID cannot be empty.")
                else:
                    st.session_state.student_id = student_id_input.strip()
                    st.session_state.anonymous_id = anonymize_student_id(student_id_input)
                    st.rerun()

        st.stop()

    st.sidebar.success(f"Student ID: {st.session_state.student_id}")
    if st.sidebar.button("Log out"):
        del st.session_state.student_id
        del st.session_state.anonymous_id
        st.rerun()


def run_pre_test_gate():
    if "pre_test_done" not in st.session_state:
        try:
            gc = get_google_client()
            sh = gc.open_by_url(SHEET_URL)
            worksheet2 = sh.get_worksheet(1)
            existing_ids = worksheet2.col_values(1)
            st.session_state.pre_test_done = st.session_state.anonymous_id in existing_ids
        except Exception as e:
            st.error(f"Failed to read pre-test status: {e}")
            st.stop()

    if st.session_state.pre_test_done:
        return

    st.title("AI Literacy Survey (pre-test)")
    st.info("Please complete this short survey before using Luminer.")

    with st.form("pre_test_form"):
        q1 = st.slider("1. I know how to ask AI questions that help clarify my understanding.", 1, 5, 3)
        q2 = st.slider("2. When using AI, I explain my own reasoning or attempt before asking for help.", 1, 5, 3)
        q3 = st.slider("3. I use AI to help me understand concepts, not just to obtain answers.", 1, 5, 3)
        q4 = st.slider("4. I evaluate whether AI responses are correct before accepting them.", 1, 5, 3)
        q5 = st.slider("5. When AI responses are unclear, I ask follow-up questions to improve my understanding.", 1, 5, 3)
        q6 = st.slider("6. Using AI helps me identify gaps in my understanding.", 1, 5, 3)
        submitted = st.form_submit_button("Submit")

        if submitted:
            try:
                gc = get_google_client()
                sh = gc.open_by_url(SHEET_URL)
                worksheet2_write = sh.get_worksheet(1)
                worksheet2_write.append_row([st.session_state.anonymous_id, q1, q2, q3, q4, q5, q6])
                st.session_state.pre_test_done = True
                st.success("Pre-test submitted successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Pre-test submission failed: {e}")

    st.stop()


@st.cache_data
def load_lecture_pdf(filepath):
    with open(filepath, "rb") as f:
        pdf_bytes = f.read()
    return {
        "mime_type": "application/pdf",
        "data": base64.standard_b64encode(pdf_bytes).decode("utf-8"),
    }


def find_lecture_pdf(chapter):
    static_dir = "static"
    if not chapter or not os.path.isdir(static_dir):
        return None

    keyword = chapter.casefold().replace(" ", "")
    for filename in os.listdir(static_dir):
        if not filename.lower().endswith(".pdf"):
            continue
        normalized_filename = filename.casefold().replace(" ", "")
        if keyword in normalized_filename or normalized_filename in keyword or ("gauss" in keyword and "gauss" in normalized_filename):
            return os.path.join(static_dir, filename)

    return None


def get_model():
    model_name = st.secrets["MODEL_GeneralQA"] if "MODEL_GeneralQA" in st.secrets else st.secrets["MODEL_GUIDED"]
    return genai.GenerativeModel(
        model_name,
        system_instruction=(
            "You are Luminer, an AI teaching assistant for university-level General Physics. "
            "In Physics Review Zone, help students prepare for exams with clear diagnostics, "
            "concept review, and encouraging follow-up explanations. "
            "For any display equation, put opening $$ on its own line, equation content on the next line, "
            "and closing $$ on its own line. Add a blank line before and after every display equation."
        ),
    )


def parse_json_response(text):
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def normalize_math_markdown(text):
    """Keep display equations on their own lines so Streamlit renders LaTeX cleanly."""
    if not text:
        return text

    text = text.replace("\\[", "$$").replace("\\]", "$$")
    parts = text.split("$$")
    if len(parts) > 1:
        normalized_parts = []
        for index, part in enumerate(parts):
            if index % 2 == 0:
                normalized_parts.append(part)
            else:
                normalized_parts.append(f"\n\n$$\n{part.strip()}\n$$\n\n")
        text = "".join(normalized_parts)

    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_quiz(raw_quiz):
    questions = raw_quiz.get("questions", [])
    normalized = []

    for index, question in enumerate(questions[:15], start=1):
        q_type = question.get("type", "multiple_choice")
        if q_type not in {"multiple_choice", "fill_in"}:
            q_type = "multiple_choice"

        item = {
            "id": question.get("id", f"Q{index}"),
            "type": q_type,
            "question": question.get("question", "").strip(),
            "concept": question.get("concept", "").strip(),
            "answer": str(question.get("answer", "")).strip(),
            "explanation": question.get("explanation", "").strip(),
        }

        if q_type == "multiple_choice":
            options = question.get("options", [])
            item["options"] = [str(option).strip() for option in options if str(option).strip()]
            if len(item["options"]) < 4:
                continue

        if item["question"] and item["answer"]:
            normalized.append(item)

    return normalized


def generate_quiz(chapter, question_count):
    model = get_model()
    lecture_path = find_lecture_pdf(chapter)
    content = []
    chapter_focus = available_review_chapters().get(chapter, f"Key concepts from the {chapter} lecture notes")

    if lecture_path:
        content.append(load_lecture_pdf(lecture_path))
        content.append(
            f"Use the attached lecture notes for '{chapter}' as the primary reference. "
            "When referring to them, say 'according to the lecture notes' instead of 'according to your notes'."
        )

    content.append(
        f"""
Create a General Physics exam review quiz for chapter: {chapter}.
Chapter focus: {chapter_focus}.
When mentioning the source material, say "according to the lecture notes" instead of "according to your notes".

Generate exactly {question_count} questions.
Use a mix of multiple_choice and fill_in questions.
About 70% should be multiple_choice and 30% should be fill_in.
Questions should test concepts, common misconceptions, and light calculation skills.

Return ONLY valid JSON in this exact shape:
{{
  "chapter": "{chapter}",
  "questions": [
    {{
      "id": "Q1",
      "type": "multiple_choice",
      "concept": "short concept label",
      "question": "question text",
      "options": ["A ...", "B ...", "C ...", "D ..."],
      "answer": "A",
      "explanation": "one or two sentence explanation"
    }},
    {{
      "id": "Q2",
      "type": "fill_in",
      "concept": "short concept label",
      "question": "question text",
      "answer": "expected answer",
      "explanation": "one or two sentence explanation"
    }}
  ]
}}
"""
    )

    response = model.generate_content(content)
    quiz = parse_json_response(response.text)
    questions = normalize_quiz(quiz)

    if len(questions) < 8:
        raise ValueError("The generated quiz did not contain enough valid questions.")

    return {
        "chapter": chapter,
        "questions": questions,
    }


def grade_with_ai(chapter, questions, answers):
    model = get_model()
    grading_payload = {
        "chapter": chapter,
        "questions": questions,
        "student_answers": answers,
    }

    response = model.generate_content(
        [
            "Grade this Physics Review Zone quiz. Be fair with fill-in answers, including equivalent wording or formulas. "
            "Give concise exam-focused feedback. Mention strengths, weak concepts, and what to review next. "
            "If you refer to the source material, say 'according to the lecture notes' instead of 'according to your notes'. "
            "Then ask whether the student has questions.",
            json.dumps(grading_payload, ensure_ascii=False),
        ]
    )
    return response.text


def reset_review():
    for key in [
        "review_quiz",
        "review_answers",
        "review_feedback",
        "review_chat_messages",
        "review_submitted",
    ]:
        st.session_state.pop(key, None)


run_login_gate()
run_pre_test_gate()

st.title("Physics Review Zone")
st.caption("Review key exam concepts by chapter, then discuss your mistakes with Luminer.")

st.markdown(
    """
    <style>
    .stChatMessage p { margin-bottom: 1.1rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

review_chapters = available_review_chapters()
selected_chapter = st.sidebar.selectbox("Review chapter:", list(review_chapters.keys()))
question_count = st.sidebar.slider("Number of questions:", 10, 15, 12)

if st.sidebar.button("Start new review"):
    reset_review()
    st.rerun()

if "review_chat_messages" not in st.session_state:
    st.session_state.review_chat_messages = []

if "review_quiz" not in st.session_state:
    st.markdown("#### Choose a chapter and generate a review quiz")
    st.write(f"Current chapter: **{selected_chapter}**")
    st.write(review_chapters[selected_chapter])

    if st.button("Generate Review Quiz", type="primary"):
        with st.spinner("Luminer is designing your review quiz..."):
            try:
                st.session_state.review_quiz = generate_quiz(selected_chapter, question_count)
                st.session_state.review_answers = {}
                st.session_state.review_submitted = False
                st.rerun()
            except Exception as e:
                st.error(f"Quiz generation failed: {e}")

    st.stop()


quiz = st.session_state.review_quiz
questions = quiz["questions"]
st.markdown(f"#### {quiz['chapter']} Review Quiz")

if not st.session_state.get("review_submitted", False):
    with st.form("review_quiz_form"):
        answers = {}
        for index, question in enumerate(questions, start=1):
            st.markdown(f"**{index}. {question['question']}**")
            if question.get("concept"):
                st.caption(f"Concept: {question['concept']}")

            if question["type"] == "multiple_choice":
                answers[question["id"]] = st.radio(
                    "Choose one:",
                    question["options"],
                    key=f"review_answer_{question['id']}",
                    label_visibility="collapsed",
                )
            else:
                answers[question["id"]] = st.text_input(
                    "Your answer:",
                    key=f"review_answer_{question['id']}",
                )

            st.divider()

        submitted = st.form_submit_button("Submit Review")

    if submitted:
        st.session_state.review_answers = answers
        with st.spinner("Luminer is reviewing your answers..."):
            feedback = grade_with_ai(quiz["chapter"], questions, answers)
        st.session_state.review_feedback = feedback
        st.session_state.review_submitted = True

        tw_timezone = timezone(timedelta(hours=8))
        current_time = datetime.now(tw_timezone).strftime("%Y-%m-%d %H:%M:%S")
        safe_text = f"Completed review quiz: {quiz['chapter']}; questions={len(questions)}"
        threading.Thread(
            target=log_to_sheets,
            args=(st.session_state.anonymous_id, current_time, safe_text),
            daemon=True,
        ).start()

        st.rerun()

    st.stop()


st.markdown("#### Luminer's Feedback")
st.markdown(normalize_math_markdown(st.session_state.review_feedback))

with st.expander("Review your answers"):
    for index, question in enumerate(questions, start=1):
        answer = st.session_state.review_answers.get(question["id"], "")
        st.markdown(f"**{index}. {question['question']}**")
        st.write(f"Your answer: {answer}")
        st.write(f"Reference answer: {question['answer']}")
        if question.get("explanation"):
            st.caption(question["explanation"])

st.divider()
st.markdown("#### Ask Luminer about this review")

for message in st.session_state.review_chat_messages:
    with st.chat_message(message["role"]):
        st.markdown(normalize_math_markdown(message["content"]))

chat_prompt = st.chat_input("Ask about any question, concept, or mistake from this review...")

if chat_prompt:
    st.session_state.review_chat_messages.append({"role": "user", "content": chat_prompt})
    with st.chat_message("user"):
        st.markdown(chat_prompt)

    history = []
    for message in st.session_state.review_chat_messages[:-1]:
        role = "user" if message["role"] == "user" else "model"
        history.append({"role": role, "parts": [message["content"]]})

    chat = get_model().start_chat(history=history)
    review_context = {
        "chapter": quiz["chapter"],
        "questions": questions,
        "student_answers": st.session_state.review_answers,
        "feedback": st.session_state.review_feedback,
    }

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = chat.send_message(
                [
                    "The student just completed this review quiz. Use this context to answer follow-up questions.",
                    "If you refer to the source material, say 'according to the lecture notes' instead of 'according to your notes'.",
                    json.dumps(review_context, ensure_ascii=False),
                    chat_prompt,
                ],
                stream=True,
            )

        full_response = ""
        for chunk in response:
            if chunk.text:
                full_response += chunk.text
        full_response = normalize_math_markdown(full_response)
        st.markdown(full_response)

    st.session_state.review_chat_messages.append({"role": "assistant", "content": full_response})


st.sidebar.divider()
st.sidebar.markdown("**Contact**")
st.sidebar.markdown("If you encounter any issues or have questions, please contact us at: [b12202069@g.ntu.edu.tw](mailto:b12202069@g.ntu.edu.tw)")
