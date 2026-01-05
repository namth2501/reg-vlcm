from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch
import os
import string
import base64
import aiohttp
import asyncio
import json

def normalize_captcha_image(image: Image.Image) -> Image.Image:
    image = image.convert("L")
    image = image.resize((160, 60))
    image = image.point(lambda x: 0 if x < 150 else 255)
    return image.convert("RGB")

class OCRSolver:
    def __init__(self, model_name='anuashok/ocr-captcha-v3'):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Loading OCR Model: {model_name} on {self.device}...")
        try:
            self.processor = TrOCRProcessor.from_pretrained(model_name)
            self.model = VisionEncoderDecoderModel.from_pretrained(model_name).to(self.device)
            print("OCR Model loaded successfully.")
        except Exception as e:
            print(f"Failed to load OCR model: {e}")
            raise e

    def solve(self, image_path_or_bytes):
        """
        Solves CAPTCHA from file path or bytes/PIL Image.
        """
        if isinstance(image_path_or_bytes, str):
            image = Image.open(image_path_or_bytes).convert("RGB")
        elif isinstance(image_path_or_bytes, (bytes, bytearray)):
            import io
            image = Image.open(io.BytesIO(image_path_or_bytes)).convert("RGB")
        else:
            image = image_path_or_bytes.convert("RGB")

        image = normalize_captcha_image(image)

        pixel_values = self.processor(images=image, return_tensors="pt").pixel_values.to(self.device)
        lowercase_ids = [
            self.processor.tokenizer.convert_tokens_to_ids(c)
            for c in string.ascii_lowercase
        ]
        generated_ids = self.model.generate(pixel_values, min_length=6, max_length=6, num_beams=4, bad_words_ids=[[i] for i in lowercase_ids], early_stopping=True)
        generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        return generated_text.strip()


class OMOcaptchaSolver:
    def __init__(self, api_key: str):
        """
        Initialize OMOcaptcha solver with API key.
        """
        if not api_key:
            raise ValueError("OMOcaptcha API key is required")
        self.api_key = api_key
        self.create_task_url = "https://api.omocaptcha.com/v2/createTask"
        self.get_result_url = "https://api.omocaptcha.com/v2/getTaskResult"
        print("OMOcaptcha solver initialized.")

    async def solve(self, image_path_or_bytes):
        """
        Solves CAPTCHA using OMOcaptcha API.
        Accepts file path, bytes, or PIL Image.
        Returns the solved text.
        """
        # Convert image to base64
        if isinstance(image_path_or_bytes, str):
            with open(image_path_or_bytes, 'rb') as f:
                image_bytes = f.read()
        elif isinstance(image_path_or_bytes, (bytes, bytearray)):
            image_bytes = image_path_or_bytes
        else:
            import io
            buffer = io.BytesIO()
            image_path_or_bytes.save(buffer, format='PNG')
            image_bytes = buffer.getvalue()
        
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Create task
        task_id = await self._create_task(image_base64)
        
        # Poll for result
        result = await self._get_result(task_id)
        
        return result

    async def _create_task(self, image_base64: str) -> str:
        """
        Create a CAPTCHA solving task.
        Returns task_id.
        """
        payload = {
            "clientKey": self.api_key,
            "task": {
                "type": "ImageToTextTask",
                "imageBase64": image_base64
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.create_task_url, json=payload) as response:
                data = await response.json()
                
                if data.get("errorId") != 0:
                    error_code = data.get("errorCode", "UNKNOWN")
                    error_desc = data.get("errorDescription", "Unknown error")
                    raise Exception(f"OMOcaptcha create task failed: {error_code} - {error_desc}")
                
                task_id = data.get("taskId")
                if not task_id:
                    raise Exception("OMOcaptcha did not return taskId")
                
                return task_id

    async def _get_result(self, task_id: str, max_retries: int = 30) -> str:
        """
        Poll for task result.
        Returns the solved text.
        """
        payload = {
            "clientKey": self.api_key,
            "taskId": task_id
        }
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(max_retries):
                async with session.post(self.get_result_url, json=payload) as response:
                    data = await response.json()
                    
                    if data.get("errorId") != 0:
                        error_code = data.get("errorCode", "UNKNOWN")
                        error_desc = data.get("errorDescription", "Unknown error")
                        raise Exception(f"OMOcaptcha get result failed: {error_code} - {error_desc}")
                    
                    status = data.get("status")
                    
                    if status == "ready":
                        solution = data.get("solution", {})
                        text = solution.get("text", "")
                        if not text:
                            raise Exception("OMOcaptcha returned empty solution")
                        return text
                    elif status == "processing":
                        # Wait 2 seconds before retrying
                        await asyncio.sleep(2)
                        continue
                    elif status == "fail":
                        error_code = data.get("errorCode", "UNKNOWN")
                        error_desc = data.get("errorDescription", "Task failed")
                        raise Exception(f"OMOcaptcha task failed: {error_code} - {error_desc}")
                    else:
                        # Unknown status, wait and retry
                        await asyncio.sleep(2)
                        continue
            
            raise Exception(f"OMOcaptcha timeout after {max_retries} attempts")
