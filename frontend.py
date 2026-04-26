import streamlit as st
import httpx
import os
import hashlib
import base64
import json
import uuid
import re
import time
from streamlit_oauth import OAuth2Component
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

st.set_page_config(page_title="AI Recruiter Pro", layout="wide")

# --- 1. LOCAL CACHE SYSTEM ---
CACHE_FILE = "local_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

cache = load_cache()

# Load Databases from Cache
if "user_credentials" not in cache:
    cache["user_credentials"] = {
        "admin@recruiter.com": "password123",
        "helpdeskai37@gmail.com": "helpdeskai",
        "nadine@recruiter.com": "nadine123"
    }
if "user_names" not in cache:
    cache["user_names"] = {
        "admin@recruiter.com": "Admin"
    }
if "pending_users" not in cache:
    cache["pending_users"] = {}
    
save_cache(cache)

USER_CREDENTIALS = cache["user_credentials"]
USER_NAMES = cache["user_names"]
PENDING_USERS = cache["pending_users"]

# --- HELPER: PASSWORD STRENGTH CHECKER ---
def check_password_strength(password):
    if not password: return 0, "", ""
    score = 0
    if len(password) >= 8: score += 1
    if re.search(r"[a-z]", password) and re.search(r"[A-Z]", password): score += 1
    if re.search(r"[0-9]", password): score += 1
    if re.search(r"[@$!%*?&#]", password): score += 1
    if score <= 1: return 25, "Weak", "red"
    elif score == 2: return 50, "Medium", "orange"
    elif score == 3: return 75, "Good", "#FFD700"
    else: return 100, "Strong", "green"

# --- 2. EMAIL VERIFICATION LISTENER ---
query_params = st.query_params
if "verify" in query_params:
    token = query_params["verify"]
    if token in PENDING_USERS:
        user_data = PENDING_USERS[token]
        USER_CREDENTIALS[user_data["email"]] = user_data["password"]
        USER_NAMES[user_data["email"]] = user_data["name"]
        del PENDING_USERS[token]
        cache["user_credentials"] = USER_CREDENTIALS
        cache["user_names"] = USER_NAMES
        cache["pending_users"] = PENDING_USERS
        save_cache(cache)
        st.success("✅ Email verified successfully! You can now log in.")
        st.query_params.clear()

# --- 3. SESSION INITIALIZATION ---
if "init" not in st.session_state:
    st.session_state.init = True
    st.session_state.auth_success = cache.get("auth_success", False)
    st.session_state.user_email = cache.get("user_email", "")
    st.session_state.user_name = cache.get("user_name", "")
    st.session_state.custom_profile_pic = cache.get("custom_profile_pic", None)
    st.session_state.candidates = cache.get("candidates", [])
    st.session_state.saved_pass = cache.get("saved_pass", "")
    st.session_state.remember_me = cache.get("remember_me", True)
    st.session_state.show_replies = {}
    st.session_state.fetched_replies = {}
    st.session_state.auth_mode = "login"

# Google OAuth Setup
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, TOKEN_URL, "")

