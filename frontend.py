import streamlit as st
import httpx
import json
import os

# --- LOCAL CACHE FOR REFRESH PERSISTENCE ---
CACHE_FILE = "ats_cache.json"

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

# Load saved results into Session State so they survive refresh
if "ats_results" not in st.session_state:
    st.session_state.ats_results = cache.get("last_results", None)

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="AI ATS Analyzer", page_icon="📄", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/942/942748.png", width=80)
    st.title("How it Works")
    st.markdown("""
    Test your resume against real jobs to see if you can beat the bots!
    
    **Features:** * Paste a **URL link** to a job posting, and our AI will read the webpage automatically.
    * Upload multiple resumes at once to see which version scores the highest.
    """)
    if st.button("🗑️ Clear Saved Results", use_container_width=True):
        st.session_state.ats_results = None
        cache["last_results"] = None
        save_cache(cache)
        st.rerun()

# --- MAIN HEADER ---
st.title("📄 Resume Analyzer With ATS Score")
st.markdown("Optimize your resumes to beat the bots and land the interview.")
st.markdown("---")

# --- LAYOUT DIVIDER ---
col_input, col_results = st.columns([1, 1.5], gap="large")

with col_input:
    st.subheader("📝 Input Data")
    
    with st.container(border=True):
        # NOTE: JD is intentionally NOT saved to session state, so it clears on refresh!
        jd_input = st.text_area(
            "1. Paste Job Description OR a Link (URL)", 
            height=200, 
            placeholder="Paste text OR https://linkedin.com/jobs/..."
        )
        
        uploaded_files = st.file_uploader("2. Upload Resumes (PDF)", type=["pdf"], accept_multiple_files=True)
        
        analyze_button = st.button("🚀 Analyze Match", type="primary", use_container_width=True)

with col_results:
    st.subheader("📊 Your Analysis Reports")
    
    # 1. Trigger Analysis
    if analyze_button:
        if not jd_input.strip() or not uploaded_files:
            st.error("⚠️ Please provide both a Job Description/Link and at least one Resume.")
        else:
            st.toast(f"Uploading {len(uploaded_files)} files...", icon="🔒")
            with st.spinner("Scanning semantics, checking links, and analyzing keywords..."):
                try:
                    files_payload = [("files", (f.name, f.getvalue(), "application/pdf")) for f in uploaded_files]
                    data = {"jd": jd_input}
                    
                    res = httpx.post("http://localhost:8000/analyze-resumes", data=data, files=files_payload, timeout=180.0)
                    
                    if res.status_code == 200:
                        results = res.json()
                        # Sort highest score first
                        results = sorted(results, key=lambda x: x.get('ats_score', 0), reverse=True)
                        
                        # Save to Cache & Session State (Persistence)
                        st.session_state.ats_results = results
                        cache["last_results"] = results
                        save_cache(cache)
                        
                        st.toast("Analysis Complete!", icon="✅")
                    else:
                        st.error(f"Server Error: {res.status_code}")
                except Exception as e:
                    st.error(f"Error connecting to backend: {e}")

    # 2. Render Results (Will render even after refresh because of Cache!)
    if st.session_state.ats_results:
        results = st.session_state.ats_results
        
        tab_titles = [f"{res_data.get('filename', 'Resume')} ({res_data.get('ats_score', 0)}%)" for res_data in results]
        tabs = st.tabs(tab_titles)
        
        for i, tab in enumerate(tabs):
            with tab:
                result = results[i]
                if "error" in result:
                    st.error(f"❌ **{result['filename']}**: {result['error']}")
                    continue
                
                score = result['ats_score']
                
                metric_col, text_col = st.columns([1, 3])
                with metric_col:
                    st.metric(label="ATS Match Score", value=f"{score}%")
                with text_col:
                    if score >= 80:
                        st.success("🔥 **Excellent!** Very strong match for this role.")
                    elif score >= 50:
                        st.warning("⚠️ **Moderate Match.** You need to weave in more keywords.")
                    else:
                        st.error("❌ **Low Match.** Heavy rewrite required.")
                
                st.progress(score / 100.0)
                st.markdown("<br>", unsafe_allow_html=True)
                
                with st.expander("🔑 Keyword Analysis", expanded=True):
                    k1, k2 = st.columns(2)
                    with k1:
                        st.markdown("#### ✅ Found Skills")
                        if result['matched_skills']:
                            for skill in result['matched_skills']:
                                st.markdown(f"- {skill}")
                        else:
                            st.write("None found.")
                    with k2:
                        st.markdown("#### ❌ Missing Skills")
                        if result['missing_skills']:
                            for missing in result['missing_skills']:
                                st.markdown(f"- **{missing}**")
                        else:
                            st.write("You hit all the key terms!")

                with st.expander("📈 Actionable Feedback", expanded=True):
                    st.markdown("#### ✍️ Tone & Action Verbs")
                    st.info(result['action_verb_feedback'])
                    
                    st.markdown("#### 💡 Next Steps to Improve")
                    for idx, tip in enumerate(result['improvement_suggestions'], 1):
                        st.markdown(f"**{idx}.** {tip}")
    else:
        if not analyze_button:
            with st.container(border=True):
                st.info("👈 Upload your resume and paste a job description or URL to generate your report.")
