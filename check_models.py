import google.generativeai as genai

# 這裡填入你的 API KEY
genai.configure(api_key="AIzaSyDlLP5G-5sxlnM-6J2qzzh730Wp6mw2px8")

print("你可以使用的模型有：")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)