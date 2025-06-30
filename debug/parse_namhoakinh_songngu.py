import pymupdf
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import unicodedata
import html

import pymupdf
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import unicodedata

from underthesea import ner, text_normalize, sent_tokenize

# ──────────────── CẤU HÌNH ────────────────
BOOK_METADATA = {
    "NAM_HOA_KINH": {
        "TITLE": "Nam Hoa Kinh",
        "VOLUME": "",
        "AUTHOR": "Trang Tử",
        "PERIOD": "Chiến Quốc",
        "LANGUAGE": "vi",
        "SOURCE": "thuviensach.vn",
    },
    "TRANG_TU_NAM_HOA_KINH": {
        "TITLE": "Trang Tử Nam Hoa Kinh",
        "VOLUME": "",
        "AUTHOR": "Nguyễn Kim Vỹ",
        "PERIOD": "Chiến Quốc",
        "LANGUAGE": "vi",
        "SOURCE": "Nhà xuất bản văn hóa",
    },
    "TRANG_TU_NAM_HOA_KINH_2": {
        "TITLE": "Trang Tử Nam Hoa Kinh",
        "VOLUME": "",
        "AUTHOR": "Thu Giang, Ngyễn Duy Cần",
        "PERIOD": "Chiến Quốc",
        "LANGUAGE": "vi",
        "SOURCE": "Nhà xuất bản trẻ",
    },
}

BASED_ENTITY_GROUPS = [
    "PER",
    "ORG",
    "LOC",
    "ORG",
    "TME",
    "TITLE",
    "NUM",
]

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


# KNOWN_SECTIONS = [
#     "LỜI NÓI ĐẦU", "TIỂU DẪN", "NỘI THIÊN", "NGOẠI THIÊN", "TẠP THIÊN",
#     "TIÊU DIÊU DU", "TỀ VẬT LUẬN", "DƯỠNG SINH CHỦ", "NHÂN GIAN THẾ",
#     "ĐỨC SUNG PHÙ", "ĐẠI TÔNG SƯ", "ỨNG ĐẾ VƯƠNG"
# ]

