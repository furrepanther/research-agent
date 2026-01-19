from pypdf import PdfReader
import re

path = r'R:/My Drive/03 Research Papers\Consciousness\Cameron Berg Why Do LLMs Report Subjective Experience.pdf'
try:
    reader = PdfReader(path)
    text = reader.pages[0].extract_text()
    
    # De-hyphenate logic
    text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)
    
    print("--- RAW TEXT START ---")
    print(text[:2000])
    print("--- RAW TEXT END ---")
except Exception as e:
    print(f"Error: {e}")
