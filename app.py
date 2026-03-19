import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
from PIL import Image

# --- 1. SMART LOGO CHECK ---
# This checks both names so you don't get an error!
if os.path.exists("logo.png.jpeg"):
    logo_path = "logo.png.jpeg"
elif os.path.exists("logo.png"):
    logo_path = "logo.png"
else:
    logo_path = None

# --- 2. PAGE CONFIG ---
if logo_path:
    img = Image.open(logo_path)
    st.set_page_config(page_title="Matrix Yield", layout="wide", page_icon=img)
else:
    st.set_page_config(page_title="Matrix Yield", layout="wide", page_icon="📈")

# --- 3. STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 10px; background-color: #1f77b4; color: white; border: none; font-weight: bold; }
    .login-box { border: 1px solid #30363d; padding: 2rem; border-radius: 15px; background-color: #161b22; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. DATABASE HELPERS ---
def load_users():
    if os.path.exists('users.csv'):
        return pd.read_csv('users.csv')
    # Create empty user file if it doesn't exist to prevent errors
    df = pd.DataFrame(columns=['Email', 'Password', 'Username'])
    df.to_csv('users.csv', index=False)
    return df

# Initialize session
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'show_signup' not in st.session_state:
    st.session_state.show_signup = False

# --- 5. AUTHENTICATION ---
if not st.session_state.logged_in:
    # Display Logo on Login
    if logo_path:
        st.image(logo_path, width=200)
    
    st.title("Matrix Yield AI")
    
    if not st.session_state.show_signup:
        with st.container():
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                users = load_users()
                match = users[(users['Email'] == email) & (users['Password'] == password)]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.username = match['Username'].values[0]
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
            if st.button("Create Account"):
                st.session_state.show_signup = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        with st.form("signup"):
            st.subheader("Join the Matrix")
            u = st.text_input("Username")
            e = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Sign Up"):
                users = load_users()
                if e in users['Email'].values:
                    st.error("Email already exists!")
                else:
                    new_user = pd.DataFrame([[e, p, u]], columns=['Email', 'Password', 'Username'])
                    pd.concat([users, new_user]).to_csv('users.csv', index=False)
                    st.success("Success! Please Login.")
                    st.session_state.show_signup = False
                    st.rerun()

# --- 6. DASHBOARD ---
else:
    # Logo in Sidebar
    if logo_path:
        st.sidebar.image(logo_path, use_container_width=True)
    
    st.sidebar.title(f"Hi, {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    st.header("📈 Market Analysis")
    uploaded_file = st.file_uploader("Upload Chart", type=['png', 'jpg', 'jpeg'])

    if uploaded_file:
        chart_img = Image.open(uploaded_file)
        st.image(chart_img, caption="Chart Received", use_container_width=True)
        
        if st.button("🚀 Run Analysis"):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = "Identify: Trend, HH, HL, LH, LL, and BOS. Suggest Entry, SL, and TP."
                response = model.generate_content([prompt, chart_img])
                st.markdown("### 📊 AI Structure Analysis")
                st.write(response.text)
            except:
                st.error("Check Streamlit Secrets for GEMINI_API_KEY!")

    st.markdown("---")
    st.caption("Matrix Yield | Educational AI Tool")
