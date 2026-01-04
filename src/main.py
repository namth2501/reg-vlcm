import asyncio
import argparse
from src.utils.ocr import OCRSolver
from src.utils.audio import AudioSolver
from src.register import register_account
import sys

async def worker(queue, ocr_solver, audio_solver, progress, total_count):
    """
    Worker that consumes tasks from queue and runs registration.
    If fails, puts task back to queue.
    """
    while True:
        task_id = await queue.get()
        try:
            print(f"Starting registration task {task_id}")
            # Run without headless to see what's happening, or pass args.headless if we added it
            await register_account(ocr_solver, audio_solver, headless=False)
            
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
    parser = argparse.ArgumentParser(description="Automate VLCM Account Registration")
    parser.add_argument("--count", type=int, default=1, help="Number of accounts to register")
    parser.add_argument("--concurrency", type=int, default=1, help="Number of concurrent browsers")
    
    args = parser.parse_args()
    
    print(f"Initializing automation: {args.count} targets, {args.concurrency} threads.")
    
    # 1. Load Models Once
    print("Loading AI Models...")
    try:
        ocr_solver = OCRSolver(model_name='anuashok/ocr-captcha-v3')
        audio_solver = AudioSolver(model_size="base")
    except Exception as e:
        print(f"Failed to initialize models: {e}")
        sys.exit(1)
        
    # 2. Setup Queue
    queue = asyncio.Queue()
    for i in range(args.count):
        queue.put_nowait(i)
        
    # 3. Start Workers
    progress = {'current': 0}
    workers = []
    for _ in range(args.concurrency):
        task = asyncio.create_task(worker(queue, ocr_solver, audio_solver, progress, args.count))
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
