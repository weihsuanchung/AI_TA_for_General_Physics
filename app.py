# import streamlit as st
# import time

# st.set_page_config(
#     page_title="普物 AI 助教", 
#     page_icon="⚛️", 
#     layout="wide", # 可以選擇 "centered" (置中) 或 "wide" (寬螢幕，適合滿版首頁)
#     # initial_sidebar_state="expanded" # 預設展開或收起側邊欄
# )

# # 設定網頁標題
# st.title("普物 AI 教學助教")
# st.caption("哈囉！我是你的普通物理 AI 助教。")

# with st.sidebar:
#     st.title("⚙️ 課程設定")
    
#     # 下拉式選單 (Selectbox) - 適合讓學生選擇當前學習的單元
#     chapter = st.selectbox(
#         "選擇物理單元",
#         ("牛頓力學", "電磁學", "熱力學", "流體力學", "近代物理")
#     )
        
#     # 單選按鈕 (Radio) - 適合切換 AI 助教的引導模式
#     mode = st.radio(
#         "選擇教學模式",
#         ("一般問答模式", "引導模式")
#     )
        
#     # 畫一條分隔線
#     st.divider()
        
#     # 提示區塊 (Info) - 可以放一些提醒或老師的話
#     st.info("💡 提示：輸入方程式時可以使用 LaTeX 語法喔！")

# # 初始化對話歷史紀錄 (Session State)
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# # 每次重新渲染網頁時，把過去的對話顯示出來
# for message in st.session_state.messages:
#     with st.chat_message(message["role"]):
#         st.markdown(message["content"])

# # 接收使用者輸入的問題
# if prompt := st.chat_input("你想討論什麼物理問題？ (例如：可以幫我複習高斯定律嗎？)"):
    
#     # 1. 顯示並儲存使用者的訊息
#     with st.chat_message("user"):
#         st.markdown(prompt)
#     st.session_state.messages.append({"role": "user", "content": prompt})

#     # 2. 顯示並儲存 AI 助教的訊息 (這裡先做一個模擬的假回應)
#     with st.chat_message("assistant"):
#         # 模擬 AI 思考的停頓感
#         with st.spinner('思考中...'):
#             time.sleep(1) 
            
#         # 模擬帶有引導性質與物理公式的回應
#         response = f"""
#         這是一個很棒的提問！針對你說的「**{prompt}**」，我們可以先從基本定義出發。
        
#         例如在電磁學中，我們常利用以下這個核心公式來處理具有高度對稱性的問題：
#         $$\oint \mathbf{{E}} \cdot d\mathbf{{A}} = \\frac{{q_{{enc}}}}{{\\varepsilon_0}}$$
        
#         **👉 換你試試看：** 你覺得在計算無限長均勻帶電圓柱的電場時，應該選擇什麼樣的高斯面（Gaussian surface）最能簡化計算？
#         """
#         st.markdown(response)
        
#     st.session_state.messages.append({"role": "assistant", "content": response})

import streamlit as st
import google.generativeai as genai
import time

# 1. 從 Secrets 讀取並設定 API Key
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# 2. 初始化 Gemini 模型 (使用反應快速的 flash 模型)
model = genai.GenerativeModel('gemini-3-flash-preview')

# 設定網頁標題
st.title("AI Teaching Assistant for General Physics")
st.caption("Hello! I'm your AI teaching assistant for general physics. Feel free to ask me any physics-related questions!")

# 3. 初始化對話歷史紀錄
if "messages" not in st.session_state:
    st.session_state.messages = []

# 渲染過去的對話紀錄
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 4. 接收使用者輸入
if prompt := st.chat_input("What physics question do you have in mind?"):
    
    # 顯示並儲存使用者的訊息
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 將 Streamlit 的對話紀錄格式，轉換成 Gemini 聽得懂的歷史紀錄格式
    gemini_history = []
    for msg in st.session_state.messages[:-1]: # 排除掉剛才輸入的最新問題
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})
    
    # 啟動帶有記憶的聊天對話框
    chat = model.start_chat(history=gemini_history)

    # 顯示 AI 助教的訊息，並使用串流效果
    with st.chat_message("assistant"):
        # 模擬 AI 思考的停頓感
        with st.spinner('Thinking...'):
            time.sleep(1) 
        # 呼叫 API 並設定 stream=True
        response = chat.send_message(prompt, stream=True)
        
        # 建立一個產生器來逐字輸出
        def stream_generator():
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        # st.write_stream 會自動處理打字機特效，並回傳完整的字串
        full_response = st.write_stream(stream_generator())
        
    # 儲存 AI 的完整回答
    st.session_state.messages.append({"role": "assistant", "content": full_response})
