import streamlit as st

st.set_page_config(page_title="Job Search Assistant", layout="wide")

pages = {
    "Job Search": [
        st.Page("pages/streamlit_app.py", title="Job Dashboard", icon="🔍"),
    ],
    "AI Tools": [
        st.Page("pages/cv_generator.py", title="CV Generator", icon="📄"),
    ],
}

pg = st.navigation(pages)
pg.run()
