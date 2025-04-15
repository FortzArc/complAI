from pypdf import PdfReader
from typing import List, Dict


def extract_cpt_modifiers_from_pdf(pdf_path: str) -> List[Dict[str, List[str]]]:
    """
    Extracts CPT codes and their corresponding modifiers from a CMS-1500 fillable PDF.

    Args:
        pdf_path (str): Path to the fillable PDF.

    Returns:
        List[Dict]: A list of dictionaries, each with 'cpt' and 'modifiers' keys.
    """
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()

    cpt_data = []

    for i in range(1, 7):  # 6 lines on CMS-1500 for CPT/modifier
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

    return cpt_data

if __name__ == "__main__":
    file_path = "BSS-CMS-1500-Fillable-2022.pdf" 
    results = extract_cpt_modifiers_from_pdf(file_path)

    for entry in results:
        print(f"CPT Code: {entry['cpt']} | Modifiers: {entry['modifiers']}")
