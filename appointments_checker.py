import os
import time
import requests
import random
import re
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

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
        else:
            send_telegram_msg(caption) # Fallback to text if no photo
    except Exception as e:
        print(f"Photo Error: {e}")

def get_chrome_version():
    """Helper to find the installed Chrome version on the runner."""
    try:
        version = os.popen('google-chrome --version').read()
        return int(re.search(r'Chrome (\d+)', version).group(1))
    except:
        return None

def check_appointments():
    # Move timestamp to the top so it's available for error reporting
    timestamp = datetime.now().strftime('%I:%M %p %Z')

    # Random jitter
    time.sleep(random.randint(30, 60))

    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    # Detect the correct version to prevent the 'SessionNotCreated' error
    chrome_main_version = get_chrome_version()
    print(f"Detected Chrome version: {chrome_main_version}")

    driver = None
    try:
        # Initialize with the specific version found on the system
        driver = uc.Chrome(options=options, version_main=chrome_main_version)
        wait = WebDriverWait(driver, 50)

        print("🔗 Step 1: Loading Consulate Page...")
        driver.get("https://www.exteriores.gob.es/Consulados/sanfrancisco/es/Comunicacion/Noticias/Paginas/Articulos/Ley-de-la-memoria-democr%C3%A1tica.aspx")

        print("Step 2: Navigating to CITA PREVIA...")
        cita_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "CITA PREVIA")))
        cita_link.click()

        time.sleep(8)
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])

        # Cloudflare Bypass Wait
        if "Verify you are human" in driver.page_source:
            print("Cloudflare Turnstile detected. Waiting...")
            time.sleep(20)

        print("Step 3: Handling Widget Buttons...")
        btn_xpath = "//button[contains(., 'Continuar') or contains(., 'Continue')]"
        target_btn = wait.until(EC.presence_of_element_located((By.XPATH, btn_xpath)))
        driver.execute_script("arguments[0].click();", target_btn)

        print("Step 4: Final Analysis...")
        time.sleep(20)

        page_text = driver.page_source
        negative_phrases = ["No hay horas disponibles", "Inténtelo de nuevo dentro de unos días"]
        found_negative = any(phrase in page_text for phrase in negative_phrases)

        if found_negative:
            print(f"Result: Still no appointments at {timestamp}.")
            send_telegram_msg(f"✅ *Bot Check: Online*\n**Time:** {timestamp}\n**Status:** No hay horas.")
        else:
            driver.save_screenshot("screenshot.png")
            send_telegram_photo(f"🚨 *¡POSIBLE CITA!* 🚨\n**Time:** {timestamp}\nReview the image!")

    except Exception as e:
        print(f"Error occurred: {e}")
        if driver:
            try:
                driver.save_screenshot("screenshot.png")
                send_telegram_photo(f"⚠️ *Bot Error* at {timestamp}\nDetails: `{str(e)[:100]}`")
            except:
                send_telegram_msg(f"⚠️ *Bot Error* at {timestamp}\nDetails: `Crash during driver setup`")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    check_appointments()
