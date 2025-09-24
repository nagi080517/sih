

# Backend/general.py
import ollama
import datetime
import json
import os

SYSTEM_PROMPT = (
    "You are a Railway Complaint Analyzer AI. "
    "Your job is to listen carefully to passenger complaints, "
    "record them clearly, and maintain a structured log. "
    "If a complaint is serious (safety, harassment, medical, accident, fire, etc.), "
    "flag it as URGENT and summarize it in one short line for immediate action. "
    "If the issue is normal (maintenance, cleanliness, comfort, etc.), "
    "save it separately as a NORMAL complaint log. "
    "Always respond politely and empathetically, making the user feel heard."
)

# Paths for logs
CHAT_LOG_FILE = "chat_logs.json"
URGENT_LOG_FILE = "urgent_logs.json"
NORMAL_LOG_FILE = "normal_logs.json"


def save_log(file, entry):
    """Save complaint/chat log entry to JSON file."""
    logs = []
    if os.path.exists(file):
        with open(file, "r") as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                logs = []
    logs.append(entry)
    with open(file, "w") as f:
        json.dump(logs, f, indent=2)


def classify_complaint(text: str) -> dict:
    """
    Basic rule-based seriousness check.
    (Can be replaced later with an AI classifier)
    """
    urgent_keywords = [
        "accident", "fire", "fight", "harassment", "theft",
        "safety", "injury", "medical", "emergency", "threat"
    ]

    for word in urgent_keywords:
        if word in text.lower():
            return {"urgent": True, "reason": word}
    return {"urgent": False, "reason": "normal"}


def handle_complaint(prompt: str, model="gemma3:4b") -> str:
    """
    Handles railway complaints.
    - Logs all chats.
    - Flags urgent and normal issues separately.
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check seriousness
    classification = classify_complaint(prompt)

    # Get AI response
    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        options={"temperature": 0.7}
    )
    ai_reply = response["message"]["content"].strip()

    # Build full log entry
    entry = {
        "timestamp": now,
        "complaint": prompt,
        "response": ai_reply,
        "urgent": classification["urgent"],
        "reason": classification["reason"]
    }

    # Save to general chat log
    save_log(CHAT_LOG_FILE, entry)

    # If urgent, save short summary
    if classification["urgent"]:
        urgent_entry = {
            "timestamp": now,
            "summary": f"URGENT: {classification['reason'].capitalize()} issue - {prompt[:60]}..."
        }
        save_log(URGENT_LOG_FILE, urgent_entry)
    else:
        normal_entry = {
            "timestamp": now,
            "summary": f"NORMAL: {prompt[:60]}..."
        }
        save_log(NORMAL_LOG_FILE, normal_entry)

    return ai_reply


def main():
    print("🚆 Railway Complaint Analyzer (using gemma3:4b). Type 'exit' to quit.\n")
    while True:
        prompt = input("Passenger: ")
        if prompt.lower() in ["exit", "quit", "bye"]:
            print("Analyzer: Thank you. Stay safe. 👋")
            break

        try:
            response = handle_complaint(prompt)
            print(f"Analyzer: {response}\n")
        except Exception as e:
            print(f"⚠️ Error: {e}\n")


if __name__ == "__main__":
    main()
