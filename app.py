import streamlit as st
import google.generativeai as genai
import time

# 1. 從 Secrets 讀取並設定 API Key
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

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
    'gemini-flash-latest',
    system_instruction=ta_instructions
)

# 設定網頁標題
st.title("AI Teaching Assistant for NTU General Physics")
st.caption("Hello! I'm your AI teaching assistant for general physics. Feel free to ask me any physics-related questions!")

with st.sidebar:
    # st.title("⚙️ Course Settings")
    
    # # 下拉式選單 (Selectbox) - 適合讓學生選擇當前學習的單元
    # chapter = st.selectbox(
    #     "Chapter",
    #     ("Newtonian Mechanics", "Electromagnetism", "Thermodynamics", "Fluid Mechanics", "Quantum Physics", "Relativity")
    # )
        
    # 單選按鈕 (Radio) - 適合切換 AI 助教的引導模式
    mode = st.radio(
        "Choose Teaching Mode",
        ("General Q&A Mode", "Guided Mode")
    )
        
    # 畫一條分隔線
    st.divider()
        
    # 提示區塊 (Info) - 可以放一些提醒或老師的話
    # st.info("💡 提示：輸入方程式時可以使用 LaTeX 語法喔！")

if "guided_messages" not in st.session_state:
    st.session_state.guided_messages = []

for message in st.session_state.guided_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
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
    st.session_state.guided_messages.append({"role": "user", "content": prompt})

    gemini_history = []
    for msg in st.session_state.guided_messages[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})
    
    chat = model.start_chat(history=gemini_history)

    with st.chat_message("assistant"):
        # 加入 st.spinner，在等待 API 回應的期間顯示轉圈圈與文字
        with st.spinner("Thinking..."):
            response = chat.send_message(prompt, stream=True)
        
        # 當接到第一個字的時候，spinner 會自動消失，接著開始像打字機一樣輸出
        def stream_generator():
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        full_response = st.write_stream(stream_generator())
        
    st.session_state.guided_messages.append({"role": "assistant", "content": full_response}) 
    # (注意：General QA 頁面的變數是 qa_messages，記得對應改好)

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
