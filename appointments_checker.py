import os
import time
import requests
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# Force Timezone for PST/PDT
os.environ['TZ'] = 'America/Los_Angeles'
if hasattr(time, 'tzset'):
    time.tzset()

def send_telegram_msg(message):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending text: {e}")

def send_telegram_photo(caption):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        if os.path.exists("screenshot.png"):
            with open("screenshot.png", "rb") as photo:
                files = {"photo": photo}
                data = {"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}
                requests.post(url, files=files, data=data)
    except Exception as e:
        print(f"Failed to send photo: {e}")

def check_appointments():
    # Anti-detection Jitter: Wait 10-45 seconds
    wait_jitter = random.randint(10, 45)
    print(f"Waiting {wait_jitter}s to look human...")
    time.sleep(wait_jitter)

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 25)
    timestamp = datetime.now().strftime('%I:%M %p %Z')

    def clear_alerts():
        try:
            while True:
                WebDriverWait(driver, 3).until(EC.alert_is_present())
                alert = driver.switch_to.alert
                print(f"Dismissed alert: {alert.text}")
                alert.accept()
                time.sleep(1)
        except TimeoutException:
            pass

    try:
        print("🔗 Step 1: Opening Widget...")
        driver.get("https://www.citaconsular.es/es/hosteds/widgetdefault/2d7c60f44f450863fb149b64fdd4b74a1/#services")

        clear_alerts()

        # Step 2: Handle landing button if present
        try:
            entry_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Ok') or contains(., 'Aceptar') or contains(., 'Continuar')]")))
            entry_btn.click()
            time.sleep(2)
        except:
            pass

        clear_alerts()

        # Step 3: Click 'Continue' (From your screenshot)
        print("Step 3: Clicking 'Continue' button...")
        clear_alerts()

        continue_xpath = "//button[contains(., 'Continuar') or contains(., 'Continue')]"
        continuar_button = wait.until(EC.element_to_be_clickable((By.XPATH, continue_xpath)))

        # Click via JS to prevent alert-blocking
        driver.execute_script("arguments[0].click();", continuar_button)
        print("Clicked 'Continue'.")

        # Wait for the results to actually load
        time.sleep(7)
        clear_alerts()

        # Step 4: Verify results
        page_text = driver.page_source
        negative_phrases = ["No hay horas disponibles", "No hay citas", "No hay fechas", "Inténtelo de nuevo"]

        # Logic: If NONE of the negative phrases are found, we assume a slot exists
        found_negative = any(phrase in page_text for phrase in negative_phrases)

        if found_negative:
            print(f"Result: No appointments at {timestamp}")
            # Optional: Heartbeat (Disabled by default to avoid spam)
            # send_telegram_msg(f"✅ *System Online*\nTime: {timestamp}\nStatus: Still no slots.")
        else:
            # SUCCESS CASE: Take a screenshot and send it!
            print("🚨 Potential appointment found! Taking screenshot...")
            driver.save_screenshot("screenshot.png")
            alert_msg = (
                f"🚨 *¡CITA DISPONIBLE O CAMBIO DETECTADO!* 🚨\n\n"
                f"**Time:** {timestamp}\n"
                f"The bot did not find the 'No appointments' text. Review the image below immediately!\n\n"
                f"[Open Booking Site](https://www.citaconsular.es/es/hosteds/widgetdefault/2d7c60f44f450863fb149b64fdd4b74a1/#services)"
            )
            send_telegram_photo(alert_msg)

    except Exception as e:
        # ERROR CASE: Also take a screenshot so we can debug
        driver.save_screenshot("screenshot.png")
        error_msg = f"⚠️ *Bot Error* at {timestamp}\nError: `{str(e)[:150]}`"
        send_telegram_photo(error_msg)
        print(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    check_appointments()
