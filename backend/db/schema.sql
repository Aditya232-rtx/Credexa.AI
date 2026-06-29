CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY,
    applicant_name TEXT,
    mobile_no TEXT,
    address TEXT,
    application_type TEXT,       -- Loan, Insurance, KYC, Account Opening, Property Registration
    application_subtype TEXT,    -- Home Loan, Business Loan, etc. (depends on application_type)
    status TEXT, -- pending, review, flagged, cleared
    risk_score INTEGER,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    case_id TEXT,
    file_name TEXT,
    file_type TEXT,
    file_size INTEGER,
    doc_category TEXT, -- Financial, Legal, Land & Identity
    status TEXT,
    FOREIGN KEY(case_id) REFERENCES cases(id)
);

CREATE TABLE IF NOT EXISTS flags (
    id TEXT PRIMARY KEY,
    case_id TEXT,
    document_id TEXT,
    layer TEXT, -- File Forensics, Visual Forensics, etc.
    finding TEXT,
    severity TEXT, -- low, medium, high
    score INTEGER,
    FOREIGN KEY(case_id) REFERENCES cases(id),
    FOREIGN KEY(document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    case_id TEXT,
    action TEXT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(case_id) REFERENCES cases(id)
);

CREATE INDEX IF NOT EXISTS idx_documents_case_id ON documents(case_id);
CREATE INDEX IF NOT EXISTS idx_flags_document_id ON flags(document_id);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);

CREATE TABLE IF NOT EXISTS feedback (
    id TEXT PRIMARY KEY,
    case_id TEXT,
    reviewer_id TEXT,
    decision TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(case_id) REFERENCES cases(id)
);
