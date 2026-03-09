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

# --- 0. CONFIGURATION (UPDATE THESE!) ---
# Replace this with your actual Render URL
BACKEND_URL = "https://ai-recruiter-backend.onrender.com" 
# Replace this with your actual Streamlit URL
FRONTEND_URL = "https://ai-recruiter-pro-adilzahoormalik000.streamlit.app" 

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
        "admin@recruiter.com": "Admin",
        "helpdeskai37@gmail.com": "Helpdesk Agent",
        "nadine@recruiter.com": "Nadine"
    }
if "pending_users" not in cache:
    cache["pending_users"] = {}
    
save_cache(cache)

USER_CREDENTIALS = cache["user_credentials"]
USER_NAMES = cache["user_names"]
PENDING_USERS = cache["pending_users"]

# --- HELPER: PASSWORD STRENGTH CHECKER ---
def check_password_strength(password):
    if not password:
        return 0, "", ""
    
    score = 0
    if len(password) >= 8: score += 1
    if re.search(r"[a-z]", password) and re.search(r"[A-Z]", password): score += 1
    if re.search(r"[0-9]", password): score += 1
    if re.search(r"[@$!%*?&#]", password): score += 1

    if score <= 1:
        return 25, "Weak", "red"
    elif score == 2:
        return 50, "Medium", "orange"
    elif score == 3:
        return 75, "Good", "#FFD700" 
    else:
        return 100, "Strong", "green"

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
    else:
        st.error("❌ Invalid or expired verification link.")
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

# --- 4. MAIN ROUTING (LOGIN VS SIGNUP VS DASHBOARD) ---
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
                    else:
                        st.error("Invalid credentials. Have you verified your email?")
                
                st.markdown("<div style='text-align: center; margin-top: 15px;'>Not registered yet?</div>", unsafe_allow_html=True)
                if st.button("Create an Account", use_container_width=True):
                    st.session_state.auth_mode = "signup"
                    st.rerun()

            else:
                st.subheader("Sign Up")
                new_name = st.text_input("Full Name", placeholder="e.g. John Doe")
                new_email = st.text_input("Email Address")
                new_pass = st.text_input("Password", type="password")
                
                if new_pass:
                    strength_val, strength_lbl, strength_color = check_password_strength(new_pass)
                    st.markdown(f"<p style='color:{strength_color}; margin-bottom: 0px; font-weight: bold;'>Strength: {strength_lbl}</p>", unsafe_allow_html=True)
                    st.progress(strength_val)
                    
                confirm_pass = st.text_input("Confirm Password", type="password")
                
                if st.button("Sign Up", use_container_width=True, type="primary"):
                    if not new_name or not new_email or not new_pass:
                        st.warning("Please fill out all fields.")
                    elif new_pass != confirm_pass:
                        st.error("Passwords do not match!")
                    elif new_email in USER_CREDENTIALS:
                        st.error("Email already registered. Please log in.")
                    else:
                        token = uuid.uuid4().hex
                        # Point this to your live Streamlit URL
                        verify_link = f"{FRONTEND_URL}/?verify={token}"
                        
                        PENDING_USERS[token] = {
                            "email": new_email,
                            "password": new_pass,
                            "name": new_name
                        }
                        cache["pending_users"] = PENDING_USERS
                        save_cache(cache)
                        
                        with st.spinner("Sending verification link..."):
                            try:
                                res = httpx.post(
                                    f"{BACKEND_URL}/send-verification",
                                    params={"email": new_email, "name": new_name, "verify_link": verify_link},
                                    timeout=20.0
                                )
                                if res.status_code == 200:
                                    st.success("Verification link sent! Check your inbox.")
                                    time.sleep(1.5)
                                    st.session_state.auth_mode = "login"
                                    st.rerun()
                                else:
                                    st.error("Failed to send verification email.")
                            except Exception as e:
                                st.error(f"Error connecting to backend: {e}")

                st.markdown("<div style='text-align: center; margin-top: 15px;'>Already have an account?</div>", unsafe_allow_html=True)
                if st.button("Log In Here", use_container_width=True):
                    st.session_state.auth_mode = "login"
                    st.rerun()

        st.markdown("<p style='text-align: center; color: gray;'>— OR —</p>", unsafe_allow_html=True)
        try:
            # Note: Update redirect_uri in Google Console to your FRONTEND_URL
            result = oauth2.authorize_button("Continue with Google", "https://www.google.com/favicon.ico", FRONTEND_URL, "openid email profile", "google_auth", use_container_width=True)
            if result and "token" in result:
                st.session_state.auth_success = True
                st.session_state.user_name = "Google User"
                st.session_state.user_email = "google@user.com"
                
                cache["auth_success"] = True
                cache["user_name"] = st.session_state.user_name
                cache["user_email"] = st.session_state.user_email
                save_cache(cache)
                st.rerun()
        except Exception as e:
            st.error(f"Google OAuth Error: {e}")

