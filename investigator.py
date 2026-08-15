from pathlib import Path


LOG_FILE = Path("logs/server.log")


def read_logs():
    if not LOG_FILE.exists():
        print("❌ Log file not found!")
        return []

    with open(LOG_FILE, "r", encoding="utf-8") as file:
        return file.readlines()


def investigate_incident(line):
    line_lower = line.lower()

    # Security incidents
    if "failed login" in line_lower or "suspicious activity" in line_lower:
        return {
            "type": "🔐 Security Incident",
            "severity": "HIGH",
            "cause": "Multiple failed authentication attempts or suspicious user activity detected.",
            "action": "Review authentication logs, verify the source IP, and temporarily restrict suspicious access."
        }

    # Web server incidents
    elif "nginx" in line_lower or "web service" in line_lower:
        return {
            "type": "🌐 Web Server Incident",
            "severity": "HIGH",
            "cause": "The web server could not start or bind to the required network port.",
            "action": "Check which process is using the required port and resolve the conflict before restarting the web server."
        }

    # Database incidents
    elif "database" in line_lower:
        return {
            "type": "🗄️ Database Incident",
            "severity": "HIGH",
            "cause": "A database-related error was detected in the server logs.",
            "action": "Check database connectivity, service status, credentials, and recent database errors."
        }

    # General errors
    elif "error" in line_lower:
        return {
            "type": "⚠️ General System Error",
            "severity": "MEDIUM",
            "cause": "An unexpected system error was detected.",
            "action": "Review the surrounding log entries and identify the service responsible for the error."
        }

    # Warnings
    elif "warning" in line_lower:
        return {
            "type": "⚠️ System Warning",
            "severity": "LOW",
            "cause": "The system reported a potentially abnormal condition.",
            "action": "Monitor the service and investigate if the warning continues."
        }

    return None


def investigate(log_lines):
    print("\n🔎 AegisOps Incident Investigator")
    print("=" * 60)

    incident_number = 0

    for line in log_lines:
        line = line.strip()

        if "ERROR" in line or "WARNING" in line:

            report = investigate_incident(line)

            if report:
                incident_number += 1

                print(f"\n🚨 INCIDENT #{incident_number}")
                print("-" * 60)

                print(f"Type:              {report['type']}")
                print(f"Severity:          {report['severity']}")
                print(f"\nLog Entry:")
                print(line)

                print(f"\nProbable Cause:")
                print(report["cause"])

                print(f"\nRecommended Action:")
                print(report["action"])

    print("\n" + "=" * 60)
    print(f"Investigation complete. Incidents analyzed: {incident_number}")


if __name__ == "__main__":
    logs = read_logs()
    investigate(logs)