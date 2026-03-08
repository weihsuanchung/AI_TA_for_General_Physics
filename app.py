import streamlit as st
import google.generativeai as genai
import time
from PIL import Image
from datetime import datetime # 新增：用來取得當下時間

# 待辦: 連上Google sheet / 上傳圖片 / 網頁美觀設計 

# 1. 從 Secrets 讀取並設定 API Key
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# ================= 新增：學號登入閘門 =================
# 如果 session_state 裡面還沒有 student_id，就顯示登入畫面
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
                
    # st.stop() 非常重要！它會讓程式停在這裡，不執行下面的聊天室 UI
    st.stop()
# ======================================================

# 如果程式能走到這裡，代表學生已經登入了！
# 你可以在側邊欄或標題顯示他的學號，讓他知道系統有認得他
st.sidebar.success(f"Student ID: {st.session_state.student_id}")
if st.sidebar.button("Log out (登出)"):
    del st.session_state.student_id
    st.rerun()

# 2. 初始化 Gemini 模型
ta_instructions ="""
You are an AI teaching assistant dedicated to university-level General Physics.
You are currently in 【Guided Mode】.
Your primary goal is to "guide students to think independently and learn physics." You must absolutely NOT just provide the final answer.
1. Refuse Direct Answers: Never provide the final numerical answer or the complete derivation process directly.
2. Socratic Guidance: Use clarifying questions to help students discover their blind spots. (e.g., "Have you drawn a free-body diagram for this system?", "Which law of thermodynamics applies here?")
3. Break Down the Framework: Guide the student step-by-step. First, define the system and coordinate system -> write down the core physical laws -> handle the mathematics -> check dimensions.
4. Perfect Formatting: All formulas and variables must be strictly formatted using LaTeX (inline with $, block with $$).
5. Tone: Enthusiastic, patient, and professional. Gently but firmly correct students when they have serious conceptual errors.
"""

model = genai.GenerativeModel(
    'gemini-3.1-pro-preview',
    system_instruction=ta_instructions
)

# 設定網頁標題
st.title("AI Teaching Assistant for NTU General Physics")
st.caption("Hello! I'm your AI teaching assistant for general physics. Feel free to ask me any physics-related questions!")

# 圖片上傳區塊
uploaded_file = st.file_uploader("Upload a physics image (optional)", type=["jpg", "jpeg", "png"])

image_to_send = None
if uploaded_file is not None:
    # 1. 把檔案讀取指標倒轉回起點
    uploaded_file.seek(0)
    # 2. 強制轉換為 RGB，避免 PNG 透明背景導致 AI 讀取失敗
    image_to_send = Image.open(uploaded_file).convert('RGB')
    st.image(image_to_send, caption="Uploaded Image", use_container_width=True)

# with st.sidebar:
#     # st.title("⚙️ Course Settings")
    
#     # # 下拉式選單 (Selectbox) - 適合讓學生選擇當前學習的單元
#     # chapter = st.selectbox(
#     #     "Chapter",
#     #     ("Newtonian Mechanics", "Electromagnetism", "Thermodynamics", "Fluid Mechanics", "Quantum Physics", "Relativity")
#     # )
        
#     # 單選按鈕 (Radio) - 適合切換 AI 助教的引導模式
#     mode = st.radio(
#         "Choose Teaching Mode",
#         ("General Q&A Mode", "Guided Mode")
#     )
        
#     # 畫一條分隔線
#     st.divider()
        
    # 提示區塊 (Info) - 可以放一些提醒或老師的話
    # st.info("💡 提示：輸入方程式時可以使用 LaTeX 語法喔！")

if "guided_messages" not in st.session_state:
    st.session_state.guided_messages = []

for message in st.session_state.guided_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
    if "image" in message and message["image"] is not None:
            st.image(message["image"], width=300)
# # 3. 初始化對話歷史紀錄
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# 渲染過去的對話紀錄
# for message in st.session_state.messages:
#     with st.chat_message(message["role"]):
#         st.markdown(message["content"])

# 4. 接收使用者輸入
if prompt := st.chat_input("What physics problem would you like to discuss?"):

    st.chat_message("user").markdown(prompt)
    st.session_state.guided_messages.append({"role": "user", "content": prompt, "image": image_to_send})

    # ================= 預留資料庫紀錄區塊 =================
    # 這裡就是未來要寫入 Google Sheets 的 4 個欄位資料
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_data = {
        "student_id": st.session_state.student_id,
        "time": current_time,
        "mode": "Guided Mode",
        "question": prompt
    }
    # (等我們把 Google Sheets 的金鑰設定好，就會在這裡加入寫入的程式碼)
    print("準備寫入資料庫：", log_data) # 先印在終端機檢查看看
    # =====================================================

    gemini_history = []
    for msg in st.session_state.guided_messages[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        # gemini_history.append({"role": role, "parts": [msg["content"]]})
        parts = [msg["content"]]
        # 如果這則舊訊息有包含圖片，也要一起塞進 parts 裡面讓模型回顧
        if "image" in msg and msg["image"] is not None:
            parts.insert(0, msg["image"])
        gemini_history.append({"role": role, "parts": parts})
    
    chat = model.start_chat(history=gemini_history)

    with st.chat_message("assistant"):
        # 加入 st.spinner，在等待 API 回應的期間顯示轉圈圈與文字
        with st.spinner("Thinking..."):
            # response = chat.send_message(prompt, stream=True)
            if image_to_send is not None:
                response = chat.send_message([image_to_send, prompt], stream=True)
            else:
                response = chat.send_message(prompt, stream=True)
        
        # 當接到第一個字的時候，spinner 會自動消失，接著開始像打字機一樣輸出
        def stream_generator():
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        full_response = st.write_stream(stream_generator())
        
    st.session_state.guided_messages.append({"role": "assistant", "content": full_response}) 

    # 顯示 AI 助教的訊息，並使用串流效果
    # with st.chat_message("assistant"):
    #     # 模擬 AI 思考的停頓感
    #     with st.spinner('Thinking...'):
    #         time.sleep(1) 
    #     # 呼叫 API 並設定 stream=True
    #     response = chat.send_message(prompt, stream=True)
        
    #     # 建立一個產生器來逐字輸出
    #     def stream_generator():
    #         for chunk in response:
    #             if chunk.text:
    #                 yield chunk.text
                    
        # st.write_stream 會自動處理打字機特效，並回傳完整的字串
    #     full_response = st.write_stream(stream_generator())
        
    # # 儲存 AI 的完整回答
    # st.session_state.messages.append({"role": "assistant", "content": full_response})
