import os
import fitz  # PyMuPDF
import smtplib
import imaplib
import email
from email.header import decode_header
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field
from email.message import EmailMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- DATA MODEL ---
class Candidate(BaseModel):
    name: str
    email: str
    technical_skills_analysis: str = Field(description="Detailed analysis of hard skills")
    experience_level_match: str = Field(description="Analysis of seniority")
    score: int = Field(description="Score from 0-100")
    reasoning: str = Field(description="A concise 2-sentence summary")

def get_pdf_text(file_bytes):
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return " ".join([page.get_text() for page in doc])
    except Exception:
        return ""

@app.post("/rank")
async def rank(jd: str = Form(...), files: list[UploadFile] = File(...)):
    results = []
    try:
        for file in files:
            content = await file.read()
            text = get_pdf_text(content)
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"Professional HR Auditor. Perform gap analysis for JD: {jd}. Low match = low score."},
                    {"role": "user", "content": f"Resume Text: {text}"}
                ],
                response_format=Candidate
            )
            results.append(completion.choices[0].message.parsed.dict())
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-invite")
async def send_invite(email: str, name: str, recruiter_name: str):
    try:
        msg = EmailMessage()
        msg['Subject'] = f"Interview Invitation: {recruiter_name}"
        msg['To'] = email
        msg['From'] = os.getenv("SENDER_EMAIL")
        msg.set_content(f"Dear {name},\n\nWe were impressed by your background and would like to invite you for an interview.\n\nBest,\n{recruiter_name}")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(os.getenv("SENDER_EMAIL"), os.getenv("EMAIL_PASSWORD"))
            smtp.send_message(msg)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-rejection")
async def send_rejection(email: str, name: str, recruiter_name: str):
    try:
        msg = EmailMessage()
        msg['Subject'] = "Update regarding your application"
        msg['To'] = email
        msg['From'] = os.getenv("SENDER_EMAIL")
        msg.set_content(f"Dear {name},\n\nThank you for your interest. We have decided to move forward with other candidates.\n\nBest,\n{recruiter_name}")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(os.getenv("SENDER_EMAIL"), os.getenv("EMAIL_PASSWORD"))
            smtp.send_message(msg)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/check-replies")
async def check_replies(candidate_email: str):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(os.getenv("SENDER_EMAIL"), os.getenv("EMAIL_PASSWORD"))
        mail.select('"[Gmail]/All Mail"')
        status, messages = mail.search(None, 'OR', f'FROM "{candidate_email}"', f'TO "{candidate_email}"')
        if status != "OK" or not messages[0]: return {"replies": []}
        replies = []
        for e_id in messages[0].split()[-15:]:
            _, msg_data = mail.fetch(e_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            sender = "Applicant" if candidate_email.lower() in msg.get("From", "").lower() else "Recruiter"
            
            # Robust multipart extraction (FIXED for Gmail/Outlook)
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")
            
            replies.append({"sender": sender, "body": body[:500].strip()})
        return {"replies": replies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reply-to-candidate")
async def reply_to_candidate(email: str, subject: str, message_body: str, recruiter_name: str):
    try:
        msg = EmailMessage()
        msg['Subject'] = f"Re: {subject}"
        msg['To'] = email
        msg['From'] = os.getenv("SENDER_EMAIL")
        msg.set_content(f"{message_body}\n\nBest,\n{recruiter_name}")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(os.getenv("SENDER_EMAIL"), os.getenv("EMAIL_PASSWORD"))
            smtp.send_message(msg)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-verification")
async def send_verification(email: str, name: str, verify_link: str):
    try:
        msg = EmailMessage()
        msg['Subject'] = "Verify AI Recruiter Account"
        msg['To'] = email
        msg['From'] = os.getenv("SENDER_EMAIL")
        msg.set_content(f"Hello {name},\nVerify here: {verify_link}")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(os.getenv("SENDER_EMAIL"), os.getenv("EMAIL_PASSWORD"))
            smtp.send_message(msg)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
