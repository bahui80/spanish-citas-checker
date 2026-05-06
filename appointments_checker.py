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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoAlertPresentException
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
    # Jitter to avoid bot detection
    time.sleep(random.randint(30, 90))

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    # Stealth Settings
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # Mask Selenium webdriver flag
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    wait = WebDriverWait(driver, 45)
    timestamp = datetime.now().strftime('%I:%M %p %Z')

    def clear_all_alerts():
        try:
            for _ in range(3):
                WebDriverWait(driver, 3).until(EC.alert_is_present())
                alert = driver.switch_to.alert
                print(f"Dismissed alert: {alert.text}")
                alert.accept()
                time.sleep(1)
        except:
            pass

    try:
        print("🔗 Step 1: Loading Consulate Landing Page...")
        driver.get("https://www.exteriores.gob.es/Consulados/sanfrancisco/es/Comunicacion/Noticias/Paginas/Articulos/Ley-de-la-memoria-democr%C3%A1tica.aspx")

        print("Step 2: Navigating to CITA PREVIA...")
        cita_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "CITA PREVIA")))
        cita_link.click()

        time.sleep(5)
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])

        # Step 3: Handle initial popup and potential iframes
        clear_all_alerts()

        print("Step 4: Attempting to click 'Continuar'...")
        # Broad XPath to find the button shown in your screenshot
        btn_xpath = "//button[contains(., 'Continuar') or contains(., 'Continue')]"

        # 1. Clear alerts again immediately before interaction
        clear_all_alerts()

        # 2. Wait for presence then force interact
        try:
            target_btn = wait.until(EC.presence_of_element_located((By.XPATH, btn_xpath)))

            # Technique A: Scroll and Move Mouse (ActionChains)
            actions = ActionChains(driver)
            actions.move_to_element(target_btn).perform()
            time.sleep(1)

            # Technique B: Javascript Direct Click (Bypasses overlays)
            driver.execute_script("arguments[0].click();", target_btn)
            print("Successfully forced click via Javascript.")
        except Exception:
            # Technique C: Fallback standard click after one more alert sweep
            clear_all_alerts()
            target_btn = wait.until(EC.element_to_be_clickable((By.XPATH, btn_xpath)))
            target_btn.click()

        print("Step 5: Analyzing results...")
        time.sleep(15)
        clear_all_alerts()

        page_text = driver.page_source
        # Phrases from your previous successful runs
        negative_phrases = ["No hay horas disponibles", "Inténtelo de nuevo dentro de unos días"]
        found_negative = any(phrase in page_text for phrase in negative_phrases)

        if found_negative:
            print(f"Result: No appointments at {timestamp}.")
            send_telegram_msg(f"✅ *Bot Check: Online*\n**Time:** {timestamp}\n**Status:** No hay horas disponibles.")
        else:
            # If the negative text is missing, assume success or change
            driver.save_screenshot("screenshot.png")
            alert_msg = f"🚨 *¡POSIBLE CITA!* 🚨\n\n**Time:** {timestamp}\nClick succeeded. Review the screenshot!"
            send_telegram_photo(alert_msg)

    except Exception as e:
        driver.save_screenshot("screenshot.png")
        error_msg = f"⚠️ *Bot Error* at {timestamp}\nDetails: `Button Click Timeout`"
        send_telegram_photo(error_msg)
        print(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    check_appointments()