KNOWN_SECTIONS = [
    "LỜI NÓI ĐẦU", "TIỂU DẪN", "NỘI THIÊN", "NGOẠI THIÊN", "TẠP THIÊN",
    "TIÊU DIÊU DU", "TỀ VẬT LUẬN", "DƯỠNG SINH CHỦ", "NHÂN GIAN THẾ",
    "ĐỨC SUNG PHÙ", "ĐẠI TÔNG SƯ", "ỨNG ĐẾ VƯƠNG", "DỊCH NGHĨA", "LƯỢC SỬ", "CHÚ"
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
    clean_patterns = ["999", "F.F.F", "***", "---", "___"]
    for pattern in clean_patterns:
        text = text.replace(pattern, "")
    
    # Remove invisible characters
    text = re.sub(r"[\u200b\u200e\u202a\u202c\ufeff]+", "", text)
    
    # Clean up multiple spaces
    text = re.sub(r"\s+", " ", text)
    
    # Remove the specific characters requested by the user
    text = text.replace('⸈', '')
    
    return text.strip()

def clean_page(text: str, known_sections: list[str]=KNOWN_SECTIONS) -> str:
    """Clean page OCR text."""
    text = normalize(text)
    text = remove_html_entities(text)
    
    for section_name in known_sections:  # Detect and preserve titles
        if section_name in text:
            preserved_title = section_name
            text = re.sub(rf'(?i)^{re.escape(section_name)}', preserved_title, text)  # Keep title
            break  # Only handle the first match
    
    # Remove unwanted sections and headers
    text = re.sub(r"TRANG TỬ.*NAM HOA KINH.*", "", text, flags=re.I)  # Existing removal
    text = re.sub(r"Dịch kinh.*", "", text, flags=re.I)  # Remove "Dịch kinh" sections
    text = re.sub(r"DỊCH KINH.*", "", text, flags=re.I)  # Remove uppercase variant
    text = re.sub(r"Trang \d+", "", text, flags=re.I)
    text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    
    return text.strip()

def ner_underthesea(text: str) -> list[dict]:
    """Extract named entities from Vietnamese text."""
    result = ner(text, deep=True)
    return result

def merge_adjacent_entities(entities: list[dict], text: str) -> list[dict]:
    """
    Merge adjacent entities that are consecutive in the text.
    
    Args:
        entities: List of entity dictionaries with 'start', 'end', 'word', 'entity' keys
        text: Original text to verify merging
    
    Returns:
        List of merged entities
    """
    if not entities or len(entities) < 2:
        return entities
    
    # Sort entities by start position
    sorted_entities = sorted(entities, key=lambda x: x.get('start', 0))
    merged_entities = []
    current_entity = sorted_entities[0].copy()
    
    for i in range(1, len(sorted_entities)):
        next_entity = sorted_entities[i]
        
        # Check if entities are adjacent: end_current + 1 = start_next
        current_end = current_entity.get('end', 0)
        next_start = next_entity.get('start', 0)
        
        # Also check if they have the same entity type (optional - you can remove this condition)
        current_type = current_entity.get('entity', '').split('-')[-1]
        next_type = next_entity.get('entity', '').split('-')[-1]
        
        if current_end + 1 == next_start and current_type == next_type:
            # Merge entities
            print(f"   🔗 Merging adjacent entities: '{current_entity.get('word', '')}' + '{next_entity.get('word', '')}'")
            
            # Update current entity with merged information
            current_entity['end'] = next_entity.get('end', current_end)
            
            # Reconstruct the word from the original text
            merged_start = current_entity.get('start', 0)
            merged_end = current_entity.get('end', 0)
            current_entity['word'] = text[merged_start:merged_end]
            
            # Keep the entity type of the first entity
            print(f"   ✅ Merged result: '{current_entity.get('word', '')}' ({current_type})")
            
        else:
            # No merge possible, add current entity to results and move to next
            merged_entities.append(current_entity)
            current_entity = next_entity.copy()
    
    # Add the last entity
    merged_entities.append(current_entity)
    
    if len(merged_entities) < len(sorted_entities):
        print(f"   📊 Entity merging: {len(sorted_entities)} -> {len(merged_entities)} entities")
    
    return merged_entities

def process_ner_with_merging(text: str) -> list[dict]:
    """
    Extract NER entities and merge adjacent ones.
    
    Args:
        text: Input text for NER processing
        
    Returns:
        List of processed and merged entities
    """
    # Get raw NER results
    raw_entities = ner_underthesea(text)
    
    if not raw_entities:
        return []
    
    # Filter for valid entity types first
    valid_entities = [
        ent for ent in raw_entities
        if ent.get("entity", "").split("-")[-1] in BASED_ENTITY_GROUPS
    ]
    
    if not valid_entities:
        return []
    
    # Merge adjacent entities
    merged_entities = merge_adjacent_entities(valid_entities, text)
    
    return merged_entities

def split_into_paragraphs(text: str, min_length: int = 20, max_length: int = 1000) -> list[str]:
    """
    Split text into paragraphs using improved heuristics for Vietnamese text.
    
    Args:
        text: Input text to split
        min_length: Minimum length for a valid paragraph
        max_length: Maximum length for a paragraph before considering splitting
        
    Returns:
        List of paragraphs
    """
    # First normalize the text
    text = text_normalize(text)
    
    # Remove excessive whitespace while preserving paragraph breaks
    text = re.sub(r'\s*\n\s*\n\s*', '\n\n', text)
    text = re.sub(r'\s+', ' ', text)
    
    # Split on double newlines first
    paragraphs = [p.strip() for p in text.split('\n\n')]
    
    # Process each potential paragraph
    valid_paragraphs = []
    current_paragraph = []
    
    for p in paragraphs:
        if not p:  # Skip empty paragraphs
            continue
            
        # Clean the paragraph
        p = clean_text(p)
        
        if len(p) < min_length:
            # If too short, try to combine with the previous paragraph
            if current_paragraph:
                current_paragraph.append(p)
            else:
                current_paragraph = [p]
        elif len(p) > max_length:
            # If too long, try to split on sentence boundaries
            if current_paragraph:
                valid_paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
            
            sentences = split_into_sentences(p)
            temp_paragraph = []
            current_length = 0
            
            for sent in sentences:
                if current_length + len(sent) > max_length and temp_paragraph:
                    valid_paragraphs.append(' '.join(temp_paragraph))
                    temp_paragraph = [sent]
                    current_length = len(sent)
                else:
                    temp_paragraph.append(sent)
                    current_length += len(sent)
            
            if temp_paragraph:
                valid_paragraphs.append(' '.join(temp_paragraph))
        else:
            # If it's a valid length paragraph
            if current_paragraph:
                valid_paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
            valid_paragraphs.append(p)
    
    # Add any remaining paragraph
    if current_paragraph:
        valid_paragraphs.append(' '.join(current_paragraph))
    
    return valid_paragraphs

def split_into_sentences(text: str) -> list[str]:
    """
    Split text into sentences using underthesea's Vietnamese-specific tokenizer.
    
    Args:
        text: Input text to split into sentences
        
    Returns:
        List of sentences
    """
    # First normalize and clean the text
    text = text_normalize(text)
    text = clean_text(text)
    
    # Use underthesea's sentence tokenizer
    sentences = sent_tokenize(text)
    
    # Post-process sentences
    processed_sentences = []
    for sent in sentences:
        sent = sent.strip()
        
        # Skip empty or invalid sentences
        if not sent or len(sent) < 3:
            continue
            
        # Clean up common issues
        sent = re.sub(r'^\s*[""]\s*', '', sent)  # Remove leading quotes
        sent = re.sub(r'\s*[""]\s*$', '', sent)  # Remove trailing quotes
        sent = re.sub(r'([.!?])\s*([.!?])+', r'\1', sent)  # Remove multiple punctuation
        
        # Validate sentence
        if sent[-1] not in '.!?':  # If sentence doesn't end with punctuation
            if len(sent) > 3:  # Only add period if it's a substantial sentence
                sent += '.'
        
        processed_sentences.append(sent)
    
    return processed_sentences

def process_text_with_structure(text: str) -> dict:
    """
    Process text by splitting it into paragraphs and sentences with proper structure.
    
    Args:
        text: Input text to process
        
    Returns:
        Dictionary containing structured text with paragraphs and sentences
    """
    # First clean the text
    text = clean_text(text)
    
    # Split into paragraphs
    paragraphs = split_into_paragraphs(text)
    
    # Process each paragraph
    structured_text = {
        'paragraphs': []
    }
    
    for para in paragraphs:
        # Split paragraph into sentences
        sentences = split_into_sentences(para)
        
        # Add to structure
        structured_text['paragraphs'].append({
            'text': para,
            'sentences': sentences,
            'language': classify_text(para)
        })
    
    return structured_text

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


def split_mixed_text_pairs(text: str) -> list[dict]:
    """
    Split mixed Chinese-Vietnamese text into pairs.
    
    Args:
        text: Input text containing mixed Chinese and Vietnamese
        
    Returns:
        List of dictionaries containing paired Chinese-Vietnamese text
    """
    # Split text into chunks by spaces
    chunks = text.split()
    pairs = []
    current_chinese = []
    current_vietnamese = []
    
    i = 0
    while i < len(chunks):
        chunk = chunks[i]
        
        # Skip dots and spaces
        if chunk in ['.', ' ']:
            i += 1
            continue
            
        # Check if chunk is Chinese
        if is_chinese(chunk):
            current_chinese.append(chunk)
            # Look ahead for more Chinese characters
            while i + 1 < len(chunks) and is_chinese(chunks[i + 1]):
                current_chinese.append(chunks[i + 1])
                i += 1
        # Check if chunk is Vietnamese
        elif is_vietnamese(chunk) or chunk.isupper():
            current_vietnamese.append(chunk)
            # Look ahead for more Vietnamese words in the same phrase
            while i + 1 < len(chunks) and (is_vietnamese(chunks[i + 1]) or chunks[i + 1].isupper()):
                if chunks[i + 1] in ['Kính', 'dâng', 'hương', 'hồn', 'thân', 'phụ']:
                    break
                current_vietnamese.append(chunks[i + 1])
                i += 1
            
            # If we have both Chinese and Vietnamese, create a pair
            if current_chinese:
                pairs.append({
                    'chinese': ' '.join(current_chinese),
                    'vietnamese': ' '.join(current_vietnamese)
                })
                current_chinese = []
                current_vietnamese = []
            else:
                # Standalone Vietnamese phrase
                pairs.append({
                    'chinese': '',
                    'vietnamese': ' '.join(current_vietnamese)
                })
                current_vietnamese = []
        
        i += 1
    
    # Handle any remaining text
    if current_chinese or current_vietnamese:
        pairs.append({
            'chinese': ' '.join(current_chinese),
            'vietnamese': ' '.join(current_vietnamese)
        })
    
    return pairs

def merge_text_pairs(pairs: list[dict], format_type: str = 'aligned') -> str:
    """
    Merge Chinese-Vietnamese pairs into different formats.
    
    Args:
        pairs: List of dictionaries containing Chinese-Vietnamese pairs
        format_type: Type of formatting ('aligned', 'inline', or 'table')
        
    Returns:
        Formatted string with merged pairs
    """
    if format_type == 'aligned':
        # Create two columns with aligned text
        chinese_lines = []
        vietnamese_lines = []
        max_length = 0
        
        for pair in pairs:
            chinese = pair['chinese']
            vietnamese = pair['vietnamese']
            max_length = max(max_length, len(vietnamese), len(chinese))
            
            chinese_lines.append(chinese)
            vietnamese_lines.append(vietnamese)
        
        # Format in columns
        result = []
        for ch, vn in zip(chinese_lines, vietnamese_lines):
            if ch and vn:
                result.append(f"{vn:<{max_length}} | {ch}")
            elif vn:
                result.append(f"{vn:<{max_length}} |")
            elif ch:
                result.append(f"{'':>{max_length}} | {ch}")
        
        return '\n'.join(result)
        
    elif format_type == 'inline':
        # Format inline with Chinese in parentheses
        result = []
        for pair in pairs:
            chinese = pair['chinese']
            vietnamese = pair['vietnamese']
            
            if chinese and vietnamese:
                result.append(f"{vietnamese} ({chinese})")
            elif vietnamese:
                result.append(vietnamese)
            elif chinese:
                result.append(f"({chinese})")
        
        return ' '.join(result)
        
    elif format_type == 'table':
        # Format as a markdown table
        result = ["| Vietnamese | Chinese |", "|------------|----------|"]
        
        for pair in pairs:
            chinese = pair['chinese']
            vietnamese = pair['vietnamese']
            result.append(f"| {vietnamese or '-'} | {chinese or '-'} |")
        
        return '\n'.join(result)
    
    else:
        raise ValueError(f"Unknown format type: {format_type}")

def build_xml_for_book(pdf_path, metadata: dict, output_path="nam_hoa_kinh_parsed.xml", code="PKS_001"):
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
    ET.SubElement(meta, "TITLE").text = metadata.get("TITLE", "")
    ET.SubElement(meta, "VOLUME").text = metadata.get("VOLUME", "")
    ET.SubElement(meta, "AUTHOR").text = metadata.get("AUTHOR", "")
    ET.SubElement(meta, "PERIOD").text = metadata.get("PERIOD", "")
    ET.SubElement(meta, "LANGUAGE").text = metadata.get("LANGUAGE", "")
    ET.SubElement(meta, "TRANSLATOR").text = metadata.get("TRANSLATOR", "")
    ET.SubElement(meta, "SOURCE").text = metadata.get("SOURCE", "")
    
    # Step 4: Process sections
    total_pairs = 0
    
    for sect_id, section in enumerate(sections, 1):
        sect_el = ET.SubElement(
            file_el, "SECT", ID=f"{code}.{sect_id:03}", NAME=section["name"]
        )
        
        for page_num, page_text in section["pages"]:
            if not page_text:
                continue
            
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
                    
                    # Process NER with merging for Vietnamese sentences
                    merged_entities = process_ner_with_merging(pair["vietnamese"])
                    if merged_entities:
                        ner_el = ET.SubElement(stc_el, "NER")
                        for entity in merged_entities:
                            entity_type = entity["entity"].split("-")[-1]
                            ET.SubElement(
                                ner_el, "ENTITY",
                                TYPE=entity_type,
                                START=str(entity.get("start", 0)),
                                END=str(entity.get("end", 0))
                            ).text = entity.get("word", "")

                elif pair["chinese"]:
                    # Only Chinese - use C tag
                    ET.SubElement(stc_el, "C").text = pair["chinese"]
                elif pair["vietnamese"]:
                    ET.SubElement(stc_el, "V").text = pair["vietnamese"]
                    
                    # Process NER with merging for Vietnamese sentences
                    merged_entities = process_ner_with_merging(pair["vietnamese"])
                    if merged_entities:
                        ner_el = ET.SubElement(stc_el, "NER")
                        for entity in merged_entities:
                            entity_type = entity["entity"].split("-")[-1]
                            ET.SubElement(
                                ner_el, "ENTITY",
                                TYPE=entity_type,
                                START=str(entity.get("start", 0)),
                                END=str(entity.get("end", 0))
                            ).text = entity.get("word", "")
                
                total_pairs += 1
    
    # Step 5: Write XML
    tree = ET.ElementTree(root)
    write_pretty_xml(tree, output_path)
    
    print(f"✅ Created XML file: {output_path}")
    print(f"📊 Total sentence pairs: {total_pairs}")
    
    return output_path

if __name__ == "__main__":
    code = "PAS_003"
    version = "015"
    output_path = f"{code}_nam_hoa_kinh_donngu_{version}.xml"
    des = build_xml_for_book(
        pdf_path="/home/octoopt/workspace/projects/learn-from-basics/nlp-vietnamese-phd/temp/Nam-hoa-kinh.pdf",
        metadata=BOOK_METADATA["NAM_HOA_KINH"],
        output_path=output_path,
        code=code
    )
    print("des: ", des)