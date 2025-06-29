import pymupdf
import pytesseract
from PIL import Image
import os
import re
import unicodedata
import html

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

def extract_images_from_pdf(pdf_path, output_dir="extracted_images"):
    """Extract all images from PDF and save them."""
    os.makedirs(output_dir, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    image_list = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_dict = page.get_images()
        
        for img_index, img in enumerate(image_dict):
            xref = img[0]
            pix = pymupdf.Pixmap(doc, xref)
            
            if pix.n - pix.alpha < 4:  # GRAY or RGB
                img_filename = f"333_BLOCK{page_num+1:03d}_LINE{img_index+1:03d}.png"
                img_path = os.path.join(output_dir, img_filename)
                pix.save(img_path)
                
                image_list.append({
                    'page': page_num + 1,
                    'filename': img_filename,
                    'path': img_path,
                    'index': img_index + 1
                })
            
            pix = None
    
    doc.close()
    return image_list

def ocr_image(image_path, lang='vie'):
    """Extract text from image using OCR."""
    try:
        # Configure tesseract for Vietnamese
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(
            Image.open(image_path), 
            lang=lang, 
            config=custom_config
        )
        return clean_text(text)
    except Exception as e:
        print(f"OCR error for {image_path}: {e}")
        return ""

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
                # Keep both Vietnamese and meaningful text
                if cleaned and len(cleaned) > 5:
                    sentences.append(cleaned)
            current_sentence = ""
    
    # Add remaining text
    if current_sentence.strip():
        cleaned = clean_text(current_sentence)
        if cleaned and len(cleaned) > 5:
            sentences.append(cleaned)
    
    return sentences

def process_images_with_ocr(pdf_path, output_file="ocr_results.txt", start_line=13013):
    """Extract images from PDF and process with OCR, format like your example."""
    print(f"🔄 Extracting images from PDF: {pdf_path}")
    
    # Extract images
    images = extract_images_from_pdf(pdf_path)
    print(f"📷 Found {len(images)} images")
    
    # Process with OCR
    results = []
    line_number = start_line
    
    for img_info in images:
        print(f"🔍 Processing OCR for: {img_info['filename']}")
        ocr_text = ocr_image(img_info['path'])
        
        if ocr_text:
            # Split into sentences or meaningful chunks
            sentences = split_sentences(ocr_text)
            
            if not sentences:  # If no sentences found, use the whole text
                sentences = [ocr_text]
            
            for sentence in sentences:
                if len(sentence.strip()) > 3:  # Only meaningful text
                    result_line = f'"{img_info["filename"]}": "{sentence}",'
                    results.append((line_number, result_line))
                    line_number += 1
    
    # Write results to file
    with open(output_file, 'w', encoding='utf-8') as f:
        for line_num, content in results:
            f.write(f"{line_num}\t{content}\n")
    
    print(f"✅ OCR results saved to: {output_file}")
    print(f"📊 Total processed lines: {len(results)}")
    
    return results

def process_pdf_pages_ocr(pdf_path, output_file="page_ocr_results.txt", start_line=13013):
    """Process entire PDF pages with OCR (alternative approach)."""
    print(f"🔄 Processing PDF pages with OCR: {pdf_path}")
    
    doc = pymupdf.open(pdf_path)
    results = []
    line_number = start_line
    file = open(output_file, 'w', encoding='utf-8')
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Convert page to image
        mat = pymupdf.Matrix(2.0, 2.0)  # Increase resolution
        pix = page.get_pixmap(matrix=mat)
        img_path = f"temp_page_{page_num+1}.png"
        pix.save(img_path)
        
        print(f"🔍 Processing OCR for page {page_num+1}")
        ocr_text = ocr_image(img_path)
        
        if ocr_text:
            sentences = split_sentences(ocr_text)
            
            for sentence in sentences:
                if len(sentence.strip()) > 5:
                    filename = f"333_BLOCK{page_num+1:03d}_LINE{len(results)+1:03d}.png"
                    result_line = f'"{filename}": "{sentence}",'
                    file.write(f"{line_number}\t{result_line}\n")
                    results.append((line_number, result_line))
                    line_number += 1
        
        # Clean up temp file
        if os.path.exists(img_path):
            os.remove(img_path)
        
        pix = None
    
    doc.close()
    
    # Write results to file
    # with open(output_file, 'w', encoding='utf-8') as f:
    #     for line_num, content in results:
    #         f.write(f"{line_num}\t{content}\n")
    
    print(f"✅ OCR results saved to: {output_file}")
    print(f"📊 Total processed lines: {len(results)}")
    
    return results

# Example usage:
if __name__ == "__main__":
    # Method 1: Extract embedded images and OCR them
    # results = process_images_with_ocr("your_pdf_file.pdf", "image_ocr_output.txt")
    
    # Method 2: Convert each page to image and OCR (recommended for scanned PDFs)
    results = process_pdf_pages_ocr("/home/octoopt/workspace/projects/learn-from-basics/nlp-vietnamese-phd/temp/TRANG TỬ NAM HOA KINH.pdf", "page_ocr_output.txt")
    
    
    print(results)