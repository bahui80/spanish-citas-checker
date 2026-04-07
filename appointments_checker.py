import os
import time
import requests
import random
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Force Timezone for PST
os.environ['TZ'] = 'America/Los_Angeles'
if hasattr(time, 'tzset'):
    time.tzset()

def send_telegram_msg(message):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def send_telegram_photo(caption):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id: return

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open("screenshot.png", "rb") as photo:
            files = {"photo": photo}
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}
            requests.post(url, files=files, data=data)
    except Exception as e:
        print(f"Failed to send photo: {e}")

def check_appointments():
    # Anti-detection Jitter: Wait 10-60 seconds
    wait_jitter = random.randint(10, 60)
    print(f"Waiting {wait_jitter}s to look human...")
    time.sleep(wait_jitter)

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 30)

    timestamp = datetime.now().strftime('%I:%M %p PST')

    try:
        print("🔗 Loading Widget...")
        driver.get("https://www.citaconsular.es/es/hosteds/widgetdefault/2d7c60f44f450863fb149b64fdd4b74a1/#services")
        time.sleep(5) # Allow JS to initialize

        # Save a screenshot of the initial load
        driver.save_screenshot("screenshot.png")

        # Step 1: Look for any "Aceptar" or "Continuar" buttons
        try:
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Ok') or contains(., 'Aceptar') or contains(., 'Continuar')]")))
            btn.click()
            print("Initial button clicked.")
            time.sleep(2)
        except:
            print("No initial popup found.")

        # Step 2: Final Check
        page_text = driver.page_source
        negative_phrases = ["No hay horas disponibles", "No hay citas", "No hay fechas"]

        found_negative = any(phrase in page_text for phrase in negative_phrases)

        if found_negative:
            print(f"Result: No appointments at {timestamp}")
            # Optional: Heartbeat (Uncomment to get a message every run)
            # send_telegram_msg(f"✅ *System Online*\nTime: {timestamp}\nStatus: No appointments.")
        else:
            # If the negative phrase is NOT found, send a screenshot immediately!
            driver.save_screenshot("screenshot.png")
            alert_msg = f"🚨 *POSSIBLE SLOT DETECTED!* 🚨\nTime: {timestamp}\nThe usual 'No slots' message was not found. Look at the attached image!"
            send_telegram_photo(alert_msg)

    except Exception as e:
        driver.save_screenshot("screenshot.png")
        error_msg = f"⚠️ *Bot Error* at {timestamp}\nDetails: `{str(e)[:100]}...`"
        send_telegram_photo(error_msg)
    finally:
        driver.quit()

if __name__ == "__main__":
    check_appointments()
