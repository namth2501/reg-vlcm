from transformers import VisionEncoderDecoderModel, TrOCRProcessor, AutoModelForVision2Seq, AutoProcessor
from PIL import Image
import torch
import glob
import os

import time

def solve_hf(image_path, model, processor, device):
    image = Image.open(image_path).convert("RGB")
    pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(device)

    generated_ids = model.generate(pixel_values)
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    
    return generated_text

def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    print("Loading model anuashok/ocr-captcha-v3...")
    try:
        processor = TrOCRProcessor.from_pretrained('anuashok/ocr-captcha-v3')
        model = VisionEncoderDecoderModel.from_pretrained('anuashok/ocr-captcha-v3').to(device)
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    samples_dir = 'samples'
    image_files = glob.glob(os.path.join(samples_dir, '*.png')) + \
                  glob.glob(os.path.join(samples_dir, '*.jpg'))
    
    print(f"Found {len(image_files)} images.")
    
    for img_path in sorted(image_files):
        print(f"Processing {os.path.basename(img_path)}...")
        try:
            start_time = time.time()
            result = solve_hf(img_path, model, processor, device)
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"File: {os.path.basename(img_path)} -> Text: '{result}' (Time: {elapsed_time:.4f}s)")
        except Exception as e:
            print(f"Error processing {img_path}: {e}")

if __name__ == "__main__":
    main()
