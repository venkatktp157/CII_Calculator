import streamlit as st
import streamlit_authenticator as stauth
import bcrypt

def load_authenticator():
    # ✅ Nested access (compatible with Streamlit Secrets)
    usernames = st.secrets["credentials"]["usernames"]
    cookie = st.secrets["cookie"]

    # 🔐 Authenticator instance
    authenticator = stauth.Authenticate(
        {"usernames": dict(usernames)},
        cookie["name"],
        cookie["key"],
        cookie["expiry_days"]
    )

    return authenticator


  