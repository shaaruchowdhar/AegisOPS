from dotenv import load_dotenv
from google import genai
from pathlib import Path
import os

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Gemini API key not found.")
    exit()

client = genai.Client(api_key=api_key)

LOG_FILE = Path("logs/server.log")


def read_logs():
    if not LOG_FILE.exists():
        print("❌ server.log not found!")
        return ""

    with open(LOG_FILE, "r", encoding="utf-8") as file:
        return file.read()


logs = read_logs()

if not logs:
    exit()

print("🔌 Sending server logs to Gemini...")
print("=" * 60)

prompt = f"""
You are AegisOps, an AI-powered DevOps incident investigator.

Analyze the following server logs.

Identify:
1. What incidents occurred
2. Severity of each incident
3. Probable root cause
4. Recommended action
5. Whether there is a possible security concern

Give the result in a clear technical incident report.

SERVER LOGS:
{logs}
"""

interaction = client.interactions.create(
    model="gemini-3.6-flash",
    input=prompt
)

print("\n🤖 AegisOps AI Analysis")
print("=" * 60)
print(interaction.output_text)
