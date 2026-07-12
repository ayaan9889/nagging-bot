import telebot
import google.generativeai as genai
import time
import threading

# --- CONFIGURATION ---
# Yahan apne dono tokens daalna mat bhoolna
BOT_TOKEN = "8804710104:AAFdJQstVTI0c3loUxo7fp_l6rWzgRJ6WLw"
GEMINI_KEY = "AQ.Ab8RN6LvUVtFcSLmPghKov5JmsfOqOW5NvaL58rPgcLUp3g8jw"
# ---------------------

bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

active_tasks = {} 

def nagging_loop(chat_id, task_name):
    # Jab tak task ka status PENDING rahega, ye loop chalta rahega
    while active_tasks.get(chat_id) == "PENDING":
        # Gemini AI se har baar ek alag style ka tokne wala message generate karwana
        prompt = f"Mujhe apne dost ko yaad dilana hai ki uska kaam '{task_name}' pending hai. Wo reply nahi kar raha. Ek desi, friendly aur thoda tokne wala short text message likho hindi/hinglish me. Aisa bano jaise saccha dost daant raha ho."
        try:
            response = model.generate_content(prompt)
            bot.send_message(chat_id, response.text)
        except Exception as e:
            bot.send_message(chat_id, f"Bhai kaam yaad dila raha hu: {task_name}")
        
        # Har 15 minute (900 seconds) baad dobara poochega. 
        # Testing ke liye aap ise 60 seconds (1 minute) bhi kar sakte ho.
        time.sleep(900) 

@bot.message_handler(func=lambda message: True)
def handle_chat(message):
    text = message.text.lower()
    chat_id = message.chat.id
    
    if "done" in text or "ho gaya" in text or "khatam" in text:
        active_tasks[chat_id] = "DONE"
        bot.send_message(chat_id, "Mast bhai! Task completed. 👍 Ab mai shant hu.")
    else:
        # Gemini AI khud text se main task nikalega
        prompt = f"Is message se task extract karo: '{message.text}'. Mujhe bas task ka naam do short me, koi extra text mat likhna."
        try:
            task_name = model.generate_content(prompt).text
        except:
            task_name = message.text
            
        active_tasks[chat_id] = "PENDING"
        bot.send_message(chat_id, f"Theek hai bhai, '{task_name.strip()}' yaad rakhunga aur tab tak piche pada rahunga jab tak khatam nahi hota!")
        
        # Background me nagging loop shuru karna
        threading.Thread(target=nagging_loop, args=(chat_id, task_name)).start()

bot.polling()
