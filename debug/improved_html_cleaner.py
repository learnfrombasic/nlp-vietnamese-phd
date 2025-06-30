import re
import html
import unicodedata


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


def clean_text_improved(text, clean_pattern: list[str] = ["&quot;", "***"]):
    """
    Improved clean text function with comprehensive HTML entity removal
    """
    # Use the comprehensive HTML entity removal
    text = remove_html_entities(text)

    # Handle any remaining custom patterns
    for pattern in clean_pattern:
        text = text.replace(pattern, "")

    # Remove text within double quotes (more comprehensive)
    cleaned = re.sub(r'"[^"]*"', "", text)

    # Also remove text within single quotes
    cleaned = re.sub(r"'[^']*'", "", cleaned)

    # Remove URLs (http, https, or www)
    cleaned = re.sub(r"https?://\S+|www\.\S+", "", cleaned)

    # Clean up multiple spaces and trim
    cleaned = " ".join(cleaned.split())

    return cleaned.strip()


def normalize(s):
    return unicodedata.normalize("NFC", s)


def clean_page_improved(text):
    """
    Improved page cleaning with HTML entity removal
    """
    text = normalize(text)
    text = remove_html_entities(text)  # Add HTML entity removal here
    text = re.sub(r"TRANG TỬ.*NAM HOA KINH.*", "", text, flags=re.I)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)  # nối dòng giữa câu
    return text.strip()


def split_sentences_improved(
    text, delimiters=[".", "!", "?", "... "], is_clean_text: bool = True
):
    """
    Improved sentence splitting with better HTML entity handling
    """
    sentences = []
    current_sentence = ""

    if is_clean_text:
        text = clean_text_improved(text)  # Use improved cleaning

    for char in text:
        current_sentence += char
        if char in delimiters:
            if current_sentence.strip():
                normalized_sentence = current_sentence.strip()
                # Apply HTML entity removal again just in case
                normalized_sentence = remove_html_entities(normalized_sentence)
                sentences.append(normalize(normalized_sentence))
            current_sentence = ""

    if current_sentence.strip():  # Add any remaining text
        normalized_sentence = current_sentence.strip()
        # Apply HTML entity removal again just in case
        normalized_sentence = remove_html_entities(normalized_sentence)
        sentences.append(normalize(normalized_sentence))

    return sentences


# Test function
def test_html_cleaning():
    """
    Test the HTML entity removal with various examples
    """
    test_cases = [
        "This has &quot;quoted text&quot;",
        "This has &quot quoted text&quot;",
        "This has quot;quoted text&quot;",
        "This has &QUOT;quoted text&quot;",
        "This has &Quot;quoted text&quot;",
        "This has &amp; and &lt; and &gt;",
        "Mixed &quot;quotes&quot; and &amp; symbols",
    ]

    print("Testing HTML entity removal:")
    print("=" * 50)

    for i, test_text in enumerate(test_cases, 1):
        cleaned = clean_text_improved(test_text)
        print(f"Test {i}:")
        print(f"  Original: {test_text}")
        print(f"  Cleaned:  {cleaned}")
        print(f"  Contains &quot;: {'&quot;' in cleaned}")
        print()


if __name__ == "__main__":
    test_html_cleaning()
