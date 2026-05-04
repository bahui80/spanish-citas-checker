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
    # Keep the high jitter to stay bypassed
    time.sleep(random.randint(45, 120))

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
    
    # CDP Masking
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    wait = WebDriverWait(driver, 45)
    timestamp = datetime.now().strftime('%I:%M %p %Z')

    def clear_all_alerts():
        """Aggressively clears any browser popups that block clicking."""
        try:
            for _ in range(3): # Check up to 3 times for stacked alerts
                WebDriverWait(driver, 5).until(EC.alert_is_present())
                alert = driver.switch_to.alert
                print(f"Dismissed alert: {alert.text}")
                alert.accept()
                time.sleep(1)
        except:
            pass

    try:
        print("🔗 Step 1: Loading Consulate Page...")
        driver.get("https://www.exteriores.gob.es/Consulados/sanfrancisco/es/Comunicacion/Noticias/Paginas/Articulos/Ley-de-la-memoria-democr%C3%A1tica.aspx")
        
        print("Step 2: Navigating to CITA PREVIA...")
        cita_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "CITA PREVIA")))
        cita_link.click()
        
        time.sleep(5)
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])

        # IMPORTANT: Clear the 'Welcome' alert first
        clear_all_alerts()

        print("Step 4: Attempting to click 'Continuar'...")
        # Use a very specific XPATH that matches the button in your screenshot
        btn_xpath = "//button[contains(@class, 'btn') and (contains(., 'Continuar') or contains(., 'Continue'))]"
        
        # We try to find the button, but use Javascript to click it immediately 
        # to bypass any "Element is not clickable" errors
        try:
            target_btn = wait.until(EC.presence_of_element_located((By.XPATH, btn_xpath)))
            driver.execute_script("arguments[0].scrollIntoView(true);", target_btn)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", target_btn)
            print("Successfully forced click via Javascript.")
        except Exception:
            # Fallback: if alert was still there, clear again and try one last time
            clear_all_alerts()
            target_btn = wait.until(EC.element_to_be_clickable((By.XPATH, btn_xpath)))
            driver.execute_script("arguments[0].click();", target_btn)

        print("Step 5: Analyzing results...")
        time.sleep(15) # Wait for the next page to load
        clear_all_alerts()

        page_text = driver.page_source
        negative_phrases = ["No hay horas disponibles", "Inténtelo de nuevo dentro de unos días"]
        found_negative = any(phrase in page_text for phrase in negative_phrases)

        if found_negative:
            print(f"Result: No appointments at {timestamp}.")
            send_telegram_msg(f"✅ *Bot Check: Online*\n**Time:** {timestamp}\n**Status:** No hay horas disponibles.")
        else:
            driver.save_screenshot("screenshot.png")
            alert_msg = f"🚨 *¡POSIBLE CITA!* 🚨\n\n**Time:** {timestamp}\nButton clicked successfully. Review the screenshot!"
            send_telegram_photo(alert_msg)

    except Exception as e:
        driver.save_screenshot("screenshot.png")
        # If it failed at the button step, we want to see why
        send_telegram_photo(f"⚠️ *Bot Error* at {timestamp}\nDetails: `Button Click Timeout`")
        print(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    check_appointments()
