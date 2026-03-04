import streamlit as st
import google.generativeai as genai

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

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