import os
import cv2
import numpy as np
from paddleocr import PaddleOCR
from pathlib import Path
import re
import unicodedata
import html
from PIL import Image

def normalize(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())

def remove_html_entities(text):
    """Remove HTML entities comprehensively."""
    try:
        text = html.unescape(text)
    except:
        pass
    
    # Remove &quot; and &quote; variations
    text = text.replace("&quot;", "")
    text = text.replace("&quot", "")
    text = text.replace("&quote;", "")
    text = text.replace("&quote", "")
    text = text.replace("quot;", "")
    text = text.replace("quote;", "")
    
    # Remove other common entities
    html_entities = {
        "&amp;": "&", "&lt;": "<", "&gt;": ">", "&apos;": "'",
        "&nbsp;": " ", "&hellip;": "...", "&mdash;": "—", "&ndash;": "–"
    }
    
    for entity, replacement in html_entities.items():
        text = text.replace(entity, replacement)
    
    # Clean remaining entities with regex
    text = re.sub(r"&[a-zA-Z]+;?", "", text)
    
    return text

def clean_text(text: str) -> str:
    """Clean text comprehensively."""
    text = normalize(text)
    text = remove_html_entities(text)
    
    clean_patterns = ["***", "---", "___", "..."]
    for pattern in clean_patterns:
        text = text.replace(pattern, "")
    
    # Remove invisible characters and normalize spaces
    text = re.sub(r"[\u200b\u200e\u202a\u202c\ufeff]+", "", text)
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()

def is_vietnamese(text: str) -> bool:
    """Check if text contains Vietnamese characters."""
    vietnamese_pattern = re.compile(r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ]')
    return bool(vietnamese_pattern.search(text))

# Initialize PaddleOCR with Vietnamese language
print("🚀 Initializing PaddleOCR for Vietnamese...")
ocr = PaddleOCR(use_angle_cls=True, lang='vi', show_log=False)
print("✅ PaddleOCR initialized successfully!")

def ocr_image_with_paddle(image_path, confidence_threshold=0.6):
    """Extract text from image using PaddleOCR."""
    try:
        print(f"🔍 Processing: {os.path.basename(image_path)}")
        
        # Read image
        if isinstance(image_path, str):
            img = cv2.imread(image_path)
            if img is None:
                print(f"❌ Could not read image: {image_path}")
                return "", []
        else:
            img = image_path
        
        # Perform OCR
        result = ocr.ocr(img, cls=True)
        
        # Extract text and details
        extracted_text = []
        detailed_results = []
        
        if result and result[0]:
            for line in result[0]:
                if len(line) >= 2:
                    bbox = line[0]  # Bounding box coordinates
                    text_info = line[1]  # (text, confidence)
                    text = text_info[0]
                    confidence = text_info[1]
                    
                    # Only keep text with good confidence
                    if confidence >= confidence_threshold:
                        cleaned_text = clean_text(text)
                        if cleaned_text and len(cleaned_text) > 2:
                            extracted_text.append(cleaned_text)
                            
                            detailed_results.append({
                                'text': cleaned_text,
                                'confidence': confidence,
                                'bbox': bbox
                            })
                            
                            print(f"   📝 '{cleaned_text}' (confidence: {confidence:.2f})")
        
        full_text = " ".join(extracted_text)
        return clean_text(full_text), detailed_results
        
    except Exception as e:
        print(f"❌ PaddleOCR error for {image_path}: {e}")
        return "", []

def process_single_image(image_path, output_format="formatted"):
    """Process a single image and return results."""
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return None
    
    print(f"\n{'='*60}")
    print(f"Processing: {os.path.basename(image_path)}")
    print(f"{'='*60}")
    
    # Get OCR results
    text, details = ocr_image_with_paddle(image_path)
    
    if not text:
        print("❌ No text extracted from this image")
        return None
    
    # Prepare results
    result = {
        'image_path': image_path,
        'filename': os.path.basename(image_path),
        'extracted_text': text,
        'is_vietnamese': is_vietnamese(text),
        'word_count': len(text.split()),
        'confidence_avg': sum(d['confidence'] for d in details) / len(details) if details else 0,
        'details': details
    }
    
    # Display results
    print(f"✅ Text extracted successfully!")
    print(f"📊 Stats: {result['word_count']} words, avg confidence: {result['confidence_avg']:.2f}")
    print(f"🇻🇳 Vietnamese text detected: {'Yes' if result['is_vietnamese'] else 'No'}")
    print(f"\n📝 EXTRACTED TEXT:")
    print("-" * 40)
    print(text)
    print("-" * 40)
    
    return result

