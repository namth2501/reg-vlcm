import random
import string
import asyncio
import os
from patchright.async_api import async_playwright
import time
import aiohttp

# Helper to capture and solve CAPTCHAs
# Note: AI models should be passed in to avoid reloading them per browser instance

async def verify_cdp_endpoint(cdp_address: str, username: str, max_retries: int = 10, retry_delay: float = 0.5):
    """
    Verify that the CDP endpoint is accessible by checking the /json/version endpoint.
    Retries up to max_retries times with retry_delay between attempts.
    """
    # Parse the address to get base URL
    if cdp_address.startswith('http://'):
        base_url = cdp_address
    elif cdp_address.startswith('https://'):
        base_url = cdp_address
    else:
        base_url = f"http://{cdp_address}"
    
    version_url = f"{base_url}/json/version"
    
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
                async with session.get(version_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"[{username}] CDP endpoint verified successfully (attempt {attempt + 1}/{max_retries})")
                        return True
                    else:
                        print(f"[{username}] CDP endpoint returned status {response.status}, retrying...")
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"[{username}] CDP endpoint check failed (attempt {attempt + 1}/{max_retries}): {e}, retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                print(f"[{username}] CDP endpoint verification failed after {max_retries} attempts: {e}")
                raise Exception(f"CDP endpoint not accessible after {max_retries} attempts: {e}")
    
    raise Exception(f"CDP endpoint verification failed after {max_retries} attempts")

def ramdom_username():
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    # Make sure username starts with a letter
    if username[0].isdigit():
        username = 'a' + username[1:]
    return username

