import streamlit as st
import google.generativeai as genai

# 這裡填入你的 API KEY
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

print("你可以使用的模型有：")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)