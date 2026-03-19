import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
from PIL import Image

# --- 1. SMART LOGO DETECTION ---
# This looks for the specific name you have on GitHub
if os.path.exists("logo.png.jpeg"):
    logo_path = "logo.png.jpeg"
elif os.path.exists("logo.png"):
    logo_path = "logo.png"
else:
    logo_path = None

# --- 2. PAGE CONFIGURATION ---
if logo_path:
    try:
        img_icon = Image.open(logo_path)
        st.set_page_config(page_title="Matrix Yield", layout="wide", page_icon=img_icon)
    except:
        st.set_page_config(page_title="Matrix Yield", layout="wide", page_icon="📈")
else:
    st.set_page_config(page_title="Matrix Yield", layout="wide", page_icon="📈")

# --- 3. PROFESSIONAL DARK THEME STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #1f77b4; color: white; font-weight: bold; border: none; transition: 0.3s; }
    .stButton>button:hover { background-color: #2980b9; border: 1px solid white; }
    .login-box { border: 1px solid #30363d; padding: 2.5rem; border-radius: 20px; background-color: #161b22; box-shadow: 0px 4px 15px rgba(0,0,0,0.5); }
    .stTextInput>div>div>input { background-color: #0d1117; color: white; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. DATABASE & AUTH LOGIC ---
def load_users():
    file = 'users.csv'
    if not os.path.exists(file):
        # Create the file immediately if it's missing to prevent errors
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

# Session Management
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'signup_mode' not in st.session_state:
    st.session_state.signup_mode = False

# --- 5. ENTRANCE (LOGIN/SIGNUP) ---
if not st.session_state.logged_in:
    # Show Logo at the top of the Login page
    if logo_path:
        st.image(logo_path, width=180)
    
    st.title("🛡️ Matrix Yield AI")
    st.subheader("Advanced Market Structure Analysis")

    if not st.session_state.signup_mode:
        with st.container():
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            if st.button("Sign In"):
                users = load_users()
                match = users[(users['Email'] == email) & (users['Password'] == password)]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.username = match['Username'].values[0]
                    st.rerun()
                else:
                    st.error("Access Denied: Invalid Credentials")
            
            st.write("---")
            if st.button("Create New Matrix Account"):
                st.session_state.signup_mode = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        # SIGNUP FORM
        with st.form("matrix_signup"):
            st.subheader("Initialize Account")
            new_u = st.text_input("User Name")
            new_e = st.text_input("Email")
            new_p = st.text_input("Secure Password", type="password")
            if st.form_submit_button("Complete Registration"):
                if new_u and new_e and new_p:
                    if save_user(new_e, new_p, new_u):
                        st.success("Account Ready! Redirecting...")
                        st.session_state.signup_mode = False
                        st.rerun()
                    else:
                        st.error("This email is already registered.")
                else:
                    st.warning("All fields are required.")
        if st.button("Back to Login"):
            st.session_state.signup_mode = False
            st.rerun()

# --- 6. MAIN APPLICATION ---
else:
    # Sidebar Profile & Logo
    with st.sidebar:
        if logo_path:
            st.image(logo_path, use_container_width=True)
        st.title(f"Hello, {st.session_state.username}")
        st.write("Logged in to Matrix Network")
        if st.button("Secure Logout"):
            st.session_state.logged_in = False
            st.rerun()

    st.header("📈 AI Chart Analysis")
    st.write("Upload your chart to identify HH, HL, LH, LL, and BOS structure.")
    
    file = st.file_uploader("Drop Chart Image (PNG/JPG)", type=['png', 'jpg', 'jpeg'])

    if file:
        img = Image.open(file)
        st.image(img, caption="Target Chart", use_container_width=True)
        
        if st.button("🚀 Analyze Market Structure"):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                with st.spinner("Matrix AI is processing price action..."):
                    prompt = "Analyze this chart. Identify: Trend, HH, HL, LH, LL. Mark BOS. Give Trade Idea: Entry, SL, TP."
                    response = model.generate_content([prompt, img])
                    st.markdown("### 📊 Analysis Result")
                    st.write(response.text)
            except Exception as e:
                st.error("Error: Check GEMINI_API_KEY in Streamlit Secrets.")

    st.markdown("---")
    st.caption("Matrix Yield v2.0 | Trading requires risk management. AI is for educational use.")