# --- 4. MAIN ROUTING ---
if not st.session_state.auth_success:
    _, login_col, _ = st.columns([1, 2, 1])
    with login_col:
        st.title("🤖 AI Recruiter")
        with st.container(border=True):
            if st.session_state.auth_mode == "login":
                st.subheader("Sign In")
                email_input = st.text_input("Email Address", value=st.session_state.user_email)
                pass_input = st.text_input("Password", type="password", value=st.session_state.saved_pass)
                remember_me = st.checkbox("Keep me logged in", value=st.session_state.remember_me)
                if st.button("Sign In", use_container_width=True, type="primary"):
                    if email_input in USER_CREDENTIALS and USER_CREDENTIALS[email_input] == pass_input:
                        st.success("✅ Login Successful!")
                        st.session_state.auth_success = True
                        st.session_state.user_email = email_input
                        st.session_state.user_name = USER_NAMES.get(email_input, email_input.split('@')[0].capitalize())
                        cache["auth_success"] = True
                        cache["user_email"] = email_input
                        cache["user_name"] = st.session_state.user_name
                        cache["remember_me"] = remember_me
                        cache["saved_pass"] = pass_input if remember_me else ""
                        save_cache(cache)
                        time.sleep(0.5)
                        st.rerun()
                    else: st.error("Invalid credentials.")
                if st.button("Create an Account", use_container_width=True):
                    st.session_state.auth_mode = "signup"; st.rerun()
            else:
                st.subheader("Sign Up")
                new_name = st.text_input("Full Name")
                new_email = st.text_input("Email Address")
                new_pass = st.text_input("Password", type="password")
                if new_pass:
                    s_val, s_lbl, s_col = check_password_strength(new_pass)
                    st.markdown(f"<p style='color:{s_col}; font-weight: bold;'>Strength: {s_lbl}</p>", unsafe_allow_html=True)
                    st.progress(s_val)
                confirm_pass = st.text_input("Confirm Password", type="password")
                if st.button("Sign Up", use_container_width=True, type="primary"):
                    if new_pass == confirm_pass and new_email not in USER_CREDENTIALS:
                        token = uuid.uuid4().hex
                        verify_link = f"http://localhost:8501/?verify={token}"
                        PENDING_USERS[token] = {"email": new_email, "password": new_pass, "name": new_name}
                        cache["pending_users"] = PENDING_USERS; save_cache(cache)
                        httpx.post("http://localhost:8000/send-verification", params={"email": new_email, "name": new_name, "verify_link": verify_link})
                        st.success("Verification link sent!"); time.sleep(1.5)
                        st.session_state.auth_mode = "login"; st.rerun()
                if st.button("Log In Here", use_container_width=True):
                    st.session_state.auth_mode = "login"; st.rerun()

        st.markdown("<p style='text-align: center; color: gray;'>— OR —</p>", unsafe_allow_html=True)
        result = oauth2.authorize_button("Continue with Google", "https://www.google.com/favicon.ico", "http://localhost:8501", "openid email profile", "google_auth", use_container_width=True)
        if result and "token" in result:
            st.session_state.auth_success = True; st.rerun()

