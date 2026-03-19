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

# --- 2. ADVANCED CHAT INTERFACE CSS ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    
    /* Center the Analysis Hub Title */
    .hub-title {
        text-align: center;
        font-size: 40px;
        font-weight: 700;
        margin-bottom: 30px;
    }

    /* THE CHAT BAR CONTAINER */
    .chat-bar {
        display: flex;
        align-items: center;
        background-color: #21262d;
        border: 1px solid #30363d;
        border-radius: 30px;
        padding: 5px 15px;
        width: 100%;
        max-width: 800px;
        margin: 0 auto;
    }

    /* Make the File Uploader look like a circular (+) button */
    .stFileUploader section {
        padding: 0 !important;
        min-height: unset !important;
        background-color: transparent !important;
        border: none !important;
    }
    .stFileUploader label { display: none; }
    
    /* Circular Buttons Styling */
    .circle-btn {
        width: 40px;
        height: 40px;
        background-color: #30363d;
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        cursor: pointer;
        color: white;
        font-size: 20px;
        border: none;
    }

    .send-btn {
        background-color: #ffffff;
        color: #000000;
    }

    /* Results Styling */
    .result-area {
        background-color: #161b22;
        padding: 25px;
        border-radius: 20px;
        border: 1px solid #30363d;
        margin-top: 30px;
        max-width: 850px;
        margin-left: auto;
        margin-right: auto;
    }

    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATABASE FUNCTIONS ---
def load_users():
    if not os.path.exists('users.csv'):
        pd.DataFrame(columns=['Email', 'Password', 'Username']).to_csv('users.csv', index=False)
    return pd.read_csv('users.csv')

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

# --- 4. LOGIN SCREEN ---
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
                else: st.error("Invalid Credentials")

# --- 5. THE CHAT ANALYSIS HUB ---
else:
    with st.sidebar:
        if logo_path: st.image(logo_path, use_container_width=True)
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    st.markdown('<div class="hub-title">How can Matrix Yield help you today?</div>', unsafe_allow_html=True)

    # Main Chat Interface Area
    container = st.container()
    
    # 1. THE BAR: (+) INPUT (UP-ARROW)
    # Using columns to create the layout
    c1, c2, c3 = st.columns([0.15, 0.7, 0.15])

    with c1:
        # THE PLUS (+) BUTTON (FILE UPLOADER)
        # Clicking this opens the file explorer directly
        uploaded_file = st.file_uploader("➕", type=['png', 'jpg', 'jpeg'], key="plus_btn")
    
    with c2:
        # THE CHAT BOX
        user_query = st.text_input("", placeholder="Message Matrix Yield...", label_visibility="collapsed")
    
    with c3:
        # THE SEND (UP-ARROW) BUTTON
        send_trigger = st.button("↑")

    # --- PROCESSING ---
    if send_trigger:
        if uploaded_file:
            img = Image.open(uploaded_file)
            
            with container:
                st.markdown('<div class="result-area">', unsafe_allow_html=True)
                st.image(img, width=500)
                
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    with st.spinner("Analyzing structure..."):
                        prompt = user_query if user_query else "Identify Trend, HH, HL, LH, LL, BOS, and Entry/SL/TP."
                        response = model.generate_content([prompt, img])
                        
                        st.markdown("### 📊 Analysis Result")
                        st.write(response.text)
                except:
                    st.error("Error: Check your API Key in Streamlit Secrets.")
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("Please tap the (+) button to upload your chart first.")

    st.markdown("<br><br>", unsafe_allow_html=True)
