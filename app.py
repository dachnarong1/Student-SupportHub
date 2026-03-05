import streamlit as st
from google import genai
import PyPDF2
import sqlite3
from youtube_transcript_api import YouTubeTranscriptApi
import json
import re
import time

# ------------------ CONFIG ------------------
st.set_page_config(
    page_title="🎓 Intelligent Student Hub",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- STYLE ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap');

* { font-family: 'Prompt', sans-serif; }

/* พื้นหลังหลัก */
.stApp {
    background: linear-gradient(135deg, #0f2027, #203a43, #000000);
    color: white;
}

/* ปุ่มหลัก */
.stButton>button {
    border-radius: 12px;
    background: linear-gradient(90deg, #1e3c72, #2a5298);
    color: white;
    border: none;
    font-weight: 600;
    padding: 0.6rem 1.5rem;
    transition: all 0.3s ease;
    font-size: 0.95rem;
}
.stButton>button:hover {
    background: linear-gradient(90deg, #2a5298, #1e3c72);
    transform: scale(1.03);
    box-shadow: 0 4px 20px rgba(42, 82, 152, 0.5);
}

/* Card */
.card {
    padding: 24px;
    border-radius: 16px;
    background: linear-gradient(145deg, #1b2735, #090a0f);
    box-shadow: 0 0 20px rgba(0, 140, 255, 0.2);
    margin-bottom: 20px;
    border: 1px solid rgba(42, 82, 152, 0.3);
    line-height: 1.8;
}

/* Flashcard */
.flashcard {
    padding: 20px;
    border-radius: 14px;
    background: linear-gradient(145deg, #16222a, #0a0e14);
    border-left: 4px solid #2a5298;
    margin-bottom: 12px;
    transition: all 0.3s ease;
}
.flashcard:hover {
    box-shadow: 0 0 15px rgba(42, 82, 152, 0.4);
    transform: translateX(4px);
}

/* Status badges */
.status-ok {
    background: linear-gradient(90deg, #0d7a3e, #11a34f);
    color: white;
    padding: 8px 16px;
    border-radius: 20px;
    display: inline-block;
    font-weight: 500;
    font-size: 0.9rem;
}
.status-warn {
    background: linear-gradient(90deg, #b8860b, #daa520);
    color: white;
    padding: 8px 16px;
    border-radius: 20px;
    display: inline-block;
    font-weight: 500;
    font-size: 0.9rem;
}
.status-error {
    background: linear-gradient(90deg, #8b0000, #cd3333);
    color: white;
    padding: 8px 16px;
    border-radius: 20px;
    display: inline-block;
    font-weight: 500;
    font-size: 0.9rem;
}

/* hero header */
.hero {
    text-align: center;
    padding: 20px 0;
}
.hero h1 {
    font-size: 2.5rem;
    font-weight: 700;
    background: linear-gradient(90deg, #5dade2, #2a5298, #8e44ad);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
}
.hero p {
    font-size: 1.1rem;
    color: #a0b4c8;
}

/* Content preview */
.content-preview {
    background: rgba(30, 60, 114, 0.15);
    border: 1px solid rgba(42, 82, 152, 0.3);
    padding: 16px;
    border-radius: 12px;
    max-height: 200px;
    overflow-y: auto;
    font-size: 0.85rem;
    color: #c0d0e0;
    line-height: 1.6;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f2027, #000000);
}

/* Tabs */
button[role="tab"] {
    background-color: #16222a !important;
    color: white !important;
    border-radius: 8px 8px 0 0 !important;
    font-weight: 500 !important;
}
button[role="tab"][aria-selected="true"] {
    background: linear-gradient(90deg, #1e3c72, #2a5298) !important;
    color: white !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: rgba(30, 60, 114, 0.2);
    border-radius: 10px;
}

/* Radio */
.stRadio > label { font-weight: 500; }

/* Metric cards */
.metric-card {
    text-align: center;
    padding: 16px;
    border-radius: 12px;
    background: linear-gradient(145deg, #1b2735, #0d1117);
    border: 1px solid rgba(42, 82, 152, 0.2);
}
.metric-card h3 { font-size: 2rem; margin: 0; color: #5dade2; }
.metric-card p { font-size: 0.85rem; color: #a0b4c8; margin: 4px 0 0 0; }
</style>
""", unsafe_allow_html=True)

# ------------------ SIDEBAR: SETTINGS ------------------

st.sidebar.markdown("## ⚙️ ตั้งค่า")

# API Key
api_key = st.sidebar.text_input(
    "🔑 Google Gemini API Key",
    value="",
    type="password",
    placeholder="วาง API Key ของคุณที่นี่...",
    help="สร้าง API Key ฟรีได้ที่ [Google AI Studio](https://aistudio.google.com/apikey)"
)

# Model selection
model_choice = st.sidebar.selectbox(
    "🤖 เลือกโมเดล AI",
    ["gemini-2.0-flash-lite", "gemini-2.0-flash"],
    index=0,
    help="ถ้าหมดโควต้าลองเปลี่ยนโมเดลอื่น"
)

# Language
lang_choice = st.sidebar.selectbox(
    "🌍 ภาษาผลลัพธ์",
    ["ไทย", "English", "ตามเนื้อหาต้นฉบับ"],
    index=0
)

lang_instruction = {
    "ไทย": "ตอบเป็นภาษาไทยเท่านั้น",
    "English": "Answer in English only",
    "ตามเนื้อหาต้นฉบับ": "Answer in the same language as the content"
}[lang_choice]

st.sidebar.divider()

# ------------------ API SETUP ------------------

client = None
api_ready = False
api_valid = False

if api_key:
    try:
        # ทดสอบว่า API Key ใช้งานได้จริงหรือไม่โดยการดึงข้อมูลโมเดล
        test_client = genai.Client(api_key=api_key)
        # ลองดึงข้อมูลโมเดล gemini-2.0-flash-lite เพื่อทดสอบ
        test_client.models.get(model="gemini-2.0-flash-lite")
        client = test_client
        api_ready = True
        api_valid = True
        st.sidebar.markdown('<div class="status-ok">🔑 API Key พร้อมใช้งาน</div>', unsafe_allow_html=True)
    except Exception as e:
        error_msg = str(e)
        if "API key not valid" in error_msg or "400" in error_msg or "403" in error_msg:
             st.sidebar.error("❌ API Key ไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง")
        else:
             st.sidebar.error(f"❌ เกิดข้อผิดพลาดในการตรวจสอบ API Key: {e}")
        api_ready = False
        api_valid = False
else:
    st.sidebar.info("👆 กรุณาใส่ API Key เพื่อเริ่มใช้งาน")

# ------------------ DATABASE ------------------
conn = sqlite3.connect("studyhub.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# ------------------ FUNCTIONS ------------------

def extract_pdf_text(uploaded_file):
    """ดึงข้อความจากไฟล์ PDF"""
    reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text


def extract_youtube_id(url):
    """ดึง Video ID จาก YouTube URL หลายรูปแบบ"""
    patterns = [
        r"youtu\.be/([a-zA-Z0-9_-]+)",
        r"watch\?v=([a-zA-Z0-9_-]+)",
        r"shorts/([a-zA-Z0-9_-]+)",
        r"embed/([a-zA-Z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_youtube_transcript(video_id):
    """ดึง Transcript จาก YouTube"""
    ytt_api = YouTubeTranscriptApi()
    try:
        transcript = ytt_api.fetch(video_id, languages=["th"])
    except Exception:
        try:
            transcript = ytt_api.fetch(video_id, languages=["en"])
        except Exception:
            # ลองดึงภาษาใดก็ได้
            transcript = ytt_api.fetch(video_id)

    text = ""
    for snippet in transcript:
        text += snippet.text + " "
    return text.strip()


def generate_text(prompt):
    """เรียก Gemini API พร้อม fallback โมเดลอัตโนมัติ"""
    if not api_valid:
        st.error("❌ API Key ไม่ถูกต้อง หรือยังไม่ได้ใส่ กรุณาตรวจสอบที่ Sidebar")
        return None

    available_models = ["gemini-2.0-flash-lite", "gemini-2.0-flash"]
    models_to_try = [model_choice] + [m for m in available_models if m != model_choice]

    last_error = None
    
    print(f"--- Requesting generation with prompt length: {len(prompt)} characters ---")
    
    for model_name in models_to_try:
        try:
            print(f"Trying model: {model_name}")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            print(f"Error with model {model_name}: {repr(e)}")
            error_str = str(e).lower()
            last_error = error_str
            if "429" in error_str or "resource_exhausted" in error_str or "quota" in error_str:
                # ลองโมเดลถัดไป
                continue
            elif "400" in error_str or "api key not valid" in error_str or "403" in error_str:
                 st.error("❌ API Key ไม่ถูกต้อง กรุณาตรวจสอบ API Key ของคุณใหม่")
                 return None
            else:
                st.error(f"❌ เกิดข้อผิดพลาดกับโมเดล {model_name}: {e}")
                # อาจจะลอง fallback ก็ได้ แต่ส่วนใหญ่ error อื่นมักจะแก้ไม่ได้ด้วยการเปลี่ยนโมเดล
                continue

    # ถ้ามาถึงตรงนี้แปลว่าเฟลทุกโมเดล ตรวจสอบ error สุดท้ายว่าเกี่ยวกับโควต้าไหม
    if last_error and ("429" in last_error or "resource_exhausted" in last_error or "quota" in last_error):
         if "limit: 0" in last_error or "free_tier" in last_error:
             st.error(
                 "❌ **Google ปิดกั้นโควต้าฟรีสำหรับบัญชี/เครือข่ายนี้ (Limit: 0)**\n\n"
                 "สาเหตุที่เป็นไปได้:\n"
                 "1. Google ไม่เปิดให้ใช้ **ฟรี** ในภูมิภาค/IP ของคุณ (บางเน็ตเวิร์กโดนบล็อค)\n"
                 "2. บัญชี Google Cloud ของคุณอาจต้องผูกบัตรเครดิตก่อนถึงจะได้โควต้าเบื้องต้น\n\n"
                 "💡 **วิธีบรรเทาเบื้องต้น:** ลองต่อเน็ตมือถือ (Hotspot), ใช้บัญชี Google อื่นสร้างคีย์ใหม่ หรือเช็คใน Google AI Studio ว่ามีแจ้งเตือนให้เปิด Billing หรือไม่"
                 f"\n\n*(Technical Details: {last_error})*"
             )
         else:
             st.error(
                "❌ **API Key หมดโควต้าการใช้งานชั่วคราว (Rate Limit Exceeded)**\n\n"
                "💡 **วิธีแก้:** รอสักครู่แล้วลองใหม่\n"
                f"*(Technical Details: {last_error})*"
             )
    else:
         st.error(f"❌ ไม่สามารถสร้างเนื้อหาได้ กรุณาลองใหม่อีกครั้ง (Error: {last_error})")
         
    return None


def clean_json_response(text):
    """ลบ markdown code fences ออกแล้ว parse JSON"""
    if text is None:
        return None
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = cleaned.strip()
    return json.loads(cleaned)


# ==================== MAIN UI ====================

# Hero Header
st.markdown("""
<div class="hero">
    <h1>🎓 Intelligent Student Hub</h1>
    <p>อัปโหลด PDF หรือวาง YouTube URL → AI สร้างสรุป, แบบทดสอบ, และ Flashcard ให้เลย!</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# ------------------ INPUT SECTION ------------------

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📄 อัปโหลด PDF")
    uploaded_pdf = st.file_uploader(
        "เลือกไฟล์ PDF",
        type=["pdf"],
        label_visibility="collapsed",
        help="รองรับไฟล์ PDF ที่มีข้อความ (ไม่รองรับ PDF ที่เป็นรูปภาพ)"
    )

with col2:
    st.markdown("### 🔗 YouTube URL")
    youtube_url = st.text_input(
        "วาง YouTube URL",
        placeholder="https://www.youtube.com/watch?v=...",
        label_visibility="collapsed"
    )

# Process input
content_text = ""

if uploaded_pdf:
    try:
        content_text = extract_pdf_text(uploaded_pdf)
        if content_text.strip():
            st.success(f"✅ โหลด PDF สำเร็จ! ({len(content_text):,} ตัวอักษร)")
        else:
            st.warning("⚠️ PDF นี้ไม่มีข้อความที่อ่านได้ (อาจเป็น PDF สแกน)")
    except Exception as e:
        st.error(f"❌ อ่าน PDF ไม่ได้: {e}")

if youtube_url:
    try:
        video_id = extract_youtube_id(youtube_url)
        if video_id is None:
            st.error("❌ URL ไม่ถูกต้อง กรุณาใส่ YouTube URL")
        else:
            content_text = get_youtube_transcript(video_id)
            st.success(f"✅ โหลด YouTube Transcript สำเร็จ! ({len(content_text):,} ตัวอักษร)")
    except Exception as e:
        st.error(f"❌ ดึง Transcript ไม่ได้: {e}")

if content_text:
    st.session_state["content"] = content_text

# Content Preview
if "content" in st.session_state:
    with st.expander("👁️ ดูตัวอย่างเนื้อหาที่โหลดมา", expanded=False):
        preview = st.session_state["content"][:1000]
        st.markdown(f'<div class="content-preview">{preview}{"..." if len(st.session_state["content"]) > 1000 else ""}</div>', unsafe_allow_html=True)

        # Metrics
        mc1, mc2 = st.columns(2)
        with mc1:
            st.markdown(f'<div class="metric-card"><h3>{len(st.session_state["content"]):,}</h3><p>ตัวอักษร</p></div>', unsafe_allow_html=True)
        with mc2:
            word_count = len(st.session_state["content"].split())
            st.markdown(f'<div class="metric-card"><h3>{word_count:,}</h3><p>คำ</p></div>', unsafe_allow_html=True)

# ==================== STUDY ENGINE ====================

if "content" in st.session_state:

    st.divider()
    st.markdown("## 🧠 Study Engine")

    tab1, tab2, tab3 = st.tabs(["📌 สรุปเนื้อหา", "📝 แบบทดสอบ", "📚 Flashcards"])

    # -------- SUMMARY --------
    with tab1:
        # ถ่ายทอดตรรกะให้ทำงานทันทีเมื่อมีเนื้อหา
        if "summary" not in st.session_state:
            if not api_valid:
                st.warning("⚠️ กรุณาใส่ API Key ที่ใช้งานได้ เพื่อเริ่มสรุปเนื้อหาอัตโนมัติ")
            else:
                with st.spinner("⏳ AI กำลังอ่านและสรุปเนื้อหา..."):
                    prompt = f"""
                    สรุปเนื้อหาต่อไปนี้อย่างกระชับ ชัดเจน เข้าใจง่าย
                    - ใช้หัวข้อย่อยและ bullet points
                    - เน้นประเด็นสำคัญ
                    - {lang_instruction}

                    เนื้อหา:
                    {st.session_state["content"]}
                    """
                    summary = generate_text(prompt)
                    if summary:
                        st.session_state["summary"] = summary
                        st.rerun()

        if "summary" in st.session_state:
            st.markdown(
                f"<div class='card'>{st.session_state['summary']}</div>",
                unsafe_allow_html=True
            )
            
            if st.button("🔄 สร้างสรุปใหม่"):
                 st.session_state.pop("summary", None)
                 st.rerun()

    # -------- QUIZ --------
    with tab2:
        num_questions = st.slider("จำนวนข้อ", min_value=3, max_value=10, value=5)

        if st.button("🎯 สร้างแบบทดสอบ", use_container_width=True):
            if not api_key:
                st.error("❌ กรุณาใส่ API Key ที่ Sidebar ก่อน")
            else:
                with st.spinner("⏳ AI กำลังสร้างแบบทดสอบ..."):
                    quiz_prompt = f"""
                    สร้างแบบทดสอบ {num_questions} ข้อ จากเนื้อหาด้านล่าง
                    ตอบเป็น JSON เท่านั้น ห้ามมี markdown ห้ามมีคำอธิบาย
                    {lang_instruction}

                    รูปแบบ JSON:
                    [
                      {{
                        "question": "คำถาม...",
                        "options": ["A. ตัวเลือก1", "B. ตัวเลือก2", "C. ตัวเลือก3", "D. ตัวเลือก4"],
                        "answer": "A. ตัวเลือก1"
                      }}
                    ]

                    เนื้อหา:
                    {st.session_state["content"]}
                    """
                    quiz_data = generate_text(quiz_prompt)

                    try:
                        parsed = clean_json_response(quiz_data)
                        if parsed:
                            st.session_state["quiz"] = parsed
                            st.session_state["quiz_submitted"] = False
                            st.session_state["quiz_score"] = 0
                            st.rerun()
                    except Exception:
                        st.error("❌ แปลง JSON ไม่สำเร็จ กรุณาลองใหม่")

        if "quiz" in st.session_state:
            for i, q in enumerate(st.session_state["quiz"]):
                st.markdown(f"#### ข้อ {i+1}. {q['question']}")
                st.radio(
                    "เลือกคำตอบ",
                    q["options"],
                    key=f"q{i}",
                    label_visibility="collapsed"
                )
                st.markdown("---")

            col_submit, col_reset = st.columns([1, 1])
            with col_submit:
                if st.button("✅ ส่งคำตอบ", use_container_width=True):
                    score = 0
                    total = len(st.session_state["quiz"])
                    for i, q in enumerate(st.session_state["quiz"]):
                        if st.session_state.get(f"q{i}") == q["answer"]:
                            score += 1
                    st.session_state["quiz_submitted"] = True
                    st.session_state["quiz_score"] = score
                    st.session_state["quiz_total"] = total

            with col_reset:
                if st.button("🔄 สร้างใหม่", use_container_width=True):
                    for key in ["quiz", "quiz_submitted", "quiz_score", "quiz_total"]:
                        st.session_state.pop(key, None)
                    st.rerun()

            if st.session_state.get("quiz_submitted"):
                score = st.session_state["quiz_score"]
                total = st.session_state["quiz_total"]
                pct = (score / total) * 100

                if pct == 100:
                    st.balloons()
                    st.markdown(f'<div class="status-ok">🎉 เยี่ยมมาก! คะแนน: {score}/{total} ({pct:.0f}%)</div>', unsafe_allow_html=True)
                elif pct >= 60:
                    st.markdown(f'<div class="status-ok">👍 ดีมาก! คะแนน: {score}/{total} ({pct:.0f}%)</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="status-warn">📖 คะแนน: {score}/{total} ({pct:.0f}%) — ลองทบทวนเนื้อหาอีกครั้ง</div>', unsafe_allow_html=True)

                # แสดงเฉลย
                with st.expander("📋 ดูเฉลย"):
                    for i, q in enumerate(st.session_state["quiz"]):
                        user_ans = st.session_state.get(f"q{i}", "ไม่ได้ตอบ")
                        correct = q["answer"]
                        icon = "✅" if user_ans == correct else "❌"
                        st.markdown(f"**ข้อ {i+1}.** {icon} คุณตอบ: `{user_ans}` | เฉลย: `{correct}`")

    # -------- FLASHCARDS --------
    with tab3:
        num_cards = st.slider("จำนวน Flashcard", min_value=3, max_value=15, value=5)

        if st.button("🃏 สร้าง Flashcards", use_container_width=True):
            if not api_key:
                st.error("❌ กรุณาใส่ API Key ที่ Sidebar ก่อน")
            else:
                with st.spinner("⏳ AI กำลังสร้าง Flashcards..."):
                    flash_prompt = f"""
                    สร้าง Flashcard {num_cards} ใบ จากเนื้อหาด้านล่าง
                    ด้านหน้าเป็นคำถาม ด้านหลังเป็นคำตอบ
                    ตอบเป็น JSON เท่านั้น ห้ามมี markdown
                    {lang_instruction}

                    รูปแบบ:
                    [{{"question": "...", "answer": "..."}}]

                    เนื้อหา:
                    {st.session_state["content"]}
                    """
                    flash_data = generate_text(flash_prompt)

                    try:
                        parsed = clean_json_response(flash_data)
                        if parsed:
                            st.session_state["flashcards"] = parsed
                    except Exception:
                        st.error("❌ สร้าง Flashcard ไม่สำเร็จ กรุณาลองใหม่")

        if "flashcards" in st.session_state:
            for i, card in enumerate(st.session_state["flashcards"]):
                st.markdown(f"""
                <div class="flashcard">
                    <strong>🃏 {card['question']}</strong>
                </div>
                """, unsafe_allow_html=True)
                with st.expander(f"👀 เปิดดูคำตอบ ข้อ {i+1}"):
                    st.markdown(card["answer"])

# ==================== CHAT ====================

st.sidebar.divider()
st.sidebar.markdown("## 💬 ถาม-ตอบกับเนื้อหา")

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

question = st.sidebar.text_input(
    "พิมพ์คำถามของคุณ",
    placeholder="ถามอะไรก็ได้เกี่ยวกับเนื้อหา...",
    label_visibility="collapsed"
)

if question and "content" in st.session_state:
    if not api_key:
        st.sidebar.error("❌ ใส่ API Key ก่อน")
    else:
        with st.sidebar:
            with st.spinner("🤔 กำลังคิด..."):
                chat_prompt = f"""
                ตอบคำถามโดยอ้างอิงจากเนื้อหานี้เท่านั้น
                ถ้าคำถามไม่เกี่ยวกับเนื้อหา ให้แจ้งว่าไม่เกี่ยวข้อง
                ตอบกระชับ ชัดเจน
                {lang_instruction}

                เนื้อหา:
                {st.session_state["content"]}

                คำถาม:
                {question}
                """
                answer = generate_text(chat_prompt)
                if answer:
                    st.session_state["chat_history"].append(("🧑 คุณ", question))
                    st.session_state["chat_history"].append(("🤖 AI", answer))
elif question and "content" not in st.session_state:
    st.sidebar.warning("⚠️ กรุณาอัปโหลดเนื้อหาก่อน")

# แสดงประวัติแชท
for role, msg in st.session_state["chat_history"]:
    st.sidebar.markdown(f"**{role}:** {msg}")

if st.sidebar.button("🗑️ ล้างประวัติแชท"):
    st.session_state["chat_history"] = []
    st.rerun()

# ==================== FOOTER / NO CONTENT ====================

if "content" not in st.session_state:
    st.markdown("---")
    st.markdown("""
    <div style="text-align:center; padding: 40px 0; color: #6c8ea4;">
        <h2>👆 เริ่มต้นใช้งาน</h2>
        <p style="font-size: 1.1rem;">1. ใส่ API Key ที่ Sidebar (ซ้ายมือ)</p>
        <p style="font-size: 1.1rem;">2. อัปโหลด PDF หรือวาง YouTube URL</p>
        <p style="font-size: 1.1rem;">3. ให้ AI สร้างสรุป, แบบทดสอบ, และ Flashcards!</p>
    </div>
    """, unsafe_allow_html=True)
