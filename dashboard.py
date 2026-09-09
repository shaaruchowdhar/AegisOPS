import streamlit as st
import os
import re
import time
import random
from dotenv import load_dotenv
from google import genai

# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
except Exception:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LOG_FILE = "server_logs.txt"

# Gemini
client = None
GEMINI_AVAILABLE = False
GEMINI_ERROR = ""

if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        GEMINI_AVAILABLE = True
    except Exception as e:
        GEMINI_ERROR = str(e)
else:
    GEMINI_ERROR = "GEMINI_API_KEY not found in .env"

# Page
st.set_page_config(
    page_title="AegisOps - AI Incident Response",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# READ LIVE LOGS
# ============================================================

def read_live_logs():

    attacks = []

    if not os.path.exists(LOG_FILE):
        return attacks

    try:

        with open(LOG_FILE, "r", encoding="utf-8") as file:
            lines = file.readlines()

        for line in lines:

            if "Brute-force credential exploit attempt" not in line:
                continue

            time_match = re.search(
                r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
                line
            )

            ip_match = re.search(
                r"suspicious IP ([0-9.]+)",
                line
            )

            timestamp = (
                time_match.group(1)
                if time_match
                else "Unknown"
            )

            ip = (
                ip_match.group(1)
                if ip_match
                else "Unknown"
            )

            attacks.append({
                "timestamp": timestamp,
                "ip": ip,
                "type": "Authentication Attack",
                "severity": "HIGH",
                "endpoint": "AEGIS-LAPTOP-07",
                "status": "Investigating"
            })

    except Exception:
        return []

    return attacks


# ============================================================
# GEMINI AI
# ============================================================

SYSTEM_PROMPT = """
You are AegisOps AI Assistant.

You are a friendly, intelligent cybersecurity incident-response assistant.

Dashboard information:

Total historical incidents: 5
Active historical incidents: 3
Resolved incidents: 2

Endpoints:
AEGIS-LAPTOP-07
Windows 11
192.168.1.25

AEGIS-SERVER-03
Ubuntu 22.04
10.0.0.53

AEGIS-FW-01
FortiOS 7.4
10.0.0.1

AI Engine:
12.4M events/hour
99.7% accuracy
0.3 second response time

Rules:
- Keep answers short.
- Maximum 5-6 lines.
- Use bullets when useful.
- Be professional but friendly.
- Use 1-2 emojis maximum.
- No tables.
- No long paragraphs.
"""


def local_fallback_answer(question, latest_attack=None):
    """
    Hackathon-safe offline fallback.
    This keeps the assistant useful even if Gemini is temporarily unavailable.
    """
    q = question.lower().strip()

    if latest_attack:
        ip = latest_attack["ip"]
        endpoint = latest_attack["endpoint"]
        timestamp = latest_attack["timestamp"]
    else:
        ip = "No live attacker IP"
        endpoint = "AEGIS-LAPTOP-07"
        timestamp = "No live event"

    if any(word in q for word in ["threat", "risk", "severity", "danger"]):
        return (
            "🛡️ **Current Threat Level: HIGH (78/100)**\n\n"
            f"• Latest source: `{ip}`\n"
            f"• Endpoint: `{endpoint}`\n"
            "• Detected activity: Authentication / brute-force attack\n"
            "• Recommended action: contain the endpoint and block the suspicious source."
        )

    if any(word in q for word in ["incident", "attack", "event", "what happened"]):
        return (
            "🚨 **Latest AegisOps Incident**\n\n"
            "• Type: Authentication Attack\n"
            f"• Source IP: `{ip}`\n"
            f"• Endpoint: `{endpoint}`\n"
            f"• Time: `{timestamp}`\n"
            "• Severity: HIGH — Status: Investigating"
        )

    if any(word in q for word in ["endpoint", "server", "laptop", "firewall", "machine"]):
        return (
            "💻 **Monitored Endpoints**\n\n"
            "• AEGIS-LAPTOP-07 — Windows 11 — 192.168.1.25\n"
            "• AEGIS-SERVER-03 — Ubuntu 22.04 — 10.0.0.53\n"
            "• AEGIS-FW-01 — FortiOS 7.4 — 10.0.0.1"
        )

    if any(word in q for word in ["recommend", "recommendation", "secure", "protect", "fix", "solution"]):
        return (
            "🔐 **Recommended Response**\n\n"
            "• Block the suspicious source IP.\n"
            "• Isolate the affected endpoint if the attack continues.\n"
            "• Review authentication logs for related accounts.\n"
            "• Enable/verify MFA and rate limiting.\n"
            "• Continue monitoring for lateral movement."
        )

    if any(word in q for word in ["who", "aegisops", "project", "system"]):
        return (
            "🛡️ **AegisOps** is an AI-powered incident-response dashboard.\n\n"
            "• Monitors endpoints and security logs\n"
            "• Detects suspicious activity\n"
            "• Uses Gemini for incident analysis\n"
            "• Provides containment and recovery recommendations"
        )

    return (
        "🛡️ **AegisOps Local Incident Intelligence**\n\n"
        "Gemini is temporarily unavailable, so I'm using the dashboard's "
        "built-in incident intelligence.\n\n"
        "Ask me about **threats, incidents, endpoints, or recommendations**."
    )


def ask_gemini(question, latest_attack=None):
    if not GEMINI_API_KEY:
        return local_fallback_answer(question, latest_attack)

    if not GEMINI_AVAILABLE or client is None:
        return local_fallback_answer(question, latest_attack)

    if latest_attack:
        live_context = f"""
LIVE ATTACK:

Attack Type: {latest_attack['type']}
Source IP: {latest_attack['ip']}
Endpoint: {latest_attack['endpoint']}
Time: {latest_attack['timestamp']}
Severity: HIGH
Status: Investigating
"""
    else:
        live_context = """
LIVE ATTACK:
No live attack detected currently.
"""

    prompt = f"""
{SYSTEM_PROMPT}

{live_context}

User question:
{question}

Answer the user directly.
"""

    # Stable models ordered from the primary model to lightweight fallbacks.
    # If one model is temporarily overloaded, try another.
    models = [
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
    ]

    last_error = ""

    for model_name in models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )

                if response and response.text:
                    return response.text

                last_error = "Empty response from Gemini."

            except Exception as e:
                last_error = str(e)

                # Retry only temporary/service/rate-limit failures.
                temporary = any(code in last_error for code in [
                    "503",
                    "UNAVAILABLE",
                    "429",
                    "RESOURCE_EXHAUSTED",
                    "500",
                    "INTERNAL",
                    "504",
                    "DEADLINE_EXCEEDED",
                    "timeout",
                    "Timeout",
                ])

                if not temporary:
                    # Invalid key, permission, malformed request, etc.
                    # Do not waste time retrying the same bad request.
                    return local_fallback_answer(question, latest_attack)

                if attempt == 0:
                    # Small exponential backoff + jitter.
                    time.sleep(1.5 + random.uniform(0, 1.0))

    # IMPORTANT: never leave the hackathon demo with a raw Gemini error.
    return local_fallback_answer(question, latest_attack)


