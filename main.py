import telebot
import google.generativeai as genai
import time
import threading
import os
import json
from datetime import datetime, timedelta
from flask import Flask

# Secure tokens (Render Environment se)
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN") 
GEMINI_KEY = os.environ.get("GEMINI_API_KEY") 

bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Store tasks per chat_id
# Structure: active_tasks[chat_id] = {"Task Name": {"status": "pending"}}
active_tasks = {}

app = Flask(__name__)
@app.route('/')
def home():
    return "AI Agent is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def get_ist_time():
    # Render servers UTC par hote hain, hume IST (+5:30) chahiye
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

def reminder_thread(chat_id, task_name, delay_min, nag_interval_min):
    # Agar delay manga hai (e.g. "2 ghante baad yaad dilana")
    if delay_min > 0:
        time.sleep(delay_min * 60)
        
    # Check if task was completed or cancelled during the wait
    if chat_id not in active_tasks or task_name not in active_tasks.get(chat_id, {}):
        return

    # Pehla Reminder
    try:
        bot.send_message(chat_id, f"🚨 Bhai yaad dila raha hu, tumhara task pending hai: **{task_name}**\n\n(Kaam ho jaye to 'done' bol dena)")
    except:
        pass

    # Agar loop wala nagging maanga hai (e.g. "har 10 min me yaad dilana")
    if nag_interval_min > 0:
        while chat_id in active_tasks and task_name in active_tasks.get(chat_id, {}):
            time.sleep(nag_interval_min * 60)
            
            # Wapas check karo loop chalne ke baad
            if chat_id not in active_tasks or task_name not in active_tasks.get(chat_id, {}):
                break
                
            prompt = f"Mera dost B.Tech Cybersecurity ka student hai. Usne '{task_name}' nahi kiya hai. Ek short, funny aur chidhne wala text message likho hinglish me use daantne ke liye."
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

    # AI Brain Setup - Instructing Gemini to parse intents strictly
    sys_prompt = f"""
    You are a smart AI assistant. Read the user's message and determine what they want.
    Current Date & Time in IST: {current_time_str}
    
    You MUST respond ONLY with a raw JSON object (no markdown, no formatting).
    Analyze the intent and provide these fields:
    - "action": strictly one of ["chat", "set_reminder", "mark_done"]
    - "reply": "Your conversational response in Hinglish/Hindi based on the action."
    - "task_name": "Short extracted name of the task" (only if action is set_reminder, otherwise empty string)
    - "delay_minutes": integer. If the user specifies a time (e.g., 'at 5 PM', 'after 2 hours'), calculate the difference from current time in minutes. If they want it immediately or don't specify a wait time, output 0.
    - "nag_interval_minutes": integer. If the user explicitly asks to repeat the reminder (e.g., 'har 10 min me', 'bar bar batana'), put that number in minutes. Default is 0.

    User Message: "{text}"
    """
    
    try:
        response = model.generate_content(sys_prompt).text.strip()
        
        # Cleaning JSON format if Gemini adds markdown blocks
        if response.startswith("```json"):
            response = response[7:-3]
        elif response.startswith("```"):
            response = response[3:-3]
            
        data = json.loads(response.strip())
        
        action = data.get("action", "chat")
        reply_text = data.get("reply", "Haan bhai, sun raha hu.")
        task_name = data.get("task_name", "")
        delay_min = int(data.get("delay_minutes", 0))
        nag_interval_min = int(data.get("nag_interval_minutes", 0))

        if action == "mark_done":
            # Clear all tasks for this user (simplest approach for now)
            if chat_id in active_tasks:
                active_tasks[chat_id] = {}
            bot.send_message(chat_id, reply_text)
            
        elif action == "set_reminder":
            if chat_id not in active_tasks:
                active_tasks[chat_id] = {}
            
            active_tasks[chat_id][task_name] = {"status": "pending"}
            bot.send_message(chat_id, reply_text)
            
            # Start a background thread specifically for this task's timing
            threading.Thread(target=reminder_thread, args=(chat_id, task_name, delay_min, nag_interval_min)).start()
            
        else:
            # Normal AI Chat
            bot.send_message(chat_id, reply_text)

    except Exception as e:
        # Fallback if JSON parsing fails or API issue occurs
        try:
            bot.send_message(chat_id, model.generate_content(f"User said: {text}. Reply in Hinglish conversationally.").text)
        except:
            bot.send_message(chat_id, "Bhai abhi network error hai, thodi der me try karna.")

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.polling(none_stop=True)