def process_image_directory(image_dir, output_file="paddle_ocr_results.txt", start_line=13013):
    """Process all images in a directory with PaddleOCR."""
    
    image_dir = Path(image_dir)
    if not image_dir.exists():
        print(f"❌ Directory not found: {image_dir}")
        return []
    
    # Find all image files
    image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(image_dir.glob(f"*{ext}"))
        image_files.extend(image_dir.glob(f"*{ext.upper()}"))
    
    if not image_files:
        print(f"❌ No image files found in: {image_dir}")
        return []
    
    print(f"🔄 Found {len(image_files)} images to process")
    print(f"📁 Processing directory: {image_dir}")
    
    results = []
    line_number = start_line
    
    # Process each image
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, img_path in enumerate(sorted(image_files), 1):
            print(f"\n[{i}/{len(image_files)}] Processing: {img_path.name}")
            
            text, details = ocr_image_with_paddle(str(img_path))
            
            if text and len(text.strip()) > 5:
                # Split into sentences for better organization
                sentences = split_sentences(text)
                
                if not sentences:
                    sentences = [text]
                
                for sentence in sentences:
                    if len(sentence.strip()) > 3:
                        # Create result line in your desired format
                        result_line = f'"{img_path.name}": "{sentence}",'
                        f.write(f"{line_number}\t{result_line}\n")
                        
                        results.append({
                            'line_number': line_number,
                            'filename': img_path.name,
                            'text': sentence,
                            'confidence': sum(d['confidence'] for d in details) / len(details) if details else 0
                        })
                        
                        line_number += 1
                        print(f"   ✅ Line {line_number-1}: '{sentence[:50]}...'")
            else:
                print(f"   ⚠️ No meaningful text extracted from {img_path.name}")
    
    print(f"\n🎯 SUMMARY:")
    print(f"   📄 Images processed: {len(image_files)}")
    print(f"   📝 Text lines extracted: {len(results)}")
    print(f"   💾 Results saved to: {output_file}")
    
    return results

def split_sentences(text: str) -> list[str]:
    """Split text into Vietnamese sentences."""
    text = clean_text(text)
    
    # Split by common sentence delimiters
    sentences = []
    current_sentence = ""
    
    for char in text:
        current_sentence += char
        if char in [".", "!", "?", "。", ";", ":"]:
            if current_sentence.strip():
                cleaned = clean_text(current_sentence)
                if cleaned and len(cleaned) > 5:
                    sentences.append(cleaned)
            current_sentence = ""
    
    # Add remaining text
    if current_sentence.strip():
        cleaned = clean_text(current_sentence)
        if cleaned and len(cleaned) > 5:
            sentences.append(cleaned)
    
    return sentences

# Example usage functions
def test_single_image():
    """Test with a single image."""
    image_path = "page_images_big/page_005_big.png"
    if os.path.exists(image_path):
        result = process_single_image(image_path)
        return result
    else:
        print(f"❌ Test image not found: {image_path}")
        print("Available images in page_images_big:")
        if os.path.exists("page_images_big"):
            for f in os.listdir("page_images_big"):
                if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                    print(f"   📷 {f}")
        return None

def process_all_images():
    """Process all images in the big images directory."""
    results = process_image_directory(
        "page_images_big", 
        "paddle_ocr_results.txt",
        start_line=13013
    )
    return results

if __name__ == "__main__":
    print("🐼 PaddleOCR Vietnamese Text Recognition")
    print("=" * 50)
    
    # Test with single image first
    print("STEP 1: Testing with single image")
    print("-" * 30)
    test_result = test_single_image()
    
    if test_result:
        print(f"\n✅ Single image test successful!")
        
        # Ask user if they want to process all images
        print("\nSTEP 2: Process all images")
        print("-" * 30)
        
        # Process all images in directory
        all_results = process_all_images()
        
        if all_results:
            print(f"\n🎉 SUCCESS! Processed {len(all_results)} text lines from images")
            print(f"📝 Check 'paddle_ocr_results.txt' for full results")
        else:
            print("❌ No results from batch processing")
    else:
        print("❌ Single image test failed. Please check your image directory.") 