# ============================================================
# CSS  (rendered ONCE — no longer re-injected every refresh)
# ============================================================

st.markdown(
"""
<style>

@import url(
'https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800;900&display=swap'
);

.stApp {

    background:
    linear-gradient(
        135deg,
        #fdf2f8,
        #ede9fe,
        #e0f2fe,
        #ecfdf5,
        #fef3c7
    );

    background-size:400% 400%;

    animation:bgShift 15s ease infinite;

    font-family:'Nunito',sans-serif !important;
}

@keyframes bgShift {

    0% {
        background-position:0% 50%;
    }

    50% {
        background-position:100% 50%;
    }

    100% {
        background-position:0% 50%;
    }

}

#MainMenu,
footer,
header {

    visibility:hidden;
}

.stApp p,
.stApp span,
.stApp div,
.stApp li {

    font-family:'Nunito',sans-serif !important;
    color:#1e1b4b;
}

h1,h2,h3 {

    font-family:'Nunito',sans-serif !important;
    color:#4c1d95 !important;
}


/* HEADER */

.aegis-header {

    background:rgba(255,255,255,.92);

    border:
    2px solid
    rgba(199,146,234,.2);

    border-radius:24px;

    padding:28px 36px;

    margin-bottom:28px;

    display:flex;

    justify-content:space-between;

    align-items:center;

    position:relative;

    overflow:hidden;

    box-shadow:
    0 8px 32px
    rgba(199,146,234,.12);
}

.aegis-header:before {

    content:'';

    position:absolute;

    top:0;
    left:0;
    right:0;

    height:5px;

    background:
    linear-gradient(
        90deg,
        #c084fc,
        #60a5fa,
        #f472b6,
        #34d399,
        #fbbf24
    );

    background-size:300% 100%;

    animation:sweep 4s linear infinite;
}

@keyframes sweep {

    0% {
        background-position:0%;
    }

    100% {
        background-position:300%;
    }

}

.logo-title {

    font-size:38px !important;

    font-weight:900 !important;

    margin:0;

    background:
    linear-gradient(
        90deg,
        #7c3aed,
        #ec4899,
        #3b82f6,
        #7c3aed
    );

    background-size:300% 100%;

    -webkit-background-clip:text;

    -webkit-text-fill-color:transparent;

    animation:gradient 4s ease infinite;
}

@keyframes gradient {

    0%,100% {
        background-position:0%;
    }

    50% {
        background-position:100%;
    }

}

.logo-subtitle {

    font-size:14px !important;

    color:#7c3aed !important;

    text-transform:uppercase;

    letter-spacing:3px;

    font-weight:700;
}

.live-badge,
.status-badge {

    display:inline-flex;

    align-items:center;

    gap:8px;

    padding:10px 16px;

    border-radius:20px;

    font-weight:800;

    margin-left:8px;
}

.live-badge {

    background:#fce7f3;

    color:#be185d !important;
}

.status-badge {

    background:#d1fae5;

    color:#047857 !important;
}

.dot {

    width:10px;
    height:10px;

    border-radius:50%;

    display:inline-block;

    background:#ec4899;

    animation:pulse 1.3s infinite;
}

.green {

    background:#10b981;
}

@keyframes pulse {

    50% {

        transform:scale(1.2);

        box-shadow:
        0 0 0 8px
        rgba(236,72,153,0);
    }

}


/* CARDS */

.stat-card {

    background:
    rgba(255,255,255,.92);

    border:
    2px solid
    rgba(199,146,234,.15);

    border-radius:22px;

    padding:26px 18px;

    text-align:center;

    transition:.3s;
}

.stat-card:hover {

    transform:
    translateY(-7px);

    box-shadow:
    0 16px 40px
    rgba(124,58,237,.15);
}

.stat-icon {

    font-size:38px !important;
}

.stat-value {

    font-size:40px !important;

    font-weight:900 !important;
}

.stat-label {

    font-size:13px !important;

    color:#6d28d9 !important;

    text-transform:uppercase;

    letter-spacing:2px;

    font-weight:800;
}


/* PANELS */

.panel,
.ai-panel,
.endpoint-card {

    background:
    rgba(255,255,255,.92);

    border:
    2px solid
    rgba(199,146,234,.15);

    border-radius:22px;

    padding:30px;

    margin-bottom:20px;

    box-shadow:
    0 8px 25px
    rgba(199,146,234,.08);
}

.ai-panel {

    position:relative;

    overflow:hidden;
}

.ai-panel:before {

    content:'';

    position:absolute;

    top:0;
    left:0;
    right:0;

    height:5px;

    background:
    linear-gradient(
        90deg,
        #c084fc,
        #60a5fa,
        #34d399,
        #fbbf24
    );

    background-size:200%;

    animation:sweep 3s linear infinite;
}

.panel-title {

    font-size:16px !important;

    font-weight:900 !important;

    text-transform:uppercase;

    letter-spacing:2px;

    color:#6d28d9 !important;

    padding-bottom:14px;

    border-bottom:
    2px solid
    rgba(199,146,234,.1);

    margin-bottom:18px;
}

.severity-high {

    display:inline-block;

    background:
    linear-gradient(
        135deg,
        #fee2e2,
        #fecaca
    );

    color:#be123c !important;

    padding:8px 18px;

    border-radius:12px;

    font-weight:900;
}


/* INCIDENT */

.incident-row {

    display:flex;

    align-items:center;

    gap:16px;

    padding:18px 22px;

    border-radius:16px;

    margin-bottom:10px;

    transition:.3s;
}

.incident-row:hover {

    transform:
    translateX(7px);

    box-shadow:
    0 5px 18px
    rgba(124,58,237,.12);
}


/* ENDPOINT */

.endpoint-card {

    min-height:220px;

    transition:.3s;
}

.endpoint-card:hover {

    transform:
    translateY(-7px);

    box-shadow:
    0 16px 40px
    rgba(124,58,237,.15);
}


/* BUTTON */

.stButton > button {

    border-radius:16px !important;

    font-weight:800 !important;

    padding:13px 20px !important;

    background:
    linear-gradient(
        135deg,
        #e9d5ff,
        #ddd6fe
    ) !important;

    color:#5b21b6 !important;

    border:
    2px solid
    #c4b5fd !important;
}

.stButton > button:hover {

    transform:translateY(-2px);

}


/* METRICS */

[data-testid="stMetricValue"] {

    color:#6d28d9 !important;

    font-weight:900 !important;
}


/* CHAT */

.stChatMessage {

    background:
    rgba(255,255,255,.9) !important;

    border:
    1px solid
    #e9d5ff !important;

    border-radius:16px !important;
}

</style>
""",
unsafe_allow_html=True
)


