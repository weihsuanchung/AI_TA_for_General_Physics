import streamlit as st
import google.generativeai as genai
import time
import hashlib
import gspread
from PIL import Image
import pandas as pd
from datetime import datetime, timezone, timedelta
from streamlit_gsheets import GSheetsConnection

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def anonymize_student_id(raw_id):
    # 去除頭尾空白，並全部轉成小寫
    clean_id = str(raw_id).strip().lower()
    
    salt = "luminer_secret_ntu_physics" 
    salted_id = clean_id + salt
    
    # 使用 SHA-256 演算法進行hashing
    hash_object = hashlib.sha256(salted_id.encode('utf-8'))
    
    hex_digest = hash_object.hexdigest()
    anonymous_number = str(int(hex_digest[:8], 16))
    
    return anonymous_number

# ================= 學號登入閘門 =================
if "student_id" not in st.session_state:
    st.title("🎓 Hi! I'm your AI teaching assistant, Luminer!")
    st.info("Please enter your student ID to get started. (請輸入學號以開始使用)")

    st.write("**Important**: Your student ID will be anonymized (hashed) and stored securely. We only use it to track your progress and analyze for our research. Your privacy is our top priority!")
    
    # 使用表單 (form) 讓使用者輸入並按下 Enter 或按鈕送出
    with st.form("login_form"):
        student_id_input = st.text_input("Student ID (學號):")
        submitted = st.form_submit_button("Log in (登入)")
        
        if submitted:
            if student_id_input.strip() == "":
                st.error("Student ID cannot be empty! (學號不能為空！)")
            else:
                anonymous_id = anonymize_student_id(student_id_input)
                # 把學號存進 session_state，並重新整理網頁
                st.session_state.student_id = student_id_input.strip()
                st.session_state.anonymous_id = anonymous_id
                st.rerun()
                
    st.stop()
# ======================================================
# 在側邊欄或標題顯示學號
st.sidebar.success(f"Student ID: {st.session_state.student_id}")
if st.sidebar.button("Log out (登出)"):
    del st.session_state.student_id
    del st.session_state.anonymous_id
    st.rerun()

# ================= 前測問卷攔截閘門 =================
if "pre_test_done" not in st.session_state:
    try:
        # 連線到 Google Sheets
        credentials_dict = dict(st.secrets["connections"]["gsheets"])
        gc = gspread.service_account_from_dict(credentials_dict)
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1BP0F_gTlwAJkcYFRqDDAnX3O4utJdnKg3pCthVBlHiI/edit?usp=sharing" 
        sh = gc.open_by_url(SHEET_URL)
        
        # 取得第二個分頁 (索引值為 1，因為第一個是 0)
        worksheet2 = sh.get_worksheet(1) 
        
        existing_ids = worksheet2.col_values(1)
        
        # 檢查現在登入的學號是不是已經在問卷紀錄裡了
        if st.session_state.anonymous_id in existing_ids:
            st.session_state.pre_test_done = True
        else:
            st.session_state.pre_test_done = False
            
    except Exception as e:
        st.error(f"Failed to read pre-test status: {e}")
        st.stop()

