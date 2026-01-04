from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch
import os

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

        pixel_values = self.processor(images=image, return_tensors="pt").pixel_values.to(self.device)
        generated_ids = self.model.generate(pixel_values)
        generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        return generated_text.strip()
