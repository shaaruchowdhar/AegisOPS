from investigator import read_logs, investigate_incident
from google import genai
from dotenv import load_dotenv
import os


# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Gemini API key not found.")
    exit()

client = genai.Client(api_key=api_key)


def main():

    print("\n" + "=" * 60)
    print("🛡️  AEGISOPS - AI INCIDENT RESPONSE SYSTEM")
    print("=" * 60)

    # Read server logs
    logs = read_logs()

    if not logs:
        print("❌ No logs found.")
        return

    incidents = []

    # Detect incidents
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

    print(f"\n🔎 Incidents detected: {len(incidents)}")

    # Display detected incidents
    for number, incident in enumerate(incidents, start=1):

        print(f"\n🚨 Incident #{number}")
        print(f"Type: {incident['type']}")
        print(f"Severity: {incident['severity']}")
        print(f"Log: {incident['log']}")

    # Send complete logs to Gemini
    print("\n🤖 Sending incidents to Gemini AI...")
    print("=" * 60)

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

Keep the report clear and practical for a DevOps engineer.
"""

    response = client.interactions.create(
        model="gemini-3.6-flash",
        input=prompt
    )

    print("\n🤖 AI INCIDENT REPORT")
    print("=" * 60)
    print(response.output_text)

    print("\n" + "=" * 60)
    print("✅ AegisOps investigation completed.")
    print("=" * 60)


if __name__ == "__main__":
    main()