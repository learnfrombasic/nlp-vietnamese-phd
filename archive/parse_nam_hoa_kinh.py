import pymupdf
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import unicodedata
from pathlib import Path
import html

# Import the improved HTML cleaning functions

def remove_html_entities(text):
    """
    Comprehensive HTML entity removal function that handles all variations of &quot;
    and other HTML entities.
    """
    # First try html.unescape for standard entities
    try:
        text = html.unescape(text)
    except:
        pass

    # Aggressive &quot; removal - handle all variations
    text = text.replace("&quot;", "")
    text = text.replace("&quot", "")  # Missing semicolon
    text = text.replace("quot;", "")  # Missing ampersand
    text = text.replace("&QUOT;", "")  # Uppercase
    text = text.replace("&Quot;", "")  # Mixed case

    # Handle other common HTML entities
    html_entities = {
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&apos;": "'",
        "&nbsp;": " ",
        "&hellip;": "...",
        "&mdash;": "—",
        "&ndash;": "–",
        "&ldquo;": "",
        "&rdquo;": "",
        "&lsquo;": "",
        "&rsquo;": "",
    }

    for entity, replacement in html_entities.items():
        text = text.replace(entity, replacement)
        # Also handle uppercase versions
        text = text.replace(entity.upper(), replacement)

    # Use regex to catch any remaining HTML entity patterns
    text = re.sub(r"&[a-zA-Z]+;", "", text)
    text = re.sub(r"&[a-zA-Z]+", "", text)  # Missing semicolon

    return text



# ──────────────── CONFIGURATION ────────────────
BOOK_METADATA = {
    "TITLE": "Nam Hoa Kinh",
    "VOLUME": "",
    "AUTHOR": "Trang Tử",
    "PERIOD": "Chiến Quốc",
    "LANGUAGE": "Hán-Việt",
    "TRANSLATOR": "Nguyễn Duy Cần",
    "SOURCE": "thuviensach.vn",
}

KNOWN_SECTIONS = [
    "LỜI NÓI ĐẦU", "TIỂU DẪN", "NỘI THIÊN", "NGOẠI THIÊN", "TẠP THIÊN",
    "TIÊU DIÊU DU", "TỀ VẬT LUẬN", "DƯỠNG SINH CHỦ", "NHÂN GIAN THẾ",
    "ĐỨC SUNG PHÙ", "ĐẠI TÔNG SƯ", "ỨNG ĐẾ VƯƠNG"
]

# ──────────────── UTILITY FUNCTIONS ────────────────
def normalize(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())

def is_chinese(text: str) -> bool:
    """Check if text contains Chinese characters."""
    chinese_chars = sum(1 for c in text if 0x4E00 <= ord(c) <= 0x9FFF)
    total_chars = len([c for c in text if c.isalnum()])
    return chinese_chars > 0 and (chinese_chars / max(total_chars, 1)) > 0.3

def is_vietnamese(text: str) -> bool:
    """Check if text contains Vietnamese characters."""
    vietnamese_pattern = re.compile(r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ]')
    return bool(vietnamese_pattern.search(text))

def classify_text(text: str) -> str:
    """Classify text as Chinese, Vietnamese, or Mixed."""
    text = normalize(text)
    has_chinese = is_chinese(text)
    has_vietnamese = is_vietnamese(text)
    
    if has_chinese and has_vietnamese:
        return "Mixed"
    elif has_chinese:
        return "Chinese"
    elif has_vietnamese:
        return "Vietnamese"
    return "Other"

def clean_text(text: str) -> str:
    """Clean text with comprehensive HTML entity removal."""
    # Remove HTML entities first
    text = remove_html_entities(text)
    text = normalize(text)
    
    # Remove common OCR artifacts
    clean_patterns = ["999", "F.F.F", "***", "---", "___", "A.", "B.", "C."]
    for pattern in clean_patterns:
        text = text.replace(pattern, "")
    
    # Remove invisible characters
    text = re.sub(r"[\u200b\u200e\u202a\u202c\ufeff]+", "", text)
    
    # Clean up multiple spaces
    text = re.sub(r"\s+", " ", text)
    
    # Remove the specific characters requested by the user
    text = text.replace('⸈', '')
    
    return text.strip()

