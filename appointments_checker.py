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
from selenium.webdriver.common.action_chains import ActionChains

os.environ['TZ'] = 'America/Los_Angeles'
if hasattr(time, 'tzset'):
    time.sleep(0) # Logic dummy

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
        if os.path.exists("screenshot.png"):
            with open("screenshot.png", "rb") as photo:
                files = {"photo": photo}
                data = {"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}
                requests.post(url, files=files, data=data)
        else:
            send_telegram_msg(caption)
    except:
        pass

def get_chrome_version():
    try:
        version = os.popen('google-chrome --version').read()
        return int(re.search(r'Chrome (\d+)', version).group(1))
    except:
        return None

def check_appointments():
    timestamp = datetime.now().strftime('%I:%M %p %Z')
    # High jitter to break the 30/60 minute pattern
    time.sleep(random.randint(90, 300))

    chrome_main_version = get_chrome_version()
    options = uc.ChromeOptions()

    # Randomize viewport to avoid bot fingerprinting
    options.add_argument(f"--window-size={random.randint(1280, 1920)},{random.randint(720, 1080)}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = None
    try:
        driver = uc.Chrome(options=options, version_main=chrome_main_version, headless=True)
        wait = WebDriverWait(driver, 60)

        print("🔗 Loading Landing Page...")
        driver.get("https://www.exteriores.gob.es/Consulados/sanfrancisco/es/Comunicacion/Noticias/Paginas/Articulos/Ley-de-la-memoria-democr%C3%A1tica.aspx")

        # Human mimicry: scrolling
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(random.uniform(2, 5))

        cita_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "CITA PREVIA")))
        cita_link.click()

        time.sleep(10)
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])

        # ATTEMPT TO SOLVE TURNSTILE
        if "Verify you are human" in driver.page_source:
            print("Cloudflare Turnstile found. Attempting coordinates click...")
            driver.save_screenshot("screenshot.png")

            try:
                # Turnstile is usually in an iframe. We try to click the center of the screen
                # where the checkbox typically resides as a 'blind' attempt.
                actions = ActionChains(driver)
                actions.move_by_offset(300, 300).click().perform()
                time.sleep(25) # Give it a long time to verify
            except:
                pass

        print("Step 4: Button Interaction...")
        btn_xpath = "//button[contains(., 'Continuar') or contains(., 'Continue')]"
        target_btn = wait.until(EC.presence_of_element_located((By.XPATH, btn_xpath)))
        driver.execute_script("arguments[0].click();", target_btn)

        time.sleep(20)

        page_text = driver.page_source
        negative_phrases = ["No hay horas disponibles", "Inténtelo de nuevo dentro de unos días"]
        found_negative = any(phrase in page_text for phrase in negative_phrases)

        if found_negative:
            print(f"Still no appointments at {timestamp}.")
            send_telegram_msg(f"✅ *Bot Check: Online*\nTime: {timestamp}\nStatus: No hay horas.")
        elif "Verify you are human" in page_text:
            driver.save_screenshot("screenshot.png")
            send_telegram_photo(f"⚠️ *Blocked* at {timestamp}\nCloudflare won't budge.")
        else:
            driver.save_screenshot("screenshot.png")
            send_telegram_photo(f"🚨 *¡POSIBLE CITA!* 🚨\nTime: {timestamp}\nBypassed! Check image.")

    except Exception as e:
        if driver:
            driver.save_screenshot("screenshot.png")
            send_telegram_photo(f"⚠️ *Bot Error* at {timestamp}\nDetails: `Security Blocked`")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    check_appointments()
