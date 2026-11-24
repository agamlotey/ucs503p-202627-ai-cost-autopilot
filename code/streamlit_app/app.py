"""Run from code/ with: streamlit run streamlit_app/app.py"""
import os

import requests
import streamlit as st

gateway = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8000").rstrip("/")
st.set_page_config(page_title="AI Cost Autopilot", layout="centered")
st.title("AI Cost Autopilot")
model = st.sidebar.text_input("Model", value=os.environ.get("DEFAULT_MODEL", "gpt-4o-mini"))
source = st.radio("Request source", ["notes_api example", "Custom request"], horizontal=True)
if source == "Custom request":
    prompt = st.text_area("Task")
    code = st.text_area("Source code (optional)", height=180)
else:
    st.caption("Run “fix create_note” with the source files from the notes_api fixture.")

run, repeat = st.columns(2)
submit = run.button("Run request", type="primary")
replay = repeat.button("Repeat last request", disabled="last_body" not in st.session_state)

if submit or replay:
    try:
        if replay:
            body = st.session_state.last_body
        elif source == "notes_api example":
            example = requests.get(f"{gateway}/demo/example-request", timeout=10)
            example.raise_for_status()
            body = {"messages": example.json()["messages"]}
        else:
            if not prompt.strip():
                st.warning("Enter a task to run.")
                st.stop()
            messages = [{"role": "user", "content": prompt}]
            if code.strip():
                messages.append({"role": "user", "content": code})
            body = {"messages": messages}

        if not replay:
            if not model.strip():
                st.warning("Enter a model name.")
                st.stop()
            body["model"] = model.strip()

        with st.spinner("Running through the gateway…"):
            response = requests.post(f"{gateway}/v1/chat/completions", json=body, timeout=130)
            response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"]
        headers = response.headers
        st.session_state.result = (
            reply, headers["X-Autopilot-Outcome"], headers["X-Autopilot-Provider"],
            headers["X-Autopilot-Input-Tokens"], headers["X-Autopilot-Forwarded-Tokens"],
        )
        st.session_state.last_body = body
        st.rerun()
    except (requests.RequestException, KeyError, IndexError, TypeError) as error:
        st.error(f"Couldn't complete the request. Check the gateway at {gateway}. {error}")
        st.stop()

if "result" in st.session_state:
    reply, outcome, provider, original, forwarded = st.session_state.result
    labels = {"cache": "Cache hit", "trim": "Trimmed", "forward": "Forwarded"}
    st.subheader(labels[outcome])
    st.caption(f"{provider.capitalize()} provider · gateway estimates for message text")
    left, right = st.columns(2)
    left.metric("Original input tokens", original)
    right.metric("Forwarded input tokens", forwarded)
    st.markdown("**Response**")
    st.text(reply)
