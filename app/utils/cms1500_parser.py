from pypdf import PdfReader
from typing import List, Dict


def extract_cpt_modifiers_and_icd_from_pdf(pdf_path: str) -> Dict[str, List[Dict[str, List[str]]]]:

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
