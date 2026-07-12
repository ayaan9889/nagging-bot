import telebot
import google.generativeai as genai
import time
import threading
import os
from flask import Flask

# Render ke environment variables se tokens uthana (100% Secure)
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

active_tasks = {} 

app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def nagging_loop(chat_id, task_name):
    while active_tasks.get(chat_id) == "PENDING":
        prompt = f"Mujhe apne dost ko yaad dilana hai ki uska kaam '{task_name}' pending hai. Wo reply nahi kar raha. Ek desi, friendly aur thoda tokne wala short text message likho hindi/hinglish me. Aisa bano jaise saccha dost daant raha ho."
        try:
            response = model.generate_content(prompt)
            bot.send_message(chat_id, response.text)
        except Exception as e:
            bot.send_message(chat_id, f"Bhai kaam yaad dila raha hu: {task_name}")
        time.sleep(900) 

@bot.message_handler(func=lambda message: True)
def handle_chat(message):
    text = message.text.lower()
    chat_id = message.chat.id
    
    if "done" in text or "ho gaya" in text or "khatam" in text:
        active_tasks[chat_id] = "DONE"
        bot.send_message(chat_id, "Mast bhai! Task completed. 👍 Ab mai shant hu.")
    else:
        prompt = f"Is message se task extract karo: '{message.text}'. Mujhe bas task ka naam do short me, koi extra text mat likhna."
        try:
            task_name = model.generate_content(prompt).text
        except:
            task_name = message.text
            
        active_tasks[chat_id] = "PENDING"
        bot.send_message(chat_id, f"Theek hai bhai, '{task_name.strip()}' yaad rakhunga aur tab tak piche pada rahunga!")
        threading.Thread(target=nagging_loop, args=(chat_id, task_name)).start()

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.polling()
