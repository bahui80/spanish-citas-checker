import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException
from webdriver_manager.chrome import ChromeDriverManager

def send_telegram_notification(message):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')

    if not token or not chat_id:
        print("Error: Telegram credentials missing.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending Telegram: {e}")

def check_appointments():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    # Long timeout because government servers can be slow
    wait = WebDriverWait(driver, 20)

    try:
        print("🔗 Step 1: Opening Consulate website...")
        driver.get("https://www.exteriores.gob.es/Consulados/sanfrancisco/es/Comunicacion/Noticias/Paginas/Articulos/Ley-de-la-memoria-democr%C3%A1tica.aspx")

        print("Step 2: Clicking 'CITA PREVIA'...")
        cita_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "CITA PREVIA")))
        cita_link.click()

        # --- HANDLE BROWSER ALERT ---
        print("Step 3: Waiting for 'Welcome' browser alert...")
        try:
            wait.until(EC.alert_is_present())
            alert = driver.switch_to.alert
            print(f"Alert found with text: {alert.text}")
            alert.accept()
            print("Alert accepted.")
        except TimeoutException:
            print("No browser alert appeared within timeout.")

        # --- CLICK CONTINUAR ---
        print("Step 4: Clicking 'Continuar'...")
        # Sometimes the button is inside a frame or takes a moment to be 'interactable'
        time.sleep(2)
        continuar_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Continuar')]")))
        continuar_button.click()

        # --- CHECK FINAL PAGE ---
        print("Step 5: Checking for availability...")
        time.sleep(5) # Final wait for the calendar/text to load

        page_source = driver.page_source
        negative_phrase = "No hay horas disponibles"

        if negative_phrase in page_source:
            print("Result: Still no appointments.")
        else:
            print("🚨 SUCCESS: Page content changed!")
            alert_msg = (
                "🚨 *¡CITA DISPONIBLE!* 🚨\n\n"
                "The 'No hay horas' message is NOT on the page. Check now!\n\n"
                "[Open Consulate Site](https://www.exteriores.gob.es/Consulados/sanfrancisco/es/Comunicacion/Noticias/Paginas/Articulos/Ley-de-la-memoria-democr%C3%A1tica.aspx)"
            )
            send_telegram_notification(alert_msg)

    except Exception as e:
        print(f"❌ Error during execution: {e}")
        send_telegram_notification(f"⚠️ Bot Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    check_appointments()
