from pypdf import PdfReader
from typing import List, Dict
import tempfile
import os
import contextlib


# Context manager to handle temporary PDF files with proper cleanup
@contextlib.contextmanager
def temp_pdf_file():
    temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    try:
        yield temp_file.name
    finally:
        # Ensure file is closed before deletion attempt
        if hasattr(temp_file, 'close'):
            temp_file.close()
        # Handle permission issues during cleanup
        try:
            if os.path.exists(temp_file.name):
                os.chmod(temp_file.name, 0o666)  # Ensure write permissions
                os.unlink(temp_file.name)
        except (PermissionError, OSError) as e:
            # Log error but don't raise - we want to continue execution
            print(f"Warning: Failed to delete temporary file {temp_file.name}: {e}")


def extract_cpt_modifiers_and_icd_from_pdf(pdf_path: str) -> Dict[str, List[Dict[str, List[str]]]]:
    try:
        reader = PdfReader(pdf_path)
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
    except Exception as e:
        # Ensure any errors during processing are caught
        raise RuntimeError(f"Error processing PDF file: {e}")


def extract_cpt_and_modifiers_from_pdf(pdf_path: str) -> List[Dict[str, List[str]]]:
    try:
        reader = PdfReader(pdf_path)
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
    except Exception as e:
        # Ensure any errors during processing are caught
        raise RuntimeError(f"Error processing PDF file: {e}")