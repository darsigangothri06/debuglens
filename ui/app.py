import requests
import streamlit as st

st.set_page_config(page_title="DebugLens", page_icon="🔍", layout="wide")

API_URL = "http://localhost:8000/api"

# --- Sidebar: Settings ---
with st.sidebar:
    st.header("⚙️ Settings")
    provider = st.selectbox("LLM Provider", ["gemini", "openai"])
    api_key = st.text_input("API Key", type="password")
    llm_model = st.text_input(
        "Model (optional)",
        placeholder="gemini-2.5-flash or gpt-4o-mini",
    )
    st.divider()
    repo_source = st.text_input(
        "Repository",
        placeholder="/path/to/repo or https://github.com/user/repo",
    )
    github_token = st.text_input("GitHub Token (optional)", type="password")

# --- Main Area ---
st.title("🔍 DebugLens")
st.caption("Paste a stack trace. Get the root cause and fix.")

error_text = st.text_area(
    "Stack Trace / Error Log",
    height=250,
    placeholder="Paste your error here...",
)

analyze_disabled = not error_text or not api_key or not repo_source

if st.button("Analyze", type="primary", disabled=analyze_disabled):
    with st.status("Analyzing...", expanded=True) as status:
        st.write("⏳ Sending to DebugLens API...")

        payload = {
            "error_text": error_text,
            "repo_source": repo_source,
            "llm_provider": provider,
            "llm_api_key": api_key,
            "llm_model": llm_model or None,
            "github_token": github_token or None,
        }

        try:
            resp = requests.post(
                f"{API_URL}/analyze",
                json=payload,
                timeout=120,
            )
        except requests.ConnectionError:
            st.error("Cannot connect to DebugLens API. Is the server running on port 8000?")
            st.stop()
        except requests.Timeout:
            st.error("API request timed out after 120 seconds.")
            st.stop()

        if resp.status_code != 200:
            detail = resp.json().get("detail", resp.text) if resp.headers.get("content-type", "").startswith("application/json") else resp.text
            st.error(f"Analysis failed: {detail}")
            st.stop()

        report = resp.json()
        status.update(label="Analysis complete!", state="complete")

    # --- Results ---
    st.divider()

    # Error Summary
    with st.expander("📋 Error Summary", expanded=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("Error Type", report["error_type"])
        col2.metric("Language", report["language"].title())
        col3.metric("Confidence", report["confidence"].title())
        st.code(report["error_message"], language=None)

    # Call Chain
    with st.expander("🔗 Call Chain", expanded=True):
        for i, frame in enumerate(report["call_chain"]):
            st.markdown(
                f"**Frame {i + 1}:** `{frame['function_name']}` "
                f"— `{frame['file_path']}:{frame['line_number']}`"
            )
            if frame["code_snippet"]:
                code = "\n".join(frame["code_snippet"])
                st.code(code, language=report["language"])

    # Root Cause
    with st.expander("🎯 Root Cause", expanded=True):
        confidence_colors = {"high": "🟢", "medium": "🟡", "low": "🔴"}
        badge = confidence_colors.get(report["confidence"], "⚪")
        st.markdown(f"**Confidence:** {badge} {report['confidence'].title()}")
        st.markdown(report["root_cause"])

    # Similar Issues
    with st.expander("🔎 Similar Issues", expanded=bool(report["similar_issues"])):
        if report["similar_issues"]:
            for issue in report["similar_issues"]:
                icon = "✅" if issue["is_accepted"] else "❓"
                src_label = "SO" if issue["source"] == "stackoverflow" else "GH"
                st.markdown(
                    f"{icon} **[{src_label}]** [{issue['title']}]({issue['url']}) "
                    f"(score: {issue['score']})"
                )
        else:
            st.info("No similar issues found online.")

    # Suggested Fix
    with st.expander("🛠️ Suggested Fix", expanded=True):
        if report.get("fix_file"):
            st.markdown(
                f"**Apply to:** `{report['fix_file']}`"
                + (f" (line {report['fix_line']})" if report.get("fix_line") else "")
            )
        st.code(report["suggested_fix"], language=report["language"])

    # Prevention Tips
    with st.expander("🛡️ Prevention Tips"):
        st.markdown(
            "- Add validation for the identified root cause pattern\n"
            "- Write regression tests covering this edge case\n"
            "- Consider adding type checking / null guards at the identified location"
        )
