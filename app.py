import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
from PIL import Image

# --- 1. CONFIG & LOGO ---
if os.path.exists("logo.png.jpeg"):
    logo_path = "logo.png.jpeg"
elif os.path.exists("logo.png"):
    logo_path = "logo.png"
else:
    logo_path = None

st.set_page_config(page_title="Matrix Yield", layout="wide", page_icon=logo_path if logo_path else "📈")

# --- 2. THE CHAT-STYLE CSS ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    
    /* Big Header */
    .big-title {
        font-size: 50px !important;
        font-weight: 800;
        text-align: center;
        margin-top: -20px;
        color: #ffffff;
    }

    /* Modern Chat Input Container */
    .chat-container {
        position: fixed;
        bottom: 30px;
        left: 50%;
        transform: translateX(-50%);
        width: 70%;
        background-color: #21262d;
        border-radius: 25px;
        padding: 10px 20px;
        border: 1px solid #30363d;
        display: flex;
        align-items: center;
        z-index: 1000;
    }

    /* Customizing the Streamlit Uploader to look like a (+) Button */
    .stFileUploader section {
        padding: 0 !important;
        background-color: transparent !important;
        border: none !important;
    }
    
    /* Style for Analysis Results */
    .result-card {
        background-color: #161b22;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #30363d;
        margin-top: 20px;
    }

    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. CORE LOGIC ---
def load_users():
    if not os.path.exists('users.csv'):
        pd.DataFrame(columns=['Email', 'Password', 'Username']).to_csv('users.csv', index=False)
    return pd.read_csv('users.csv')

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

# --- 4. LOGIN SCREEN (SAME AS PREVIOUS) ---
if not st.session_state.logged_in:
    st.markdown('<h1 style="font-size:90px; text-align:center;">MATRIX YIELD</h1>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login"):
            e = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("SIGN IN"):
                db = load_users()
                if not db[(db['Email'] == e) & (db['Password'] == p)].empty:
                    st.session_state.logged_in = True
                    st.session_state.username = db[db['Email'] == e]['Username'].values[0]
                    st.rerun()
                else: st.error("Invalid Login")

# --- 5. THE NEW ANALYSIS HUB (CHAT INTERFACE) ---
else:
    with st.sidebar:
        if logo_path: st.image(logo_path, use_container_width=True)
        st.write(f"Logged in as: **{st.session_state.username}**")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    st.markdown('<h1 class="big-title">ANALYSIS HUB</h1>', unsafe_allow_html=True)

    # UI for Chat & Upload
    # We use columns to simulate the (+) [Text] [^] layout
    display_col1, display_col2 = st.columns([2, 1])

    with st.container():
        st.write("### 👋 How can Matrix Yield help you today?")
        
        # 1. THE PLUS (+) BUTTON AREA
        uploaded_file = st.file_uploader("➕ Upload Chart", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")
        
        # 2. THE TEXT INPUT AREA
        user_query = st.text_input("Type your message or ask about a chart...", placeholder="Analyze this chart for BOS and entry...", label_visibility="collapsed")
        
        # 3. THE ANALYSIS BUTTON (The "Arrow Up" Trigger)
        if st.button("⬆️ Run Analysis"):
            if uploaded_file:
                img = Image.open(uploaded_file)
                st.image(img, width=400)
                
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    with st.spinner("Analyzing market structure..."):
                        prompt = user_query if user_query else "Identify Trend, HH, HL, LH, LL, BOS, and provide Entry/SL/TP."
                        response = model.generate_content([prompt, img])
                        
                        st.markdown('<div class="result-card">', unsafe_allow_html=True)
                        st.markdown("### 📊 Matrix AI Response")
                        st.write(response.text)
                        st.markdown('</div>', unsafe_allow_html=True)
                except:
                    st.error("Error: Please check your API Key in Streamlit Secrets.")
            else:
                st.warning("Please upload a chart using the (+) button first.")

    # Footer spacing
    st.markdown("<br><br><br>", unsafe_allow_html=True)
