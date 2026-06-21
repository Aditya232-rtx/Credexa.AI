from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/mock-gov", tags=["Mock Govt APIs"])


@router.get("/traces/26as/{pan}")
async def mock_traces(pan: str):
    return {"pan": pan, "name": "Rajesh Kumar M.", "financial_year": "2024-25", "total_tds_deposited": 45000, "employers": [{"name": "Tech Corp India", "tan": "MUMT12345E", "tds": 45000}]}


@router.get("/mca/company/{cin}")
async def mock_mca(cin: str):
    return {"cin": cin, "company_name": "Demo Enterprises Pvt Ltd", "status": "Active", "incorporation_date": "12/04/2015"}


@router.get("/aa/fi-data/{consent_id}")
async def mock_account_aggregator(consent_id: str):
    return {"consent_id": consent_id, "status": "ACTIVE", "accounts": [{"type": "DEPOSIT", "masked_acc": "XXXX1234", "bank": "HDFC", "current_balance": 154200.5}]}


@router.get("/bhulekh/712/{survey_no}")
async def mock_bhulekh(survey_no: str):
    return {"survey_no": survey_no, "owner_name": "Rajesh Kumar M.", "area_hectares": 1.25, "encumbrances": ["Crop Loan - SBI (₹50,000)"]}


@router.get("/health")
async def mock_health():
    return {"status": "ok"}
