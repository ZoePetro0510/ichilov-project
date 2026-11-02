"""Demo UI for the API.   Run:  streamlit run ui/streamlit_app.py

Works without an LLM key: the Search tab shows the retrieved passages with
document and page. Ask / Agent tabs need LLM_API_KEY in .env.
"""

import os

import requests
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="עוזר נהלים רפואיים", page_icon="🏥", layout="wide")
st.markdown(
    """<style>
    .stApp, .stMarkdown, .stTextInput, .stTabs {direction: rtl; text-align: right;}
    textarea, input {direction: rtl; text-align: right;}
    </style>""",
    unsafe_allow_html=True,
)

EXAMPLES = [
    "תוך כמה זמן יש לדווח על אירוע חריג?",
    "כמה זמן נמשך חיטוי ידיים בג'ל אלכוהולי?",
    "איזה ציון בסולם מורס מצביע על סיכון גבוה לנפילה?",
    "מה הכללים למתן תרופות בסיכון גבוה?",
]
AGENT_EXAMPLES = [
    "כמה נהלים יש במאגר לפי קטגוריה?",
    "בנה לי צ'קליסט למניעת נפילות",
]


def api(method: str, path: str, **kwargs):
    """Call the API; show a friendly error and return None on failure."""
    try:
        r = requests.request(method, f"{API}{path}", timeout=120, **kwargs)
    except requests.RequestException:
        st.error(f"אין חיבור לשרת ה-API ({API}). הפעל אותו עם ./run_demo.sh")
        return None
    if r.status_code >= 400:
        try:
            st.error(r.json().get("detail", r.text))
        except ValueError:
            st.error(r.text)
        return None
    return r.json()


def example_buttons(examples: list[str], key: str) -> str | None:
    cols = st.columns(len(examples))
    for i, (col, text) in enumerate(zip(cols, examples, strict=True)):
        if col.button(text, key=f"{key}{i}", use_container_width=True):
            return text
    return None


def sources_line(sources: list[dict]) -> str:
    return " · ".join(f"{s['title']} (עמוד {s['page']})" for s in sources)


# ---------- header + status ----------
st.title("🏥 עוזר נהלים רפואיים")
st.caption("דמו הנדסי על מסמכים סינתטיים בלבד. אינו מיועד לקבלת החלטות רפואיות.")

health = None
try:
    health = requests.get(f"{API}/health", timeout=3).json()
except requests.RequestException:
    pass

with st.sidebar:
    st.subheader("סטטוס מערכת")
    if health:
        st.success("שרת API פעיל")
        if health["llm_configured"]:
            st.success("מודל שפה מחובר")
        else:
            st.warning("אין מפתח LLM: חיפוש עובד, שאלות וסוכן דורשים LLM_API_KEY")
    else:
        st.error("שרת API לא מגיב")
    st.divider()
    st.markdown(
        "**איך זה עובד**\n\n"
        "1. PDF ← חילוץ ותיקון עברית\n"
        "2. חיתוך לקטעים ← embeddings\n"
        "3. חיפוש וקטורי ב-pgvector\n"
        "4. LLM עונה עם ציטוט מסמך ועמוד\n"
        "5. סוכן בוחר בין 3 כלים"
    )

tab_search, tab_ask, tab_agent, tab_docs = st.tabs(
    ["🔎 חיפוש בנהלים", "💬 שאלה עם תשובה", "🤖 סוכן", "📄 מסמכים"]
)

with tab_search:
    st.caption("מחזיר את הקטעים הרלוונטיים ביותר מהנהלים, עם ציון דמיון. לא דורש LLM.")
    picked = example_buttons(EXAMPLES, "s")
    q = st.text_input("שאלה", value=picked or "", key="search_q")
    if q:
        hits = api("POST", "/search", json={"question": q, "top_k": 3})
        for h in hits or []:
            with st.container(border=True):
                st.markdown(f"**{h['title']}** · עמוד {h['page']} · דמיון {h['score']:.2f}")
                st.write(h["text"])

with tab_ask:
    picked = example_buttons(EXAMPLES, "a")
    q = st.text_input("שאלה על נוהל", value=picked or "", key="ask_q")
    clicked = st.button("שאל", type="primary", key="ask_btn")
    if q and (clicked or picked):
        with st.spinner("מחפש וכותב תשובה..."):
            out = api("POST", "/ask", json={"question": q})
        if out:
            st.markdown("### תשובה")
            st.write(out["answer"])
            st.caption(f"מקורות: {sources_line(out['sources'])} · {out['latency_ms']} ms")

with tab_agent:
    st.caption("הסוכן בוחר בעצמו כלי: חיפוש בנהלים, SQL על המטא-דאטה, או בניית צ'קליסט.")
    picked = example_buttons(AGENT_EXAMPLES, "g")
    q = st.text_input("בקשה לסוכן", value=picked or "", key="agent_q")
    clicked = st.button("הרץ", type="primary", key="agent_btn")
    if q and (clicked or picked):
        with st.spinner("הסוכן עובד..."):
            out = api("POST", "/agent", json={"question": q})
        if out:
            st.markdown("### תשובה")
            st.write(out["answer"])
            with st.expander(f"צעדי הסוכן ({len(out['steps'])})", expanded=True):
                for s in out["steps"]:
                    st.markdown(f"**{s['step']}. `{s['tool']}`**")
                    st.json(s["input"])
                    st.text(s["output"][:1200])

with tab_docs:
    docs = api("GET", "/documents") or []
    st.dataframe(docs, hide_index=True)
    up = st.file_uploader("העלאת PDF חדש", type="pdf")
    if up and st.button("העלה ועבד", key="upload_btn"):
        out = api(
            "POST",
            "/documents",
            files={"file": (up.name, up.getvalue(), "application/pdf")},
        )
        if out:
            st.success(f"נוסף: {out['title']} ({out['pages']} עמודים, {out['chunks']} קטעים)")
            st.rerun()
