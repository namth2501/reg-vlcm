from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch
import os
import string

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
