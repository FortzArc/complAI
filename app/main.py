from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pdfminer.high_level import extract_text
from app.utils.text_chunker import chunk_text
from app.utils.embedding import get_embedding_model, create_vectorstore
from app.utils.rag import build_qa_chain
from app.utils.cms1500_parser import extract_cpt_modifiers_and_icd_from_pdf
from dotenv import load_dotenv
import os

from langchain.vectorstores import FAISS
from PIL import Image


# Load environment variables
load_dotenv()

# In-memory vector store
VECTORSTORE = None

app = FastAPI()


def extract_text_with_ocr_fallback(temp_path):
    text = extract_text(temp_path)
    if not text.strip():
        try:
            parsed = extract_fields_from_image(temp_path)
            text = f"""
            📄 OCR EXTRACTED TEXT (Structured):
            Raw CPT Text:
            {parsed['raw_cpt_text']}

            Raw ICD Text:
            {parsed['raw_icd_text']}

            Detected CPT Codes:
            {', '.join(parsed['cpt_codes'])}

            Detected ICD Codes:
            {', '.join(parsed['icd_codes'])}
            """
            print(text)
        except Exception as e:
            raise RuntimeError(f"OCR fallback failed: {e}")
    else:
        print("📄 Text extracted via pdfminer")
    return text

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    contents = await file.read()
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(contents)

    try:
        text = extract_text_with_ocr_fallback(temp_path)
        os.remove(temp_path)
        return JSONResponse(content={
            "filename": file.filename,
            "text": text[:1000]
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/embed")
async def embed_pdf(file: UploadFile = File(...)):
    global VECTORSTORE

    contents = await file.read()
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(contents)

    try:
        text = extract_text_with_ocr_fallback(temp_path)
        os.remove(temp_path)

        chunks = chunk_text(text)
        embedding_model = get_embedding_model()
        VECTORSTORE = create_vectorstore(chunks, embedding_model)

        return {
            "chunks": len(chunks),
            "status": "Embedded to FAISS!",
            "example_chunk": chunks[0] if chunks else "No chunks created"
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/query")
async def query_doc(question: str = Form(...)):
    global VECTORSTORE
    if VECTORSTORE is None:
        return {"error": "No vectorstore loaded. Please upload and embed a PDF first."}

    try:
        qa_chain = build_qa_chain(VECTORSTORE)
        result = qa_chain.run(question)
        return {
            "question": question,
            "answer": result
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

from app.utils.cms1500_parser import extract_cpt_and_modifiers_from_pdf
@app.post("/modifier-check")
async def modifier_compliance_check(file: UploadFile = File(...)):
    global VECTORSTORE
    if VECTORSTORE is None:
        return {"error": "No vectorstore loaded. Please embed modifier rules first."}

    contents = await file.read()
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(contents)

    try:
        cpt_mod_pairs = extract_cpt_and_modifiers_from_pdf(temp_path)
        os.remove(temp_path)

        qa_chain = build_qa_chain(VECTORSTORE)
        results = []

        for pair in cpt_mod_pairs:
            cpt = pair["cpt"]
            modifiers = pair["modifiers"]

            if modifiers:
                mod_list = ", ".join(modifiers)
                question = (
                    f"You are a healthcare billing compliance auditor. "
                    f"Determine if the use of modifier(s) {mod_list} with CPT code {cpt} is likely compliant or non-compliant. "
                    f"Tell whether it's compliant or non-compliant clearly. "
                    f"Respond with one of the following risk levels: High Risk, Medium Risk, or Low Risk. "
                    f"Justify your assessment based on CMS guidelines in one line."
                )
            else:
                question = (
                    f"You are a healthcare billing compliance auditor. "
                    f"Determine if CPT code {cpt} by itself is associated with any common modifier misuse, billing compliance risks, or audit flags. "
                    f"Respond with one of the following risk levels: High Risk, Medium Risk, or Low Risk. "
                    f"Justify your assessment based on CMS guidelines in one line."
                )

            answer = qa_chain.run(question)
            results.append({
                "cpt": cpt,
                "modifiers": modifiers,
                "question": question,
                "answer": answer
            })

        return {
            "filename": file.filename,
            "extracted_pairs": len(cpt_mod_pairs),
            "results": results
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})



# Shared logic for general business cases
def run_generic_compliance_check(text, vectorstore, prompt_template, extract_info=None):
    qa_chain = build_qa_chain(vectorstore)
    results = []

    items = extract_info(text) if extract_info else [{"text": text}]
    for item in items:
        question = prompt_template.format(**item)
        answer = qa_chain.run(question)
        results.append({
            "question": question,
            "answer": answer,
            **item
        })

    return results


from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
from app.utils.cms1500_parser import extract_cpt_modifiers_and_icd_from_pdf

@app.post("/necessity-check")
async def medical_necessity_check(file: UploadFile = File(...)):
    global VECTORSTORE
    if VECTORSTORE is None:
        return {"error": "No vectorstore loaded. Please embed necessity policy PDF first."}

    # Save uploaded file temporarily
    contents = await file.read()
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(contents)

    try:
        # Extract CPT and ICD codes
        data = extract_cpt_modifiers_and_icd_from_pdf(temp_path)
        cpt_entries = data.get("cpt_data", [])
        icd_codes = data.get("icd_codes", [])

        # ✅ Log what was found
        print(f"[CMS1500 PARSER] CPTs found: {[entry['cpt'] for entry in cpt_entries]}")
        print(f"[CMS1500 PARSER] ICDs found: {icd_codes}")

        if not cpt_entries or not icd_codes:
            return {"error": "No CPT or ICD codes found in the form."}

        results = []

        # Cross-check each CPT–ICD pair using vector search
        for entry in cpt_entries:
            cpt = entry["cpt"]
            for icd in icd_codes:
                query = f"Does CPT code {cpt} require or allow ICD code {icd}?"
                retrieved_docs = VECTORSTORE.similarity_search(query, k=3)

                # Basic match heuristic
                match_found = any(
                    cpt in doc.page_content and icd in doc.page_content
                    for doc in retrieved_docs
                )

                results.append({
                    "cpt": cpt,
                    "icd": icd,
                    "query": query,
                    "match_found": match_found,
                    "supporting_docs": [doc.page_content for doc in retrieved_docs]
                })

        return JSONResponse(content={"results": results})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})



@app.post("/pairing-check")
async def code_modifier_pairing_check(file: UploadFile = File(...)):
    global VECTORSTORE
    if VECTORSTORE is None:
        return {"error": "No vectorstore loaded. Please embed CPT/modifier pairing rules first."}

    contents = await file.read()
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(contents)

    try:
        pairs = extract_cpt_modifiers_and_icd_from_pdf(temp_path)
        os.remove(temp_path)

        qa_chain = build_qa_chain(VECTORSTORE)
        results = []

        for pair in pairs:
            cpt = pair["cpt"]
            for modifier in pair["modifiers"]:
                question = (
                    f"Check if CPT code {cpt} can be legally and compliantly used with modifier {modifier}. "
                    f"Respond with Compliant or Non-Compliant and explain briefly."
                )
                answer = qa_chain.run(question)
                results.append({
                    "cpt": cpt,
                    "modifier": modifier,
                    "question": question,
                    "answer": answer
                })

        return {
            "filename": file.filename,
            "total_checks": len(results),
            "results": results
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/duplicate-check")
async def duplicate_billing_check(file: UploadFile = File(...)):
    global VECTORSTORE
    if VECTORSTORE is None:
        return {"error": "No vectorstore loaded. Please embed billing policy or EOB guide first."}

    contents = await file.read()
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(contents)

    try:
        text = extract_text_with_ocr_fallback(temp_path)
        os.remove(temp_path)

        prompt = (
            "You are reviewing this CMS-1500 claim for signs of duplicate billing. "
            "Identify repeated CPT codes or suspicious charges. Report concerns."
        )

        results = run_generic_compliance_check(text, VECTORSTORE, prompt)
        return {"results": results}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/coverage-check")
async def coverage_limit_check(file: UploadFile = File(...)):
    global VECTORSTORE
    if VECTORSTORE is None:
        return {"error": "No vectorstore loaded. Please embed the coverage policy PDF first."}

    contents = await file.read()
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(contents)

    try:
        text = extract_text_with_ocr_fallback(temp_path)
        os.remove(temp_path)

        prompt = (
            "Determine whether any CPT code in this claim may exceed the coverage limits specified "
            "in the embedded policy document. Mention which codes might violate limits and why."
        )

        results = run_generic_compliance_check(text, VECTORSTORE, prompt)
        return {"results": results}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/audit-check")
async def audit_trigger_check(file: UploadFile = File(...)):
    global VECTORSTORE
    if VECTORSTORE is None:
        return {"error": "No vectorstore loaded. Please embed audit trigger rules first."}

    contents = await file.read()
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(contents)

    try:
        text = extract_text_with_ocr_fallback(temp_path)
        os.remove(temp_path)

        prompt = (
            "Evaluate this CMS-1500 form for any potential audit triggers based on CMS audit criteria. "
            "List any high-risk CPT codes, missing documentation, or suspicious billing patterns."
        )

        results = run_generic_compliance_check(text, VECTORSTORE, prompt)
        return {"results": results}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