# 如果還沒做過問卷，就顯示表單並擋住後面的對話框
if not st.session_state.pre_test_done:
    st.title("📝 AI Literacy Survey (pre-test)")
    st.info("Instructions: Please indicate your level of agreement with the following statements. This will help us understand your current familiarity with AI and physics. (請根據以下陳述選擇你的認同程度，這將幫助我們了解你目前對 AI 和物理的熟悉程度。)")
    
    with st.form("pre_test_form"):
        # 這裡可以自由替換成你想問的問題！
        q1 = st.slider("1. I know how to ask AI questions that help clarify my understanding. (5 = Strongly Agree, 4 = Agree, 3 = Neutral, 2 = Disagree, 1 = Strongly Disagree)", 1, 5, 3)
        q2 = st.slider("2. When using AI, I explain my own reasoning or attempt before asking for help. (5 = Strongly Agree, 4 = Agree, 3 = Neutral, 2 = Disagree, 1 = Strongly Disagree)", 1, 5, 3)
        q3 = st.slider("3. I use AI to help me understand concepts, not just to obtain answers. (5 = Strongly Agree, 4 = Agree, 3 = Neutral, 2 = Disagree, 1 = Strongly Disagree)", 1, 5, 3)
        q4 = st.slider("4. I evaluate whether AI responses are correct before accepting them. (5 = Strongly Agree, 4 = Agree, 3 = Neutral, 2 = Disagree, 1 = Strongly Disagree)", 1, 5, 3)
        q5 = st.slider("5. When AI responses are unclear, I ask follow-up questions to improve my understanding. (5 = Strongly Agree, 4 = Agree, 3 = Neutral, 2 = Disagree, 1 = Strongly Disagree)", 1, 5, 3)
        q6 = st.slider("6. Using AI helps me identify gaps in my understanding. (5 = Strongly Agree, 4 = Agree, 3 = Neutral, 2 = Disagree, 1 = Strongly Disagree)", 1, 5, 3)

        
        submitted = st.form_submit_button("Submit (送出)")
        
        if submitted:
            tw_timezone = timezone(timedelta(hours=8))
            current_time = datetime.now(tw_timezone).strftime("%Y-%m-%d %H:%M:%S")
            row_to_append = [st.session_state.anonymous_id, q1, q2, q3, q4, q5, q6]
            
            try:
                credentials_dict = dict(st.secrets["connections"]["gsheets"])
                gc = gspread.service_account_from_dict(credentials_dict)
                SHEET_URL = "https://docs.google.com/spreadsheets/d/1BP0F_gTlwAJkcYFRqDDAnX3O4utJdnKg3pCthVBlHiI/edit?usp=sharing"
                sh = gc.open_by_url(SHEET_URL)
                worksheet2_write = sh.get_worksheet(1)
                # 寫入第二個分頁
                worksheet2_write.append_row(row_to_append)
                
                # 標記為已完成，並重新整理網頁
                st.session_state.pre_test_done = True
                st.success("✅ Pre-test submitted successfully! You can now access the AI teaching assistant.")
                st.rerun()
            except Exception as e:
                st.error(f"Pre-test submission failed: {e}")

    st.stop()
# =====================================================

general_qa_instruction = """
### main instruction:
You are an AI teaching assistant dedicated to university-level General Physics.
Your name is Luminer, and you are here to help students solve physics problems in a clear and comprehensive way.
You are currently in 【General QA Mode】.
Your goal is to "clearly, accurately, and comprehensively answer students' physics questions."
1. Direct and Detailed Solutions: When a student asks a question, provide the complete, step-by-step physics derivation and the final answer.
2. Conceptual Breakdown: While giving the answer, clearly explain the core physics concepts behind it so the student understands the "why".
3. Perfect Formatting: 
   - For simple variables mentioned in sentences, use inline LaTeX (e.g., $x$, $v$, $t$).
   - For ALL equations, formulas, and calculation steps, you MUST use block LaTeX with double dollar signs (e.g., $$ F = ma $$) so they are rendered on a new line and centered.

### Identity & Background
You were developed by Wei-Hsuan Chung (鍾瑋軒), a 3rd-year Physics undergraduate at NTU, in collaboration with Prof. Pei-Yun Yang (楊珮芸). This project is supported by NTU CTLD X DLC (教育發展中心). If a user asks about your identity, proudly mention these creators.
Also, if the user keeps asking about your identity or technical specs, politely remind them that your main mission is to help them with General Physics and guide them back to the physical concepts.

### Privacy & Memory:
- Student IDs are anonymized using an irreversible hash (SHA-256) before being stored.
- You remember the recent conversation history in the current session, but your memory will be cleared if the page is refreshed.

### Handling Off-topic / Non-science Questions:
If a student asks something NOT related to Physics or Mathematics (e.g., life advice, gossip, what to eat):
Respond humorously and briefly, but then steer the conversation back to physics. For example:
"Oh, that's an interesting question! But honestly, I'm more of a physics buff than a lifestyle guru. Let's get back to the fascinating world of physics! What physics problem are you working on?"
"""

model = genai.GenerativeModel(
    'gemini-3.1-pro-preview',
    system_instruction=general_qa_instruction
)

st.title("🌟 Luminer: AI Teaching Assistant - General Q&A Mode")
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
        # "student_id": st.session_state.student_id,
        "anonymous_id": st.session_state.anonymous_id,
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
            st.session_state.anonymous_id,
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

# ============== contact information =============
st.sidebar.divider()
st.sidebar.markdown("**Contact**")
st.sidebar.markdown("If you encounter any issues or have questions, please contact us at: [b12202069@g.ntu.edu.tw](mailto:b12202069@g.ntu.edu.tw)")