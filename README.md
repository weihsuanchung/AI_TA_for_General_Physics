# 🌟 Luminer: AI Teaching Assistant for General Physics

> **"Shedding light on challenging physics concepts through interactive guidance."**

**Luminer** is an AI-powered teaching assistant specifically designed for university-level **General Physics** courses at **National Taiwan University (NTU)**. Unlike standard AI chatbots, Luminer is built on pedagogical principles to foster deep learning rather than just providing quick answers.

---

## 🚀 Key Features

### 1. Guided Mode (Socratic Learning)
This is the flagship feature of Luminer. Instead of delivering final answers, Luminer acts as a coach:
* **Socratic Questioning**: Uses leading questions to help students uncover conceptual blind spots step-by-step.
* **Visual Recognition**: Analyzes uploaded images (photos of handwritten work or textbook pages) to identify specific points of confusion.
* **Iterative Feedback**: Encourages students to discuss their thought processes and provides constructive feedback.

### 2. General QA Mode
Available for quick conceptual breakdowns and complete mathematical derivations when students are truly stuck. It provides step-by-step solutions and thorough explanations.

### 3. Privacy-First Architecture
* **Anonymized Identity**: Student IDs are processed using an **irreversible hash** before storage to ensure total student privacy.
* **Data for Research**: Collected data is used solely to analyze learning progress and common conceptual hurdles for educational research.
* **Session-Based Memory**: Conversations are stored in the browser's temporary memory; chat history is cleared once the page is refreshed to maintain server stability.

---

## 🛠️ Tech Stack

* **Frontend/Deployment**: [Streamlit](https://streamlit.io/) 
* **AI Engine**: [Google Gemini API](https://ai.google.dev/) (Utilizing advanced reasoning models)
* **Database Integration**: [gspread](https://github.com/burnash/gspread) via Google Sheets API for research logging.
* **Security**: Python `hashlib` for student ID anonymization.

---

## 📖 Research Context

Luminer is a research-oriented initiative exploring the impact of Generative AI on physics education. The project focuses on:
* Reducing "AI dependency" by enforcing Socratic interaction.
* Understanding current student familiarity with AI tools in a physics context.

---

## 🏗️ Installation & Setup

If you wish to run this locally:

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/](https://github.com/) weihsuanchung/AI_TA_for_General_Physics.git
