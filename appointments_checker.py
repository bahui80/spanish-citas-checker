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
        print(f"Telegram Error: {e}")

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
        print(f"Photo Error: {e}")

def check_appointments():
    # Jitter to avoid being flagged as a bot
    time.sleep(random.randint(20, 60))

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    # Stealth Settings
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.{random.randint(10, 99)} Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # Mask Selenium webdriver flag
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    wait = WebDriverWait(driver, 45)
    timestamp = datetime.now().strftime('%I:%M %p %Z')

    def handle_alert():
        try:
            WebDriverWait(driver, 8).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            print(f"Alert cleared: {alert.text}")
            alert.accept()
            time.sleep(2)
        except:
            pass

    try:
        # STEP 1: LOAD LANDING PAGE
        print("🔗 Step 1: Loading Consulate Landing Page...")
        driver.get("https://www.exteriores.gob.es/Consulados/sanfrancisco/es/Comunicacion/Noticias/Paginas/Articulos/Ley-de-la-memoria-democr%C3%A1tica.aspx")

        # STEP 2: CLICK CITA PREVIA
        print("Step 2: Clicking CITA PREVIA link...")
        cita_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "CITA PREVIA")))
        cita_link.click()

        # Switch to widget tab
        time.sleep(4)
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])

        # STEP 3: HANDLE INITIAL POPUP
        handle_alert()

        # STEP 4: CLICK GREEN CONTINUE BUTTON
        print("Step 4: Clicking 'Continuar'...")
        handle_alert()
        continue_xpath = "//button[contains(., 'Continuar') or contains(., 'Continue')]"
        continuar_button = wait.until(EC.element_to_be_clickable((By.XPATH, continue_xpath)))
        driver.execute_script("arguments[0].click();", continuar_button)

        # STEP 5: ANALYZE FINAL PAGE
        print("Step 5: Analyzing results...")
        time.sleep(15) # Essential for Bookitit to load the "No available" text
        handle_alert() # Catch any final error alerts

        page_text = driver.page_source
        # Specific phrases from your screenshot
        negative_phrases = [
            "No hay horas disponibles",
            "Inténtelo de nuevo dentro de unos días",
            "No hay citas disponibles"
        ]

        found_negative = any(phrase in page_text for phrase in negative_phrases)

        if found_negative:
            # Result: Still empty. We print this to the GitHub log.
            print(f"Result: No appointments available at {timestamp}.")
        else:
            # CHANGE DETECTED: Take a photo and send the alert!
            print("🚨 CHANGE DETECTED! Sending alert...")
            driver.save_screenshot("screenshot.png")
            alert_msg = (
                f"🚨 *¡CITA DISPONIBLE!* 🚨\n\n"
                f"**Time:** {timestamp}\n"
                f"The 'No hay horas' message is NO LONGER visible. Check the screenshot and book now!\n\n"
                f"[Booking Link](https://www.citaconsular.es/es/hosteds/widgetdefault/2d7c60f44f450863fb149b64fdd4b74a1/#services)"
            )
            send_telegram_photo(alert_msg)

    except Exception as e:
        # Error handling with screenshot for debugging
        driver.save_screenshot("screenshot.png")
        error_msg = f"⚠️ *Bot Error* at {timestamp}\nDetails: `Page Timeout or Structure Change`"
        send_telegram_photo(error_msg)
        print(f"Detailed Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    check_appointments()
