import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.title("📄 CV & Motivation Letter Generator")
st.caption("Select a job, fill in your profile, and generate a tailored CV and motivation letter.")

# --- Step 1: Job selection ---
st.subheader("1. Select a job")

@st.cache_data(ttl=60)
def fetch_jobs():
    try:
        resp = requests.get(f"{API_URL}/job/", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Could not fetch jobs: {e}")
        return []

jobs = fetch_jobs()

if not jobs:
    st.warning("No jobs found. Run a crawler first to populate the database.")
    st.stop()

job_options = {
    f"{j['title']} — {j['company']} ({j['platform']})": j["id"]
    for j in jobs
}

selected_label = st.selectbox("Choose a job posting:", list(job_options.keys()))
selected_job_id = job_options[selected_label]
selected_job = next(j for j in jobs if j["id"] == selected_job_id)

with st.expander("View job details"):
    st.markdown(f"**{selected_job['title']}** at **{selected_job['company']}**")
    st.markdown(f"📍 {selected_job.get('location', 'N/A')} | 🎯 {selected_job.get('exp_level', 'N/A')} | 📋 {selected_job.get('contract', 'N/A')}")
    if selected_job.get("job_desc"):
        st.markdown("**Description:**")
        st.text(selected_job["job_desc"][:800] + ("..." if len(selected_job.get("job_desc", "")) > 800 else ""))

st.divider()

# --- Step 2: Profile form ---
st.subheader("2. Your profile")

with st.form("profile_form"):
    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("Full name *", placeholder="Alice Dupont")
        gender = st.radio("Gender *", ["Homme", "Femme", "Autre"], horizontal=True)
        email = st.text_input("Email *", placeholder="alice@example.com")
        phone = st.text_input("Phone", placeholder="+33 6 12 34 56 78")
        languages = st.text_input("Languages spoken", placeholder="Français (natif), Anglais (C1)")

    with col2:
        skills = st.text_area(
            "Skills *",
            placeholder="Python, SQL, Docker, Machine Learning, ...",
            height=100,
        )
        education = st.text_area(
            "Education *",
            placeholder="Master Data Science — Université Paris Saclay, 2023\nBachelor Informatique — ...",
            height=100,
        )

    experience = st.text_area(
        "Work experience *",
        placeholder="Data Analyst @ Company X (2022–2024): Built dashboards, automated reporting pipelines...\nIntern @ Company Y (2021): ...",
        height=120,
    )

    projects = st.text_area(
        "Projects",
        placeholder="Auto Job Apply Agent: Web crawler + Streamlit dashboard for job search (Python, FastAPI, PostgreSQL)\nSentiment Analysis Tool: ...",
        height=120,
    )

    submitted = st.form_submit_button("🚀 Generate CV & Motivation Letter", use_container_width=True)

# --- Step 3: Generation ---
if submitted:
    if not all([name, email, skills, experience, education]):
        st.error("Please fill in all required fields (marked with *).")
        st.stop()

    payload = {
        "job_id": selected_job_id,
        "user_profile": {
            "name": name,
            "gender": gender,
            "email": email,
            "phone": phone,
            "skills": skills,
            "experience": experience,
            "projects": projects,
            "education": education,
            "languages": languages,
        },
    }

    with st.spinner("Generating your CV and motivation letter... This may take 30–60 seconds."):
        try:
            resp = requests.post(
                f"{API_URL}/agent/generate",
                json=payload,
                timeout=660,
            )
            resp.raise_for_status()
            result = resp.json()
        except requests.exceptions.Timeout:
            st.error("The request timed out. The model may still be loading — please try again in a moment.")
            st.stop()
        except Exception as e:
            st.error(f"Generation failed: {e}")
            st.stop()

    st.success("Done! Your documents are ready below.")
    st.divider()

    from markdown_it import MarkdownIt
    _md = MarkdownIt()

    def render_document(html_body: str, accent: str = "#2c5f8a") -> str:
        return f"""
<style>
  body {{ margin: 0; padding: 8px; background: #f5f5f5; }}
  .doc {{
    background: white; padding: 36px 44px; max-width: 100%;
    box-shadow: 0 4px 20px rgba(0,0,0,0.10); border-radius: 6px;
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 13.5px; line-height: 1.7; color: #1a1a1a;
  }}
  h1 {{ font-size: 1.55em; color: {accent}; border-bottom: 2px solid {accent}; padding-bottom: 4px; margin-bottom: 6px; }}
  h2 {{ font-size: 1.1em; color: {accent}; border-bottom: 1px solid #dde; padding-bottom: 2px; margin-top: 16px; }}
  h3 {{ font-size: 1em; color: #333; margin-top: 10px; }}
  ul  {{ padding-left: 18px; margin: 4px 0; }}
  li  {{ margin-bottom: 2px; }}
  hr  {{ border: none; border-top: 1px solid #ddd; margin: 12px 0; }}
  strong {{ color: #111; }}
  p   {{ margin: 5px 0; }}
</style>
<div class="doc">{html_body}</div>"""

    col_cv, col_letter = st.columns(2)

    with col_cv:
        st.subheader("📋 CV")
        st.html(render_document(_md.render(result["cv_markdown"])))
        with st.expander("Raw markdown"):
            st.code(result["cv_markdown"], language="markdown")
        st.download_button("⬇ Download CV (.md)", result["cv_markdown"],
                           file_name="cv.md", mime="text/markdown", use_container_width=True)

    with col_letter:
        st.subheader("✉️ Motivation Letter")
        st.html(render_document(_md.render(result["letter_markdown"]), accent="#5a3e8a"))
        with st.expander("Raw markdown"):
            st.code(result["letter_markdown"], language="markdown")
        st.download_button("⬇ Download Letter (.md)", result["letter_markdown"],
                           file_name="motivation_letter.md", mime="text/markdown", use_container_width=True)
