import streamlit as st
import os
import base64
import google.generativeai as genai
import time
import hashlib
import gspread
import threading
import fitz
from PIL import Image
import pandas as pd
from datetime import datetime, timezone, timedelta
from streamlit_gsheets import GSheetsConnection
from urllib.parse import quote

st.set_page_config(layout="wide")

# Read API key from Secrets and configure GenAI
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def anonymize_student_id(raw_id):
    # Remove leading/trailing whitespace and convert to lowercase
    clean_id = str(raw_id).strip().lower()
    
    salt = st.secrets["ID_SALT"]  # Read salt value from Secrets
    salted_id = clean_id + salt
    
    # Use SHA-256 algorithm for hashing
    hash_object = hashlib.sha256(salted_id.encode('utf-8'))
    
    hex_digest = hash_object.hexdigest()
    anonymous_number = str(int(hex_digest[:8], 16))
    
    return anonymous_number

# ================= Student ID Login Gate =================
if "student_id" not in st.session_state:
    st.title("🎓 Hi! I'm your AI teaching assistant, **Luminer**!")
    st.info("Please enter your student ID to get started. (請輸入學號以開始使用)")

    st.write("**Important:** Your student ID will be anonymized (hashed) and stored securely. We only use it to track your progress and analyze for our research. Your privacy is our top priority!")
    
    # Let them enter their student ID and press Enter or click the button to submit
    with st.form("login_form"):
        student_id_input = st.text_input("Student ID (學號):")
        submitted = st.form_submit_button("Log in (登入)")
        
        if submitted:
            if student_id_input.strip() == "":
                st.error("Student ID cannot be empty! (學號不能為空！)")
            else:
                anonymous_id = anonymize_student_id(student_id_input)
                # Store the student ID in session_state and refresh the page
                st.session_state.student_id = student_id_input.strip()
                st.session_state.anonymous_id = anonymous_id
                st.rerun()
                
    st.stop()
# ======================================================

# Show the logged-in student ID in the sidebar with a logout button
st.sidebar.success(f"Student ID: {st.session_state.student_id}")
if st.sidebar.button("Log out (登出)"):
    del st.session_state.student_id
    del st.session_state.anonymous_id
    st.rerun()

# ================= Pre-Test Survey Intercept Gate =================
if "pre_test_done" not in st.session_state:
    try:
        # Connect to Google Sheets
        credentials_dict = dict(st.secrets["connections"]["gsheets"])
        gc = gspread.service_account_from_dict(credentials_dict)
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1BP0F_gTlwAJkcYFRqDDAnX3O4utJdnKg3pCthVBlHiI/edit?usp=sharing" 
        sh = gc.open_by_url(SHEET_URL)
        
        # Read the second worksheet for pre-test records
        worksheet2 = sh.get_worksheet(1) 
        
        existing_ids = worksheet2.col_values(1)
        
        # Check if the current anonymous ID is already in the pre-test records
        if st.session_state.anonymous_id in existing_ids:
            st.session_state.pre_test_done = True
        else:
            st.session_state.pre_test_done = False
            
    except Exception as e:
        st.error(f"Failed to read pre-test status: {e}")
        st.stop()

# If no, show the pre-test survey form and block access to the teaching assistant until they complete it
if not st.session_state.pre_test_done:
    st.title("📝 AI Literacy Survey (pre-test)")
    st.info("Instructions: Please indicate your level of agreement with the following statements. This will help us understand your current familiarity with AI and physics. (請根據以下陳述選擇你的認同程度，這將幫助我們了解你目前對 AI 和物理的熟悉程度。)")
    
    with st.form("pre_test_form"):
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
                # Write to the second worksheet
                worksheet2_write.append_row(row_to_append)
                
                # Mark as completed and refresh the page
                st.session_state.pre_test_done = True
                st.success("✅ Pre-test submitted successfully! You can now access the AI teaching assistant.")
                st.rerun()
            except Exception as e:
                st.error(f"Pre-test submission failed: {e}")

    st.stop()
