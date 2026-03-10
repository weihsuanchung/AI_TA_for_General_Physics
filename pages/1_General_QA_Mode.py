import streamlit as st
import google.generativeai as genai
import time
import gspread
from PIL import Image
import pandas as pd
from datetime import datetime, timezone, timedelta
from streamlit_gsheets import GSheetsConnection

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# ================= 學號登入閘門 =================
if "student_id" not in st.session_state:
    st.title("🎓 Hi! I'm your AI teaching assistant!")
    st.info("Please enter your student ID to get started. (請輸入學號以開始使用)")
    
    # 使用表單 (form) 讓使用者輸入並按下 Enter 或按鈕送出
    with st.form("login_form"):
        student_id_input = st.text_input("Student ID (學號):")
        submitted = st.form_submit_button("Log in (登入)")
        
        if submitted:
            if student_id_input.strip() == "":
                st.error("Student ID cannot be empty! (學號不能為空！)")
            else:
                # 把學號存進 session_state，並重新整理網頁
                st.session_state.student_id = student_id_input.strip()
                st.rerun()
                
    st.stop()
# ======================================================
# 在側邊欄或標題顯示學號
st.sidebar.success(f"Student ID: {st.session_state.student_id}")
if st.sidebar.button("Log out (登出)"):
    del st.session_state.student_id
    st.rerun()

general_qa_instruction = """
You are an AI teaching assistant dedicated to university-level General Physics.
You are currently in 【General QA Mode】.
Your goal is to "clearly, accurately, and comprehensively answer students' physics questions."
1. Direct and Detailed Solutions: When a student asks a question, provide the complete, step-by-step physics derivation and the final answer.
2. Conceptual Breakdown: While giving the answer, clearly explain the core physics concepts behind it so the student understands the "why".
3. Perfect Formatting: 
   - For simple variables mentioned in sentences, use inline LaTeX (e.g., $x$, $v$, $t$).
   - For ALL equations, formulas, and calculation steps, you MUST use block LaTeX with double dollar signs (e.g., $$ F = ma $$) so they are rendered on a new line and centered.
"""

model = genai.GenerativeModel(
    'gemini-3.1-pro-preview',
    system_instruction=general_qa_instruction
)

st.title("AI Teaching Assistant for NTU General Physics - General Q&A Mode")
st.caption("Hello! I'm your AI teaching assistant for general physics. Get complete physics derivations and conceptual breakdowns here!")

if "qa_messages" not in st.session_state:
    st.session_state.qa_messages = []

for message in st.session_state.qa_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
    if "image" in message and message["image"] is not None:
            st.image(message["image"], width=300)

if prompt := st.chat_input("Enter your physics question here:", accept_file=True, file_type=["png", "jpg", "jpeg"]):

    user_text = prompt.text
    uploaded_file = prompt.files[0] if prompt.files else None

    image_to_send = None
    if uploaded_file is not None:
        uploaded_file.seek(0)
        image_to_send = Image.open(uploaded_file).convert('RGB')

    with st.chat_message("user"):
        if user_text:
            st.markdown(user_text)
        if image_to_send:
            st.image(image_to_send, width=300)

    safe_text = user_text if user_text else "Only image uploaded."

    # st.chat_message("user").markdown(prompt)
    st.session_state.qa_messages.append({"role": "user", "content": safe_text, "image": image_to_send})

    # ================= 資料庫紀錄區塊 =================
    tw_timezone = timezone(timedelta(hours=8))
    current_time = datetime.now(tw_timezone).strftime("%Y-%m-%d %H:%M:%S")
    log_data = {
        "student_id": st.session_state.student_id,
        "time": current_time,
        "mode": "General Q&A Mode",
        "question": safe_text
    }

    try:
        # 建立與 Google Sheets 的連線
        # conn = st.connection("gsheets", type=GSheetsConnection)
        credentials_dict = dict(st.secrets["connections"]["gsheets"])
        gc = gspread.service_account_from_dict(credentials_dict)
        
        # SHEET_URL = st.secrets["SHEET_URL"] 
        SHEET_URL = 'https://docs.google.com/spreadsheets/d/1BP0F_gTlwAJkcYFRqDDAnX3O4utJdnKg3pCthVBlHiI/edit?usp=sharing'

        # 打開試算表的第一個分頁
        # spreadsheet = conn.client.open_by_url(SHEET_URL)
        # worksheet = spreadsheet.sheet1 
        sh = gc.open_by_url(SHEET_URL)
        worksheet = sh.sheet1
        
        # 把要紀錄的資料排成一列 (List 格式)
        row_to_append = [
            st.session_state.student_id,
            current_time,
            "General Q&A Mode",
            safe_text
        ]
        
        # 往下新增一行
        worksheet.append_row(row_to_append)

    except Exception as e:
        st.error(f"Failed to log data to Google Sheets: {e}")
    # ==============================================================

    gemini_history = []
    for msg in st.session_state.qa_messages[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        # gemini_history.append({"role": role, "parts": [msg["content"]]})
        parts = [msg["content"]]

        if "image" in msg and msg["image"] is not None:
            parts.insert(0, msg["image"])
        gemini_history.append({"role": role, "parts": parts})
    
    chat = model.start_chat(history=gemini_history)


    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            
            content_to_send = []
            if image_to_send:
                content_to_send.append(image_to_send)
            if user_text:
                content_to_send.append(user_text)
            else:
                content_to_send.append("Please analyze the uploaded image and provide the step-by-step solution.") 
            response = chat.send_message(content_to_send, stream=True)
        
        # 像打字機一樣輸出
        def stream_generator():
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        full_response = st.write_stream(stream_generator())
        
    st.session_state.qa_messages.append({"role": "assistant", "content": full_response}) 