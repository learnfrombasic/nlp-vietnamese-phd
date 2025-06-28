import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import unicodedata


def normalize(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def clean_page(text: str) -> str:
    text = normalize(text)
    text = re.sub(r"TRANG TỬ.*NAM HOA KINH.*", "", text, flags=re.I)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)  # nối dòng giữa câu
    return text.strip()


def split_paragraphs(text: str) -> list[str]:
    return [normalize(p.strip()) for p in re.split(r"\n\s*\n", text) if p.strip()]


def split_sentences(text: str) -> list[str]:
    # Split by Vietnamese sentence delimiters
    # Vietnamese sentences typically end with ., !, or ?
    delimiters = [".", "!", "?"]
    sentences = []
    current_sentence = ""

    for char in text:
        current_sentence += char
        if char in delimiters:
            if current_sentence.strip():
                sentences.append(normalize(current_sentence.strip()))
            current_sentence = ""

    if current_sentence.strip():  # Add any remaining text
        sentences.append(normalize(current_sentence.strip()))

    return sentences


def detect_sections(
    pages: list[str],
    current_section: str = "Giới thiệu",
    pattern: str = r"^(PHẦN|CHƯƠNG)\s+[IVXLCDM\d]+\.*\s+.+$",
    flags=re.MULTILINE,
) -> list[dict[str, list[tuple[int, str]]]]:
    section_pattern = re.compile(pattern, flags)
    sections = []
    current = {"name": current_section, "pages": []}

    for i, txt in enumerate(pages, 1):
        matches = section_pattern.findall(txt)
        if matches:
            if current["pages"]:
                sections.append(current)
            title = re.findall(section_pattern, txt)[0]
            current = {"name": normalize(title), "pages": [(i, txt)]}
        else:
            current["pages"].append((i, txt))
    sections.append(current)
    return sections


def write_pretty_xml(tree: ET.ElementTree, out_path: str):
    pretty = minidom.parseString(ET.tostring(tree.getroot(), encoding="utf-8"))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(pretty.toprettyxml(indent="  "))
