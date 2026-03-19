import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
from PIL import Image

# --- 1. LOGO LOGIC (Keeps the Website Identity) ---
if os.path.exists("logo.png.jpeg"):
    logo_path = "logo.png.jpeg"
elif os.path.exists("logo.png"):
    logo_path = "logo.png"
else:
    logo_path = None

# Set the Browser Tab Logo
if logo_path:
    try:
        img_icon = Image.open(logo_path)
        st.set_page_config(page_title="Matrix Yield", layout="wide", page_icon=img_icon)
    except:
        st.set_page_config(page_title="Matrix Yield", layout="wide", page_icon="📈")
else:
    st.set_page_config(page_title="Matrix Yield", layout="wide", page_icon="📈")

# --- 2. STYLING (Massive Title & Clean Box) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    
    .big-title {
        font-size: 95px !important;
        font-weight: 900;
        text-align: center;
        margin-bottom: 5px;
        color: #ffffff;
        text-transform: uppercase;
        letter-spacing: -3px;
    }

    .sub-text {
        text-align: center;
        font-size: 22px;
        color: #5d6d7e;
        margin-bottom: 40px;
    }

    .login-box {
        border: 1px solid #30363d;
        padding: 35px;
        border-radius: 20px;
        background-color: #161b22;
        box-shadow: 0px 15px 40px rgba(0,0,0,0.6);
    }

    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3.8em;
        background-color: #1f77b4;
        color: white;
        font-weight: bold;
        border: none;
    }

    /* Fix spacing at the top */
    .block-container { padding-top: 3rem !important; }
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. CORE FUNCTIONS ---
def load_users():
    file = 'users.csv'
    if not os.path.exists(file):
        df = pd.DataFrame(columns=['Email', 'Password', 'Username'])
        df.to_csv(file, index=False)
        return df
    return pd.read_csv(file)

def save_user(email, pw, user):
    users = load_users()
    if email in users['Email'].values: return False
    new_data = pd.DataFrame([[email, pw, user]], columns=['Email', 'Password', 'Username'])
    pd.concat([users, new_data], ignore_index=True).to_csv('users.csv', index=False)
    return True

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'signup_mode' not in st.session_state: st.session_state.signup_mode = False

# --- 4. LOGIN / SIGNUP VIEW ---
if not st.session_state.logged_in:
    st.markdown('<h1 class="big-title">MATRIX YIELD</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-text">PRO CHART ANALYSIS AI</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        if not st.session_state.signup_mode:
            e = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.button("SIGN IN"):
                u_db = load_users()
                match = u_db[(u_db['Email'] == e) & (u_db['Password'] == p)]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.username = match['Username'].values[0]
                    st.rerun()
                else: st.error("Invalid Credentials")
            
            st.write("---")
            if st.button("CREATE ACCOUNT"):
                st.session_state.signup_mode = True
                st.rerun()
        else:
            un = st.text_input("Username")
            em = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            if st.button("REGISTER"):
                if save_user(em, pw, un):
                    st.success("Ready! Please Login.")
                    st.session_state.signup_mode = False
                    st.rerun()
            if st.button("BACK"):
                st.session_state.signup_mode = False
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- 5. DASHBOARD (MAIN LOGO LIVES HERE) ---
else:
    with st.sidebar:
        # THE LOGO REMAINS HERE
        if logo_path:
            st.image(logo_path, use_container_width=True)
        
        st.title(f"Welcome, {st.session_state.username}")
        if st.button("LOGOUT"):
            st.session_state.logged_in = False
            st.rerun()

    st.markdown('<h1 class="big-title" style="font-size: 55px !important;">ANALYSIS HUB</h1>', unsafe_allow_html=True)
    
    chart = st.file_uploader("Upload Market Chart", type=['png', 'jpg', 'jpeg'])

    if chart:
        img = Image.open(chart)
        st.image(img, use_container_width=True)
        
        if st.button("🚀 ANALYZE STRUCTURE"):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = "Analyze: Trend, HH, HL, LH, LL, BOS. Provide Entry, SL, TP."
                res = model.generate_content([prompt, img])
                st.markdown("### 📊 Results")
                st.write(res.text)
            except:
                st.error("API Key missing in Streamlit Cloud!")