# ============================================================
# HEADER  (rendered ONCE — no longer re-injected every refresh)
# ============================================================

st.markdown(
"""
<div class="aegis-header">

<div style="display:flex;align-items:center;gap:16px">

<div style="
width:56px;
height:56px;
background:linear-gradient(135deg,#c084fc,#60a5fa);
border-radius:16px;
display:flex;
align-items:center;
justify-content:center;
font-size:30px;
">

🛡️

</div>

<div>

<p class="logo-title">
AEGISOPS
</p>

<p class="logo-subtitle">
AI Incident Response & Threat Management
</p>

</div>

</div>

<div>

<span class="live-badge">
<span class="dot"></span>
LIVE
</span>

<span class="status-badge">
<span class="dot green"></span>
OPERATIONAL
</span>

</div>

</div>
""",
unsafe_allow_html=True
)


# ============================================================
# LIVE DASHBOARD FRAGMENT
# Only this part reruns every 5s. The CSS/header above stay
# mounted, so the gradient/pulse animations never restart and
# the page no longer flashes.
# ============================================================

@st.fragment(run_every=5)
def render_live_dashboard():

    live_attacks = read_live_logs()

    latest_attack = (
        live_attacks[-1]
        if live_attacks
        else None
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📊 Overview",
        "🚨 Incidents",
        "💻 Endpoints",
        "🤖 AI Analysis",
        "💬 AI Assistant"
    ]
    )

    # ============================================================
    # TAB 1 — OVERVIEW
    # ============================================================

    with tab1:

        total_incidents = 5 + len(live_attacks)

        c1,c2,c3,c4,c5 = st.columns(5)

        cards = [

            ("🚨",total_incidents,"Incidents","#f9a8d4"),

            (
                "🔥",
                3 + len(live_attacks),
                "High Severity",
                "#fcd34d"
            ),

            ("✅",2,"Resolved","#6ee7b7"),

            ("💻",3,"Endpoints","#c4b5fd"),

            ("🤖","ON","AI Active","#93c5fd")

        ]

        for col,card in zip(
            [c1,c2,c3,c4,c5],
            cards
        ):

            icon,value,label,border = card

            with col:

                st.markdown(
                f"""
                <div class="stat-card"
                style="border-bottom:5px solid {border}">

                <div class="stat-icon">
                {icon}
                </div>

                <div class="stat-value">
                {value}
                </div>

                <div class="stat-label">
                {label}
                </div>

                </div>
                """,
                unsafe_allow_html=True
                )


        st.markdown("<br>",unsafe_allow_html=True)


        left,right = st.columns(2)


        # LIVE INCIDENT
        with left:

            if latest_attack:

                st.markdown(
                f"""
                <div class="panel">

                <div class="panel-title">
                🚨 LIVE ACTIVE INCIDENT
                </div>

                <div class="severity-high">
                ⚠️ HIGH SEVERITY
                </div>

                <h3>
                Authentication Attack
                </h3>

                <p style="line-height:1.8">

                Brute-force credential attack detected
                against

                <b>
                {latest_attack["endpoint"]}
                </b>

                from suspicious IP

                <b>
                {latest_attack["ip"]}
                </b>

                </p>

                <div style="
                padding:12px;
                background:#faf5ff;
                border-radius:12px;
                ">

                🕐
                {latest_attack["timestamp"]}

                &nbsp; | &nbsp;

                🔴
                <b>
                INVESTIGATING
                </b>

                </div>

                </div>
                """,
                unsafe_allow_html=True
                )

            else:

                st.markdown(
                """
                <div class="panel">

                <div class="panel-title">
                🛡️ LIVE MONITOR
                </div>

                <h3>
                Waiting for live attacks...
                </h3>

                <p>
                Start your attacker simulator to generate
                safe test incidents.
                </p>

                </div>
                """,
                unsafe_allow_html=True
                )


        # ENDPOINT
        with right:

            current_ip = (
                latest_attack["ip"]
                if latest_attack
                else "Waiting..."
            )

            st.markdown(
            f"""
            <div class="panel">

            <div class="panel-title">
            💻 AFFECTED ENDPOINT
            </div>

            <p>
            <b>Hostname</b><br>
            AEGIS-LAPTOP-07
            </p>

            <p>
            <b>Operating System</b><br>
            Windows 11
            </p>

            <p>
            <b>Endpoint IP</b><br>
            192.168.1.25
            </p>

            <p>
            <b>Latest Attacker IP</b><br>
            {current_ip}
            </p>

            </div>
            """,
            unsafe_allow_html=True
            )


        # AI INVESTIGATION
        st.markdown(
        """
        <div class="ai-panel">

        <div class="panel-title">
        🧠 AI-POWERED INVESTIGATION
        </div>

        <div style="
        display:grid;
        grid-template-columns:
        repeat(3,1fr);
        gap:20px;
        ">

        <div style="
        background:#faf5ff;
        padding:24px;
        border-radius:18px;
        text-align:center;
        ">

        <b>ROOT CAUSE</b>

        <h3>
        Credential Attack
        </h3>

        </div>


        <div style="
        background:#faf5ff;
        padding:24px;
        border-radius:18px;
        text-align:center;
        ">

        <b>CONFIDENCE</b>

        <h3>
        94%
        </h3>

        </div>


        <div style="
        background:#fff1f2;
        padding:24px;
        border-radius:18px;
        text-align:center;
        ">

        <b>
        RISK LEVEL
        </b>

        <h3>
        Critical
        </h3>

        </div>

        </div>

        </div>
        """,
        unsafe_allow_html=True
        )


        st.markdown("<br>",unsafe_allow_html=True)


        b1,b2,b3 = st.columns(3)


        with b1:

            if st.button(
                "🛑 CONTAIN THREAT",
                use_container_width=True
            ):

                st.success(
                    "Containment protocol initiated."
                )


        with b2:

            if st.button(
                "🔍 DEEP INVESTIGATE",
                use_container_width=True
            ):

                st.info(
                    f"AI analyzing {len(live_attacks)} live events."
                )


        with b3:

            if st.button(
                "🟢 START RECOVERY",
                use_container_width=True
            ):

                st.success(
                    "Recovery process initiated."
                )


    # ============================================================
    # TAB 2 — INCIDENTS
    # ============================================================

    with tab2:

        st.subheader("🚨 Live Incidents")


        if live_attacks:

            for index,attack in enumerate(
                reversed(live_attacks[-10:])
            ):

                incident_number = (
                    len(live_attacks)
                    - index
                )

                st.markdown(
                f"""
                <div class="incident-row"

                style="
                background:
                linear-gradient(
                135deg,
                #fff1f2,
                #ffe4e6
                );

                border:
                2px solid
                rgba(225,29,72,.15);
                ">

                <span style="
                font-family:monospace;
                font-weight:900;
                ">

                LIVE-{incident_number:03d}

                </span>


                <span style="
                flex:1;
                font-weight:800;
                ">

                🚨
                Authentication Attack

                </span>


                <span style="
                background:#fecaca;
                padding:6px 12px;
                border-radius:8px;
                font-weight:900;
                ">

                HIGH

                </span>


                <span style="
                color:#be123c;
                font-weight:800;
                ">

                Investigating

                </span>

                </div>


                <div style="
                padding:
                2px 20px 14px;
                color:#6d28d9 !important;
                ">

                🕐
                {attack["timestamp"]}

                &nbsp; | &nbsp;

                🌐
                Source IP:
                <b>
                {attack["ip"]}
                </b>

                &nbsp; | &nbsp;

                💻
                {attack["endpoint"]}

                </div>
                """,
                unsafe_allow_html=True
                )

        else:

            st.info(
                "🛡️ No live attacks detected. "
                "Run attacker_simulator.py."
            )


        st.divider()


        st.subheader(
            "Historical Incidents"
        )


        history = [

            (
                "INC-001",
                "Authentication Attack",
                "Investigating"
            ),

            (
                "INC-002",
                "Malware Detection",
                "Investigating"
            ),

            (
                "INC-003",
                "Network Intrusion",
                "Investigating"
            ),

            (
                "INC-004",
                "Privilege Escalation",
                "Resolved"
            ),

            (
                "INC-005",
                "Data Exfiltration",
                "Resolved"
            )

        ]


        for inc_id,name,status in history:

            color = (
                "#047857"
                if status == "Resolved"
                else "#be123c"
            )

            st.markdown(
            f"""
            <div class="incident-row"
            style="
            background:#faf5ff;
            border:
            2px solid #eee7ff;
            ">

            <span style="
            font-family:monospace;
            font-weight:900;
            ">

            {inc_id}

            </span>

            <span style="
            flex:1;
            font-weight:800;
            ">

            {name}

            </span>

            <span style="
            color:{color} !important;
            font-weight:800;
            ">

            {status}

            </span>

            </div>
            """,
            unsafe_allow_html=True
            )


    # ============================================================
    # TAB 3 — ENDPOINTS
    # ============================================================

    with tab3:

        st.subheader(
            "💻 Monitored Endpoints"
        )


        endpoints = [

            (
                "AEGIS-LAPTOP-07",
                "Windows 11",
                "192.168.1.25",
                "At Risk",
                "💻",
                "#f9a8d4"
            ),

            (
                "AEGIS-SERVER-03",
                "Ubuntu 22.04",
                "10.0.0.53",
                "Monitoring",
                "🖥️",
                "#fcd34d"
            ),

            (
                "AEGIS-FW-01",
                "FortiOS 7.4",
                "10.0.0.1",
                "Monitoring",
                "🔥",
                "#c4b5fd"
            )

        ]


        columns = st.columns(3)


        for column,endpoint in zip(
            columns,
            endpoints
        ):

            name,os_name,ip,status,icon,border = endpoint

            with column:

                st.markdown(
                f"""
                <div class="endpoint-card"
                style="
                border-top:
                5px solid {border};
                ">

                <div style="
                font-size:42px;
                ">

                {icon}

                </div>

                <h3>
                {name}
                </h3>

                <p>
                {os_name}
                <br>
                {ip}
                </p>

                <b>
                {status}
                </b>

                </div>
                """,
                unsafe_allow_html=True
                )


    # ============================================================
    # TAB 4 — AI ANALYSIS
    # ============================================================

    with tab4:

        st.markdown(
        """
        <div class="panel"
        style="
        text-align:center;
        padding:45px;
        ">

        <div style="
        font-size:60px;
        ">
        🧠
        </div>

        <h2>
        Neural Threat Engine Active
        </h2>

        <p>
        AI models continuously analyze
        network patterns, logs and
        threat activity.
        </p>

        </div>
        """,
        unsafe_allow_html=True
        )


        m1,m2,m3 = st.columns(3)


        with m1:

            st.metric(
                "Events / Hour",
                "12.4M"
            )


        with m2:

            st.metric(
                "Accuracy",
                "99.7%"
            )


        with m3:

            st.metric(
                "Response Time",
                "0.3s"
            )


        st.progress(
            78,
            text="Overall Threat Level: HIGH (78/100)"
        )


        if latest_attack:

            st.success(
                f"🚨 Live attack detected from "
                f"{latest_attack['ip']} "
                f"at {latest_attack['timestamp']}."
            )


    # ============================================================
    # TAB 5 — AI CHAT
    # ============================================================

    with tab5:

        st.markdown(
        """
        <div class="panel"
        style="
        text-align:center;
        ">

        <div style="
        font-size:55px;
        ">
        🤖
        </div>

        <h2>
        AegisOps AI Assistant
        </h2>

        <p>
        Ask about incidents, threats,
        endpoints or security recommendations.
        </p>

        </div>
        """,
        unsafe_allow_html=True
        )


        if GEMINI_AVAILABLE:

            st.success(
                "🟢 Gemini AI Online"
            )

        else:

            st.error(
                "🔴 Gemini AI Offline"
            )


        if "messages" not in st.session_state:

            st.session_state.messages = [

                {
                    "role":"assistant",

                    "content":
                    "Hey! 💜 I'm your **AegisOps AI Assistant**.\n\n"
                    "Ask me about the live incidents, "
                    "threats, endpoints or security recommendations."
                }

            ]


        for message in st.session_state.messages:

            if message["role"] == "user":
                avatar = "👩‍💻"
            else:
                avatar = "🤖"

            with st.chat_message(
                message["role"],
                avatar=avatar
            ):

                st.markdown(
                    message["content"]
                )


        prompt = st.chat_input(
            "Ask AegisOps AI..."
        )


        if prompt:

            st.session_state.messages.append(
            {
                "role":"user",
                "content":prompt
            }
            )


            with st.chat_message("user", avatar="👩‍💻"):

                st.markdown(prompt)


            with st.chat_message("assistant", avatar="🤖"):

                with st.spinner(
                    "🧠 AegisOps AI is thinking..."
                ):

                    answer = ask_gemini(
                        prompt,
                        latest_attack
                    )

                st.markdown(answer)


            st.session_state.messages.append(
            {
                "role":"assistant",
                "content":answer
            }
            )


render_live_dashboard()
