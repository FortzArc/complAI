import re
from typing import List, Dict

def extract_cpt_modifiers(text: str) -> List[Dict[str, str]]:
    # Normalize common OCR dash issues
    text = (
        text.replace("—", "-")  # em dash
            .replace("–", "-")  # en dash
            .replace("−", "-")  # minus sign
            .replace("--", "-")  # double dashes
    )
    pattern = re.compile(r"\b(\d{5})(?:\s*-\s*(\d{2}))?\b")

    results = []
    for match in pattern.finditer(text):
        cpt_code = match.group(1)
        modifier = match.group(2) if match.group(2) else ""
        results.append({"cpt": cpt_code, "modifier": modifier})

    return results
