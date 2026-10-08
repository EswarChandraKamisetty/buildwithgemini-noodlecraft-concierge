import time
import os
import glob
import subprocess
from playwright.sync_api import sync_playwright

def send_and_wait(page, text, wait_seconds=14):
    page.fill("#input", text)
    time.sleep(1)
    page.click("#form button[type='submit']")
    for _ in range(wait_seconds):
        time.sleep(1)
        page.evaluate("document.querySelector('#log').scrollTop = document.querySelector('#log').scrollHeight")

def run():
    os.makedirs("video_recordings", exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--font-render-hinting=none"
            ]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 768},
            record_video_dir="video_recordings",
            record_video_size={"width": 1280, "height": 768}
        )
        page = context.new_page()
        print("Navigating to NoodleCraft Concierge...")
        page.goto("http://localhost:8080", wait_until="networkidle")
        time.sleep(4)

        # Scene 1: Initial Landing and Overview
        print("Scene 1: Initial Landing...")
        time.sleep(5)

        # Scene 2: Inventory & Allergen Inspection
        print("Scene 2: Checking live inventory & allergens...")
        send_and_wait(page, "Show current noodle inventory with allergens and pricing", wait_seconds=15)
        time.sleep(3)
        page.evaluate("document.querySelector('#log').scrollTop += 320")
        time.sleep(4)
        page.evaluate("document.querySelector('#log').scrollTop = document.querySelector('#log').scrollHeight")
        time.sleep(3)

        # Scene 3: Activity-based Recommendations
        print("Scene 3: Asking for activity-based recommendations...")
        send_and_wait(page, "Based on our recent order activity, what noodle items do you recommend for our menu and why?", wait_seconds=15)
        time.sleep(4)
        page.evaluate("document.querySelector('#log').scrollTop = document.querySelector('#log').scrollHeight")
        time.sleep(3)

        # Scene 4: Interactive Noodle Configurator Modal
        print("Scene 4: Launching Custom Noodle Configurator...")
        page.click("button:has-text('🎛️ Noodle Configurator')")
        time.sleep(3)

        page.evaluate("document.querySelector('#cfgFlour').selectedIndex = 1; document.querySelector('#cfgFlour').dispatchEvent(new Event('change'))")
        time.sleep(2)
        page.evaluate("document.querySelector('#cfgCutter').selectedIndex = 1; document.querySelector('#cfgCutter').dispatchEvent(new Event('change'))")
        time.sleep(2)
        page.evaluate("document.querySelector('#cfgHydration').value = 28; document.querySelector('#cfgHydration').dispatchEvent(new Event('input'))")
        time.sleep(3)
        page.evaluate("document.querySelector('#cfgHydration').value = 42; document.querySelector('#cfgHydration').dispatchEvent(new Event('input'))")
        time.sleep(3)

        # Submit custom spec to Concierge
        page.click("#configModal button:has-text('Submit Spec to Factory Concierge')")
        for _ in range(16):
            time.sleep(1)
            page.evaluate("document.querySelector('#log').scrollTop = document.querySelector('#log').scrollHeight")
        time.sleep(4)

        # Scene 5: Low-Stock Walk-in Cooler Depletion Alert
        print("Scene 5: Checking Low-Stock & Depletion Alerts...")
        page.click("button:has-text('🔔 Low-Stock Check')")
        time.sleep(3)
        page.evaluate("document.querySelector('#stockClient').selectedIndex = 0")
        time.sleep(2)
        page.evaluate("document.querySelector('#stockVelocity').value = 160; document.querySelector('#stockVelocityVal').textContent = '160 bowls/day'")
        time.sleep(2.5)
        page.click("#stockModal button:has-text('Run Depletion Forecast & Reorder')")
        for _ in range(16):
            time.sleep(1)
            page.evaluate("document.querySelector('#log').scrollTop = document.querySelector('#log').scrollHeight")
        time.sleep(4)

        # Scene 6: Multi-Language Kitchen Support (Switch to Japanese)
        print("Scene 6: Switching kitchen dialect to Japanese...")
        page.evaluate("document.querySelector('#langSelector').value = 'ja'; document.querySelector('#langSelector').dispatchEvent(new Event('change'))")
        for _ in range(16):
            time.sleep(1)
            page.evaluate("document.querySelector('#log').scrollTop = document.querySelector('#log').scrollHeight")
        time.sleep(5)

        # Wrap up
        print("Wrapping up recording session...")
        time.sleep(4)
        context.close()
        browser.close()
        print("Finished recording session cleanly!")

if __name__ == "__main__":
    run()
