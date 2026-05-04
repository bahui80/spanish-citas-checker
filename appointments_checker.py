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
    # HIGH JITTER: Wait 1 to 5 minutes to avoid detection patterns
    time.sleep(random.randint(60, 300))

    chrome_options = Options()
    # Using 'headless=new' is essential for bypassing Cloudflare
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # STEALTH: Disabling 'AutomationControlled' is the most important step
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Updated User Agent to a very recent Chrome version
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # Final layer of masking the 'webdriver' flag
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    wait = WebDriverWait(driver, 60)
    timestamp = datetime.now().strftime('%I:%M %p %Z')

    def handle_alert():
        try:
            WebDriverWait(driver, 10).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            alert.accept()
            time.sleep(2)
        except:
            pass

    try:
        print("🔗 Step 1: Loading Consulate Page...")
        driver.get("https://www.exteriores.gob.es/Consulados/sanfrancisco/es/Comunicacion/Noticias/Paginas/Articulos/Ley-de-la-memoria-democr%C3%A1tica.aspx")
        
        # Check if we are immediately blocked by Cloudflare on the main site
        if "Verify you are human" in driver.page_source or "Cloudflare" in driver.page_source:
            print("Cloudflare detected on landing page. Waiting for potential auto-pass...")
            time.sleep(20)

        print("Step 2: Clicking CITA PREVIA link...")
        cita_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "CITA PREVIA")))
        cita_link.click()
        
        time.sleep(5)
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])

        # HANDLE CLOUDFLARE ON WIDGET
        if "Verify you are human" in driver.page_source:
            print("Cloudflare detected on widget. Waiting...")
            time.sleep(25) # Give the 'Turnstile' a chance to resolve automatically

        handle_alert()

        # Step 4: Click 'Continuar'
        print("Step 4: Clicking 'Continuar'...")
        handle_alert()
        continue_xpath = "//button[contains(., 'Continuar') or contains(., 'Continue')]"
        continuar_button = wait.until(EC.element_to_be_clickable((By.XPATH, continue_xpath)))
        driver.execute_script("arguments[0].click();", continuar_button)

        # Step 5: Analyze final results
        print("Step 5: Analyzing results...")
        time.sleep(20) # Extended wait for Bookitit after security checks
        handle_alert()

        page_text = driver.page_source
        negative_phrases = ["No hay horas disponibles", "Inténtelo de nuevo dentro de unos días"]
        found_negative = any(phrase in page_text for phrase in negative_phrases)

        if found_negative:
            print(f"Result: No appointments available at {timestamp}.")
            send_telegram_msg(f"✅ *Bot Check: Online*\n**Time:** {timestamp}\n**Status:** No slots found.")
        else:
            print("🚨 Potential Match found!")
            driver.save_screenshot("screenshot.png")
            alert_msg = f"🚨 *¡POSIBLE CITA!* 🚨\n\n**Time:** {timestamp}\nSecurity check passed. Review the screenshot!"
            send_telegram_photo(alert_msg)

    except Exception as e:
        driver.save_screenshot("screenshot.png")
        # Check if the screenshot shows we are still stuck on Cloudflare
        error_context = "Cloudflare Block" if "Verify you are human" in driver.page_source else "Timeout/Element Error"
        send_telegram_photo(f"⚠️ *Bot Error* at {timestamp}\nStatus: `{error_context}`")
        print(f"Detailed Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    check_appointments()
