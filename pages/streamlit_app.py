import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

PLATFORM_OPTIONS = {"All": None, "Indeed": "Indeed", "WTTJ": "WTTJ", "LinkedIn": "Linkedin"}
CONTRACT_OPTIONS = {
    "All": None,
    "Full-time": "full_time",
    "Part-time": "part_time",
    "Contractor": "contractor",
    "Temporary": "temporary",
    "Internship": "internship",
    "Other": "other",
}
EXP_LEVEL_OPTIONS = {
    "All": None,
    "Internship": "Internship",
    "Junior": "Junior",
    "Mid": "Mid",
    "Senior": "Senior",
    "Lead": "Lead",
}
PLATFORM_BADGE = {
    "Indeed": "🔵 Indeed",
    "Linkedin": "💼 LinkedIn",
    "Welcome to the jungle": "🌴 WTTJ",
}

# ── Page config ───────────────────────────────────────────────────────────────
st.markdown("<style>.block-container{padding-top:2rem}</style>", unsafe_allow_html=True)


def fetch_jobs(params: dict) -> list[dict]:
    clean = {k: v for k, v in params.items() if v}
    try:
        resp = requests.get(f"{API_URL}/job/", params=clean, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return []


# ── Session state ─────────────────────────────────────────────────────────────
if "jobs" not in st.session_state:
    st.session_state.jobs = []

# ── Centered search area ──────────────────────────────────────────────────────
_, center, _ = st.columns([1, 3, 1])
with center:
    st.markdown("## 🔍 Job Search Assistant")
    kw_col, loc_col = st.columns(2)
    # Explicit keys prevent widget-ID collisions when labels are empty strings
    keyword  = kw_col.text_input("Keyword",   placeholder="Keyword — e.g. data scientist",
                                  label_visibility="collapsed", key="kw_input")
    location = loc_col.text_input("Location", placeholder="Location — e.g. Paris",
                                   label_visibility="collapsed", key="loc_input")

    f1, f2, f3 = st.columns(3)
    platform_label = f1.selectbox("Platform", list(PLATFORM_OPTIONS.keys()),
                                   label_visibility="collapsed", key="platform_input")
    contract_label  = f2.selectbox("Contract",  list(CONTRACT_OPTIONS.keys()),
                                    label_visibility="collapsed", key="contract_input")
    exp_level_label = f3.selectbox("Exp Level", list(EXP_LEVEL_OPTIONS.keys()),
                                    label_visibility="collapsed", key="explevel_input")

    if st.button("Search", use_container_width=True):
        st.session_state.jobs = fetch_jobs({
            "title":    keyword    or None,
            "location": location   or None,
            "platform": PLATFORM_OPTIONS[platform_label],
            "contract": CONTRACT_OPTIONS[contract_label],
            "exp_level": EXP_LEVEL_OPTIONS[exp_level_label],
        })

# ── Job list as dataframe ──────────────────────────────────────────────────────
st.divider()
st.caption(f"Results: {len(st.session_state.jobs)}")

if not st.session_state.jobs:
    st.info("Enter search terms above and click **Search**.")
else:
    rows = []
    for job in st.session_state.jobs:
        platform_val = job.get("platform", "")
        if isinstance(platform_val, dict):
            platform_val = platform_val.get("value", "")
        badge = PLATFORM_BADGE.get(platform_val, platform_val)
        sal = job.get("salary")
        cur = job.get("currency", "") or ""
        salary_str = f"{sal} {cur}".strip() if sal else "—"
        rows.append({
            "Platform": badge,
            "Title": job.get("title", ""),
            "Company": job.get("company", ""),
            "Location": job.get("location", "") or "—",
            "Contract": job.get("contract", "") or "—",
            "Salary": salary_str,
            "Experience": job.get("exp_level", "") or "—",
            "Published": job.get("published_at", "") or "—",
            "Link": job.get("url", ""),
        })

    st.dataframe(
        rows,
        column_config={
            "Link": st.column_config.LinkColumn("Link", display_text="View ↗"),
        },
        use_container_width=True,
        hide_index=True,
    )

# ── Floating chat widget (pure HTML/CSS/JS — no Streamlit state needed) ───────
#
# Design:
#   • Hidden checkbox #chat-cb drives open/close via CSS sibling selector.
#   • The FAB <label> and close ✕ both toggle that checkbox — zero JavaScript.
#   • Message send uses inline onclick with createElement (no <script> block
#     needed, works even though React's dangerouslySetInnerHTML skips <script>).
#   • Because the HTML string never changes between Streamlit reruns, React's
#     virtual-DOM diff leaves the DOM untouched → checkbox state survives search
#     clicks and other reruns.
#
SEND_ONCLICK = (
    "var inp=document.getElementById('chat-input');"
    "var v=inp.value.trim();"
    "if(!v)return;"
    "var m=document.getElementById('chat-msgs');"
    "var ph=m.querySelector('.chat-ph');"
    "if(ph)ph.remove();"
    "var ud=document.createElement('div');"
    "ud.style.cssText='display:flex;justify-content:flex-end;margin:4px 0';"
    "var ub=document.createElement('div');"
    "ub.style.cssText='background:#4F8BF9;color:white;border-radius:12px 12px 2px 12px;"
    "padding:7px 12px;max-width:80%;font-size:13px;word-break:break-word';"
    "ub.textContent=v;"
    "ud.appendChild(ub);m.appendChild(ud);"
    "var bd=document.createElement('div');"
    "bd.style.cssText='display:flex;justify-content:flex-start;margin:4px 0';"
    "var bb=document.createElement('div');"
    "bb.style.cssText='background:#f0f2f6;color:#262730;border-radius:12px 12px 12px 2px;"
    "padding:7px 12px;max-width:80%;font-size:13px';"
    "bb.textContent='Coming soon \U0001F6A7';"
    "bd.appendChild(bb);m.appendChild(bd);"
    "m.scrollTop=m.scrollHeight;inp.value='';"
)

st.markdown(f"""
<style>
  #chat-cb {{ display: none; }}

  /* FAB button */
  .chat-fab {{
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 52px;
    height: 52px;
    border-radius: 50%;
    background: #4F8BF9;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    z-index: 99999;
    font-size: 24px;
    box-shadow: 0 4px 16px rgba(79,139,249,0.5);
    user-select: none;
    transition: transform 0.2s, box-shadow 0.2s;
  }}
  .chat-fab:hover {{
    transform: scale(1.08);
    box-shadow: 0 6px 22px rgba(79,139,249,0.65);
  }}

  /* Panel — hidden by default, shown when checkbox is checked */
  .chat-panel {{
    display: none;
    flex-direction: column;
    position: fixed;
    bottom: 88px;
    right: 24px;
    width: 340px;
    height: 460px;
    background: white;
    border-radius: 16px;
    z-index: 99998;
    box-shadow: 0 8px 32px rgba(0,0,0,0.18);
    overflow: hidden;
  }}
  #chat-cb:checked ~ .chat-panel {{ display: flex; }}

  .chat-header {{
    background: linear-gradient(135deg, #4F8BF9 0%, #6C63FF 100%);
    color: white;
    padding: 14px 16px;
    font-weight: 600;
    font-size: 0.9rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
  }}
  .chat-close {{
    cursor: pointer;
    font-size: 20px;
    line-height: 1;
    opacity: 0.8;
  }}
  .chat-close:hover {{ opacity: 1; }}

  .chat-msgs {{
    flex: 1;
    overflow-y: auto;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}
  .chat-ph {{
    color: #bbb;
    text-align: center;
    font-size: 13px;
    margin-top: 40px;
    line-height: 1.7;
  }}

  .chat-input-row {{
    display: flex;
    padding: 10px 12px;
    gap: 8px;
    border-top: 1px solid #f0f0f0;
    flex-shrink: 0;
    background: #fafafa;
  }}
  .chat-input-row input {{
    flex: 1;
    border: 1px solid #ddd;
    border-radius: 20px;
    padding: 8px 14px;
    font-size: 13px;
    outline: none;
    background: white;
  }}
  .chat-input-row input:focus {{ border-color: #4F8BF9; }}
  .chat-send {{
    background: #4F8BF9;
    color: white;
    border: none;
    border-radius: 50%;
    width: 36px;
    height: 36px;
    min-width: 36px;
    cursor: pointer;
    font-size: 15px;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .chat-send:hover {{ background: #3a7ae8; }}
</style>

<input type="checkbox" id="chat-cb">
<label for="chat-cb" class="chat-fab" title="Chat with AI Assistant">💬</label>

<div class="chat-panel">
  <div class="chat-header">
    <span>🤖 Job Assistant</span>
    <label for="chat-cb" class="chat-close" title="Close">✕</label>
  </div>
  <div class="chat-msgs" id="chat-msgs">
    <div class="chat-ph">👋 Hi! I can help you understand job listings.<br>LLM integration coming soon 🚧</div>
  </div>
  <div class="chat-input-row">
    <input id="chat-input" type="text" placeholder="Ask about a job..."
      onkeydown="if(event.key==='Enter'){{document.getElementById('chat-send-btn').click();}}"/>
    <button id="chat-send-btn" class="chat-send" onclick="{SEND_ONCLICK}">➤</button>
  </div>
</div>
""", unsafe_allow_html=True)