# =====================================================

# ================= Background Logging Function =================
def log_to_sheets(anonymous_id, current_time, safe_text):
    try:
        credentials_dict = dict(st.secrets["connections"]["gsheets"])
        gc = gspread.service_account_from_dict(credentials_dict)
        sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1BP0F_gTlwAJkcYFRqDDAnX3O4utJdnKg3pCthVBlHiI/edit?usp=sharing")
        worksheet = sh.sheet1
        worksheet.append_row([anonymous_id, current_time, "Guided Mode", safe_text])
    except Exception as e:
        print(f"Logging failed silently: {e}")  # won't show to user
# ===============================================================

# ================= Lecture Slides Loader =================
@st.cache_data
def load_lecture_pdf(filepath):
    """Load and cache PDF as base64 — only re-runs if file changes."""
    with open(filepath, "rb") as f:
        pdf_bytes = f.read()
    return {
        "mime_type": "application/pdf",
        "data": base64.standard_b64encode(pdf_bytes).decode("utf-8")
    }

LECTURE_ORDER = [
    "Electrostatic Field",
    "Gauss",
    "Electric Potential",
    "Capacitance",
    "DC Circuit",
    "Magnetostatics",
    "Electromagnetic Induction",
    "Inductance",
]

def clean_lecture_name(filename):
    return os.path.splitext(filename)[0].strip()

def build_lecture_slides():
    lectures = {"None (No lecture linked)": None}
    static_dir = "static"
    if not os.path.isdir(static_dir):
        return lectures

    pdf_names = [
        clean_lecture_name(filename)
        for filename in os.listdir(static_dir)
        if filename.lower().endswith(".pdf")
    ]

    ordered_names = []
    for keyword in LECTURE_ORDER:
        normalized_keyword = keyword.casefold().replace(" ", "")
        match = next(
            (
                name for name in pdf_names
                if normalized_keyword in name.casefold().replace(" ", "")
            ),
            None,
        )
        if match and match not in ordered_names:
            ordered_names.append(match)

    ordered_names.extend(sorted(name for name in pdf_names if name not in ordered_names))

    for index, name in enumerate(ordered_names, start=1):
        lectures[f"Lecture {index} - {name}"] = name

    return lectures

LECTURE_SLIDES = build_lecture_slides()

def find_lecture_pdf(keyword):
    """Find a lecture PDF in static/ even when filenames contain spaces or smart quotes."""
    if not keyword:
        return None

    static_dir = "static"
    if not os.path.isdir(static_dir):
        return None

    normalized_keyword = keyword.casefold().replace(" ", "")
    for filename in os.listdir(static_dir):
        if not filename.lower().endswith(".pdf"):
            continue
        normalized_filename = filename.casefold().replace(" ", "")
        if normalized_keyword in normalized_filename:
            return os.path.join(static_dir, filename)

    return None

def get_static_pdf_url(filepath):
    """Build the URL used by Streamlit static file serving."""
    return "/app/static/" + quote(os.path.basename(filepath))

@st.cache_data
def get_pdf_page_count(filepath):
    doc = fitz.open(filepath)
    page_count = doc.page_count
    doc.close()
    return page_count

@st.cache_data
def render_pdf_page(filepath, page_index, zoom=1.6):
    """Render one PDF page as an image so Chrome never blocks an embedded PDF viewer."""
    doc = fitz.open(filepath)
    page = doc.load_page(page_index)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    image_bytes = pix.tobytes("png")
    doc.close()
    return image_bytes

