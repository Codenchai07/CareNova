# chatbot_flow.py

from collections import defaultdict

# In-memory user session storage (replace with DB or session in production)
user_sessions = defaultdict(dict)

def initialize_session(user_id):
    user_sessions[user_id] = {
        "stage": "ask_symptom",
        "symptoms": [],
        "days": None,
        "followup_done": False
    }

def handle_message(user_id, message):
    if user_id not in user_sessions:
        initialize_session(user_id)

    session = user_sessions[user_id]
    stage = session["stage"]

    # Stage 1: Ask for symptoms
    if stage == "ask_symptom":
        session["symptoms"] = [s.strip().lower() for s in message.split(",")]
        session["stage"] = "ask_days"
        return "For how many days have you had these symptoms?"

    # Stage 2: Ask for duration
    elif stage == "ask_days":
        try:
            session["days"] = int(message.strip())
        except ValueError:
            return "Please enter the number of days as a number (e.g., 3)."
        session["stage"] = "followup"
        return "Are you experiencing any pain or discomfort? (yes/no)"

    # Stage 3: Simple follow-up
    elif stage == "followup":
        session["followup_done"] = True
        session["stage"] = "final"
        return evaluate_symptoms(session)

    return "Sorry, I didn't understand. Please start over."

def evaluate_symptoms(session):
    symptoms = session["symptoms"]
    days = session["days"]

    # Dummy logic (replace with model logic)
    if "fever" in symptoms and "cough" in symptoms:
        if days > 2:
            return "You may have flu or viral infection. Please consult a doctor."
        else:
            return "It might be a common cold. Monitor your condition."

    return "Your symptoms don't match any known pattern. Please consult a doctor."
