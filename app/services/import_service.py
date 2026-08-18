import io
import json
import os

import pandas as pd
from fastapi import Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log
from app.core.exceptions import AppException, ResourceNotFoundException
from app.models.import_job import ImportError, ImportJob, ImportStatus
from app.models.user import User
from app.models.voter import Voter, VoterStatus, VotingStatus
from app.repositories.base import BaseRepository
from app.schemas.import_job import ImportConfirmRequest, ImportPreviewResponse, ImportReportResponse


class BulkImportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_repo = BaseRepository(ImportJob, db)

    async def process_upload_and_preview(
        self,
        request: Request,
        election_id: str,
        file: UploadFile,
        current_user: User
    ) -> ImportPreviewResponse:
        # Validate extension
        filename = file.filename or "upload.csv"
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".csv", ".xlsx", ".xls"]:
            raise AppException(code="INVALID_FILE_TYPE", message="Only CSV and Excel (.xlsx, .xls) files are supported.")

        content = await file.read()
        file_size = len(content)

        # Parse with Pandas
        try:
            if ext == ".csv":
                df = pd.read_csv(io.BytesIO(content))
            else:
                df = pd.read_excel(io.BytesIO(content))
        except Exception as e:
            raise AppException(code="FILE_PARSING_ERROR", message=f"Failed to parse uploaded spreadsheet: {str(e)}")

        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

        required_columns = ["voter_id_number", "first_name", "last_name"]
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            raise AppException(
                code="MISSING_COLUMNS",
                message=f"Missing required columns in header: {', '.join(missing_cols)}"
            )

        # Create ImportJob
        job = ImportJob(
            organization_id=current_user.organization_id,
            election_id=election_id,
            file_name=filename,
            file_path="",
            file_size_bytes=file_size,
            status=ImportStatus.VALIDATING,
            created_by=current_user.id
        )
        job = await self.job_repo.create(job)

        # Fetch existing voter IDs for this election
        stmt = select(Voter.voter_id_number).where(Voter.election_id == election_id)
        existing_ids = set((await self.db.execute(stmt)).scalars().all())

        seen_in_file = set()
        valid_records = []
        import_errors = []
        duplicate_count = 0
        invalid_count = 0

        for idx, row in df.iterrows():
            row_num = idx + 2 # Excel row index
            raw_voter_id = str(row.get("voter_id_number", "")).strip().upper()
            first_name = str(row.get("first_name", "")).strip()
            last_name = str(row.get("last_name", "")).strip()

            if not raw_voter_id or raw_voter_id == "NAN":
                err = ImportError(
                    import_job_id=job.id,
                    row_number=row_num,
                    field_name="voter_id_number",
                    raw_data_json=json.dumps(row.to_dict()),
                    error_reason="Missing voter_id_number"
                )
                import_errors.append(err)
                invalid_count += 1
                continue

            if not first_name or first_name == "NAN":
                err = ImportError(
                    import_job_id=job.id,
                    row_number=row_num,
                    field_name="first_name",
                    raw_data_json=json.dumps(row.to_dict()),
                    error_reason="Missing first_name"
                )
                import_errors.append(err)
                invalid_count += 1
                continue

            # Duplicate Check
            if raw_voter_id in seen_in_file or raw_voter_id in existing_ids:
                duplicate_count += 1
                err = ImportError(
                    import_job_id=job.id,
                    row_number=row_num,
                    field_name="voter_id_number",
                    raw_data_json=json.dumps(row.to_dict()),
                    error_reason=f"Duplicate voter ID '{raw_voter_id}'"
                )
                import_errors.append(err)
                continue

            seen_in_file.add(raw_voter_id)
            valid_records.append({
                "voter_id_number": raw_voter_id,
                "first_name": first_name,
                "last_name": last_name if last_name != "NAN" else "",
                "father_or_spouse_name": str(row.get("father_or_spouse_name", "")) if pd.notna(row.get("father_or_spouse_name")) else None,
                "age": int(row["age"]) if "age" in row and pd.notna(row["age"]) and str(row["age"]).isdigit() else None,
                "gender": str(row.get("gender", "")) if pd.notna(row.get("gender")) else None,
                "phone_number": str(row.get("phone_number", "")).replace(".0", "") if pd.notna(row.get("phone_number")) else None,
                "email": str(row.get("email", "")) if pd.notna(row.get("email")) else None,
                "address": str(row.get("address", "")) if pd.notna(row.get("address")) else None,
                "house_number": str(row.get("house_number", "")) if pd.notna(row.get("house_number")) else None,
                "ward_name": str(row.get("ward_name", "")) if pd.notna(row.get("ward_name")) else None,
            })

        for err in import_errors:
            self.db.add(err)

        job.total_rows = len(df)
        job.valid_rows = len(valid_records)
        job.duplicate_rows = duplicate_count
        job.invalid_rows = invalid_count
        job.status = ImportStatus.PREVIEW_READY
        job.preview_data_json = json.dumps(valid_records[:50]) # Save preview slice
        job.report_json = json.dumps(valid_records) # Temporary hold for confirmation
        await self.job_repo.update(job)

        await record_audit_log(
            self.db,
            request,
            action="voter.import_preview",
            resource_type="import_job",
            resource_id=job.id,
            current_user=current_user,
            new_state={"valid_count": len(valid_records), "duplicate_count": duplicate_count}
        )

        return ImportPreviewResponse(
            job_id=job.id,
            file_name=filename,
            total_rows=len(df),
            valid_count=len(valid_records),
            duplicate_count=duplicate_count,
            invalid_count=invalid_count,
            sample_valid_records=valid_records[:5],
            errors_sample=[
                {
                    "row_number": e.row_number,
                    "field_name": e.field_name,
                    "raw_data_json": e.raw_data_json,
                    "error_reason": e.error_reason
                }
                for e in import_errors[:10]
            ]
        )

    async def confirm_bulk_import(
        self,
        request: Request,
        confirm_in: ImportConfirmRequest,
        current_user: User
    ) -> ImportReportResponse:
        job = await self.job_repo.get_by_id(confirm_in.job_id)
        if not job:
            raise ResourceNotFoundException("ImportJob", confirm_in.job_id)

        if job.status != ImportStatus.PREVIEW_READY:
            raise AppException(code="INVALID_JOB_STATUS", message="Import job is not ready for confirmation.")

        records = json.loads(job.report_json or "[]")
        org_id = current_user.organization_id

        voter_objects = []
        for r in records:
            voter = Voter(
                organization_id=org_id,
                election_id=job.election_id,
                voter_id_number=r["voter_id_number"],
                first_name=r["first_name"],
                last_name=r["last_name"],
                father_or_spouse_name=r.get("father_or_spouse_name"),
                age=r.get("age"),
                gender=r.get("gender"),
                phone_number=r.get("phone_number"),
                email=r.get("email"),
                address=r.get("address"),
                house_number=r.get("house_number"),
                ward_name=r.get("ward_name"),
                status=VoterStatus.REGISTERED,
                voting_status=VotingStatus.NOT_VOTED,
                has_voted=False
            )
            voter_objects.append(voter)
            self.db.add(voter)

        job.status = ImportStatus.COMPLETED
        job.imported_rows = len(voter_objects)
        await self.job_repo.update(job)

        await record_audit_log(
            self.db,
            request,
            action="voter.import_confirmed",
            resource_type="import_job",
            resource_id=job.id,
            current_user=current_user,
            new_state={"imported_count": len(voter_objects)}
        )

        return ImportReportResponse(
            job_id=job.id,
            status=job.status,
            total_records=job.total_rows,
            successfully_imported=job.imported_rows,
            duplicate_records=job.duplicate_rows,
            invalid_records=job.invalid_rows,
            errors=[]
        )