async def register_account(ocr_solver, audio_solver, headless=False, task_id=0, save_ocr_images=False, gpm_client=None, gpm_config=None):
    """
    Registers a single account.
    ocr_solver: Instance of OCRSolver or OMOcaptchaSolver
    audio_solver: Instance of AudioSolver
    save_ocr_images: Whether to save CAPTCHA images to ocr_images folder
    gpm_client: Optional GPM Login Client instance
    gpm_config: Optional dict with GPM config (profile_name_prefix, group_name, raw_proxy)
    """
    
    # Generate random creds
    username = ramdom_username()
    
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    
    # Track created GPM profile for cleanup
    created_gpm_profile_id = None
    browser = None
    
    # Patchright execution
    async with async_playwright() as p:
        # Use GPM profile if configured
        if gpm_client and gpm_config:
            try:
                # Create new GPM profile
                profile_name_prefix = gpm_config.get('profile_name_prefix', 'vlcm_reg_')
                group_name = gpm_config.get('group_name', 'All')
                raw_proxy = gpm_config.get('raw_proxy', '')
                
                profile_name = f"{profile_name_prefix}{username}_{task_id}"
                
                print(f"[{username}] Creating GPM profile: {profile_name}")
                
                create_options = {
                    'profile_name': profile_name,
                    'group_name': group_name,
                    'browser_core': 'chromium'
                }
                
                if raw_proxy:
                    create_options['raw_proxy'] = raw_proxy
                
                create_result = await gpm_client.create_profile(create_options)
                
                if not create_result.get('success') or not create_result.get('data'):
                    raise Exception(f"Failed to create GPM profile: {create_result.get('message', 'Unknown error')}")
                
                created_gpm_profile_id = create_result['data'].get('id')
                if not created_gpm_profile_id:
                    raise Exception("GPM did not return profile ID after creation")
                
                print(f"[{username}] Created GPM profile: {created_gpm_profile_id}")
                
                # Wait 3 seconds after creating profile
                print(f"[{username}] Waiting 3 seconds after profile creation...")
                await asyncio.sleep(3)
                
                # Calculate window position based on task_id
                cols = 4
                x = (task_id % cols) * 500
                y = (task_id // cols) * 300
                
                # Start GPM profile with window position
                start_options = {
                    'win_pos': f"{x},{y}"
                }
                start_result = await gpm_client.start_profile(created_gpm_profile_id, start_options)
                
                # Check if top-level success is True
                if not start_result.get('success'):
                    error_msg = start_result.get('message', 'Unknown error')
                    raise Exception(f"Failed to start GPM profile: {error_msg}")
                
                # Get data
                browser_data = start_result.get('data')
                if not browser_data:
                    raise Exception(f"GPM start_profile did not return data: {start_result}")
                
                # Check nested success only if it exists (some APIs may not have it)
                # If top-level success is True and we have data, proceed
                if isinstance(browser_data, dict) and browser_data.get('success') is False:
                    error_msg = start_result.get('message', 'Unknown error')
                    raise Exception(f"Failed to start GPM profile (data.success=False): {error_msg}")
                
                remote_debugging_address = browser_data.get('remote_debugging_address')
                
                if not remote_debugging_address:
                    raise Exception("GPM did not return remote_debugging_address")
                
                # Ensure the address is in the correct format (http://host:port)
                if not remote_debugging_address.startswith('http://') and not remote_debugging_address.startswith('https://'):
                    remote_debugging_address = f"http://{remote_debugging_address}"
                
                print(f"[{username}] Verifying CDP endpoint is accessible at {remote_debugging_address}")
                
                # Verify CDP endpoint is accessible before connecting
                await verify_cdp_endpoint(remote_debugging_address, username)
                
                print(f"[{username}] Connecting to GPM browser at {remote_debugging_address}")
                
                # Connect to existing browser via remote debugging
                browser = await p.chromium.connect_over_cdp(remote_debugging_address)
                
                # Get existing context or create new one
                contexts = browser.contexts
                if contexts:
                    context = contexts[0]
                else:
                    context = await browser.new_context()
                
                # Get existing page or create new one
                pages = context.pages
                if pages:
                    page = pages[0]
                else:
                    page = await context.new_page()
                
            except Exception as e:
                print(f"[{username}] Failed to use GPM profile: {e}")
                print(f"[{username}] Falling back to regular Chromium launch")
                # Fallback to regular launch
                cols = 4
                x = (task_id % cols) * 500
                y = (task_id // cols) * 300
                
                args = [
                    f"--window-position={x},{y}"
                ]
                
                browser = await p.chromium.launch(headless=headless, args=args)
                context = await browser.new_context()
                page = await context.new_page()
        else:
            # Regular Chromium launch
            # Calculate window position based on task_id
            # Layout: Grid of 4 columns
            # Window size: 500x700
            cols = 4
            x = (task_id % cols) * 500
            y = (task_id // cols) * 300
            
            args = [
                f"--window-position={x},{y}"
            ]
            
            browser = await p.chromium.launch(headless=headless, args=args)
            
            # Create context with viewport matching window
            context = await browser.new_context()
            page = await context.new_page()
        
        try:
            print(f"[{username}] Navigating... (Task {task_id}, Pos: {x},{y})")
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
            
            await page.click('#reg_account')
            await asyncio.sleep(1)
            # check if has #reg_account_error with display not none <div class="zme_wg_rowlogin notelog txtfail" id="reg_account_error" style="display: none;">Tài khoản này đã tồn tại.</div>
            # then use another username and fill again
            if await page.locator('#reg_account_error').is_visible():
                username = ramdom_username()
                await page.locator('#reg_account').clear()
                await page.fill('#reg_account', username)
                await page.click('#reg_account')
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
                    # Solve - handle both sync (OCR) and async (OMOcaptcha) solvers
                    if hasattr(ocr_solver, 'solve') and asyncio.iscoroutinefunction(ocr_solver.solve):
                        # Async solver (OMOcaptcha)
                        captcha_text = await ocr_solver.solve(png_bytes)
                    else:
                        # Sync solver (OCR)
                        captcha_text = ocr_solver.solve(png_bytes)
                    
                    print(f"[{username}] CAPTCHA Result: {captcha_text}")
                    
                    if len(captcha_text) != 6:
                        raise Exception("Invalid captcha length")
                    
                    # Save image if enabled (after solving to include text in filename)
                    if save_ocr_images:
                        os.makedirs("ocr_images", exist_ok=True)
                        # Sanitize captcha text for filename (remove invalid characters)
                        safe_captcha_text = "".join(c for c in captcha_text if c.isalnum() or c in ('-', '_'))
                        image_filename = f"ocr_images/{safe_captcha_text}.png"
                        with open(image_filename, "wb") as f:
                            f.write(png_bytes)
                        print(f"[{username}] Saved CAPTCHA image to {image_filename}")

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
            challenge_frame = page.frame_locator('iframe[src*="https://www.google.com/recaptcha"]:not([title="reCAPTCHA"])')
            
            # Check if the audio button is visible (meaning challenge is active)
            # Note: we might need to wait for it
            try:
                # Wait for the frame to be attached
                await page.locator('iframe[src*="https://www.google.com/recaptcha"]:not([title="reCAPTCHA"])').wait_for(timeout=15000)
                
                # Click audio button to request audio challenge
                await challenge_frame.locator('#recaptcha-audio-button').click()
                
                # Check for "Try again later" error immediately
                # Selector for error: .rc-doscaptcha-header-text
                try:
                    # Wait up to 5 seconds for either download link OR error message
                    # We can't wait for both simultaneously easily with just wait_for, so we poll or use race.
                    # Simple approach: Wait for download link with timeout.
                    
                    download_link = challenge_frame.locator('.rc-audiochallenge-tdownload-link')
                    await download_link.wait_for(state="visible", timeout=5000)
                    
                    audio_url = await download_link.get_attribute('href')
                    print(f"[{username}] Audio URL found: {audio_url}")
                    
                    # Download audio
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
                    try:
                        os.remove(temp_audio_file)
                    except:
                        pass
                    
                    # Fill audio input: #audio-response
                    await challenge_frame.locator('#audio-response').fill(audio_text)
                    await asyncio.sleep(1)
                    
                    # Click Verify: #recaptcha-verify-button
                    await challenge_frame.locator('#recaptcha-verify-button').click()
                    await asyncio.sleep(4)

                except Exception as e_link:
                    # Check if it was an IP block/error message
                    if await challenge_frame.locator('.rc-doscaptcha-header-text').is_visible():
                        print(f"[{username}] ReCaptcha Error: Your queries are acting like an automated computer (IP Block).")
                    else:
                        print(f"[{username}] Audio download link not found or timeout: {e_link}")
        
            except Exception as e:
                print(f"[{username}] ReCaptcha interaction failed: {e}")

            if await page.locator('#reg_account').is_visible():
                print(f"[{username}] Registration failed (Form still visible).")
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
            # Close browser
            if browser:
                try:
                    await browser.close()
                except Exception as e:
                    print(f"[{username}] Error closing browser: {e}")
            
            # Close and delete GPM profile if it was created
            if gpm_client and created_gpm_profile_id:
                try:
                    # Close the profile first
                    await gpm_client.close_profile(created_gpm_profile_id)
                    print(f"[{username}] Closed GPM profile: {created_gpm_profile_id}")
                except Exception as e:
                    print(f"[{username}] Error closing GPM profile: {e}")
                
                try:
                    # Hard delete the profile (database and storage)
                    from src.utils.gpm import DeleteMode
                    await gpm_client.delete_profile(created_gpm_profile_id, DeleteMode.DatabaseAndStorage)
                    print(f"[{username}] Deleted GPM profile: {created_gpm_profile_id}")
                except Exception as e:
                    print(f"[{username}] Error deleting GPM profile: {e}")

if __name__ == "__main__":
    # Test run
    # Mock solvers for testing without loading heavy models? No, user wants integration.
    # But for a quick test of browser logic, I can import them.
    pass
