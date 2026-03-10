import streamlit as st
import google.generativeai as genai
import time
import gspread
from PIL import Image
import pandas as pd
from datetime import datetime, timezone, timedelta
from streamlit_gsheets import GSheetsConnection

# 待辦: 連上Google sheet / 上傳圖片 / 網頁美觀設計 
# 2026/3/10 completed!

# 從 Secrets 讀取並設定 API Key
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# ================= 學號登入閘門 =================
if "student_id" not in st.session_state:
    st.title("🎓 Hi! I'm your AI teaching assistant, Luminer!")
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
        if st.session_state.student_id in existing_ids:
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
            row_to_append = [st.session_state.student_id, current_time, q1, q2, q3, q4, q5, q6]
            
            try:
                # 寫入第二個分頁
                worksheet2.append_row(row_to_append)
                
                # 標記為已完成，並重新整理網頁
                st.session_state.pre_test_done = True
                st.success("✅ Pre-test submitted successfully! You can now access the AI teaching assistant.")
                st.rerun()
            except Exception as e:
                st.error(f"⚠️ Pre-test submission failed: {e}")

    st.stop()
# =====================================================

# 初始化 Gemini 模型
ta_instructions ="""
You are an AI teaching assistant dedicated to university-level General Physics.
Your name is Luminer, and you are here to help students learn physics in a fun and engaging way.
You are currently in 【Guided Mode】.
Your primary goal is to "guide students to think independently and learn physics." You must absolutely NOT just provide the final answer.
1. Refuse Direct Answers: Never provide the final numerical answer or the complete derivation process directly.
2. Socratic Guidance: Use clarifying questions to help students discover their blind spots. (e.g., "Have you drawn a free-body diagram for this system?", "Which law of thermodynamics applies here?")
3. Break Down the Framework: Guide the student step-by-step. First, define the system and coordinate system -> write down the core physical laws -> handle the mathematics -> check dimensions.
4. Perfect Formatting: 
   - For simple variables mentioned in sentences, use inline LaTeX (e.g., $x$, $v$, $t$).
   - For ALL equations, formulas, and calculation steps, you MUST use block LaTeX with double dollar signs (e.g., $$ F = ma $$) so they are rendered on a new line and centered.
5. Tone: Enthusiastic, patient, and professional. Gently but firmly correct students when they have serious conceptual errors.
"""

model = genai.GenerativeModel(
    'gemini-3.1-pro-preview',
    system_instruction=ta_instructions
)

st.title("🌟 Luminer: AI Teaching Assistant - Guided Mode")
st.caption("Hello! I'm your AI teaching assistant for general physics. Feel free to ask me any physics-related questions!")


if "guided_messages" not in st.session_state:
    st.session_state.guided_messages = []

for message in st.session_state.guided_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
    if "image" in message and message["image"] is not None:
            st.image(message["image"], width=300)
# 初始化對話歷史紀錄
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# 渲染過去的對話紀錄
# for message in st.session_state.messages:
#     with st.chat_message(message["role"]):
#         st.markdown(message["content"])

# 接收使用者輸入
if prompt := st.chat_input("What physics problem would you like to discuss?", accept_file=True, file_type=["png", "jpg", "jpeg"]):

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
    st.session_state.guided_messages.append({"role": "user", "content": safe_text, "image": image_to_send})

    # ================= 資料庫紀錄區塊 =================
    tw_timezone = timezone(timedelta(hours=8))
    current_time = datetime.now(tw_timezone).strftime("%Y-%m-%d %H:%M:%S")
    log_data = {
        "student_id": st.session_state.student_id,
        "time": current_time,
        "mode": "Guided Mode",
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
            "Guided Mode",
            safe_text
        ]
        
        # 往下新增一行
        worksheet.append_row(row_to_append)
        
        # # 讀取目前試算表裡的舊資料
        # existing_data = conn.read(spreadsheet=SHEET_URL, usecols=[0, 1, 2, 3], ttl=0)
        
        # new_row = pd.DataFrame([log_data])

        # new_row.columns = ["student id", "time", "mode", "question"] 
        # existing_data.columns = ["student id", "time", "mode", "question"]
        
        # updated_data = pd.concat([existing_data, new_row], ignore_index=True)
        
        # # 把合併後的資料寫回 Google Sheets
        # conn.update(spreadsheet=SHEET_URL, data=updated_data)
        # print("Successfully logged data to Google Sheets.")
        
    except Exception as e:
        st.error(f"Failed to log data to Google Sheets: {e}")
    # =====================================================
    # =====================================================

    gemini_history = []
    for msg in st.session_state.guided_messages[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        # gemini_history.append({"role": role, "parts": [msg["content"]]})
        parts = [msg["content"]]

        if "image" in msg and msg["image"] is not None:
            parts.insert(0, msg["image"])
        gemini_history.append({"role": role, "parts": parts})
    
    chat = model.start_chat(history=gemini_history)

    # with st.chat_message("assistant"):
    #     # 加入 st.spinner，在等待 API 回應的期間顯示轉圈圈與文字
    #     with st.spinner("Thinking..."):
    #         # response = chat.send_message(prompt, stream=True)
    #         if image_to_send is not None:
    #             response = chat.send_message([image_to_send, prompt], stream=True)
    #         else:
    #             response = chat.send_message(prompt, stream=True)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            
            content_to_send = []
            if image_to_send:
                content_to_send.append(image_to_send)
            if user_text:
                content_to_send.append(user_text)
            else:
                content_to_send.append("Please analyze the uploaded image and provide guidance.") 
            response = chat.send_message(content_to_send, stream=True)
        
        # 像打字機一樣輸出
        def stream_generator():
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        full_response = st.write_stream(stream_generator())
        
    st.session_state.guided_messages.append({"role": "assistant", "content": full_response}) 
