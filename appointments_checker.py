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
    time.tzset()

def send_telegram_msg(message):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except:
        pass

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
    # High initial delay to avoid "burst" detection
    time.sleep(random.randint(60, 120))

    chrome_main_version = get_chrome_version()
    options = uc.ChromeOptions()

    # We use a non-standard window size to look less like a default bot
    options.add_argument(f"--window-size={random.randint(1200, 1920)},{random.randint(800, 1080)}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = None
    try:
        driver = uc.Chrome(options=options, version_main=chrome_main_version, headless=True)
        wait = WebDriverWait(driver, 60)

        print("🔗 Step 1: Loading Landing Page...")
        driver.get("https://www.exteriores.gob.es/Consulados/sanfrancisco/es/Comunicacion/Noticias/Paginas/Articulos/Ley-de-la-memoria-democr%C3%A1tica.aspx")

        # HUMAN SIMULATION: Move mouse randomly
        actions = ActionChains(driver)
        for _ in range(3):
            actions.move_by_offset(random.randint(0, 100), random.randint(0, 100)).perform()
            time.sleep(random.uniform(1, 3))

        # Check for Cloudflare on landing
        if "Verify you are human" in driver.page_source:
            print("Cloudflare detected. Attempting to wait it out...")
            time.sleep(30) # Turnstile sometimes auto-solves if you just wait

        print("Step 2: Navigating to CITA PREVIA...")
        cita_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "CITA PREVIA")))
        cita_link.click()

        time.sleep(10)
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])

        # Step 3: Handle Widget Security
        if "Verify you are human" in driver.page_source:
            print("Cloudflare on Widget. Taking screenshot and waiting...")
            driver.save_screenshot("screenshot.png")
            time.sleep(40)

        print("Step 4: Clicking 'Continuar'...")
        btn_xpath = "//button[contains(., 'Continuar') or contains(., 'Continue')]"
        target_btn = wait.until(EC.presence_of_element_located((By.XPATH, btn_xpath)))

        # Try to scroll to it first
        driver.execute_script("arguments[0].scrollIntoView();", target_btn)
        time.sleep(2)
        driver.execute_script("arguments[0].click();", target_btn)

        print("Step 5: Final Analysis...")
        time.sleep(20)

        page_text = driver.page_source
        negative_phrases = ["No hay horas disponibles", "Inténtelo de nuevo dentro de unos días"]
        found_negative = any(phrase in page_text for phrase in negative_phrases)

        if found_negative:
            print(f"Result: No appointments at {timestamp}.")
            send_telegram_msg(f"✅ *Bot Check: Online*\n**Time:** {timestamp}\n**Status:** No hay horas.")
        elif "Verify you are human" in page_text:
            print("Stuck on Cloudflare.")
            driver.save_screenshot("screenshot.png")
            send_telegram_photo(f"⚠️ *Bot Blocked* at {timestamp}\nCloudflare is still blocking the GitHub IP.")
        else:
            driver.save_screenshot("screenshot.png")
            send_telegram_photo(f"🚨 *¡POSIBLE CITA!* 🚨\n**Time:** {timestamp}\nBypassed security! Review image!")

    except Exception as e:
        print(f"Error: {e}")
        if driver:
            driver.save_screenshot("screenshot.png")
            send_telegram_photo(f"⚠️ *Bot Error* at {timestamp}\nDetails: `Blocked by Security`")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    check_appointments()
