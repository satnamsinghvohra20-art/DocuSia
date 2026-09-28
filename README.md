# DocuSia — Secure Identity & Agreements

**Tagline:** Smart Legal Drafting, UIDAI Biometrics & Statutory Compliance.

> **DocuSia** is an enterprise legal platform for Maharashtra Leave & License agreements. Powered by Secure Identity & Agreements (SIA), it automates statutory stamp duty calculation, UIDAI biometric verification, and police tenant reporting with tamper-evident cryptographic security and instant PDF issuance.

---

## 🚀 Key Features
- **⚡ 1-Prompt AI Agreement Creation:** Paste raw notes or WhatsApp chats to auto-generate complete 11-month Maharashtra Leave & License contracts with zero manual data entry.
- **🧮 Statutory Stamp Duty & Registration Fee Calculator:** Automated 0.25% consideration computation + ₹1,000/₹500 registration fee under Section 55 of Maharashtra Rent Control Act, 1999.
- **🧬 UIDAI RD-Service Biometric Verification Console:** STQC Level-0 compliant integration for Mantra MFS100 / Morpho MSO 1300 E3 devices with NFIQ 2.0 quality scoring and downloadable Biometric Certificate PDFs.
- **👮 Police Tenant Verification Engine:** Heuristic jurisdiction matcher covering 40+ Maharashtra localities, smart dossier autofill, cryptographic SHA-256 seal, and official Police Acknowledgment Certificate generation.
- **🌐 1-Click MahaPolice Citizen Portal Sync:** JavaScript bookmarklet and JSON payload generator for `citizen.mahapolice.gov.in`.
- **📋 Schedule II Move-In Inventory:** Fixtures and appliance inspection tracker with handover PDF generation.
- **🧾 HRA Rent Receipts:** Section 10(13A) compliant rent payment ledger and PDF receipt generator.
- **💬 Instant WhatsApp Notifications:** 1-click click-to-chat links for draft review, biometric scheduling, and Index-II dispatch.

---

## 🛠️ Quickstart (Windows)
1. Ensure Python 3.11+ is installed.
2. Open terminal in this folder:
   ```powershell
   .\.venv\Scripts\activate
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Run the development server:
   ```powershell
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
5. Open your browser at:
   **http://127.0.0.1:8000**

---

## ⚖️ Compliance & Privacy
DocuSia is designed as an operational facilitation and document automation tool under Section 55 of the Maharashtra Rent Control Act, 1999. It complies with UIDAI Registered Device (RD) specifications and Section 29 of the Aadhaar Act, 2016 for data encryption and privacy.
