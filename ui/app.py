import os

import requests
import streamlit as st

st.set_page_config(page_title="DebugLens", page_icon="D", layout="wide")

API_URL = os.getenv("API_URL", "http://localhost:8000/api")

st.title("DebugLens")
st.caption("Paste a stack trace. Get the root cause and a suggested fix.")

st.info(
    "This demo uses an open-source LLM (Llama 3.3 70B via Groq) on a free tier. "
    "Output quality may vary compared to commercial models. "
    "Analysis typically takes 10 to 30 seconds depending on error complexity."
)

repo_source = st.text_input(
    "Repository",
    placeholder="/path/to/repo or https://github.com/user/repo",
)
github_token_input = st.text_input(
    "GitHub Token (optional, for private repos)",
    type="password",
)

error_text = st.text_area(
    "Stack Trace / Error Log",
    height=250,
    placeholder="Paste your error here...",
)

analyze_disabled = not error_text or not repo_source

if st.button("Analyze", type="primary", disabled=analyze_disabled):
    with st.status("Analyzing...", expanded=True) as status:
        st.write("Sending to DebugLens API...")

        payload = {
            "error_text": error_text,
            "repo_source": repo_source,
            "github_token": github_token_input or None,
        }

        try:
            resp = requests.post(
                f"{API_URL}/analyze",
                json=payload,
                timeout=120,
            )
        except requests.ConnectionError:
            st.error(
                "Cannot connect to DebugLens API. "
                "Is the server running on port 8000?"
            )
            st.stop()
        except requests.Timeout:
            st.error("API request timed out after 120 seconds.")
            st.stop()

        if resp.status_code != 200:
            detail = (
                resp.json().get("detail", resp.text)
                if resp.headers.get("content-type", "").startswith(
                    "application/json"
                )
                else resp.text
            )
            st.error(f"Analysis failed: {detail}")
            st.stop()

        report = resp.json()
        status.update(label="Analysis complete", state="complete")

    st.divider()

    with st.expander("Error Summary", expanded=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("Error Type", report["error_type"])
        col2.metric("Language", report["language"].title())
        col3.metric("Confidence", report["confidence"].title())
        st.code(report["error_message"], language=None)

    with st.expander("Call Chain", expanded=True):
        for i, frame in enumerate(report["call_chain"]):
            st.markdown(
                f"**Frame {i + 1}:** `{frame['function_name']}` "
                f"in `{frame['file_path']}:{frame['line_number']}`"
            )
            if frame["code_snippet"]:
                code = "\n".join(frame["code_snippet"])
                st.code(code, language=report["language"])

    with st.expander("Root Cause", expanded=True):
        confidence_labels = {"high": "High", "medium": "Medium", "low": "Low"}
        label = confidence_labels.get(report["confidence"], report["confidence"])
        st.markdown(f"**Confidence:** {label}")
        st.markdown(report["root_cause"])

    with st.expander(
        "Similar Issues", expanded=bool(report["similar_issues"])
    ):
        if report["similar_issues"]:
            for issue in report["similar_issues"]:
                accepted = "Accepted" if issue["is_accepted"] else "Unverified"
                src_label = (
                    "StackOverflow"
                    if issue["source"] == "stackoverflow"
                    else "GitHub"
                )
                st.markdown(
                    f"**[{src_label}]** [{issue['title']}]({issue['url']}) "
                    f"(score: {issue['score']}, {accepted})"
                )
        else:
            st.info("No similar issues found online.")

    with st.expander("Suggested Fix", expanded=True):
        if report.get("fix_file"):
            location = f"**Apply to:** `{report['fix_file']}`"
            if report.get("fix_line"):
                location += f" (line {report['fix_line']})"
            st.markdown(location)
        st.code(report["suggested_fix"], language=report["language"])

    with st.expander("Prevention Tips"):
        st.markdown(
            "- Add validation for the identified root cause pattern\n"
            "- Write regression tests covering this edge case\n"
            "- Consider adding type checking or null guards at the identified location"
        )
