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
    # Wait a random time
    time.sleep(random.randint(5, 15))

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    # STEALTH SETTINGS
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # Execute CDP command to hide selenium
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })

    wait = WebDriverWait(driver, 60) # Increased to 60s for slow government servers
    timestamp = datetime.now().strftime('%I:%M %p %Z')

    def clear_alerts():
        try:
            while True:
                WebDriverWait(driver, 5).until(EC.alert_is_present())
                alert = driver.switch_to.alert
                print(f"Dismissed alert: {alert.text}")
                alert.accept()
                time.sleep(2)
        except:
            pass

    try:
        print("🔗 Step 1: Opening Widget...")
        driver.get("https://www.citaconsular.es/es/hosteds/widgetdefault/2d7c60f44f450863fb149b64fdd4b74a1/#services")

        # Long initial sleep to let the heavy widget load
        time.sleep(15)
        clear_alerts()

        # Step 2: Handle entry button
        print("Step 2: Looking for entry button...")
        # If the spinner is still there, this will wait up to 60s
        entry_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Ok') or contains(., 'Aceptar') or contains(., 'Continuar')]")))
        driver.execute_script("arguments[0].click();", entry_btn)
        time.sleep(5)

        clear_alerts()

        # Step 3: Click 'Continue'
        print("Step 3: Clicking 'Continue'...")
        continue_xpath = "//button[contains(., 'Continuar') or contains(., 'Continue')]"
        continuar_button = wait.until(EC.element_to_be_clickable((By.XPATH, continue_xpath)))
        driver.execute_script("arguments[0].click();", continuar_button)

        time.sleep(10)
        clear_alerts()

        # Step 4: Verify results
        page_text = driver.page_source.lower()
        negative_phrases = ["no hay horas", "no hay citas", "no hay fechas", "inténtelo de nuevo"]

        found_negative = any(phrase in page_text for phrase in negative_phrases)

        if found_negative:
            print(f"Result: No appointments at {timestamp}")
        else:
            driver.save_screenshot("screenshot.png")
            alert_msg = f"🚨 *¡POSIBLE CITA!* 🚨\n\n**Time:** {timestamp}\nNo negative message found. Check immediately!"
            send_telegram_photo(alert_msg)

    except Exception as e:
        driver.save_screenshot("screenshot.png")
        error_msg = f"⚠️ *Bot Error* at {timestamp}\nDetails: `Page Timeout or Detection Block`"
        send_telegram_photo(error_msg)
        print(f"Full error for logs: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    check_appointments()
