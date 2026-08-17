from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.import_job import ImportStatus


class ImportErrorDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    row_number: int
    field_name: Optional[str] = None
    raw_data_json: Optional[str] = None
    error_reason: str


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    election_id: str
    file_name: str
    status: ImportStatus
    total_rows: int
    valid_rows: int
    duplicate_rows: int
    invalid_rows: int
    imported_rows: int
    created_at: datetime


class ImportPreviewResponse(BaseModel):
    job_id: str
    file_name: str
    total_rows: int
    valid_count: int
    duplicate_count: int
    invalid_count: int
    sample_valid_records: List[Dict[str, Any]] = []
    errors_sample: List[ImportErrorDetail] = []


class ImportConfirmRequest(BaseModel):
    job_id: str
    skip_duplicates: bool = True


class ImportReportResponse(BaseModel):
    job_id: str
    status: ImportStatus
    total_records: int
    successfully_imported: int
    duplicate_records: int
    invalid_records: int
    errors: List[ImportErrorDetail] = []
