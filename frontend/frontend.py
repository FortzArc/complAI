import requests
import streamlit as st

# App Config
st.set_page_config(page_title="Compliance AI Assistant", layout="wide")
API_BASE = "http://127.0.0.1:8000"  # Backend base URL

# Sidebar Navigation
st.sidebar.title("📂 Business Cases")
selected_case = st.sidebar.radio(
    "Choose a Compliance Scenario",
    [
        "🏠 Home - Ask Anything",
        "🧾 Modifier Misuse",
        "📋 Medical Necessity Check",
        "🔗 Code-Modifier Pairing Errors",
        "🔁 Duplicate Billing Detection",
        "🚫 Coverage Limit Breach",
        "🚨 Audit Trigger Flagging",
    ]
)

st.title("🩺 Healthcare Compliance AI Assistant")

# ================================
# Shared: Reference Upload Section
# ================================
def upload_reference(label, key_suffix):
    st.subheader("Step 1: Upload Reference Guidelines")
    ref_pdf = st.file_uploader(label, type=["pdf"], key=f"ref_upload_{key_suffix}")
    if ref_pdf and st.button("Embed Reference File", key=f"embed_btn_{key_suffix}"):
        with st.spinner("Embedding..."):
            files = {"file": (ref_pdf.name, ref_pdf, "application/pdf")}
            res = requests.post(f"{API_BASE}/embed", files=files)
            if res.status_code == 200:
                st.success("✅ Reference embedded successfully!")
            else:
                st.error("❌ Failed to embed reference.")
                st.text(res.text)
    return

def upload_claim_and_check(api_path, key_suffix):
    st.subheader("Step 2: Upload CMS-1500 Claim Form")
    cms_pdf = st.file_uploader("Upload CMS-1500 PDF", type=["pdf"], key=f"cms_upload_{key_suffix}")
    
    if cms_pdf and st.button("Run Compliance Check", key=f"check_btn_{key_suffix}"):
        with st.spinner("Running compliance check..."):
            files = {"file": (cms_pdf.name, cms_pdf, "application/pdf")}
            res = requests.post(f"{API_BASE}/{api_path}", files=files)

            if res.status_code == 200:
                result = res.json()
                results = result.get("results", [])

                if results:
                    st.success(f"✅ Found {len(results)} item(s) to evaluate.")
                    for i, item in enumerate(results, 1):
                        st.markdown("----")
                        st.markdown(f"### 🧾 Finding #{i}")

                        if "cpt" in item:
                            st.markdown(f"**CPT Code:** `{item['cpt']}`")
                        
                        if "modifiers" in item and isinstance(item["modifiers"], list):
                            mods = ", ".join(item["modifiers"])
                            st.markdown(f"**Modifiers:** `{mods}`")

                        if "icd" in item:
                            st.markdown(f"**ICD Code:** `{item['icd']}`")
                        
                        if "query" in item:
                            st.markdown("**Query:**")
                            st.code(item["query"])

                        if "question" in item:
                            st.markdown("**Question Asked:**")
                            st.code(item["question"])
                        
                        if "match_found" in item:
                            if item["match_found"]:
                                st.success("✅ Match found in policy reference.")
                            else:
                                st.warning("⚠️ No clear match found for this CPT–ICD pair.")
                        
                        if "answer" in item:
                            st.markdown("**AI Compliance Evaluation:**")
                            st.write(item["answer"])
                        
                        if "supporting_docs" in item:
                            st.markdown("**Supporting Docs:**")
                            for doc in item["supporting_docs"]:
                                st.markdown(f"- {doc[:300]}...")  # Show preview
                else:
                    st.warning("⚠️ No results returned from compliance check.")
            else:
                st.error("❌ Compliance check failed.")
                st.text(res.text)



# ================================
# CASE: General Q&A
# ================================
if selected_case == "🏠 Home - Ask Anything":
    st.subheader("Ask general healthcare billing compliance questions using embedded guidelines.")

    # Step 1
    upload_reference("Upload Reference Guidelines (e.g. CMS Rules, Modifiers)", "home")

    # Step 2
    st.subheader("Step 2: Ask a General Compliance Question")
    question = st.text_input("Enter your question", key="compliance_q")
    if st.button("Get Answer"):
        if not question.strip():
            st.warning("⚠️ Please enter a question.")
        else:
            with st.spinner("Querying model..."):
                res = requests.post(f"{API_BASE}/query", data={"question": question})
                if res.status_code == 200:
                    st.success("🤖 Answer:")
                    st.write(res.json().get("answer"))
                else:
                    st.error("❌ Failed to get answer.")
                    st.text(res.text)

# ================================
# CASE: Modifier Misuse
# ================================
elif selected_case == "🧾 Modifier Misuse":
    st.markdown("Analyze CPT/modifier misuse using guideline-based risk detection.")
    upload_reference("Upload Modifier Guidelines PDF", "modifier")
    upload_claim_and_check("modifier-check", "modifier")

# ================================
# CASE: Medical Necessity
# ================================
elif selected_case == "📋 Medical Necessity Check":
    st.markdown("Evaluate if procedures on a claim meet medical necessity criteria.")
    upload_reference("Upload Medical Necessity Guidelines", "necessity")
    
    # Use the tailored upload+check function for necessity
    upload_claim_and_check("necessity-check", "necessity")


# ================================
# CASE: Code-Modifier Pairing Errors
# ================================
elif selected_case == "🔗 Code-Modifier Pairing Errors":
    st.markdown("Check for invalid or unsupported code-modifier combinations.")
    upload_reference("Upload CPT + Modifier Pairing Rules", "pairing")
    upload_claim_and_check("pairing-check", "pairing")

# ================================
# CASE: Duplicate Billing
# ================================
elif selected_case == "🔁 Duplicate Billing Detection":
    st.markdown("Detect repeated codes, duplicate procedures, or overbilling.")
    upload_reference("Upload Billing Policy or EOB Sample", "duplicate")
    upload_claim_and_check("duplicate-check", "duplicate")

# ================================
# CASE: Coverage Limit Breach
# ================================
elif selected_case == "🚫 Coverage Limit Breach":
    st.markdown("Check if the claim exceeds coverage limits (e.g. visits/year).")
    upload_reference("Upload Coverage Guidelines", "coverage")
    upload_claim_and_check("coverage-check", "coverage")

# ================================
# CASE: Audit Trigger Flagging
# ================================
elif selected_case == "🚨 Audit Trigger Flagging":
    st.markdown("Scan for audit flags based on CMS or internal audit patterns.")
    upload_reference("Upload Audit Risk Criteria", "audit")
    upload_claim_and_check("audit-check", "audit")
