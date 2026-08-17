import streamlit as st
from investigator import read_logs, investigate_incident
from google import genai
from dotenv import load_dotenv
import os
from collections import Counter

load_dotenv()

st.set_page_config(
    page_title="AegisOps | AI Incident Response",
    page_icon="🛡️",
    layout="wide"
)

# -----------------------------
# Header
# -----------------------------

st.title("🛡️ AegisOps")
st.caption("AI-Powered DevOps Incident Response System")

st.divider()

# -----------------------------
# Gemini Configuration
# -----------------------------

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("❌ Gemini API key not found.")
    st.stop()

client = genai.Client(api_key=api_key)

# -----------------------------
# Read Logs
# -----------------------------

logs = read_logs()

if not logs:
    st.warning("⚠️ No server logs found.")
    st.stop()

incidents = []

for line in logs:
    line = line.strip()

    if "ERROR" in line or "WARNING" in line:

        report = investigate_incident(line)

        if report:
            incidents.append({
                "log": line,
                "type": report["type"],
                "severity": report["severity"]
            })

# -----------------------------
# Dashboard Metrics
# -----------------------------

total_incidents = len(incidents)

high_count = sum(
    1 for i in incidents
    if i["severity"].upper() == "HIGH"
)

security_count = sum(
    1 for i in incidents
    if "Security" in i["type"]
)

web_count = sum(
    1 for i in incidents
    if "Web" in i["type"]
)

st.subheader("📊 Incident Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🚨 Total Incidents", total_incidents)

with col2:
    st.metric("🔴 High Severity", high_count)

with col3:
    st.metric("🔐 Security", security_count)

with col4:
    st.metric("🌐 Web Server", web_count)

st.divider()

# -----------------------------
# Incident Distribution
# -----------------------------

st.subheader("📈 Incident Distribution")

type_counts = Counter(i["type"] for i in incidents)

if type_counts:
    chart_data = {
        "Incident Type": list(type_counts.keys()),
        "Count": list(type_counts.values())
    }

    st.bar_chart(
        data=chart_data,
        x="Incident Type",
        y="Count"
    )

st.divider()

# -----------------------------
# Detected Incidents
# -----------------------------

st.subheader("🚨 Detected Incidents")

for number, incident in enumerate(incidents, start=1):

    severity = incident["severity"].upper()

    if severity == "HIGH":
        icon = "🔴"
    elif severity == "MEDIUM":
        icon = "🟠"
    else:
        icon = "🟢"

    with st.expander(
        f"{icon} Incident #{number} — {severity}"
    ):

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Incident Type**")
            st.info(incident["type"])

        with col2:
            st.write("**Severity**")
            st.error(severity)

        st.write("**Log Entry**")
        st.code(incident["log"])

st.divider()

# -----------------------------
# Gemini AI Investigation
# -----------------------------

st.subheader("🤖 AI Investigation")

st.write(
    "Use Gemini AI to analyze all detected incidents "
    "and generate a professional DevOps incident report."
)

if st.button(
    "🔍 Analyze Incidents with Gemini AI",
    use_container_width=True
):

    incident_text = "\n".join(
        f"{i['severity']} - {i['type']} - {i['log']}"
        for i in incidents
    )

    prompt = f"""
You are AegisOps, an AI-powered DevOps incident investigator.

Analyze these detected server incidents:

{incident_text}

Create a professional incident report containing:

1. Executive Summary
2. Incident Types
3. Severity
4. Probable Root Cause
5. Security Concerns
6. Recommended Actions
7. Prevention Suggestions

Clearly separate confirmed facts from hypotheses.
Do not claim that one incident caused another unless the logs
provide enough evidence.

Keep the report clear and practical for a DevOps engineer.
"""

    with st.spinner("🤖 Gemini is investigating the incidents..."):

        try:
            response = client.interactions.create(
                model="gemini-3.6-flash",
                input=prompt
            )

            st.success("✅ Investigation completed!")

            st.subheader("📋 AI Incident Report")

            st.markdown(response.output_text)

        except Exception as e:

            st.error("❌ AI investigation failed.")

            st.code(str(e))

# -----------------------------
# Footer
# -----------------------------

st.divider()

st.caption(
    "🛡️ AegisOps | AI + DevOps + Cloud Incident Response"
)