import os
import time

import requests
import streamlit as st

st.set_page_config(page_title="DebugLens", page_icon="D", layout="wide")

API_URL = os.getenv("API_URL", "http://localhost:8000/api")

ANALYSIS_STEPS = [
    "Parsing stack trace...",
    "Reading source code...",
    "Analyzing root cause...",
    "Searching for similar issues...",
    "Generating fix suggestion...",
]

st.title("DebugLens")
st.caption("Paste a stack trace. Get the root cause and a suggested fix.")

st.info(
    "This demo uses an open-source LLM (GPT-OSS 20B via Groq) on a free tier. "
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


def format_elapsed(elapsed: float) -> str:
    mins, secs = divmod(int(elapsed), 60)
    if mins > 0:
        return f"{mins}m {secs}s"
    return f"{secs}s"


if st.button("Analyze", type="primary", disabled=analyze_disabled):
    progress_container = st.container()
    result_container = st.container()

    with progress_container:
        st.subheader("Analysis Progress")
        time_placeholder = st.empty()
        progress_bar = st.progress(0, text="Connecting to DebugLens API...")
        step_log = st.container()

        start_time = time.time()

        def update_elapsed():
            elapsed = time.time() - start_time
            time_placeholder.caption(
                f"Elapsed: {format_elapsed(elapsed)} | "
                "Estimated total: 10 to 30 seconds"
            )

        payload = {
            "error_text": error_text,
            "repo_source": repo_source,
            "github_token": github_token_input or None,
        }

        update_elapsed()
        progress_bar.progress(5, text="Sending to DebugLens API...")

        max_retries = 3
        resp = None

        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    f"{API_URL}/analyze",
                    json=payload,
                    timeout=120,
                )

                if resp.status_code == 429 and attempt < max_retries - 1:
                    delay = 2 * (2 ** attempt)
                    progress_bar.progress(
                        10,
                        text=f"Rate limited. Retrying in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries})...",
                    )
                    with step_log:
                        elapsed = time.time() - start_time
                        st.text(
                            f"[{format_elapsed(elapsed)}] "
                            f"Rate limited, waiting {delay}s before retry"
                        )
                    time.sleep(delay)
                    update_elapsed()
                    continue

                break

            except requests.ConnectionError:
                if attempt < max_retries - 1:
                    delay = 2 * (2 ** attempt)
                    progress_bar.progress(
                        5,
                        text=f"Connection failed. Retrying in {delay}s...",
                    )
                    with step_log:
                        elapsed = time.time() - start_time
                        st.text(
                            f"[{format_elapsed(elapsed)}] "
                            "Connection failed, server may be starting up"
                        )
                    time.sleep(delay)
                    update_elapsed()
                    continue
                progress_bar.progress(0, text="Connection failed")
                st.error(
                    "Cannot connect to DebugLens API. "
                    "The server may be starting up (free tier cold start takes ~30s). "
                    "Please try again in a moment."
                )
                st.stop()

            except requests.Timeout:
                progress_bar.progress(0, text="Request timed out")
                st.error(
                    "API request timed out after 120 seconds. "
                    "Try a simpler error or shorter stack trace."
                )
                st.stop()

        elapsed = time.time() - start_time
        update_elapsed()

        if resp is None:
            st.error("All connection attempts failed.")
            st.stop()

        if resp.status_code == 429:
            progress_bar.progress(0, text="Rate limited")
            st.warning(
                "Rate limited by API provider after multiple retries. "
                "Wait 30 to 60 seconds and try again."
            )
            st.stop()

        if resp.status_code != 200:
            progress_bar.progress(0, text="Analysis failed")
            detail = (
                resp.json().get("detail", resp.text)
                if resp.headers.get("content-type", "").startswith(
                    "application/json"
                )
                else resp.text
            )
            st.error(f"Analysis failed: {detail}")
            st.stop()

        progress_bar.progress(
            100, text=f"Analysis complete in {format_elapsed(elapsed)}"
        )
        time_placeholder.caption(f"Completed in {format_elapsed(elapsed)}")

        report = resp.json()

    with result_container:
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
            confidence_labels = {
                "high": "High",
                "medium": "Medium",
                "low": "Low",
            }
            label = confidence_labels.get(
                report["confidence"], report["confidence"]
            )
            st.markdown(f"**Confidence:** {label}")
            st.markdown(report["root_cause"])

        with st.expander(
            "Similar Issues", expanded=bool(report["similar_issues"])
        ):
            if report["similar_issues"]:
                for issue in report["similar_issues"]:
                    accepted = (
                        "Accepted" if issue["is_accepted"] else "Unverified"
                    )
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

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Confidence", report["confidence"].title())
        with col2:
            st.metric("Time Taken", format_elapsed(elapsed))
