import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
from PIL import Image

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Matrix Yield", layout="wide")

# --- 2. THE STYLING (Big Title + Reinstated Login Box) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    
    /* Massive Centered Title */
    .big-title {
        font-size: 90px !important;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0px;
        color: #ffffff;
        text-transform: uppercase;
    }

    .sub-text {
        text-align: center;
        font-size: 20px;
        color: #8899A6;
        margin-bottom: 40px;
    }

    /* The Login Box - Back and Clean */
    .login-box {
        border: 1px solid #30363d;
        padding: 30px;
        border-radius: 15px;
        background-color: #161b22;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.5);
    }

    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3.5em;
        background-color: #1f77b4;
        color: white;
        font-weight: bold;
        border: none;
    }

    /* Removes the top empty space/padding from the page */
    .block-container {
        padding-top: 2rem !important;
    }
    
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATABASE FUNCTIONS ---
def load_users():
    file = 'users.csv'
    if not os.path.exists(file):
        df = pd.DataFrame(columns=['Email', 'Password', 'Username'])
        df.to_csv(file, index=False)
        return df
    return pd.read_csv(file)

def save_user(email, pw, user):
    users = load_users()
    if email in users['Email'].values:
        return False
    new_data = pd.DataFrame([[email, pw, user]], columns=['Email', 'Password', 'Username'])
    pd.concat([users, new_data], ignore_index=True).to_csv('users.csv', index=False)
    return True

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'signup_mode' not in st.session_state:
    st.session_state.signup_mode = False

# --- 4. THE INTERFACE ---
if not st.session_state.logged_in:
    
    # MASSIVE TITLE & SUBTITLE
    st.markdown('<h1 class="big-title">MATRIX YIELD</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-text">Advanced Market Structure Analysis</p>', unsafe_allow_html=True)

    # Use columns to center the box properly
    left, mid, right = st.columns([1, 1.5, 1])
    
    with mid:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        
        if not st.session_state.signup_mode:
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            
            if st.button("SIGN IN"):
                users = load_users()
                match = users[(users['Email'] == email) & (users['Password'] == password)]
                if match.empty:
                    st.error("Invalid Login")
                else:
                    st.session_state.logged_in = True
                    st.session_state.username = match['Username'].values[0]
                    st.rerun()
            
            st.write("---")
            if st.button("CREATE NEW ACCOUNT"):
                st.session_state.signup_mode = True
                st.rerun()
        else:
            # SIGNUP SECTION
            u = st.text_input("User Name")
            e = st.text_input("Email")
            p = st.text_input("Create Password", type="password")
            if st.button("COMPLETE REGISTRATION"):
                if save_user(e, p, u):
                    st.success("Account Created!")
                    st.session_state.signup_mode = False
                    st.rerun()
                else:
                    st.error("User already exists")
            if st.button("BACK TO LOGIN"):
                st.session_state.signup_mode = False
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # MAIN DASHBOARD
    st.sidebar.title(f"User: {st.session_state.username}")
    if st.sidebar.button("LOGOUT"):
        st.session_state.logged_in = False
        st.rerun()

    st.markdown('<h1 class="big-title" style="font-size: 50px !important;">ANALYSIS HUB</h1>', unsafe_allow_html=True)
    
    file = st.file_uploader("Upload Chart Screenshot", type=['png', 'jpg', 'jpeg'])

    if file:
        img = Image.open(file)
        st.image(img, use_container_width=True)
        
        if st.button("RUN AI ANALYSIS"):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = "Analyze this chart. Identify: Trend, HH, HL, LH, LL. Mark BOS. Give Trade Idea: Entry, SL, TP."
                response = model.generate_content([prompt, img])
                st.write(response.text)
            except:
                st.error("Check your API Key in Streamlit Cloud Settings!")