# def render_pdf_viewer(pdf_base64: str, height: int = 800) -> str:
#     """Returns an HTML iframe that renders a base64 PDF inline."""
#     return f"""
#         <iframe
#             src="data:application/pdf;base64,{pdf_base64}"
#             width="100%"
#             height="{height}px"
#             style="border: 1px solid #e0e0e0; border-radius: 8px;"
#             type="application/pdf"
#         >
#             <p>Your browser does not support inline PDFs.
#             <a href="data:application/pdf;base64,{pdf_base64}" download="lecture.pdf">Download the PDF</a> instead.</p>
#         </iframe>
#     """

# @st.cache_data
# def pdf_to_images(filepath: str):
#     """Convert each PDF page to an image — cached so it only runs once per file."""
#     doc = fitz.open(filepath)
#     images = []
#     for page in doc:
#         mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for sharpness
#         pix = page.get_pixmap(matrix=mat)
#         img_bytes = pix.tobytes("png")
#         images.append(img_bytes)
#     doc.close()
#     return images

# ================= Lecture Slide Selector =================
st.sidebar.divider()
st.sidebar.markdown("**📚 Link to Lecture**")

selected_lecture_name = st.sidebar.selectbox(
    "Select your lecture:",
    list(LECTURE_SLIDES.keys()),
    index=0,
    help="Link a lecture so Luminer explains concepts using your professor's materials."
)

lecture_pdf = None
selected_path = find_lecture_pdf(LECTURE_SLIDES[selected_lecture_name])

if selected_path and os.path.exists(selected_path):
    lecture_pdf = load_lecture_pdf(selected_path)
    st.sidebar.success(f"✅ Linked: {selected_lecture_name}")
elif LECTURE_SLIDES[selected_lecture_name]:
    st.sidebar.warning("⚠️ Slide file not found.")
# ==========================================================

# ========================================================

# Initialize Gemini model with system instructions
ta_instructions ="""
### main instruction:
You are an AI teaching assistant dedicated to university-level General Physics.
Your name is Luminer, and you are here to help students learn physics in a fun and engaging way.
You are currently in 【Guided Mode】.
Your primary goal is to "guide students to think independently and learn physics." You must absolutely NOT just provide the final answer.
1. Refuse Direct Answers: Never provide the final numerical answer or the complete derivation process directly.
2. Socratic Guidance: Use clarifying questions to help students discover their blind spots. (e.g., "Have you drawn a free-body diagram for this system?", "Which law of thermodynamics applies here?")
3. Break Down the Framework: Guide the student step-by-step. First, define the system and coordinate system -> write down the core physical laws -> handle the mathematics -> check dimensions.
4. Perfect Formatting: 
   - For simple variables mentioned in sentences, use inline LaTeX (e.g., $x$, $v$, $t$).
   - For ALL equations, formulas, and calculation steps, you MUST use block LaTeX with double dollar signs (e.g., $$ F = ma $$) so they are rendered on a new line and centered, including short equations with just one step. This is crucial for readability and clarity.
   - Use double newlines (\n\n) between EVERY logical step or paragraph.
   - Use Markdown headers (e.g., ### Step 1: ...) to label different parts of the guidance.
   - Use bullet points (-) for listing variables or hints.
   - NEVER output a paragraph longer than 3 sentences. If it's longer, break it into a new paragraph or a list.
5. Tone: Enthusiastic, patient, and professional. Gently but firmly correct students when they have serious conceptual errors.
6. Before providing guidance, think step-by-step internally about the correct physical principles and mathematical derivation. Ensure your logic is sound before you output any response to the student.

### Identity & Background
You were developed by Wei-Hsuan Chung (鍾瑋軒), a 3rd-year Physics undergraduate at NTU, in collaboration with Prof. Pei-Yun Yang (楊珮芸). This project is supported by NTU CTLD X DLC (教育發展中心). If a user asks about your identity, proudly mention these creators.
Also, if the user keeps asking about your identity or technical specs, politely remind them that your main mission is to help them with General Physics and guide them back to the physical concepts. (Introduce yourself briefly at the first mention, but then steer the conversation back to physics, do not say it repeatedly.)

### Privacy & Memory:
- Student IDs are anonymized using an irreversible hash (SHA-256) before being stored.
- You remember the recent conversation history in the current session, but your memory will be cleared if the page is refreshed.

### Handling Off-topic / Non-science Questions:
If a student asks something NOT related to Physics or Mathematics (e.g., life advice, gossip, what to eat):
Respond humorously and briefly, but then steer the conversation back to physics. For example:
"Oh, that's an interesting question! But honestly, I'm more of a physics buff than a lifestyle guru. Let's get back to the fascinating world of physics! What physics problem are you working on?"
"""

