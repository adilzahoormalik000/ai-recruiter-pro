# 🚀 AI Recruiter: Semantic ATS Analyzer

> An intelligent, full-stack application that evaluates candidate resumes against job descriptions using Large Language Models to provide actionable, deterministic feedback.

## 📌 Overview
Traditional Applicant Tracking Systems (ATS) rely heavily on rigid, one-to-one keyword matching. This project bridges that gap by utilizing advanced natural language processing to understand the semantic context of a candidate's experience. Built with a **FastAPI** backend and a **Streamlit** frontend, the system extracts text from uploaded PDFs, asynchronously scrapes live job descriptions, and utilizes OpenAI's `gpt-4o-mini` to generate a rigorous match score, isolate skill gaps, and provide qualitative feedback.

## ✨ Key Features
* **Asynchronous Web Scraping:** Extracts raw text directly from job posting URLs using `httpx` and `BeautifulSoup`.
* **Robust PDF Parsing:** Efficiently reads binary PDF streams of candidate resumes using `PyMuPDF` (`fitz`).
* **Semantic LLM Evaluation:** Leverages the OpenAI API with strict Pydantic schemas to return a reliable JSON output containing match scores, found/missing keywords, and actionable next steps.
* **Interactive UI Dashboard:** A dynamic Streamlit frontend featuring progress bars, expandable keyword containers, and responsive bifurcated layouts.
* **Automated SMTP Pipeline:** Built-in email integration securely handles outbound interview invitations to high-scoring candidates.

## 🛠️ Tech Stack
* **Frontend:** Streamlit
* **Backend:** FastAPI, Uvicorn
* **AI / NLP:** OpenAI API (gpt-4o-mini), Pydantic (Structured Outputs)
* **Data Extraction:** PyMuPDF, BeautifulSoup4, httpx
* **Language:** Python 3.x

## ⚙️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/adilzahoor2812/Resume_Analyzer_With_ATS_Score.git
cd Resume_Analyzer_With_ATS_Score
cd AI_RECRUITER
2. Create a Virtual Environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
3. Install Dependencies
pip install -r requirements.txt
4. Configure Environment Variables
Create a hidden environment file in the root directory using the provided template to securely store your credentials:
cp .env.example .env
Open the new .env file and insert your OpenAI API Key and Google App Password.
🚀 Usage
You will need to run the backend and frontend simultaneously in two separate terminal windows.

Start the FastAPI Backend (Terminal 1):
uvicorn main:app --reload
The backend will run locally on http://127.0.0.1:8000.

Start the Streamlit Frontend (Terminal 2):
streamlit run app.py
The UI will launch automatically in your browser at http://localhost:8501.

📂 Architecture Flow
Data Ingestion: The user provides a job URL and uploads candidate PDF(s) via the client UI.

Extraction: The backend scrapes the web DOM and extracts the PDF byte streams concurrently.

Analysis: The LLM cross-references the data against a strict JSON schema to prevent hallucinated formats.

Rendering: The client UI parses the structured array and visualizes the ATS score, missing skills, and qualitative feedback.
