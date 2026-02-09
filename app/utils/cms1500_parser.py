import os
from contextlib import contextmanager
import tempfile
from pypdf import PdfReader
from typing import List, Dict, Generator


@contextmanager
def safe_pdf_file_handler(pdf_path: str) -> Generator[PdfReader, None, None]:
    """Context manager for safe PDF file handling with proper cleanup"""
    temp_file = None
    try:
        # Create a temporary file with proper permissions
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        # Copy original PDF content to temp file
        with open(pdf_path, 'rb') as src:
            temp_file.write(src.read())
        temp_file.close()
        
        # Open PDF with proper permissions
        reader = PdfReader(temp_file.name)
        yield reader
        
    except PermissionError as e:
        raise RuntimeError(f"Permission error accessing PDF: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Error processing PDF: {str(e)}")
    finally:
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.chmod(temp_file.name, 0o666)  # Ensure write permissions
                os.unlink(temp_file.name)
            except OSError:
                pass  # Best effort cleanup


def extract_cpt_modifiers_and_icd_from_pdf(pdf_path: str) -> Dict[str, List[Dict[str, List[str]]]]:
    with safe_pdf_file_handler(pdf_path) as reader:
        fields = reader.get_fields()

        # --- CPT + Modifiers ---
        cpt_data = []
        for i in range(1, 7):  # 6 CPT lines
            cpt_key = f"CPT/HCPCS {i}"
            mod_keys = [f"Mod {i}{letter}" for letter in ['a', 'b', 'c', 'd']]

            cpt_code = fields.get(cpt_key, {}).get("/V")
            if cpt_code:
                modifiers = [
                    fields.get(mod_key, {}).get("/V")
                    for mod_key in mod_keys
                    if fields.get(mod_key, {}).get("/V") is not None
                ]
                cpt_data.append({
                    "cpt": cpt_code,
                    "modifiers": modifiers
                })

        # --- ICD Codes ---
        icd_codes = []
        for letter in "abcdefghijkl":
            field = f"21{letter}"
            val = fields.get(field, {}).get("/V")
            if val:
                icd_codes.append(val.upper())  # Normalize to uppercase

        return {
            "cpt_data": cpt_data,
            "icd_codes": icd_codes
        }


def extract_cpt_and_modifiers_from_pdf(pdf_path: str) -> List[Dict[str, List[str]]]:
    with safe_pdf_file_handler(pdf_path) as reader:
        fields = reader.get_fields()

        cpt_mod_data = []
        for i in range(1, 7):  # CMS-1500 has 6 CPT lines
            cpt_key = f"CPT/HCPCS {i}"
            mod_keys = [f"Mod {i}{letter}" for letter in ['a', 'b', 'c', 'd']]

            cpt_code = fields.get(cpt_key, {}).get("/V")
            if cpt_code:
                modifiers = [
                    fields.get(mod_key, {}).get("/V")
                    for mod_key in mod_keys
                    if fields.get(mod_key, {}).get("/V") is not None
                ]
                cpt_mod_data.append({
                    "cpt": cpt_code,
                    "modifiers": modifiers  # list of strings
                })

        return cpt_mod_data