else:
    # --- 5. DASHBOARD SIDEBAR ---
    with st.sidebar:
        st.markdown("### Recruiter Profile")
        
        uploaded_pic = st.file_uploader("Change Profile Picture", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
        if uploaded_pic:
            bytes_data = uploaded_pic.getvalue()
            base64_img = base64.b64encode(bytes_data).decode()
            pic_data = f"data:image/png;base64,{base64_img}"
            
            st.session_state.custom_profile_pic = pic_data
            cache["custom_profile_pic"] = pic_data
            save_cache(cache)
            st.rerun()

        img_url = st.session_state.custom_profile_pic if st.session_state.custom_profile_pic else f"https://www.gravatar.com/avatar/{hashlib.md5(st.session_state.user_email.lower().encode()).hexdigest()}?d=mp&s=200"
        
        st.markdown(
            f"""
            <div style="display: flex; flex-direction: column; align-items: center; text-align: center; padding-top: 20px;">
                <img src="{img_url}" style="border-radius: 50%; width: 120px; height: 120px; object-fit: cover; border: 3px solid #2E86C1; margin-bottom: 10px;">
                <h4 style="margin: 0;">Welcome, {st.session_state.user_name}!</h4>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown("<br>", unsafe_allow_html=True)

        with st.expander("⚙️ Edit Profile"):
            updated_name = st.text_input("Full Name", value=st.session_state.user_name)
            if st.button("Save Name", use_container_width=True):
                if updated_name.strip():
                    st.session_state.user_name = updated_name.strip()
                    cache["user_name"] = st.session_state.user_name
                    USER_NAMES[st.session_state.user_email] = st.session_state.user_name
                    cache["user_names"] = USER_NAMES
                    save_cache(cache)
                    st.success("Profile updated!")
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.auth_success = False
            st.session_state.show_replies = {}
            st.session_state.fetched_replies = {}
            cache["auth_success"] = False
            save_cache(cache)
            st.rerun()

    # --- 6. MAIN DASHBOARD CONTENT ---
    st.title("🔎 AI Candidate Analysis Dashboard")
    col1, col2 = st.columns([1, 1.5])

    with col1:
        st.subheader("Upload & Settings")
        jd = st.text_area("Job Description", height=200)
        files = st.file_uploader("Upload Resumes (PDF)", accept_multiple_files=True, type="pdf")
        
        if st.button("🚀 Analyze & Rank", use_container_width=True):
            if jd and files:
                with st.spinner("AI is analyzing..."):
                    try:
                        payload = {"jd": jd}
                        file_data = [("files", (f.name, f.getvalue(), "application/pdf")) for f in files]
                        res = httpx.post(f"{BACKEND_URL}/rank", data=payload, files=file_data, timeout=120.0)
                        
                        if res.status_code == 200:
                            results = res.json()
                            st.session_state.candidates = results
                            cache["candidates"] = results
                            save_cache(cache)
                            st.success("Analysis Complete!")
                        else:
                            st.error(f"Backend Error: {res.text}")
                    except Exception as e:
                        st.error(f"Connection Error: {e}")

    with col2:
        col2_a, col2_b = st.columns([3, 1])
        with col2_a:
            st.subheader("Ranked Results")
        with col2_b:
            if st.session_state.candidates:
                if st.button("🗑️ Clear All", use_container_width=True):
                    st.session_state.candidates = []
                    st.session_state.show_replies = {}
                    st.session_state.fetched_replies = {}
                    cache["candidates"] = []
                    save_cache(cache)
                    st.rerun()

        if st.session_state.candidates:
            sorted_list = sorted(st.session_state.candidates, key=lambda x: x['score'], reverse=True)
            for idx, c in enumerate(sorted_list):
                cand_email = c['email']
                with st.expander(f"⭐ Score: {c['score']}% — {c['name']}"):
                    st.write(f"**Email:** {cand_email}")
                    st.info(f"**AI Insight:** {c['reasoning']}")
                    
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    
                    with btn_col1:
                        if st.button(f"📧 Send Invite", key=f"invite_{idx}_{cand_email}", use_container_width=True):
                            with st.spinner(f"Sending email..."):
                                try:
                                    email_res = httpx.post(
                                        f"{BACKEND_URL}/send-invite", 
                                        params={"email": cand_email, "name": c['name'], "recruiter_name": st.session_state.user_name},
                                        timeout=20.0
                                    )
                                    if email_res.status_code == 200:
                                        st.success(f"Invite sent!")
                                        st.session_state.fetched_replies.pop(cand_email, None)
                                    else:
                                        st.error("Failed to send email.")
                                except Exception as e:
                                    st.error(f"Connection failed: {e}")
                                    
                    with btn_col2:
                        is_showing = st.session_state.show_replies.get(cand_email, False)
                        btn_label = "🔼 Hide Thread" if is_showing else "📥 View Thread"
                        
                        if st.button(btn_label, key=f"toggle_{idx}_{cand_email}", use_container_width=True):
                            st.session_state.show_replies[cand_email] = not is_showing
                            st.rerun()
                                    
                    with btn_col3:
                        if st.button(f"❌ Remove", key=f"remove_{idx}_{cand_email}", use_container_width=True):
                            st.session_state.candidates = [cand for cand in st.session_state.candidates if cand['email'] != cand_email]
                            cache["candidates"] = st.session_state.candidates
                            save_cache(cache)
                            st.rerun()

                    if st.session_state.show_replies.get(cand_email, False):
                        st.markdown("---") 
                        
                        if cand_email not in st.session_state.fetched_replies:
                            with st.spinner("Fetching thread..."):
                                try:
                                    rep_res = httpx.get(
                                        f"{BACKEND_URL}/check-replies",
                                        params={"candidate_email": cand_email},
                                        timeout=20.0
                                    )
                                    if rep_res.status_code == 200:
                                        st.session_state.fetched_replies[cand_email] = rep_res.json().get("replies", [])
                                    else:
                                        st.session_state.fetched_replies[cand_email] = []
                                except Exception as e:
                                    st.error(f"Error connecting: {e}")
                                    st.session_state.fetched_replies[cand_email] = []

                        replies = st.session_state.fetched_replies.get(cand_email, [])
                        latest_subject = "Interview Update" 
                        
                        if replies:
                            latest_subject = replies[-1]['subject'] 
                            st.markdown("#### Conversation History")
                            for r in replies:
                                if r.get("sender") == "Recruiter":
                                    with st.chat_message("assistant", avatar="🏢"):
                                        st.markdown(f"**You** - *{r['subject']}*")
                                        st.write(r['body'])
                                else:
                                    with st.chat_message("user", avatar="👤"):
                                        st.markdown(f"**{c['name']}** - *{r['subject']}*")
                                        st.write(r['body'])
                        else:
                            st.info("No emails sent or received yet.")
                            
                        st.markdown("#### Send a Message")
                        reply_text = st.text_area(f"Reply to {c['name']}:", key=f"draft_{cand_email}")
                        
                        if st.button("📤 Send", key=f"send_reply_{cand_email}"):
                            if not reply_text.strip():
                                st.warning("Please type a message first.")
                            else:
                                with st.spinner("Sending message..."):
                                    try:
                                        res = httpx.post(
                                            f"{BACKEND_URL}/reply-to-candidate",
                                            params={
                                                "email": cand_email, 
                                                "subject": latest_subject, 
                                                "message_body": reply_text, 
                                                "recruiter_name": st.session_state.user_name
                                            },
                                            timeout=20.0
                                        )
                                        if res.status_code == 200:
                                            st.success("Message sent successfully!")
                                            st.session_state.fetched_replies.pop(cand_email, None)
                                            st.rerun()
                                        else:
                                            st.error("Failed to send.")
                                    except Exception as e:
                                        st.error(f"Error connecting to backend: {e}")

        else:
            st.info("Results will appear here once analysis is complete.")
