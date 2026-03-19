import streamlit as st
from PIL import Image
import os

# 1. Setup Logo and Page Config
logo_path = "logo.png"

if os.path.exists(logo_path):
    img = Image.open(logo_path)
    st.set_page_config(page_title="Matrix Yield", layout="wide", page_icon=img)
    # This displays the logo at the top of your sidebar
    st.sidebar.image(img, width=150) 
else:
    # Fallback if the logo isn't uploaded yet
    st.set_page_config(page_title="Matrix Yield", layout="wide", page_icon="📈")

# Custom CSS for a professional Dark Theme
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #007bff; color: white; font-weight: bold; border: none; }
    .stButton>button:hover { background-color: #0056b3; border: 1px solid #ffffff; }
    .login-container { max-width: 450px; margin: auto; padding: 25px; border-radius: 15px; background-color: #161b22; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE LOGIC ---
def get_user_file():
    return 'users.csv'

def load_users():
    if os.path.exists(get_user_file()):
        return pd.read_csv(get_user_file())
    return pd.DataFrame(columns=['Email', 'Password', 'Username'])

def save_new_user(email, password, username):
    users = load_users()
    if email in users['Email'].values:
        return False
    new_entry = pd.DataFrame([[email, password, username]], columns=['Email', 'Password', 'Username'])
    updated_users = pd.concat([users, new_entry], ignore_index=True)
    updated_users.to_csv(get_user_file(), index=False)
    return True

# --- 3. SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'page' not in st.session_state:
    st.session_state.page = "Login"

# --- 4. AUTHENTICATION PAGES ---
if not st.session_state.logged_in:
    st.title("🛡️ Matrix Yield AI")
    
    # SIGNUP PAGE
    if st.session_state.page == "Signup":
        with st.container():
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.subheader("Create Account")
            new_user = st.text_input("Username")
            new_email = st.text_input("Email")
            new_pass = st.text_input("Password", type="password")
            
            if st.button("Register Now"):
                if new_user and new_email and new_pass:
                    if save_new_user(new_email, new_pass, new_user):
                        st.success("Account created! Redirecting to login...")
                        st.session_state.page = "Login"
                        st.rerun()
                    else:
                        st.error("Email already registered.")
                else:
                    st.warning("Please fill in all fields.")
            
            if st.button("Already have an account? Login"):
                st.session_state.page = "Login"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # LOGIN PAGE
    else:
        with st.container():
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.subheader("Sign In")
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
                    st.error("Invalid Email or Password.")
            
            if st.button("New user? Create Account"):
                st.session_state.page = "Signup"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# --- 5. MAIN APPLICATION DASHBOARD ---
else:
    # Sidebar Navigation
    st.sidebar.title(f"Welcome, {st.session_state.username}!")
    st.sidebar.write("Analyze market structures instantly.")
    
    if st.sidebar.button("Log Out"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

    st.header("📈 Matrix Yield Analysis Hub")
    st.write("Upload your chart screenshot (TradingView/MetaTrader) below.")

    # File Upload
    uploaded_file = st.file_uploader("Choose an image...", type=['png', 'jpg', 'jpeg'])

    if uploaded_file:
        col1, col2 = st.columns([1, 1])
        image = Image.open(uploaded_file)
        
        with col1:
            st.image(image, caption="Current Chart", use_container_width=True)
        
        with col2:
            if st.button("🚀 Analyze Structure"):
                try:
                    # Connection to Gemini AI
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    with st.spinner("AI is calculating BOS and liquidity zones..."):
                        prompt = """
                        Analyze this trading chart.
                        1. Identify Trend (Bullish/Bearish).
                        2. Mark HH, HL, LH, LL.
                        3. Identify the Break of Structure (BOS).
                        4. Provide a trade recommendation: Entry, SL, and TP.
                        """
                        response = model.generate_content([prompt, image])
                        st.markdown("### 📊 AI Result")
                        st.write(response.text)
                except Exception as e:
                    st.error("API Key Error: Please check your Streamlit Secrets.")

    # Footer
    st.markdown("---")
    st.caption("Matrix Yield is an AI educational tool. Trading involves risk. No results are guaranteed.")
