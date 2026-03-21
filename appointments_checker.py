import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def send_telegram_notification(message):
    """Sends a formatted Markdown message to the Telegram Group."""
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')

    if not token or not chat_id:
        print("Error: Telegram credentials missing from Environment Variables.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Telegram notification sent to group!")
        else:
            print(f"❌ Failed to send Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Error sending Telegram: {e}")

def check_appointments():
    # Setup Chrome options for GitHub Actions (Headless)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 15)

    try:
        print("🔗 Opening Consulate website...")
        driver.get("https://www.exteriores.gob.es/Consulados/sanfrancisco/es/Comunicacion/Noticias/Paginas/Articulos/Ley-de-la-memoria-democr%C3%A1tica.aspx")

        # 1. Click CITA PREVIA
        print("Step 1: Clicking 'CITA PREVIA'...")
        cita_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "CITA PREVIA")))
        cita_link.click()

        # 2. Handle the "Bienvenido" Popup (Switch to new window if it opens one)
        time.sleep(3)
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])

        # 3. Click "Ok" on the banner
        print("Step 2: Clicking 'Ok' on Welcome banner...")
        ok_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Ok')]")))
        ok_button.click()

        # 4. Click "Continuar"
        print("Step 3: Clicking 'Continuar'...")
        continuar_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Continuar')]")))
        continuar_button.click()

        # 5. Check for availability
        print("Step 4: Checking text result...")
        time.sleep(3) # Wait for final page load
        page_source = driver.page_source

        negative_phrase = "No hay horas disponibles"

        if negative_phrase in page_source:
            print("Result: No appointments available yet.")
        else:
            print("🚨 ALERT: APPOINTMENT DETECTED OR PAGE CHANGED!")
            alert_msg = (
                "🚨 *¡CITA DISPONIBLE!* 🚨\n\n"
                "The 'No appointments' message is gone. Check the website immediately!\n\n"
                "[👉 Click here to open the Consulate Site](https://www.exteriores.gob.es/Consulados/sanfrancisco/es/Comunicacion/Noticias/Paginas/Articulos/Ley-de-la-memoria-democr%C3%A1tica.aspx)"
            )
            send_telegram_notification(alert_msg)

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        # Optional: notify you if the script breaks so you can fix the selectors
        send_telegram_notification(f"⚠️ Bot Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    check_appointments()
