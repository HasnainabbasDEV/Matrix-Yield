import streamlit as st
import pandas as pd
import os
import json
import re
import io
import base64
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Matrix Yield",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Gemini setup ───────────────────────────────────────────────────────────────
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    GEMINI_MODEL = genai.GenerativeModel("gemini-1.5-flash")
except Exception:
    GEMINI_MODEL = None

# ── Constants ──────────────────────────────────────────────────────────────────
USERS_FILE = "users.csv"
DISCLAIMER = (
    "DISCLAIMER: Matrix Yield is an AI tool for educational purposes. "
    "Trading involves risk. 100% accuracy is not guaranteed."
)
TOPIC_GUARD = (
    "I'm here only to help you with your chart, "
    "is there any chart to analyze?"
)

# ── Session defaults ───────────────────────────────────────────────────────────
for key, default in {
    "logged_in": False,
    "username": "",
    "email": "",
    "show_signup": False,
    "show_logout": False,
    "chat_history": [],
    "pending_image": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── User persistence helpers ───────────────────────────────────────────────────
def load_users() -> pd.DataFrame:
    if os.path.exists(USERS_FILE):
        return pd.read_csv(USERS_FILE)
    return pd.DataFrame(columns=["email", "password", "username"])


def save_user(email: str, password: str, username: str) -> bool:
    """Returns False if email already registered."""
    df = load_users()
    if email in df["email"].values:
        return False
    new_row = pd.DataFrame([{"email": email, "password": password, "username": username}])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(USERS_FILE, index=False)
    return True


def authenticate(email: str, password: str):
    """Returns username on success, None on failure."""
    df = load_users()
    match = df[(df["email"] == email) & (df["password"] == password)]
    if not match.empty:
        return match.iloc[0]["username"]
    return None

# ── Gemini helpers ─────────────────────────────────────────────────────────────
TRADING_KEYWORDS = [
    "chart", "price", "trade", "trading", "market", "buy", "sell",
    "stock", "forex", "crypto", "bitcoin", "support", "resistance",
    "trend", "candle", "candlestick", "analysis", "breakout", "signal",
    "indicator", "moving average", "rsi", "macd", "ema", "sma", "volume",
    "fibonacci", "pivot", "bullish", "bearish", "long", "short",
    "stop loss", "take profit", "entry", "exit", "higher high", "lower low",
    "higher low", "lower high", "bos", "break of structure", "swing",
    "pattern", "flag", "wedge", "triangle", "head and shoulders",
    "double top", "double bottom", "pump", "dump", "rally", "correction",
    "invest", "investment", "asset", "equity", "futures", "options",
    "leverage", "margin", "pip", "lot", "spread", "liquidity",
]

def is_trading_related(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in TRADING_KEYWORDS)


def ask_gemini_text(prompt: str) -> str:
    if GEMINI_MODEL is None:
        return "⚠️ Gemini API not configured. Add GEMINI_API_KEY to secrets."
    try:
        response = GEMINI_MODEL.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Gemini error: {e}"


def ask_gemini_with_image(image: Image.Image, extra_prompt: str = "") -> dict:
    """
    Sends chart image to Gemini and asks for structured analysis.
    Returns a dict with keys: points, suggestion, stop_loss, take_profit, raw.
    """
    if GEMINI_MODEL is None:
        return {"raw": "⚠️ Gemini API not configured.", "points": [], "suggestion": "", "stop_loss": "", "take_profit": ""}

    system_prompt = f"""You are an expert technical analysis AI.
Analyze the provided trading chart image and return a JSON object with this exact schema:

{{
  "points": [
    {{
      "label": "HH" | "HL" | "LH" | "LL" | "BOS",
      "x_pct": <float 0-100>,
      "y_pct": <float 0-100>,
      "description": "<brief explanation>"
    }}
  ],
  "suggestion": "Buy" | "Sell",
  "stop_loss": "<price or level>",
  "take_profit": "<price or level>",
  "summary": "<2-3 sentence analysis>"
}}

Label definitions:
- HH = Higher High (price peak higher than previous peak)
- HL = Higher Low (price trough higher than previous trough)
- LH = Lower High (price peak lower than previous peak)
- LL = Lower Low (price trough lower than previous trough)
- BOS = Break of Structure (significant level where structure broke)

x_pct and y_pct are percentage positions from the top-left corner of the image.
{f'Extra context: {extra_prompt}' if extra_prompt else ''}

Respond ONLY with valid JSON. No markdown, no explanation outside JSON."""

    try:
        response = GEMINI_MODEL.generate_content([system_prompt, image])
        raw_text = response.text.strip()

        # Strip markdown code fences if present
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

        data = json.loads(raw_text)
        data["raw"] = raw_text
        return data
    except json.JSONDecodeError:
        return {
            "raw": response.text if "response" in dir() else "Parse error",
            "points": [],
            "suggestion": "N/A",
            "stop_loss": "N/A",
            "take_profit": "N/A",
            "summary": "Could not parse structured response.",
        }
    except Exception as e:
        return {"raw": str(e), "points": [], "suggestion": "N/A", "stop_loss": "N/A", "take_profit": "N/A", "summary": str(e)}

# ── Chart annotation ───────────────────────────────────────────────────────────
LABEL_COLORS = {
    "HH":  "#00E676",   # green
    "HL":  "#69F0AE",   # light green
    "LH":  "#FF5252",   # red
    "LL":  "#FF1744",   # deep red
    "BOS": "#FFEB3B",   # yellow
}

def annotate_chart(image: Image.Image, points: list) -> Image.Image:
    """Draw labels onto a copy of the chart image."""
    img = image.copy().convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except Exception:
        font = ImageFont.load_default()

    w, h = img.size
    for pt in points:
        label = pt.get("label", "?")
        x = int(pt.get("x_pct", 50) / 100 * w)
        y = int(pt.get("y_pct", 50) / 100 * h)
        color_hex = LABEL_COLORS.get(label, "#FFFFFF")

        # Convert hex to RGBA
        r = int(color_hex[1:3], 16)
        g = int(color_hex[3:5], 16)
        b = int(color_hex[5:7], 16)
        color = (r, g, b, 255)
        bg_color = (r, g, b, 80)

        # Dot
        draw.ellipse([x - 6, y - 6, x + 6, y + 6], fill=color)

        # Background pill for text
        bbox = draw.textbbox((x + 10, y - 10), label, font=font)
        pad = 4
        draw.rounded_rectangle(
            [bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad],
            radius=6,
            fill=bg_color,
        )
        draw.text((x + 10, y - 10), label, fill=color, font=font)

    combined = Image.alpha_composite(img, overlay)
    return combined.convert("RGB")

# ── CSS ────────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown(
        """
        <style>
        /* ── Global / reset ───────────────────────────────────── */
        @import url('[fonts.googleapis.com](https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap)');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            background-color: #0A0A0F;
            color: #E8E8F0;
        }
        .stApp { background-color: #0A0A0F; }
        #MainMenu, footer, header { visibility: hidden; }
        .block-container { padding: 0 !important; max-width: 100% !important; }

        /* ── Scrollbar ────────────────────────────────────────── */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0A0A0F; }
        ::-webkit-scrollbar-thumb { background: #2A2A3E; border-radius: 3px; }

        /* ── Landing page ─────────────────────────────────────── */
        .landing-wrapper {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: radial-gradient(ellipse at 50% 0%, #1a1a3e 0%, #0A0A0F 70%);
        }
        .landing-title {
            font-size: 3rem;
            font-weight: 800;
            background: linear-gradient(135deg, #FFFFFF 0%, #A0A8FF 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 2.5rem;
            text-align: center;
            letter-spacing: -0.5px;
        }
        .login-box {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 20px;
            padding: 2.5rem 3rem;
            width: 100%;
            max-width: 420px;
            backdrop-filter: blur(20px);
            box-shadow: 0 8px 40px rgba(0,0,0,0.4);
        }
        .signin-link {
            color: #4D8FFF;
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            text-decoration: none;
            transition: color 0.2s;
        }
        .signin-link:hover { color: #7EB0FF; text-decoration: underline; }

        /* ── Input fields ─────────────────────────────────────── */
        .stTextInput > div > div > input {
            background: rgba(255,255,255,0.05) !important;
            border: 1px solid rgba(255,255,255,0.15) !important;
            border-radius: 10px !important;
            color: #E8E8F0 !important;
            padding: 0.65rem 1rem !important;
            font-size: 0.95rem !important;
            transition: border-color 0.2s !important;
        }
        .stTextInput > div > div > input:focus {
            border-color: #4D8FFF !important;
            box-shadow: 0 0 0 3px rgba(77,143,255,0.15) !important;
        }
        .stTextInput > div > div > input::placeholder { color: rgba(255,255,255,0.35) !important; }
        .stTextInput label { color: rgba(255,255,255,0.7) !important; font-size: 0.88rem !important; margin-bottom: 4px !important; }

        /* ── Buttons ──────────────────────────────────────────── */
        .stButton > button {
            background: linear-gradient(135deg, #4D8FFF 0%, #7B5EA7 100%) !important;
            color: #fff !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            padding: 0.65rem 2rem !important;
            transition: all 0.25s ease !important;
            cursor: pointer !important;
            width: 100% !important;
        }
        .stButton > button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 20px rgba(77,143,255,0.35) !important;
        }

        /* Signup button (white solid) */
        .signup-btn > button {
            background: #FFFFFF !important;
            color: #0A0A0F !important;
            border-radius: 12px !important;
        }
        .signup-btn > button:hover {
            background: #E8E8F0 !important;
            box-shadow: 0 6px 20px rgba(255,255,255,0.2) !important;
        }

        /* Send button */
        .send-btn > button {
            background: linear-gradient(135deg, #4D8FFF, #7B5EA7) !important;
            border-radius: 50% !important;
            width: 46px !important;
            height: 46px !important;
            padding: 0 !important;
            font-size: 1.2rem !important;
            min-width: unset !important;
        }

        /* ── Top navbar ───────────────────────────────────────── */
        .topbar {
            position: fixed;
            top: 0; left: 0; right: 0;
            z-index: 1000;
            background: rgba(10,10,15,0.85);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid rgba(255,255,255,0.07);
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding: 0.75rem 2rem;
            gap: 0.85rem;
        }
        .topbar-brand {
            font-size: 1.15rem;
            font-weight: 700;
            background: linear-gradient(135deg, #FFFFFF, #A0A8FF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .avatar {
            width: 38px; height: 38px;
            border-radius: 50%;
            background: linear-gradient(135deg, #4D8FFF 0%, #7B5EA7 100%);
            display: flex; align-items: center; justify-content: center;
            font-size: 1rem; font-weight: 700; color: #fff;
            cursor: pointer;
            border: 2px solid rgba(255,255,255,0.15);
            transition: border-color 0.2s;
        }
        .avatar:hover { border-color: rgba(255,255,255,0.4); }

        /* ── Chat area ────────────────────────────────────────── */
        .chat-container {
            padding-top: 70px;
            padding-bottom: 130px;
            max-width: 760px;
            margin: 0 auto;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .chat-welcome {
            text-align: center;
            margin-top: 6rem;
        }
        .chat-welcome h2 {
            font-size: 2rem; font-weight: 700;
            background: linear-gradient(135deg, #FFFFFF, #A0A8FF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .chat-welcome p {
            color: rgba(255,255,255,0.45);
            font-size: 0.95rem;
            margin-top: 0.5rem;
        }

        /* Message bubbles */
        .msg-user {
            display: flex; justify-content: flex-end; margin: 0.6rem 0;
        }
        .msg-user .bubble {
            background: linear-gradient(135deg, #4D8FFF 0%, #7B5EA7 100%);
            color: #fff;
            border-radius: 18px 18px 4px 18px;
            padding: 0.75rem 1.1rem;
            max-width: 70%;
            font-size: 0.95rem;
            line-height: 1.5;
            box-shadow: 0 2px 12px rgba(77,143,255,0.25);
        }
        .msg-ai {
            display: flex; justify-content: flex-start; margin: 0.6rem 0;
        }
        .msg-ai .bubble {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.10);
            color: #E8E8F0;
            border-radius: 18px 18px 18px 4px;
            padding: 0.75rem 1.1rem;
            max-width: 80%;
            font-size: 0.95rem;
            line-height: 1.6;
        }

        /* ── Input bar ────────────────────────────────────────── */
        .input-bar-wrapper {
            position: fixed;
            bottom: 48px; left: 0; right: 0;
            z-index: 900;
            display: flex;
            justify-content: center;
            padding: 0 1rem;
        }
        .input-bar {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 50px;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.35rem 0.35rem 0.35rem 0.75rem;
            width: 100%;
            max-width: 760px;
            backdrop-filter: blur(20px);
            box-shadow: 0 4px 24px rgba(0,0,0,0.35);
        }

        /* ── Footer disclaimer ────────────────────────────────── */
        .footer-disclaimer {
            position: fixed;
            bottom: 0; left: 0; right: 0;
            background: rgba(10,10,15,0.9);
            text-align: center;
            padding: 6px 1rem;
            font-size: 0.7rem;
            color: rgba(255,255,255,0.28);
            border-top: 1px solid rgba(255,255,255,0.05);
            z-index: 800;
        }

        /* ── Modal overlay ────────────────────────────────────── */
        .modal-overlay {
            position: fixed; inset: 0;
            background: rgba(0,0,0,0.65);
            z-index: 2000;
            display: flex; align-items: center; justify-content: center;
        }
        .modal-box {
            background: #13131F;
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 20px;
            padding: 2.5rem;
            width: 100%; max-width: 400px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.6);
        }
        .modal-title {
            font-size: 1.4rem; font-weight: 700;
            color: #E8E8F0; margin-bottom: 1.5rem;
        }

        /* ── Analysis card ────────────────────────────────────── */
        .analysis-card {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 14px;
            padding: 1.2rem 1.4rem;
            margin-top: 1rem;
        }
        .pill {
            display: inline-block;
            padding: 0.3rem 1rem;
            border-radius: 50px;
            font-weight: 700;
            font-size: 0.95rem;
            margin-right: 0.5rem;
        }
        .pill-buy  { background: rgba(0,230,118,0.15); color: #00E676; border: 1px solid #00E676; }
        .pill-sell { background: rgba(255,82,82,0.15);  color: #FF5252; border: 1px solid #FF5252; }

        /* ── File uploader ────────────────────────────────────── */
        [data-testid="stFileUploader"] {
            background: rgba(255,255,255,0.04) !important;
            border: 1px dashed rgba(255,255,255,0.15) !important;
            border-radius: 12px !important;
        }
        [data-testid="stFileUploader"] label { color: rgba(255,255,255,0.6) !important; }

        /* ── Expander ─────────────────────────────────────────── */
        .streamlit-expanderHeader {
            background: rgba(255,255,255,0.04) !important;
            border-radius: 10px !important;
            color: rgba(255,255,255,0.7) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# PAGES
# ══════════════════════════════════════════════════════════════════════════════

# ── LANDING PAGE ──────────────────────────────────────────────────────────────
def landing_page():
    inject_css()

    # ── Signup modal (rendered on top via st.form inside expander trick) ──────
    if st.session_state.show_signup:
        st.markdown(
            """
            <div class="modal-overlay">
                <div class="modal-box" id="signup-modal">
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<p class="modal-title">Make an Account</p>', unsafe_allow_html=True)
        with st.form("signup_form"):
            su_email = st.text_input("Email", placeholder="you@example.com", key="su_email")
            su_password = st.text_input("Create a Password", type="password", placeholder="Min 6 characters", key="su_password")
            su_username = st.text_input("Username", placeholder="e.g. Dream079", key="su_username")

            col_a, col_b = st.columns([1, 1])
            with col_a:
                with st.container():
                    st.markdown('<div class="signup-btn">', unsafe_allow_html=True)
                    submitted = st.form_submit_button("Sign Up")
                    st.markdown("</div>", unsafe_allow_html=True)
            with col_b:
                cancel = st.form_submit_button("Cancel")

            if submitted:
                if not su_email or not su_password or not su_username:
                    st.error("All fields are required.")
                elif len(su_password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    ok = save_user(su_email.strip(), su_password, su_username.strip())
                    if ok:
                        st.success(f"Account created! Welcome, {su_username}. Please sign in.")
                        st.session_state.show_signup = False
                        st.rerun()
                    else:
                        st.error("An account with this email already exists.")
            if cancel:
                st.session_state.show_signup = False
                st.rerun()

        st.markdown("</div></div>", unsafe_allow_html=True)
        return  # Don't render login form behind modal

    # ── Login form ─────────────────────────────────────────────────────────────
    st.markdown('<div class="landing-wrapper">', unsafe_allow_html=True)
    st.markdown('<p class="landing-title">Welcome To Matrix Yield</p>', unsafe_allow_html=True)
    st.markdown('<div class="login-box">', unsafe_allow_html=True)

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@example.com", key="login_email")
        password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password")

        st.markdown("<br>", unsafe_allow_html=True)
        login_btn = st.form_submit_button("Sign In →")

        if login_btn:
            username = authenticate(email.strip(), password)
            if username:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.email = email.strip()
                st.session_state.chat_history = []
                st.rerun()
            else:
                st.error("Invalid email or password.")

    # "Don't have an account? Sign In" link
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "Don't have an account? "
        "<a class='signin-link' id='open-signup'>Sign In</a>",
        unsafe_allow_html=True,
    )
    if st.button("Create Account →", key="open_signup_btn"):
        st.session_state.show_signup = True
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)  # login-box
    st.markdown("</div>", unsafe_allow_html=True)  # landing-wrapper

    st.markdown(f'<div class="footer-disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)


# ── MAIN APP ──────────────────────────────────────────────────────────────────
def main_app():
    inject_css()

    username = st.session_state.username
    avatar_letter = username[0].upper() if username else "U"

    # ── Topbar ─────────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="topbar">
            <span class="topbar-brand">Matrix Yield</span>
            <div class="avatar" title="Logout">{avatar_letter}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Since HTML elements can't directly call Python, we use a button hidden
    # inside a styled container in the sidebar as the logout trigger.
    with st.sidebar:
        st.markdown(f"**Logged in as:** {username}")
        st.markdown("---")
        if st.button("🔓 Logout", key="logout_sidebar"):
            st.session_state.show_logout = True
            st.rerun()

    # ── Logout modal ────────────────────────────────────────────────────────────
    if st.session_state.show_logout:
        st.markdown(
            """
            <div class="modal-overlay">
                <div class="modal-box">
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<p class="modal-title">Logout?</p>', unsafe_allow_html=True)
        st.markdown(
            f"<p style='color:rgba(255,255,255,0.55);margin-bottom:1.5rem;'>"
            f"Are you sure you want to logout, <strong>{username}</strong>?</p>",
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Logout", key="confirm_logout"):
                for k in ["logged_in", "username", "email", "chat_history", "pending_image", "show_logout"]:
                    st.session_state[k] = False if isinstance(st.session_state[k], bool) else (
                        "" if isinstance(st.session_state[k], str) else
                        [] if isinstance(st.session_state[k], list) else None
                    )
                st.session_state.logged_in = False
                st.session_state.show_logout = False
                st.rerun()
        with col2:
            if st.button("Cancel", key="cancel_logout"):
                st.session_state.show_logout = False
                st.rerun()
        st.markdown("</div></div>", unsafe_allow_html=True)
        st.markdown(f'<div class="footer-disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)
        return

    # ── Chat history ────────────────────────────────────────────────────────────
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)

    if not st.session_state.chat_history:
        st.markdown(
            f"""
            <div class="chat-welcome">
                <h2>Hello, {username} 👋</h2>
                <p>Upload a trading chart or ask me anything about the markets.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for msg in st.session_state.chat_history:
            role = msg["role"]
            content = msg.get("content", "")
            if role == "user":
                if content:
                    st.markdown(
                        f'<div class="msg-user"><div class="bubble">{content}</div></div>',
                        unsafe_allow_html=True,
                    )
                if msg.get("image"):
                    img_b64 = msg["image"]
                    st.markdown(
                        f'<div class="msg-user">'
                        f'<img src="data:image/png;base64,{img_b64}" '
                        f'style="max-width:320px;border-radius:14px;border:1px solid rgba(255,255,255,0.1);">'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                # AI message
                if msg.get("annotated_image"):
                    img_b64 = msg["annotated_image"]
                    st.markdown(
                        f'<div class="msg-ai">'
                        f'<img src="data:image/png;base64,{img_b64}" '
                        f'style="max-width:520px;border-radius:14px;border:1px solid rgba(255,255,255,0.1);margin-bottom:0.5rem;">'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                if content:
                    st.markdown(
                        f'<div class="msg-ai"><div class="bubble">{content}</div></div>',
                        unsafe_allow_html=True,
                    )
                if msg.get("analysis"):
                    _render_analysis_card(msg["analysis"])

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Input bar ───────────────────────────────────────────────────────────────
    st.markdown('<div class="input-bar-wrapper"><div class="input-bar">', unsafe_allow_html=True)

    col_plus, col_input, col_send = st.columns([0.06, 0.88, 0.06])

    with col_plus:
        show_uploader = st.button("＋", key="toggle_upload", help="Upload chart image")
        if show_uploader:
            st.session_state["uploader_open"] = not st.session_state.get("uploader_open", False)
            st.rerun()

    with col_input:
        user_text = st.text_input(
            label="",
            placeholder="Type...",
            key="chat_input",
            label_visibility="collapsed",
        )

    with col_send:
        st.markdown('<div class="send-btn">', unsafe_allow_html=True)
        send_clicked = st.button("➤", key="send_btn", help="Send")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    # ── File uploader (shown when + clicked) ───────────────────────────────────
    uploaded_file = None
    if st.session_state.get("uploader_open", False):
        with st.container():
            st.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader(
                "Upload a chart image (.jpg or .png)",
                type=["jpg", "jpeg", "png"],
                key="file_uploader",
            )
            if uploaded_file:
                st.session_state.pending_image = uploaded_file.read()
                st.session_state["uploader_open"] = False
                st.success("Chart ready — now type a message or just send to analyze.")
                st.rerun()

    # ── Process send ───────────────────────────────────────────────────────────
    if send_clicked or (user_text and user_text.endswith("\n")):
        _process_message(user_text.strip())

    st.markdown(f'<div class="footer-disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)


def _render_analysis_card(analysis: dict):
    suggestion = analysis.get("suggestion", "N/A")
    stop_loss = analysis.get("stop_loss", "N/A")
    take_profit = analysis.get("take_profit", "N/A")
    summary = analysis.get("summary", "")

    pill_class = "pill-buy" if suggestion.lower() == "buy" else "pill-sell"
    emoji = "🟢" if suggestion.lower() == "buy" else "🔴"

    st.markdown(
        f"""
        <div class="analysis-card">
            <div style="margin-bottom:0.8rem;">
                <span class="pill {pill_class}">{emoji} {suggestion.upper()}</span>
                <span style="color:rgba(255,255,255,0.5);font-size:0.85rem;">Suggested Signal</span>
            </div>
            <div style="display:flex;gap:2rem;margin-bottom:0.8rem;">
                <div>
                    <div style="color:rgba(255,255,255,0.4);font-size:0.78rem;margin-bottom:2px;">STOP LOSS</div>
                    <div style="color:#FF5252;font-weight:600;">{stop_loss}</div>
                </div>
                <div>
                    <div style="color:rgba(255,255,255,0.4);font-size:0.78rem;margin-bottom:2px;">TAKE PROFIT</div>
                    <div style="color:#00E676;font-weight:600;">{take_profit}</div>
                </div>
            </div>
            {f'<div style="color:rgba(255,255,255,0.65);font-size:0.88rem;line-height:1.6;border-top:1px solid rgba(255,255,255,0.07);padding-top:0.8rem;">{summary}</div>' if summary else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _img_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _bytes_to_b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


def _process_message(user_text: str):
    pending_img_bytes = st.session_state.pending_image

    # Build user message record
    user_msg: dict = {"role": "user", "content": user_text}

    if pending_img_bytes:
        user_msg["image"] = _bytes_to_b64(pending_img_bytes)
        st.session_state.pending_image = None

    st.session_state.chat_history.append(user_msg)

    # ── Branch: image analysis ─────────────────────────────────────────────────
    if pending_img_bytes:
        image = Image.open(io.BytesIO(pending_img_bytes))
        with st.spinner("Analyzing chart with Gemini..."):
            analysis = ask_gemini_with_image(image, extra_prompt=user_text)

        if analysis.get("points"):
            annotated = annotate_chart(image, analysis["points"])
            annotated_b64 = _img_to_b64(annotated)
        else:
            annotated_b64 = _bytes_to_b64(pending_img_bytes)

        ai_msg = {
            "role": "ai",
            "content": "Here's my analysis of your chart:",
            "annotated_image": annotated_b64,
            "analysis": analysis,
        }
        st.session_state.chat_history.append(ai_msg)

    # ── Branch: text-only query ────────────────────────────────────────────────
    elif user_text:
        if not is_trading_related(user_text):
            ai_reply = TOPIC_GUARD
        else:
            prompt = (
                "You are Matrix Yield, an expert trading and technical analysis assistant. "
                "Answer concisely and professionally.\n\n"
                f"User: {user_text}"
            )
            with st.spinner("Thinking..."):
                ai_reply = ask_gemini_text(prompt)

        st.session_state.chat_history.append({"role": "ai", "content": ai_reply})

    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.logged_in:
    main_app()
else:
    landing_page()
