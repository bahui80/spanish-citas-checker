import os
import time
import requests
import random
from datetime import datetime
import undetected_chromedriver as uc # Specialized for Cloudflare
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
    except Exception as e:
        print(f"Photo Error: {e}")

def check_appointments():
    # High Jitter to stay under the radar
    time.sleep(random.randint(60, 180))

    options = uc.ChromeOptions()
    options.add_argument("--headless") # uc works best with standard headless
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    # Randomize User Agent slightly
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ]
    options.add_argument(f"user-agent={random.choice(user_agents)}")

    try:
        driver = uc.Chrome(options=options, headless=True)
        wait = WebDriverWait(driver, 50)
        timestamp = datetime.now().strftime('%I:%M %p %Z')

        print("🔗 Step 1: Loading Consulate Page...")
        driver.get("https://www.exteriores.gob.es/Consulados/sanfrancisco/es/Comunicacion/Noticias/Paginas/Articulos/Ley-de-la-memoria-democr%C3%A1tica.aspx")

        print("Step 2: Navigating to CITA PREVIA...")
        cita_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "CITA PREVIA")))
        cita_link.click()

        time.sleep(8)
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])

        # CLOUDFLARE BYPASS SLEEP
        # undetected-chromedriver often solves Turnstile automatically if given time
        if "Verify you are human" in driver.page_source:
            print("Cloudflare Turnstile detected. Waiting for auto-resolve...")
            time.sleep(20)

        print("Step 4: Clicking 'Continuar'...")
        btn_xpath = "//button[contains(., 'Continuar') or contains(., 'Continue')]"
        target_btn = wait.until(EC.presence_of_element_located((By.XPATH, btn_xpath)))

        # Click via JS
        driver.execute_script("arguments[0].click();", target_btn)

        # EXTENDED WAIT for the final page
        print("Step 5: Final analysis...")
        time.sleep(20)

        page_text = driver.page_source
        negative_phrases = ["No hay horas disponibles", "Inténtelo de nuevo dentro de unos días"]
        found_negative = any(phrase in page_text for phrase in negative_phrases)

        if found_negative:
            print(f"Result: Still no appointments at {timestamp}.")
            send_telegram_msg(f"✅ *Bot Check: Online*\n**Time:** {timestamp}\n**Status:** No hay horas.")
        elif "Verify you are human" in page_text:
            driver.save_screenshot("screenshot.png")
            send_telegram_photo(f"⚠️ *Bot Blocked* at {timestamp}\nCloudflare reappeared.")
        else:
            driver.save_screenshot("screenshot.png")
            send_telegram_photo(f"🚨 *¡POSIBLE CITA!* 🚨\n**Time:** {timestamp}\nBypassed Cloudflare. Check image!")

    except Exception as e:
        if 'driver' in locals():
            driver.save_screenshot("screenshot.png")
        send_telegram_photo(f"⚠️ *Bot Error* at {timestamp}\nDetails: `Automation Blocked`")
        print(f"Error: {e}")
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    check_appointments()
