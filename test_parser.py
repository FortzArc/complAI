import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageOps
import pytesseract
import pandas as pd
import re

def pdf_to_image(pdf_path):
    """Convert first page of a PDF to a PIL Image."""
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=300)  # 300 DPI preserves CPT layout
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img

def preprocess(img):
    """Enhance contrast and convert to grayscale for better OCR."""
    gray = ImageOps.grayscale(img)
    enhanced = ImageEnhance.Contrast(gray).enhance(2.5)
    return enhanced

def extract_icd_from_box21(image):
    """AI-style ICD extractor using grid layout with smart padding and leading-letter fixing."""
    # Final corrected Box 21 grid area: wider on both sides
    box21_crop = image.crop((80, 1920, 1340, 2130))  # 👈 Wider right to catch D, H, L
    box21_crop.save("debug_icd_box21_full.png")
    enhanced = preprocess(box21_crop)

    labels = ['A', 'B', 'C', 'D',
              'E', 'F', 'G', 'H',
              'I', 'J', 'K', 'L']

    full_width = 1340 - 80
    full_height = 2130 - 1920
    grid_width = full_width // 4
    grid_height = full_height // 3

    extracted = []

    for row in range(3):
        for col in range(4):
            idx = row * 4 + col
            label = labels[idx]

            left = 80 + col * grid_width - 15   # Add horizontal padding
            top = 1920 + row * grid_height - 5  # Vertical padding
            right = left + grid_width + 30
            bottom = top + grid_height + 10

            cell = image.crop((left, top, right, bottom))
            cell_img = preprocess(cell)

            text = pytesseract.image_to_string(cell_img, config="--psm 6").strip()

            # Try to extract a code-like pattern
            match = re.search(r"([A-Z]?[0-9]{2,3}\.[0-9A-Z]{1,4})", text)
            code = match.group(1) if match else None

            # Fix missing leading letters
            if code and re.match(r"^[0-9]{2,3}\.", code):
                code = label + code  # e.g., B525.10 from 525.10 in box B

            if code:
                extracted.append((label, code))
            else:
                print(f"❌ {label}: No code found (OCR saw: '{text}')")

    codes_only = [code for _, code in extracted]

    print("\n📦 AI-Mapped ICD Codes (A–L):")
    for label, code in extracted:
        print(f"{label}: {code}")

    return {
        "icd_codes": sorted(set(codes_only)),
        "raw_text": ""  # Not used anymore
    }



def extract_precise_cpt(image):
    """Use structured OCR to extract CPT codes from CMS-1500 Box 24D."""
    df = pytesseract.image_to_data(image, output_type=pytesseract.Output.DATAFRAME)
    df = df.dropna(subset=["text"])
    df["text"] = df["text"].str.strip()
    df = df[df.conf > 40]

    code_pattern = re.compile(r"^\d{3,5}$")
    df_codes = df[df["text"].apply(lambda x: bool(code_pattern.match(x)))]

    # Coordinates for Box 24D
    box24_top = 2200
    box24_bottom = 2800
    box24D_left = 750
    box24D_right = 900

    df_codes = df_codes[
        (df_codes.top >= box24_top) & (df_codes.top <= box24_bottom) &
        (df_codes.left >= box24D_left) & (df_codes.left <= box24D_right)
    ]

    df_codes["line"] = df_codes.top // 30
    cpt_codes = df_codes.groupby("line")["text"].first().tolist()

    return {
        "cpt_codes": sorted(set(cpt_codes)),
        "raw_boxes": df_codes[["text", "left", "top"]].to_dict(orient="records")
    }

if __name__ == "__main__":
    image = pdf_to_image("cms1500_final.pdf")

    print("🚀 Extracting CPT codes...")
    cpt_result = extract_precise_cpt(image)

    print("\n🚀 Extracting ICD codes from Box 21...")
    icd_result = extract_icd_from_box21(image)

    print("\n✅ CPT Codes Extracted:")
    for code in cpt_result["cpt_codes"]:
        print("-", code)

    print("\n✅ ICD Codes Extracted:")
    for code in icd_result["icd_codes"]:
        print("-", code)

    print("\n📄 Raw OCR Text from Box 21:")
    print(icd_result["raw_text"])