model = genai.GenerativeModel(
    st.secrets["MODEL_GUIDED"],
    system_instruction=ta_instructions
)

st.title("🌟 Luminer: AI Teaching Assistant - Guided Mode")
st.caption("Hello! I'm your AI teaching assistant for general physics. Feel free to ask me any physics-related questions!")

st.markdown("""
    <style>
    /* For mobile devices */
    @media (max-width: 600px) {
        .stChatMessage {
            font-size: 14px !important;
            line-height: 1.6 !important;
        }
    }
    /* Add some breathing room between paragraphs */
    .stChatMessage p {
        margin-bottom: 1.2rem !important;
    }
    </style>
""", unsafe_allow_html=True)

if "guided_messages" not in st.session_state:
    st.session_state.guided_messages = []

if "show_lecture_notes" not in st.session_state:
    st.session_state.show_lecture_notes = True

# ================= Layout =================
show_slides = False
chat_area = None

if False and lecture_pdf:
    show_slides = st.toggle(
        "📄 Open Lecture Slides",
        value=False,
        help="View the lecture PDF side-by-side with your chat."
    )

show_slides = False

if lecture_pdf:
    notes_title, notes_action = st.columns([4, 1])
    with notes_title:
        st.markdown(f"#### Lecture Notes: {selected_lecture_name}")
    with notes_action:
        if st.button(
            "Hide notes" if st.session_state.show_lecture_notes else "Show notes",
            use_container_width=True
        ):
            st.session_state.show_lecture_notes = not st.session_state.show_lecture_notes
            st.rerun()

    if st.session_state.show_lecture_notes:
        page_count = get_pdf_page_count(selected_path)
        current_page = min(max(st.session_state.get("guided_pdf_page", 1), 1), page_count)
        page_number = st.number_input(
            "Page",
            min_value=1,
            max_value=page_count,
            value=current_page,
            step=1,
            key="guided_pdf_page"
        )
        page_image = render_pdf_page(selected_path, page_number - 1)
        st.image(page_image, use_container_width=True)
        # st.link_button("Open full PDF in a new tab", get_static_pdf_url(selected_path))
    else:
        st.info("Lecture notes are hidden. Use Show notes to turn them back on.")
else:
    st.info("Select a lecture from the sidebar to view notes here.")

if lecture_pdf and show_slides:
    # Split layout
    col_pdf, col_chat = st.columns([1, 1], gap="medium")
    chat_area = col_chat

    with col_pdf:
        st.markdown(f"#### 📄 {selected_lecture_name}")

        page_count = get_pdf_page_count(selected_path)
        current_page = min(max(st.session_state.get("guided_pdf_page", 1), 1), page_count)
        page_number = st.number_input(
            "Page",
            min_value=1,
            max_value=page_count,
            value=current_page,
            step=1,
            key="guided_pdf_page"
        )
        page_image = render_pdf_page(selected_path, page_number - 1)
        st.image(page_image, use_container_width=True)
        st.link_button("Open full PDF in a new tab", get_static_pdf_url(selected_path))

    with col_chat:
        st.markdown("#### 💬 Chat with Luminer")
        chat_container = st.container(height=750)
        with chat_container:
            for message in st.session_state.guided_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                if "image" in message and message["image"] is not None:
                    st.image(message["image"], width=300)
