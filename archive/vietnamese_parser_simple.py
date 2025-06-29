import pymupdf
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import unicodedata
from pathlib import Path
import html
from underthesea import ner

# ──────────────── CONSTANTS ────────────────
BASED_ENTITY_GROUPS = ["PER", "ORG", "LOC", "MISC"]  # Common NER entity types

# ──────────────── UTILITY FUNCTIONS ────────────────

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
    
    clean_patterns = ["***", "---", "___"]
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

def split_sentences(text: str) -> list[str]:
    """Split text into Vietnamese sentences."""
    text = clean_text(text)
    
    # Split by common sentence delimiters
    sentences = []
    current_sentence = ""
    
    for char in text:
        current_sentence += char
        if char in [".", "!", "?", "。"]:
            if current_sentence.strip():
                cleaned = clean_text(current_sentence)
                # Only keep Vietnamese sentences
                if cleaned and len(cleaned) > 10 and is_vietnamese(cleaned):
                    sentences.append(cleaned)
            current_sentence = ""
    
    # Add remaining text if it's Vietnamese
    if current_sentence.strip():
        cleaned = clean_text(current_sentence)
        if cleaned and len(cleaned) > 10 and is_vietnamese(cleaned):
            sentences.append(cleaned)
    
    return sentences

def ner_underthesea(text: str) -> list[dict]:
    """Extract named entities from Vietnamese text."""
    try:
        result = ner(text)
        # Filter for important entity types
        valid_entities = [
            ent for ent in result
            if ent.get("entity", "").split("-")[-1] in BASED_ENTITY_GROUPS
        ]
        return valid_entities
    except:
        return []

# ──────────────── MAIN FUNCTION ────────────────

def build_xml_for_book(pdf_path, metadata: dict, output_path="vietnamese_parsed.xml", code="VIE_001"):
    """Parse Vietnamese text from PDF and create XML with NER."""
    print(f"🔄 Processing PDF: {pdf_path}")
    
    # Read PDF
    doc = pymupdf.open(pdf_path)
    pages_text = [p.get_text() for p in doc]
    print(f"📄 Extracted {len(pages_text)} pages")
    
    # Create XML structure
    root = ET.Element("root")
    file_el = ET.SubElement(root, "FILE", ID=code)
    
    # Metadata
    meta = ET.SubElement(file_el, "meta")
    ET.SubElement(meta, "TITLE").text = metadata.get("TITLE", "")
    ET.SubElement(meta, "VOLUME").text = metadata.get("VOLUME", "")
    ET.SubElement(meta, "AUTHOR").text = metadata.get("AUTHOR", "")
    ET.SubElement(meta, "PERIOD").text = metadata.get("PERIOD", "")
    ET.SubElement(meta, "LANGUAGE").text = metadata.get("LANGUAGE", "")
    ET.SubElement(meta, "TRANSLATOR").text = metadata.get("TRANSLATOR", "")
    ET.SubElement(meta, "SOURCE").text = metadata.get("SOURCE", "")
    
    total_sentences = 0
    
    # Process each page
    for page_num, page_text in enumerate(pages_text, 1):
        sentences = split_sentences(page_text)
        
        if not sentences:  # Skip empty pages
            continue
            
        page_el = ET.SubElement(file_el, "PAGE", ID=f"{code}.{page_num:03}")
        
        # Create sentence elements
        for sent_id, sentence in enumerate(sentences, 1):
            stc_el = ET.SubElement(
                page_el, "STC", ID=f"{code}.{page_num:03}.{sent_id:02}"
            )
            stc_el.text = sentence
            
            # Add NER if entities found
            entities = ner_underthesea(sentence)
            print(sentence)
            if entities:
                ner_el = ET.SubElement(stc_el, "NER")
                for entity in entities:
                    entity_type = entity["entity"].split("-")[-1]
                    ET.SubElement(
                        ner_el, "ENTITY",
                        TYPE=entity_type,
                        START=str(entity.get("start", 0)),
                        END=str(entity.get("end", 0))
                    ).text = entity.get("word", "")
            
            total_sentences += 1
    
    # Write XML
    tree = ET.ElementTree(root)
    pretty = minidom.parseString(ET.tostring(tree.getroot(), encoding="utf-8"))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(pretty.toprettyxml(indent="  "))
    
    print(f"✅ Created XML file: {output_path}")
    print(f"📊 Total Vietnamese sentences: {total_sentences}")
    
    return output_path