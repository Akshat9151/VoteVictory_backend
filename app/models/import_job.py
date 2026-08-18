import enum

from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class ImportStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    PREVIEW_READY = "PREVIEW_READY"
    IMPORTING = "IMPORTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ImportJob(BaseModel):
    __tablename__ = "import_jobs"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    election_id = Column(String(36), ForeignKey("elections.id", ondelete="CASCADE"), nullable=False, index=True)

    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    status = Column(Enum(ImportStatus), default=ImportStatus.UPLOADED, nullable=False, index=True)

    total_rows = Column(Integer, default=0, nullable=False)
    valid_rows = Column(Integer, default=0, nullable=False)
    duplicate_rows = Column(Integer, default=0, nullable=False)
    invalid_rows = Column(Integer, default=0, nullable=False)
    imported_rows = Column(Integer, default=0, nullable=False)

    report_json = Column(Text, nullable=True)
    preview_data_json = Column(Text, nullable=True)
    created_by = Column(String(36), nullable=True)

    errors = relationship("ImportError", back_populates="import_job", cascade="all, delete-orphan")


class ImportError(BaseModel):
    __tablename__ = "import_errors"

    import_job_id = Column(String(36), ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    field_name = Column(String(100), nullable=True)
    raw_data_json = Column(Text, nullable=True)
    error_reason = Column(Text, nullable=False)

    import_job = relationship("ImportJob", back_populates="errors")