else:
    st.divider()
    st.markdown("#### Chat with Luminer")
    # Normal full-width layout
    if False and lecture_pdf:
        st.info(f"📚 Linked: **{selected_lecture_name}** — Toggle above to view slides.")
    for message in st.session_state.guided_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
        if "image" in message and message["image"] is not None:
            st.image(message["image"], width=300)
# ==========================================


# Input
prompt = st.chat_input(
    "Ask Luminer about the lecture notes or your physics problem...",
    accept_file=True,
    file_type=["png", "jpg", "jpeg"]
)

if prompt:
    user_text = prompt.text
    uploaded_file = prompt.files[0] if prompt.files else None

    if not user_text and uploaded_file is None:
        st.warning("Please enter a question or attach an image.")
        st.stop()

    image_to_send = None
    if uploaded_file is not None:
        uploaded_file.seek(0)
        image_to_send = Image.open(uploaded_file).convert('RGB')

    if chat_area:
        with chat_area:
            with st.chat_message("user"):
                if user_text:
                    st.markdown(user_text)
                if image_to_send:
                    st.image(image_to_send, width=300)
    else:
        with st.chat_message("user"):
            if user_text:
                st.markdown(user_text)
            if image_to_send:
                st.image(image_to_send, width=300)

    safe_text = user_text if user_text else "Only image uploaded."

    # st.chat_message("user").markdown(prompt)
    st.session_state.guided_messages.append({"role": "user", "content": safe_text, "image": image_to_send})

    # ================= Data Logging =================
    # tw_timezone = timezone(timedelta(hours=8))
    # current_time = datetime.now(tw_timezone).strftime("%Y-%m-%d %H:%M:%S")
    # log_data = {
    #     "anonymous_id": st.session_state.anonymous_id,
    #     "time": current_time,
    #     "mode": "Guided Mode",
    #     "question": safe_text
    # }

    # try:
    #     # Connect to Google Sheets and append the log data
    #     # conn = st.connection("gsheets", type=GSheetsConnection)
    #     credentials_dict = dict(st.secrets["connections"]["gsheets"])
    #     gc = gspread.service_account_from_dict(credentials_dict)
        
    #     # SHEET_URL = st.secrets["SHEET_URL"] 
    #     SHEET_URL = 'https://docs.google.com/spreadsheets/d/1BP0F_gTlwAJkcYFRqDDAnX3O4utJdnKg3pCthVBlHiI/edit?usp=sharing'

    #     # Open the first worksheet of the spreadsheet
    #     # spreadsheet = conn.client.open_by_url(SHEET_URL)
    #     # worksheet = spreadsheet.sheet1 
    #     sh = gc.open_by_url(SHEET_URL)
    #     worksheet = sh.sheet1
        
    #     # Append the new row to the worksheet
    #     row_to_append = [
    #         st.session_state.anonymous_id,
    #         current_time,
    #         "Guided Mode",
    #         safe_text
    #     ]
        
    #     # Add a new row at the bottom of the sheet
    #     worksheet.append_row(row_to_append)
        

        # existing_data = conn.read(spreadsheet=SHEET_URL, usecols=[0, 1, 2, 3], ttl=0)
        
        # new_row = pd.DataFrame([log_data])

        # new_row.columns = ["student id", "time", "mode", "question"] 
        # existing_data.columns = ["student id", "time", "mode", "question"]
        
        # updated_data = pd.concat([existing_data, new_row], ignore_index=True)

        # conn.update(spreadsheet=SHEET_URL, data=updated_data)
        # print("Successfully logged data to Google Sheets.")
        
    # except Exception as e:
    #     st.error(f"Failed to log data to Google Sheets: {e}")
    # =====================================================

    # ================= Data Logging (Background) =================
    tw_timezone = timezone(timedelta(hours=8))
    current_time = datetime.now(tw_timezone).strftime("%Y-%m-%d %H:%M:%S")
    threading.Thread(target=log_to_sheets, args=(st.session_state.anonymous_id, current_time, safe_text), daemon=True).start()
    # =============================================================

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

    chat_message_fn = chat_area.chat_message if chat_area else st.chat_message

    with chat_message_fn("assistant"):
        with st.spinner("Thinking..."):
            
            content_to_send = []

            if lecture_pdf:
                content_to_send.append(lecture_pdf)
                content_to_send.append(
                    f"The above PDF contains the professor's lecture slides for '{selected_lecture_name}'. "
                    "Use the concepts, notation, definitions, and explanations from these slides as your PRIMARY reference. "
                    "Align your guidance with how the professor has framed the material."
                )
                st.info(f"📚 Lecture linked: **{selected_lecture_name}** — Luminer will follow your professor's materials.")



            if image_to_send:
                content_to_send.append(image_to_send)
            if user_text:
                content_to_send.append(user_text)
            else:
                content_to_send.append("Please analyze the uploaded image and provide guidance.") 
            response = chat.send_message(content_to_send, stream=True)
        
        # Waiting Animation
        def stream_generator():
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        full_response = st.write_stream(stream_generator())
        
    st.session_state.guided_messages.append({"role": "assistant", "content": full_response}) 


