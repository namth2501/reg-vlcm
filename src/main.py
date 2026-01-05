import asyncio
import argparse
from src.utils.ocr import OCRSolver
from src.utils.audio import AudioSolver
from src.register import register_account
import sys

async def worker(queue, ocr_solver, audio_solver, progress, total_count, save_ocr_images=False, gpm_client=None, gpm_config=None):
    """
    Worker that consumes tasks from queue and runs registration.
    If fails, puts task back to queue.
    """
    while True:
        task_id = await queue.get()
        try:
            print(f"Starting registration task {task_id}")
            # Run without headless to see what's happening, or pass args.headless if we added it
            await register_account(ocr_solver, audio_solver, headless=False, task_id=task_id, save_ocr_images=save_ocr_images, gpm_client=gpm_client, gpm_config=gpm_config)
            
            # Update progress
            progress['current'] += 1
            print(f"[{progress['current']}/{total_count}] Task {task_id} Completed Successfully.")
            
            queue.task_done()
        except Exception as e:
            print(f"Task {task_id} Failed: {e}")
            print(f"Retrying task {task_id}...")
            # Put back in queue to retry
            queue.put_nowait(task_id)
            queue.task_done()
            await asyncio.sleep(2) # Backoff slightly

async def main():
    # Load config defaults
    import json
    import os
    
    # Ensure local ffmpeg (if downloaded by setup.py) is in PATH
    os.environ["PATH"] = os.getcwd() + os.pathsep + os.environ["PATH"]

    config = {"count": 1, "concurrency": 1}
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r") as f:
                config.update(json.load(f))
        except Exception as e:
            print(f"Warning: Failed to load config.json: {e}")

    parser = argparse.ArgumentParser(description="Automate VLCM Account Registration")
    parser.add_argument("--count", type=int, default=config.get("count", 1), help="Number of accounts to register")
    parser.add_argument("--concurrency", type=int, default=config.get("concurrency", 1), help="Number of concurrent browsers")
    
    args = parser.parse_args()
    
    print(f"Initializing automation: {args.count} targets, {args.concurrency} threads.")
    
    # 1. Load Models/Solvers
    captcha_solver_type = config.get("captcha_solver", "ocr").lower()
    print(f"Using CAPTCHA solver: {captcha_solver_type}")
    
    try:
        if captcha_solver_type == "omocaptcha":
            from src.utils.ocr import OMOcaptchaSolver
            omocaptcha_api_key = config.get("omocaptcha_api_key", "")
            if not omocaptcha_api_key:
                print("Error: omocaptcha_api_key is required in config.json when using omocaptcha solver")
                sys.exit(1)
            ocr_solver = OMOcaptchaSolver(api_key=omocaptcha_api_key)
        else:
            # Default to OCR
            ocr_solver = OCRSolver(model_name='anuashok/ocr-captcha-v3')
        
        audio_solver = AudioSolver(model_size="base")
    except Exception as e:
        print(f"Failed to initialize models: {e}")
        sys.exit(1)
        
    # 2. Setup Queue
    queue = asyncio.Queue()
    for i in range(args.count):
        queue.put_nowait(i)
    
    # Get save_ocr_images config
    save_ocr_images = config.get("save_ocr_images", False)
    
    # Initialize GPM client if enabled
    gpm_client = None
    gpm_config = None
    use_gpm = config.get("use_gpm", False)
    
    if use_gpm:
        try:
            from src.utils.gpm import GpmLoginClient
            gpm_host = config.get("gpm_host", "127.0.0.1")
            gpm_port = config.get("gpm_port", 19995)
            
            gpm_client = GpmLoginClient(host=gpm_host, port=gpm_port)
            print(f"GPM client initialized: {gpm_host}:{gpm_port}")
            
            # Prepare GPM config for profile creation
            gpm_config = {
                'profile_name_prefix': config.get("gpm_profile_name_prefix", "vlcm_reg_"),
                'group_name': config.get("gpm_group_name", "All"),
                'raw_proxy': config.get("gpm_raw_proxy", "")
            }
            print(f"GPM will create new profiles with prefix: {gpm_config['profile_name_prefix']}")
        except Exception as e:
            print(f"Warning: Failed to initialize GPM client: {e}")
            print("Falling back to regular Chromium launch")
            use_gpm = False
            gpm_client = None
            gpm_config = None
        
    # 3. Start Workers
    progress = {'current': 0}
    workers = []
    for _ in range(args.concurrency):
        task = asyncio.create_task(worker(queue, ocr_solver, audio_solver, progress, args.count, save_ocr_images, gpm_client, gpm_config))
        workers.append(task)
    
    # 4. Wait for queue to process all items
    await queue.join()
    
    print(f"All {args.count} registration tasks finished successfully.")
    
    # Cancel workers
    for w in workers:
        w.cancel()
    
    # Wait for workers to cancel (optional)
    await asyncio.gather(*workers, return_exceptions=True)

if __name__ == "__main__":
    asyncio.run(main())
