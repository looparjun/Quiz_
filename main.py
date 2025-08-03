import streamlit as st
import time
import random
import threading
import firebase_admin
from firebase_admin import credentials, firestore, auth

from google.auth.exceptions import GoogleAuthError

# ---- Firebase Setup ----
FIREBASE_CRED_PATH = "firebase_credentials.json"  # Add your Firebase Admin SDK JSON file path here
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ---- Quiz Questions ----
QUESTIONS = [
    {"question": "What is the capital of Nepal?", "options": ["Pokhara", "Lalitpur", "Kathmandu", "Biratnagar"], "answer": "Kathmandu"},
    {"question": "What is 12 x 8?", "options": ["96", "108", "84", "88"], "answer": "96"},
    {"question": "Who discovered gravity?", "options": ["Einstein", "Newton", "Galileo", "Tesla"], "answer": "Newton"},
    {"question": "Which is the largest planet?", "options": ["Earth", "Mars", "Saturn", "Jupiter"], "answer": "Jupiter"},
    {"question": "नेपालको राष्ट्रिय जनावर के हो?", "options": ["गाई", "कुकुर", "बाघ", "भालु"], "answer": "गाई"},
    {"question": "The Great Wall is located in?", "options": ["Japan", "India", "China", "Thailand"], "answer": "China"},
    # Add more questions here, ideally 50+
]

random.shuffle(QUESTIONS)

# ---- Streamlit UI & Logic ----
st.set_page_config(page_title="🔥 Real-Time Multiplayer Quiz", layout="centered")

# CSS Styling
st.markdown("""
<style>
body {
    background: linear-gradient(120deg, #2980b9, #8e44ad);
    color: white;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
h1, h2, h3 {
    text-align: center;
}
button {
    background-color: #34495e;
    border: none;
    border-radius: 10px;
    padding: 12px 24px;
    margin: 5px;
    font-size: 1.1rem;
    color: #ecf0f1;
    transition: background-color 0.3s ease;
}
button:hover {
    background-color: #2ecc71;
    cursor: pointer;
}
.timer {
    font-size: 2rem;
    font-weight: bold;
    text-align: center;
    margin: 15px 0;
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0% { color: #2ecc71; }
    50% { color: #e74c3c; }
    100% { color: #2ecc71; }
}
</style>
""", unsafe_allow_html=True)

# Initialize session state vars
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "score" not in st.session_state:
    st.session_state.score = 0
if "question_idx" not in st.session_state:
    st.session_state.question_idx = 0
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "timer" not in st.session_state:
    st.session_state.timer = 10
if "answer_given" not in st.session_state:
    st.session_state.answer_given = False

# Auth functions
def login_user(email, password):
    try:
        user = auth.get_user_by_email(email)
        st.session_state.user_email = email
        st.session_state.logged_in = True
        st.success("Logged in successfully!")
    except auth.UserNotFoundError:
        st.error("User not found! Please register.")
    except Exception as e:
        st.error(f"Login failed: {e}")

def register_user(email, password):
    try:
        auth.create_user(email=email, password=password)
        st.success("Registered successfully! Please login.")
    except Exception as e:
        st.error(f"Registration failed: {e}")

def update_leaderboard(email, score):
    user_ref = db.collection("leaderboard").document(email)
    doc = user_ref.get()
    if doc.exists:
        current_high = doc.to_dict().get("score", 0)
        if score > current_high:
            user_ref.set({"score": score})
    else:
        user_ref.set({"score": score})

def get_leaderboard():
    docs = db.collection("leaderboard").order_by("score", direction=firestore.Query.DESCENDING).limit(10).stream()
    return [(doc.id, doc.to_dict()["score"]) for doc in docs]

def countdown():
    while st.session_state.timer > 0 and not st.session_state.answer_given:
        time.sleep(1)
        st.session_state.timer -= 1
        st.experimental_rerun()
    if st.session_state.timer == 0 and not st.session_state.answer_given:
        st.session_state.score = 0
        st.session_state.answer_given = True
        st.experimental_rerun()

# UI logic
if not st.session_state.logged_in:
    st.title("👋 Welcome to the Real-Time Quiz!")
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            login_user(login_email, login_password)

    with tab2:
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Register"):
            register_user(reg_email, reg_password)

else:
    # Quiz screen
    st.title("🧠 Quiz Time!")
    q = QUESTIONS[st.session_state.question_idx]
    st.subheader(f"Question {st.session_state.question_idx + 1} of {len(QUESTIONS)}")
    st.markdown(f"### {q['question']}")
    st.markdown(f"<div class='timer'>⏳ Time left: {st.session_state.timer}</div>", unsafe_allow_html=True)

    if not st.session_state.answer_given:
        for option in q["options"]:
            if st.button(option):
                st.session_state.answer_given = True
                if option == q["answer"]:
                    st.success("🎉 Correct!")
                    st.session_state.score += 1
                else:
                    st.error(f"❌ Wrong! Correct answer was: {q['answer']}")
                    st.session_state.score = 0

                update_leaderboard(st.session_state.user_email, st.session_state.score)
                st.experimental_rerun()
    else:
        if st.button("Next Question"):
            st.session_state.answer_given = False
            st.session_state.timer = 10
            st.session_state.question_idx += 1
            if st.session_state.question_idx >= len(QUESTIONS):
                st.session_state.question_idx = 0
            st.experimental_rerun()

    st.write(f"Current Score: {st.session_state.score}")

    st.subheader("🏆 Leaderboard (Top Scores)")
    leaderboard = get_leaderboard()
    for idx, (user, score) in enumerate(leaderboard):
        st.write(f"{idx + 1}. {user} — {score}")

    if not st.session_state.answer_given and st.session_state.timer == 10:
        threading.Thread(target=countdown, daemon=True).start()

    st.write("---")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.score = 0
        st.session_state.question_idx = 0
        st.session_state.user_email = ""
        st.session_state.timer = 10
        st.session_state.answer_given = False
        st.experimental_rerun()