# ============== Built-in Feedback ==============
st.sidebar.divider()
st.sidebar.markdown("**📣 Report an Issue / Give Feedback**")

with st.sidebar.expander("Open Feedback Form"):
    with st.form("feedback_form", clear_on_submit=True):
        feedback_type = st.selectbox(
            "Issue Type",
            ["Bug / Error", "Bad AI Response", "Formatting Issue", "Feature Request", "Other"]
        )
        feedback_text = st.text_area(
            "Describe the issue or feedback:",
            placeholder="e.g. Luminer gave a wrong formula...",
            max_chars=1500
        )
        # Optionally attach the last AI message for context
        attach_last = st.checkbox("Attach last AI response for context", value=True)
        
        submitted_feedback = st.form_submit_button("Submit Feedback")

        if submitted_feedback:
            if feedback_text.strip() == "":
                st.warning("Please describe the issue before submitting.")
            else:
                tw_timezone = timezone(timedelta(hours=8))
                current_time = datetime.now(tw_timezone).strftime("%Y-%m-%d %H:%M:%S")

                # Grab last AI response if checkbox is checked
                last_ai_msg = ""
                if attach_last and st.session_state.get("guided_messages"):
                    for msg in reversed(st.session_state.guided_messages):
                        if msg["role"] == "assistant":
                            # last_ai_msg = msg["content"][:500]  # trim to 500 chars
                            last_ai_msg = msg["content"] # store the full response
                            # Note that 50,000 character limit per cell in Google Sheets
                            break

                try:
                    credentials_dict = dict(st.secrets["connections"]["gsheets"])
                    gc = gspread.service_account_from_dict(credentials_dict)
                    SHEET_URL = "https://docs.google.com/spreadsheets/d/1BP0F_gTlwAJkcYFRqDDAnX3O4utJdnKg3pCthVBlHiI/edit?usp=sharing"
                    sh = gc.open_by_url(SHEET_URL)

                    feedback_ws = sh.get_worksheet(2)
                    feedback_ws.append_row([
                        st.session_state.get("anonymous_id", "unknown"),
                        current_time,
                        "Guided Mode",
                        feedback_type,
                        feedback_text.strip(),
                        last_ai_msg
                    ])
                    st.success("✅ Feedback submitted! Thank you.")
                except Exception as e:
                    st.error(f"Failed to submit feedback: {e}")

# ============== contact information =============
st.sidebar.divider()
st.sidebar.markdown("**Contact**")
st.sidebar.markdown("If you encounter any issues or have questions, please contact us at: [b12202069@g.ntu.edu.tw](mailto:b12202069@g.ntu.edu.tw)")
