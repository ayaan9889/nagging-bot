import telebot
import google.generativeai as genai
import time
import threading
import os
import json
from datetime import datetime, timedelta
from flask import Flask

# Secure tokens
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN") or "8004710104:AAFdJQstVTI0c3louxo7fp_16rWzgRJ6WLw"
GEMINI_KEY = os.environ.get("GEMINI_API_KEY") or "AQ.Ab8RN6LvUvtFcSLmPghKovSjmsfOqOwSNvaLS8rPgcLUp3g8jw"

bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_KEY)
# System instruction fix taaki strictly clean JSON mile
model = genai.GenerativeModel(
    'gemini-1.5-flash',
    generation_config={"response_mime_type": "application/json"}
)

active_tasks = {}

app = Flask(__name__)
@app.route('/')
def home():
    return "AI Agent is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def get_ist_time():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

def reminder_thread(chat_id, task_name, delay_min, nag_interval_min):
    if delay_min > 0:
        time.sleep(delay_min * 60)
        
    if chat_id not in active_tasks or task_name not in active_tasks.get(chat_id, {}):
        return

    try:
        bot.send_message(chat_id, f"🚨 Bhai yaad dila raha hu, tumhara task pending hai: **{task_name}**\n\n(Kaam ho jaye to 'done' bol dena)")
    except:
        pass

    if nag_interval_min > 0:
        while chat_id in active_tasks and task_name in active_tasks.get(chat_id, {}):
            time.sleep(nag_interval_min * 60)
            if chat_id not in active_tasks or task_name not in active_tasks.get(chat_id, {}):
                break
            prompt = f"Mera dost B.Tech ka student hai. Usne '{task_name}' nahi kiya hai. Ek short, funny aur chidhne wala text message likho hinglish me use daantne ke liye."
            try:
                res = model.generate_content(prompt).text
                bot.send_message(chat_id, res)
            except:
                bot.send_message(chat_id, f"Abe oye! '{task_name}' abhi tak pending hai, kya kar raha hai bhai?")

@bot.message_handler(func=lambda message: True)
def handle_chat(message):
    text = message.text
    chat_id = message.chat.id
    current_time_str = get_ist_time().strftime('%Y-%m-%d %I:%M %p')

    # Explicit format guide inside prompt as well
    sys_prompt = f"""
    You are a smart AI assistant. Read the user's message and determine what they want.
    Current Date & Time in IST: {current_time_str}
    
    You MUST respond ONLY with a raw JSON object matching this structure perfectly:
    {{
      "action": "chat" OR "set_reminder" OR "mark_done",
      "reply": "Your conversational response in Hinglish/Hindi based on the action.",
      "task_name": "Short extracted name of the task (or empty string if not a reminder)",
      "delay_minutes": integer_value,
      "nag_interval_minutes": integer_value
    }}

    Rules:
    - If user wants to set a reminder (explicitly says "yaad dilana", "task hai"), set action to "set_reminder".
    - Calculate delay_minutes relative to {current_time_str}. If immediately or not specified, use 0.
    - If user wants nagging updates (e.g. 'har 10 min me'), set nag_interval_minutes. Default is 0.
    - If user says 'done', 'ho gaya', 'khatam', set action to "mark_done".
    - For everything else (general talk, questions, greetings), set action to "chat".

    User Message: "{text}"
    """
    
    try:
        response_text = model.generate_content(sys_prompt).text.strip()
        data = json.loads(response_text)
        
        action = data.get("action", "chat")
        reply_text = data.get("reply", "Haan bhai, sun raha hu.")
        task_name = data.get("task_name", "")
        delay_min = int(data.get("delay_minutes", 0))
        nag_interval_min = int(data.get("nag_interval_minutes", 0))

        if action == "mark_done":
            if chat_id in active_tasks:
                active_tasks[chat_id] = {}
            bot.send_message(chat_id, reply_text)
            
        elif action == "set_reminder":
            if chat_id not in active_tasks:
                active_tasks[chat_id] = {}
            active_tasks[chat_id][task_name] = {"status": "pending"}
            bot.send_message(chat_id, reply_text)
            threading.Thread(target=reminder_thread, args=(chat_id, task_name, delay_min, nag_interval_min)).start()
            
        else:
            bot.send_message(chat_id, reply_text)

    except Exception as e:
        # Fallback raw chat if JSON fails, prints error in logs to troubleshoot
        print(f"JSON Parsing failed: {e}")
        try:
            fallback_res = model.generate_content(f"User said: {text}. Reply in Hinglish conversationally as a friend.").text
            bot.send_message(chat_id, fallback_res)
        except Exception as gemini_err:
            print(f"Gemini completely failed: {gemini_err}")
            bot.send_message(chat_id, "Bhai API side se dikkat hai, Render Environment check karo.")

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.polling(none_stop=True)
