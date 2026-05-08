import os
import fitz  # PyMuPDF
import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# Safely initialize OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is missing from the environment variables.")
client = OpenAI(api_key=api_key)

# --- STRICT DATA SCHEMA FOR ATS ---
class ATSResult(BaseModel):
    ats_score: int = Field(description="An estimated ATS match score from 0-100 based on keyword and semantic match.")
    matched_skills: list[str] = Field(description="List of hard skills found in both the resume and JD.")
    missing_skills: list[str] = Field(description="Critical skills required by the JD that are missing from the resume.")
    action_verb_feedback: str = Field(description="Feedback on whether the candidate used strong action verbs (e.g., Engineered, Managed) vs weak ones.")
    improvement_suggestions: list[str] = Field(description="3 actionable bullet points on how to improve the resume for this specific JD.")

def get_pdf_text(file_bytes):
    """Extracts text from a binary PDF stream using PyMuPDF."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return " ".join([page.get_text() for page in doc])
    except Exception as e:
        print(f"PDF Reading Error: {e}")
        return ""

async def extract_job_description(jd_input: str) -> str:
    """Detects if the input is a URL. If yes, scrapes the website text. If no, returns the raw text."""
    jd_input = jd_input.strip()
    if jd_input.startswith("http://") or jd_input.startswith("https://"):
        try:
            async with httpx.AsyncClient() as http_client:
                # Disguise the scraper as a standard browser to avoid blocks
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                response = await http_client.get(jd_input, headers=headers, timeout=10.0)
                soup = BeautifulSoup(response.text, "html.parser")
                return soup.get_text(separator="\n", strip=True)
        except Exception as e:
            print(f"URL Scraping Error: {e}")
            return jd_input # Fallback to the raw URL string if scraping fails
    return jd_input

@app.post("/analyze-resumes")
async def analyze_resumes(jd: str = Form(...), files: list[UploadFile] = File(...)):
    """Analyzes a batch of resumes against a JD (or JD Link) to provide ATS scores."""
    results = []
    
    try:
        # Check if the JD is a URL and extract text if necessary
        actual_jd_text = await extract_job_description(jd)

        for file in files:
            content = await file.read()
            text = get_pdf_text(content)
            
            if not text.strip():
                results.append({
                    "filename": file.filename,
                    "error": "Could not extract text. Ensure the PDF is not an image-only file."
                })
                continue

            # Perform AI Gap Analysis
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "You are an elite Applicant Tracking System (ATS) and Senior Career Coach. "
                            "Perform a strict, uncompromising gap analysis between the Job Description and the Resume. "
                            f"Target Job Details:\n{actual_jd_text}\n\n"
                            "Identify missing keywords, evaluate bullet point impact, and calculate a realistic match score."
                        )
                    },
                    {"role": "user", "content": f"Resume Text:\n{text}"}
                ],
                response_format=ATSResult
            )
            
            parsed_data = completion.choices[0].message.parsed.model_dump()
            parsed_data["filename"] = file.filename
            results.append(parsed_data)
            
        return results
        
    except Exception as e:
        print(f"Backend Error: {str(e)}")
        raise HTTPException(status_code=500, detail="An internal error occurred during analysis.")
