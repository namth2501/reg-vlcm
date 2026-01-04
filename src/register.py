import random
import string
import asyncio
import os
from patchright.async_api import async_playwright
import time

# Helper to capture and solve CAPTCHAs
# Note: AI models should be passed in to avoid reloading them per browser instance

async def register_account(ocr_solver, audio_solver, headless=False):
    """
    Registers a single account.
    ocr_solver: Instance of OCRSolver
    audio_solver: Instance of AudioSolver
    """
    
    # Generate random creds
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    # Make sure username starts with a letter
    if username[0].isdigit():
        username = 'a' + username[1:]
        
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    
    # Patchright execution
    async with async_playwright() as p:
        # Launch options - can add args to avoid detection if needed
        # Patchright is designed to be stealthy by default
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print(f"[{username}] Navigating...")
            await page.goto("https://vlcm.zing.vn/")
            
            # Click 'Đăng ký nhanh'
            # Use specific ID found by inspection
            await page.locator('#zme-registerwg').click()
            
            # Wait for form inputs
            # Selectors found: #reg_account, #reg_pwd, #reg_cpwd
            await page.wait_for_selector('#reg_account', timeout=15000)
            
            # Fill Username
            await page.fill('#reg_account', username)
            await page.click('#reg_account')
            await asyncio.sleep(0.1)
            
            # Fill Password
            await page.fill('#reg_pwd', password)
            await page.click('#reg_pwd')
            await asyncio.sleep(0.1)

            await page.fill('#reg_cpwd', password) # Confirm pass
            await page.click('#reg_cpwd')
            await asyncio.sleep(0.1)
            
            # --- Visual CAPTCHA ---
            # Selector found: #captcha
            captcha_img = page.locator('#captcha')
            
            # Wait for image to be visible
            try:
                await captcha_img.wait_for(state="visible", timeout=3000)
            except:
                print(f"[{username}] CAPTCHA image not visible.")

            if await captcha_img.count():
                print(f"[{username}] Found visual CAPTCHA.")
                
                # Screenshot the element
                png_bytes = await captcha_img.screenshot()
                
                if png_bytes:
                    # Solve
                    captcha_text = ocr_solver.solve(png_bytes)
                    print(f"[{username}] OCR Result: {captcha_text}")
                    
                    if len(captcha_text) != 6:
                        raise Exception("Invalid captcha length")

                    # Fill captcha input: #veryfied_code
                    await page.fill('#veryfied_code', captcha_text)
                    await page.click('#veryfied_code')
                    await asyncio.sleep(1)

            await page.click('#reg_account')
            await asyncio.sleep(1)

            # Click Register
            # content: #btn-register
            await page.locator('#btn-register').click()
            await asyncio.sleep(3)
            
            # --- Recaptcha Audio ---
            # Selector: #recaptcha
            # Note: The presence of #recaptcha might not mean the challenge is active immediately.
            # Usually, we check if a challenge iframe pops up.
            
            # Look for the challenge iframe (BFrame)
            # It usually has a title like "recaptcha challenge expires in two minutes"
            # We use frame_locator to interact with it
            challenge_frame = page.frame_locator('iframe[title*="recaptcha challenge"]')
            
            # Check if the audio button is visible (meaning challenge is active)
            # Note: we might need to wait for it
            try:
                # Wait for the frame to be attached
                await page.locator('iframe[title*="recaptcha challenge"]').wait_for(timeout=15000)
                
                # Click audio button to request audio challenge
                await challenge_frame.locator('#recaptcha-audio-button').click()
                await asyncio.sleep(2) # Wait for audio challenge to load
                
                # Locate the audio download link
                # Standard ReCaptcha has a 'Download' button/link with class 'rc-audiochallenge-tdownload-link'
                # Or we can look for the audio source URL
                download_link = challenge_frame.locator('.rc-audiochallenge-tdownload-link')
                
                if await download_link.count() > 0:
                    audio_url = await download_link.get_attribute('href')
                    print(f"[{username}] Audio URL found: {audio_url}")
                    
                    # Download audio
                    # We can't simple 'goto' the url in the main page sometimes (it might be a blob or require cookies)
                    # But usually for ReCaptcha it works or we use request context
                    
                    # Create a new page or use request context to download
                    # To avoid navigating away, use APIRequestContext
                    response = await page.request.get(audio_url)
                    audio_bytes = await response.body()
                    
                    # Save to temp file for Whisper
                    temp_audio_file = f"temp_audio_{username}.mp3"
                    with open(temp_audio_file, "wb") as f:
                        f.write(audio_bytes)
                        
                    # Solve
                    audio_text = audio_solver.solve(temp_audio_file)
                    print(f"[{username}] Audio Result: {audio_text}")
                    
                    # Clean up
                    os.remove(temp_audio_file)
                    
                    # Fill audio input: #audio-response
                    await challenge_frame.locator('#audio-response').fill(audio_text)
                    await asyncio.sleep(3)
                    
                    # Click Verify: #recaptcha-verify-button
                    await challenge_frame.locator('#recaptcha-verify-button').click()
                    await asyncio.sleep(4)
                else:
                    print(f"[{username}] Audio download link not found. Might be blocked or different UI.")
        
            except Exception as e:
                print(f"[{username}] No ReCaptcha challenge interaction: {e}")

            if await page.locator('#reg_account').is_visible():
                print(f"[{username}] Registration failed.")
                raise Exception("Registration failed.")


            
            # Check success (url change or success message)
            # Placeholder wait
            # await asyncio.sleep(500)
            
            # Save if success (heuristic)
            # We assume success if no error alert or if URL/Cookie changes.
            # For now, just save on completion of flow.
            
            with open("accounts.txt", "a") as f:
                f.write(f"{username}|{password}\n")
            print(f"[{username}] Registered successfully (Simulated).")
            
        except Exception as e:
            print(f"[{username}] Error: {e}")
            # Take screenshot of error
            await page.screenshot(path=f"errors/error_{username}.png")
            raise e # Re-raise to trigger retry in main.py

        finally:
            await browser.close()

if __name__ == "__main__":
    # Test run
    # Mock solvers for testing without loading heavy models? No, user wants integration.
    # But for a quick test of browser logic, I can import them.
    pass
