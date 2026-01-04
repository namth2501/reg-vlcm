import asyncio
import argparse
from src.utils.ocr import OCRSolver
from src.utils.audio import AudioSolver
from src.register import register_account
import sys

async def worker(queue, ocr_solver, audio_solver, semaphore):
    """
    Worker that consumes tasks from queue and runs registration with concurrency limit.
    """
    while True:
        task_id = await queue.get()
        async with semaphore:
            try:
                print(f"Starting registration task {task_id}")
                await register_account(ocr_solver, audio_solver, headless=False)
            except Exception as e:
                print(f"Task {task_id} failed: {e}")
            finally:
                queue.task_done()

async def main():
    parser = argparse.ArgumentParser(description="Automate VLCM Account Registration")
    parser.add_argument("--count", type=int, default=1, help="Number of accounts to register")
    parser.add_argument("--concurrency", type=int, default=1, help="Number of concurrent browsers")
    
    args = parser.parse_args()
    
    print(f"Initializing automation: {args.count} accounts, {args.concurrency} concurrent threads.")
    
    # 1. Load Models Once (Global Singleton pattern)
    print("Loading AI Models...")
    try:
        ocr_solver = OCRSolver(model_name='anuashok/ocr-captcha-v3')
        # Using 'base' model for audio as tested
        audio_solver = AudioSolver(model_size="base")
    except Exception as e:
        print(f"Failed to initialize models: {e}")
        sys.exit(1)
        
    # 2. Setup Queue and Workers
    queue = asyncio.Queue()
    for i in range(args.count):
        queue.put_nowait(i)
        
    semaphore = asyncio.Semaphore(args.concurrency)
    
    workers = []
    # Create workers equal to concurrency (or count if smaller, but logic is same)
    # Actually, we can spawn 'concurrency' number of long-running workers
    # OR spawn 'count' tasks and let semaphore limit them.
    # Spawning 'count' tasks is cleaner for simple logic.
    
    tasks = []
    for i in range(args.count):
        # We need to wrap the call with semaphore
        tasks.append(asyncio.create_task(run_protected(semaphore, ocr_solver, audio_solver, i)))
    
    await asyncio.gather(*tasks)
    print("All tasks completed.")

async def run_protected(semaphore, ocr, audio, idx):
    async with semaphore:
         await register_account(ocr, audio, headless=False)

if __name__ == "__main__":
    asyncio.run(main())
