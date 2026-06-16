import requests
import json
import time
from pathlib import Path

BASE_URL = "http://127.0.0.1:8765"
DOCS_DIR = Path("test_docs")

def test_health():
    print("Testing /health...")
    resp = requests.get(f"{BASE_URL}/health")
    print(f"Status: {resp.status_code}")
    print(resp.json())
    print()

def test_metadata():
    print("Testing /metadata/document-types...")
    resp = requests.get(f"{BASE_URL}/metadata/document-types")
    print(f"Status: {resp.status_code}")
    # print(resp.json())
    print()

def test_upload_case():
    print("Testing /upload...")
    files_to_upload = [
        # Financial
        DOCS_DIR / "authentic" / "Bank_Statement_Rajesh.pdf",
        DOCS_DIR / "authentic" / "ITR_Rajesh_FY24.pdf",
        DOCS_DIR / "authentic" / "PnL_Rajesh_Business.pdf",
        DOCS_DIR / "forged" / "Bank_Statement_Rajesh_FORGED.pdf",
        # Legal
        DOCS_DIR / "authentic" / "Sale_Deed_Property_42.pdf",
        DOCS_DIR / "authentic" / "Power_Of_Attorney.pdf",
        DOCS_DIR / "forged" / "Sale_Deed_Property_42_FORGED.pdf",
        # Identity
        DOCS_DIR / "authentic" / "Aadhaar_Rajesh.pdf",
        DOCS_DIR / "authentic" / "PAN_Rajesh.pdf",
        DOCS_DIR / "forged" / "PAN_Rajesh_FORGED.pdf"
    ]
    
    files = []
    for path in files_to_upload:
        if path.exists():
            files.append(("files", (path.name, open(path, "rb"), "application/pdf")))
        else:
            print(f"Warning: {path} not found")

    data = {
        "applicant_name": "Rajesh Kumar M.",
        "application_type": "Loan",
        "application_subtype": "Home Loan",
        "mobile_no": "+91 9876543210",
        "address": "Pune, India"
    }

    resp = requests.post(f"{BASE_URL}/upload", data=data, files=files)
    print(f"Status: {resp.status_code}")
    result = resp.json()
    print(json.dumps(result, indent=2))
    print()
    return result.get("case_id")

def test_get_cases():
    print("Testing /cases...")
    resp = requests.get(f"{BASE_URL}/cases")
    print(f"Status: {resp.status_code}")
    print(f"Number of cases: {len(resp.json().get('cases', []))}")
    print()

def test_get_case(case_id):
    print(f"Testing /cases/{case_id}...")
    resp = requests.get(f"{BASE_URL}/cases/{case_id}")
    print(f"Status: {resp.status_code}")
    result = resp.json()
    print(f"Case status: {result.get('case', {}).get('status')}")
    print(f"Risk Score: {result.get('case', {}).get('risk_score')}")
    flags = result.get('flags', [])
    print(f"Number of flags: {len(flags)}")
    for f in flags:
        print(f" - [{f['severity']}] {f['layer']}: {f['finding']}")
    print()

if __name__ == "__main__":
    test_health()
    test_metadata()
    case_id = test_upload_case()
    if case_id:
        print("Waiting for processing to complete (5 seconds)...")
        time.sleep(5)
        test_get_cases()
        test_get_case(case_id)
