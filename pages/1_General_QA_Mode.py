import streamlit as st
import google.generativeai as genai

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

general_qa_instruction = """
You are an AI teaching assistant dedicated to university-level General Physics.
You are currently in 【General QA Mode】.
Your goal is to "clearly, accurately, and comprehensively answer students' physics questions."
1. Direct and Detailed Solutions: When a student asks a question, provide the complete, step-by-step physics derivation and the final answer.
2. Conceptual Breakdown: While giving the answer, clearly explain the core physics concepts behind it so the student understands the "why".
3. Perfect Formatting: All formulas and variables must be strictly formatted using LaTeX (inline with $, block with $$).
"""

model = genai.GenerativeModel('gemini-flash-latest', system_instruction=general_qa_instruction)

st.title("AI Teaching Assistant for NTU General Physics - General Q&A Mode")
st.caption("Hello! I'm your AI teaching assistant for general physics. Get complete physics derivations and conceptual breakdowns here!")

if "qa_messages" not in st.session_state:
    st.session_state.qa_messages = []

for message in st.session_state.qa_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Enter your physics question here:"):
    st.chat_message("user").markdown(prompt)
    st.session_state.qa_messages.append({"role": "user", "content": prompt})

    gemini_history = []
    for msg in st.session_state.qa_messages[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})
    
    chat = model.start_chat(history=gemini_history)

    with st.chat_message("assistant"):
        # 加入 st.spinner，在等待 API 回應的期間顯示轉圈圈與文字
        with st.spinner("Thinking..."):
            response = chat.send_message(prompt, stream=True)

    # with st.chat_message("assistant"):
    #     response = chat.send_message(prompt, stream=True)
        def stream_generator():
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        full_response = st.write_stream(stream_generator())
        
    st.session_state.qa_messages.append({"role": "assistant", "content": full_response})