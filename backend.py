import os
import fitz  # PyMuPDF
import smtplib
import imaplib
import email
from email.header import decode_header
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from openai import OpenAI
from pydantic import BaseModel
from email.message import EmailMessage
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Initialize OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Data model for AI extraction
class Candidate(BaseModel):
    name: str
    email: str
    score: int
    reasoning: str

def get_pdf_text(file_bytes):
    """Extracts text from uploaded PDF bytes."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return " ".join([page.get_text() for page in doc])
    except Exception as e:
        print(f"PDF Reading Error: {e}")
        return ""

@app.post("/rank")
async def rank(jd: str = Form(...), files: list[UploadFile] = File(...)):
    """Ranks resumes against a Job Description using GPT-4o-mini."""
    results = []
    try:
        for file in files:
            content = await file.read()
            text = get_pdf_text(content)
            
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"You are an expert recruiter. Rank the following resume against this Job Description: {jd}. focus on skills and experience match. Extract the candidate's full name and email address."},
                    {"role": "user", "content": text}
                ],
                response_format=Candidate
            )
            results.append(completion.choices[0].message.parsed.dict())
        return results
    except Exception as e:
        print(f"❌ OpenAI Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-invite")
async def send_email(email: str, name: str, recruiter_name: str):
    """Sends a personalized professional email using Gmail SMTP."""
    try:
        msg = EmailMessage()
        
        # --- PERSONALIZED CONTENT ---
        msg['Subject'] = f"Interview Invitation from {recruiter_name}"
        msg['To'] = email
        msg['From'] = os.getenv("SENDER_EMAIL")

        email_body = f"""Dear {name},

I hope this email finds you well.

Our team has reviewed your profile, and we are very impressed with your background. We believe your skills could be a great fit for our current openings and would love to schedule an introductory call to discuss this further.

Please let us know your availability over the next few days.

Best regards,

The Recruitment Team
{recruiter_name}
AI HelpDesk Solutions
"""
        msg.set_content(email_body)

        # --- SMTP CONNECTION ---
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(os.getenv("SENDER_EMAIL"), os.getenv("EMAIL_PASSWORD"))
            smtp.send_message(msg)
            
        return {"status": "success", "message": f"Email sent by {recruiter_name}"}
        
    except smtplib.SMTPAuthenticationError:
        print("❌ Gmail Authentication Failed. Check App Password.")
        raise HTTPException(status_code=401, detail="Gmail Authentication failed. Verify App Password in .env")
    except Exception as e:
        print(f"❌ Email Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/check-replies")
async def check_replies(candidate_email: str):
    """Connects to Gmail via IMAP to fetch the full thread history."""
    try:
        username = os.getenv("SENDER_EMAIL")
        password = os.getenv("EMAIL_PASSWORD")
        
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(username, password)
        
        # Look in "All Mail" to catch both Inbox (their replies) and Sent (your replies)
        try:
            mail.select('"[Gmail]/All Mail"')
        except:
            mail.select("inbox") # Fallback if All Mail isn't localized
        
        # Search for emails FROM the candidate OR TO the candidate
        status, messages = mail.search(None, 'OR', f'FROM "{candidate_email}"', f'TO "{candidate_email}"')
        
        if status != "OK" or not messages[0]:
            return {"replies": []}
            
        email_ids = messages[0].split()
        replies = []
        
        # Fetch up to the last 15 emails in the thread
        for e_id in email_ids[-15:]:
            res, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decode Subject safely
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    
                    # Determine who sent it (Recruiter or Candidate)
                    from_header = msg.get("From", "")
                    if candidate_email.lower() in from_header.lower():
                        sender = "Applicant"
                    else:
                        sender = "Recruiter"
                    
                    # Extract plain text body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")
                    
                    # Clean up long emails
                    clean_body = body[:1000] + "\n\n[... Message Truncated]" if len(body) > 1000 else body
                    replies.append({
                        "sender": sender,
                        "subject": subject,
                        "body": clean_body.strip()
                    })
        
        mail.logout()
        return {"replies": replies}
        
    except Exception as e:
        print(f"❌ IMAP Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reply-to-candidate")
async def reply_to_candidate(email: str, subject: str, message_body: str, recruiter_name: str):
    """Sends a custom reply back to the candidate."""
    try:
        msg = EmailMessage()
        
        msg['Subject'] = f"Re: {subject}" if not subject.startswith("Re:") else subject
        msg['To'] = email
        msg['From'] = os.getenv("SENDER_EMAIL")

        full_email_body = f"{message_body}\n\nBest regards,\n{recruiter_name}\nAI HelpDesk Solutions"
        msg.set_content(full_email_body)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(os.getenv("SENDER_EMAIL"), os.getenv("EMAIL_PASSWORD"))
            smtp.send_message(msg)
            
        return {"status": "success", "message": "Reply sent successfully!"}
        
    except Exception as e:
        print(f"❌ Reply Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-verification")
async def send_verification(email: str, name: str, verify_link: str):
    """Sends an account verification link to the new user."""
    try:
        msg = EmailMessage()
        msg['Subject'] = "Verify your AI Recruiter Account"
        msg['To'] = email
        msg['From'] = os.getenv("SENDER_EMAIL")

        email_body = f"""Hello {name},

Welcome to AI Recruiter Pro! 

To complete your registration and activate your account, please click the link below:
{verify_link}

If you did not request this account, you can safely ignore this email.

Best regards,
AI HelpDesk Solutions
"""
        msg.set_content(email_body)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(os.getenv("SENDER_EMAIL"), os.getenv("EMAIL_PASSWORD"))
            smtp.send_message(msg)
            
        return {"status": "success", "message": "Verification email sent"}
        
    except smtplib.SMTPAuthenticationError:
        print("❌ Gmail Authentication Failed. Check App Password.")
        raise HTTPException(status_code=401, detail="Gmail Authentication failed. Verify App Password in .env")
    except Exception as e:
        print(f"❌ Verification Email Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))