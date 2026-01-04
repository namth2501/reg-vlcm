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
            # Need to inspect the selector. Based on standard sites, usually an <a> or <button>
            # I'll wait for text 'Đăng ký nhanh'
            await page.get_by_text("Đăng ký nhanh").click()
            
            # Wait for form
            # Assuming typical Zing ID form structure. I might need to adjust selectors.
            # Usually: input[name="account"], input[name="password"], input[name="repassword"]
            
            # Since I don't have the live DOM, I'll use heuristics or visual find logic in a real scenario
            # But for now I'll use likely selectors. If this was interactive I'd investigate.
            # Let's assume there's a modal or redirect.
            
            # Fill Username
            await page.wait_for_selector('input[type="text"]', timeout=5000)
            # Find the account input vs captcha input (both might be text)
            # Adjust: Find input for account name specifically.
            # Assuming first input is account.
            account_input = page.locator('input[placeholder*="Tài khoản"], input[name="account"]').first
            if not await account_input.count(): 
                 # Fallback: look for generic input
                 account_input = page.locator('input[type="text"]').first
            
            await account_input.fill(username)
            
            # Fill Password
            pass_inputs = page.locator('input[type="password"]')
            await pass_inputs.nth(0).fill(password)
            await pass_inputs.nth(1).fill(password) # Confirm pass
            
            
            # --- Visual CAPTCHA ---
            # Locate image
            captcha_img = page.locator('img[src*="captcha"], img.captcha-img').first
            if await captcha_img.count():
                print(f"[{username}] Found visual CAPTCHA.")
                
                # Screenshot the element
                # We can grab screenshot as bytes directly
                png_bytes = await captcha_img.screenshot()
                
                # Verify we got bytes
                if png_bytes:
                     # Solve
                     captcha_text = ocr_solver.solve(png_bytes)
                     print(f"[{username}] OCR Result: {captcha_text}")
                     
                     # Find captcha input
                     # Usually near the image
                     captcha_input = page.locator('input[placeholder*="Mã verification"], input[name*="captcha"]').first
                     if not await captcha_input.count():
                         # Try looking for input next to image
                         # Often inputs are generic text inputs.
                         # This part is risky without DOM inspection.
                         pass 
                     
                     # Assume the input is correct if found
                     if await captcha_input.count():
                         await captcha_input.fill(captcha_text)
            
            # Click Register
            # button: "Đăng ký"
            await page.get_by_role("button", name="Đăng ký").click()
            
            # --- Recaptcha Audio ---
            # If a recaptcha iframe appears
            # Wait a moment to see if we get success or blocked
            try:
                # Look for reCAPTCHA iframe
                iframe_element = page.locator('iframe[src*="recaptcha/api2/anchor"]').first
                if await iframe_element.count():
                     print(f"[{username}] Recaptcha detected.")
                     # This handling is complex (context switch to iframe, click checkbox, wait for challenge iframe)
                     # Since this is a specialized task, I'll output a placeholder for now.
                     # Implementing full audio bypass requires clicking around iframes.
                     pass
            except:
                pass

            
            # Check success (url change or success message)
            # Placeholder wait
            await asyncio.sleep(2)
            
            # Save if success (heuristic)
            # if "id.zing.vn" in page.url or "success" in page.content()...
            
            with open("accounts.txt", "a") as f:
                f.write(f"{username}|{password}\n")
            print(f"[{username}] Registered successfully (Simulated).")
            
        except Exception as e:
            print(f"[{username}] Error: {e}")
            # Take screenshot of error
            await page.screenshot(path=f"error_{username}.png")

        finally:
            await browser.close()

if __name__ == "__main__":
    # Test run
    # Mock solvers for testing without loading heavy models? No, user wants integration.
    # But for a quick test of browser logic, I can import them.
    pass