def clean_page(text: str, known_sections: list[str]) -> str:
    """Clean page OCR text."""
    text = normalize(text)
    text = remove_html_entities(text)
    
    for section_name in known_sections:  # Detect and preserve titles
        if section_name in text:
            preserved_title = section_name
            text = re.sub(rf'(?i)^{re.escape(section_name)}', preserved_title, text)  # Keep title
            break  # Only handle the first match
    
    text = re.sub(r"TRANG TỬ.*NAM HOA KINH.*", "", text, flags=re.I)  # Existing removal
    text = re.sub(r"Trang \d+", "", text, flags=re.I)
    text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    
    return text.strip()

def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences with better Chinese-Vietnamese handling."""
    text = clean_text(text)
    
    # Split by paragraph first
    paragraphs = re.split(r"\n\s*\n", text)
    sentences = []
    
    for para in paragraphs:
        if not para.strip():
            continue
            
        # For each paragraph, split by common sentence delimiters
        current_sentence = ""
        i = 0
        
        while i < len(para):
            char = para[i]
            current_sentence += char
            
            # Check for sentence endings
            if char in [".", "!", "?", "。", "！", "？"]:
                # Look ahead to see if this is really end of sentence
                next_char = para[i + 1] if i + 1 < len(para) else ""
                
                # Don't split on numbers like "1.2" or "3.14"
                if char == "." and next_char.isdigit():
                    i += 1
                    continue
                
                # Don't split Chinese text on period unless followed by space/newline
                if char == "." and is_chinese(current_sentence) and next_char not in [" ", "\n", "", "\t"]:
                    i += 1
                    continue
                
                # Add sentence if not empty
                if current_sentence.strip():
                    cleaned = clean_text(current_sentence)
                    if cleaned and len(cleaned) > 5:  # Filter out very short sentences
                        sentences.append(cleaned)
                current_sentence = ""
            
            i += 1
        
        # Add any remaining text
        if current_sentence.strip():
            cleaned = clean_text(current_sentence)
            if cleaned and len(cleaned) > 5:
                sentences.append(cleaned)
    
    return sentences

def detect_sections(pages, known_sections=KNOWN_SECTIONS):
    """Detect sections from table of contents."""
    
    sections = []
    current = {"name": "TIÊU DIÊU DU", "pages": []}  # Default section
    
    for i, txt in enumerate(pages, 1):
        cleaned_txt = clean_page(txt, known_sections)
        
        # Look for section titles
        found_section = False
        for section_name in known_sections:
            if section_name in cleaned_txt:
                if current["pages"]:
                    sections.append(current)
                current = {"name": section_name, "pages": [(i, cleaned_txt)]}
                found_section = True
                print(f"Found section '{section_name}' on page {i}")
                break
        
        if not found_section:
            current["pages"].append((i, cleaned_txt))
    
    if current["pages"]:
        sections.append(current)
    
    print(f"Total sections found: {len(sections)}")
    for section in sections:
        print(f"- {section['name']}: {len(section['pages'])} pages")
    
    return sections

def pair_chinese_vietnamese_sentences(sentences):
    pairs = []
    i = 0
    
    while i < len(sentences):
        current_sent = sentences[i]
        current_lang = classify_text(current_sent)
        
        if i + 1 < len(sentences):
            next_sent = sentences[i + 1]
            next_lang = classify_text(next_sent)
            
            if current_lang == 'Chinese' and next_lang == 'Vietnamese':
                pairs.append({'chinese': current_sent, 'vietnamese': next_sent})
                i += 2  # Skip to next
            elif current_lang == 'Vietnamese':
                pairs.append({'chinese': None, 'vietnamese': current_sent})  # Unpaired Vietnamese
                i += 1
            else:
                i += 1  # Skip non-pairs
        else:
            if current_lang == 'Vietnamese':  # Last sentence is unpaired Vietnamese
                pairs.append({'chinese': None, 'vietnamese': current_sent})
            i += 1  # Move on
    
    return pairs

def write_pretty_xml(tree, out_path):
    """Write XML with pretty formatting."""
    pretty = minidom.parseString(ET.tostring(tree.getroot(), encoding="utf-8"))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(pretty.toprettyxml(indent="  "))

def build_xml_for_nam_hoa_kinh(pdf_path, output_path="nam_hoa_kinh_parsed.xml", code="PKS_001"):
    """
    Parse Nam Hoa Kinh PDF and create XML with 1:1 Chinese-Vietnamese sentence pairs.
    """
    print(f"🔄 Processing PDF: {pdf_path}")
    
    # Step 1: Read PDF
    doc = pymupdf.open(pdf_path)
    pages_text = [clean_page(p.get_text()) for p in doc]
    print(f"📄 Extracted {len(pages_text)} pages")
    
    # Step 2: Detect sections
    sections = detect_sections(pages_text, known_sections=KNOWN_SECTIONS)
    
    # Step 3: Create XML structure
    root = ET.Element("root")
    file_el = ET.SubElement(root, "FILE", ID=code)
    
    # Metadata
    meta = ET.SubElement(file_el, "meta")
    ET.SubElement(meta, "TITLE").text = BOOK_METADATA["TITLE"]
    ET.SubElement(meta, "VOLUME").text = BOOK_METADATA["VOLUME"]
    ET.SubElement(meta, "AUTHOR").text = BOOK_METADATA["AUTHOR"]
    ET.SubElement(meta, "PERIOD").text = BOOK_METADATA["PERIOD"]
    ET.SubElement(meta, "LANGUAGE").text = BOOK_METADATA["LANGUAGE"]
    ET.SubElement(meta, "TRANSLATOR").text = BOOK_METADATA["TRANSLATOR"]
    ET.SubElement(meta, "SOURCE").text = BOOK_METADATA["SOURCE"]
    
    # Step 4: Process sections
    total_pairs = 0
    
    for sect_id, section in enumerate(sections, 1):
        sect_el = ET.SubElement(
            file_el, "SECT", ID=f"{code}.{sect_id:03}", NAME=section["name"]
        )
        
        for page_num, page_text in section["pages"]:
            page_el = ET.SubElement(
                sect_el, "PAGE", ID=f"{code}.{sect_id:03}.{page_num:03}"
            )
            
            # Extract sentences from page
            sentences = split_into_sentences(page_text)
            
            # Pair Chinese and Vietnamese sentences
            pairs = pair_chinese_vietnamese_sentences(sentences)
            
            # Create STC elements
            for sent_id, pair in enumerate(pairs, 1):
                stc_el = ET.SubElement(
                    page_el, "STC", ID=f"{code}.{sect_id:03}.{page_num:03}.{sent_id:02}"
                )
                
                if pair["chinese"] and pair["vietnamese"]:
                    # Both Chinese and Vietnamese - use C and V tags
                    ET.SubElement(stc_el, "C").text = pair["chinese"]
                    ET.SubElement(stc_el, "V").text = pair["vietnamese"]
                elif pair["chinese"]:
                    # Only Chinese - use C tag
                    ET.SubElement(stc_el, "C").text = pair["chinese"]
                elif pair["vietnamese"]:
                    stc_el.text = pair["vietnamese"]  # Set text directly in STC as per user request
                
                total_pairs += 1
    
    # Step 5: Write XML
    tree = ET.ElementTree(root)
    write_pretty_xml(tree, output_path)
    
    print(f"✅ Created XML file: {output_path}")
    print(f"📊 Total sentence pairs: {total_pairs}")
    
    return output_path