else:
    # --- 5. DASHBOARD SIDEBAR ---
    with st.sidebar:
        st.markdown("### Recruiter Profile")
        uploaded_pic = st.file_uploader("Change Photo", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
        if uploaded_pic:
            base64_img = base64.b64encode(uploaded_pic.getvalue()).decode()
            pic_data = f"data:image/png;base64,{base64_img}"
            st.session_state.custom_profile_pic = pic_data
            cache["custom_profile_pic"] = pic_data; save_cache(cache); st.rerun()

        img_url = st.session_state.custom_profile_pic if st.session_state.custom_profile_pic else f"https://www.gravatar.com/avatar/{hashlib.md5(st.session_state.user_email.lower().encode()).hexdigest()}?d=mp&s=200"
        st.markdown(f'<div style="text-align: center;"><img src="{img_url}" style="border-radius: 50%; width: 100px; height: 100px; object-fit: cover; border: 3px solid #2E86C1;"><h4>{st.session_state.user_name}</h4></div>', unsafe_allow_html=True)

        # --- PROFILE EDIT SECTION ---
        with st.expander("📝 Edit Details"):
            edit_name = st.text_input("Name", value=st.session_state.user_name)
            edit_email = st.text_input("Email", value=st.session_state.user_email)
            if st.button("Save Changes"):
                old_email = st.session_state.user_email
                # Update records in cache
                if old_email != edit_email:
                    USER_CREDENTIALS[edit_email] = USER_CREDENTIALS.pop(old_email)
                    USER_NAMES[edit_email] = USER_NAMES.pop(old_email)
                
                USER_NAMES[edit_email] = edit_name
                st.session_state.user_name = edit_name
                st.session_state.user_email = edit_email
                cache["user_email"] = edit_email
                cache["user_name"] = edit_name
                save_cache(cache)
                st.success("Updated!"); st.rerun()

        st.markdown("---")
        st.markdown("### 🎯 Screening Settings")
        pass_threshold = st.slider("Qualification Threshold %", 0, 100, 70)
        st.markdown("---")

        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.auth_success = False; cache["auth_success"] = False; save_cache(cache); st.rerun()

    # --- 6. MAIN CONTENT ---
    st.title("🔎 AI Candidate Analysis Dashboard")
    col1, col2 = st.columns([1, 1.5])

    with col1:
        st.subheader("Upload & Settings")
        jd = st.text_area("Job Description", height=200)
        files = st.file_uploader("Upload Resumes (PDF)", accept_multiple_files=True, type="pdf")
        if st.button("🚀 Analyze & Rank", use_container_width=True):
            if jd and files:
                with st.spinner("AI is analyzing..."):
                    file_data = [("files", (f.name, f.getvalue(), "application/pdf")) for f in files]
                    res = httpx.post("http://localhost:8000/rank", data={"jd": jd}, files=file_data, timeout=120.0)
                    if res.status_code == 200:
                        st.session_state.candidates = res.json()
                        cache["candidates"] = st.session_state.candidates; save_cache(cache); st.success("Done!")

    with col2:
        st.subheader("Ranked Results")
        if st.session_state.candidates:
            sorted_list = sorted(st.session_state.candidates, key=lambda x: x['score'], reverse=True)
            for idx, c in enumerate(sorted_list):
                cand_email = c['email']
                with st.expander(f"⭐ Score: {c['score']}% — {c['name']}"):
                    st.write(f"**Email:** {cand_email}")
                    st.info(f"**AI Insight:** {c['reasoning']}")
                    
                    b1, b2, b3 = st.columns(3)
                    
                    with b1:
                        # --- DYNAMIC SLIDER LOGIC ---
                        if c['score'] >= pass_threshold:
                            if st.button(f"📧 Invite", key=f"inv_{idx}_{cand_email}", use_container_width=True, type="primary"):
                                with st.spinner("Sending..."):
                                    httpx.post("http://localhost:8000/send-invite", params={"email": cand_email, "name": c['name'], "recruiter_name": st.session_state.user_name})
                                    st.success("Sent!")
                        else:
                            if st.button(f"📩 Reject", key=f"rej_{idx}_{cand_email}", use_container_width=True):
                                with st.spinner("Sending..."):
                                    httpx.post("http://localhost:8000/send-rejection", params={"email": cand_email, "name": c['name'], "recruiter_name": st.session_state.user_name})
                                    st.warning("Rejected.")
                    
                    with b2:
                        is_showing = st.session_state.show_replies.get(cand_email, False)
                        btn_lbl = "🔼 Hide Thread" if is_showing else "📥 View Thread"
                        if st.button(btn_lbl, key=f"t_{idx}_{cand_email}", use_container_width=True):
                            st.session_state.show_replies[cand_email] = not is_showing; st.rerun()
                    
                    with b3:
                        if st.button("❌ Remove", key=f"rm_{idx}_{cand_email}", use_container_width=True):
                            st.session_state.candidates = [cand for cand in st.session_state.candidates if cand['email'] != cand_email]
                            cache["candidates"] = st.session_state.candidates; save_cache(cache); st.rerun()

                    # --- EMAIL THREAD HISTORY ---
                    if st.session_state.show_replies.get(cand_email, False):
                        st.markdown("---") 
                        if cand_email not in st.session_state.fetched_replies:
                            with st.spinner("Fetching emails..."):
                                try:
                                    rep_res = httpx.get("http://localhost:8000/check-replies", params={"candidate_email": cand_email}, timeout=20.0)
                                    st.session_state.fetched_replies[cand_email] = rep_res.json().get("replies", [])
                                except: st.session_state.fetched_replies[cand_email] = []

                        replies = st.session_state.fetched_replies.get(cand_email, [])
                        if replies:
                            st.markdown("#### Conversation")
                            for r in replies:
                                role = "assistant" if r.get("sender") == "Recruiter" else "user"
                                with st.chat_message(role, avatar="🏢" if role == "assistant" else "👤"):
                                    st.write(r.get('body', ''))
                        else:
                            st.info("No messages found.")
                            
                        # --- REPLY BOX ---
                        st.markdown("#### Send a Message")
                        reply_text = st.text_area(f"Message to {c['name']}:", key=f"draft_{cand_email}")
                        if st.button("📤 Send", key=f"send_reply_{cand_email}"):
                            if reply_text.strip():
                                with st.spinner("Sending..."):
                                    httpx.post("http://localhost:8000/reply-to-candidate", params={"email": cand_email, "subject": "Interview Update", "message_body": reply_text, "recruiter_name": st.session_state.user_name})
                                    st.session_state.fetched_replies.pop(cand_email, None); st.success("Sent!"); st.rerun()
