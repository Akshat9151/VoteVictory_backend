import io
import json
import os

import pandas as pd
from pypdf import PdfReader
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
        if ext not in [".csv", ".xlsx", ".xls", ".pdf"]:
            raise AppException(code="INVALID_FILE_TYPE", message="Only CSV, Excel, and text-based PDF voter rolls are supported.")

        content = await file.read()
        file_size = len(content)

        df = None
        pdf_records = []
        if ext == ".pdf":
            try:
                reader = PdfReader(io.BytesIO(content))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception as e:
                raise AppException(code="FILE_PARSING_ERROR", message=f"Failed to read PDF: {str(e)}")
            pdf_records = self._parse_pdf_rows(text)
            if not pdf_records:
                raise AppException(
                    code="PDF_TEXT_NOT_FOUND",
                    message="No voter rows could be read from this PDF. Upload a text-based electoral roll PDF or export it as CSV.",
                )
        else:
            try:
                if ext == ".csv":
                    df = pd.read_csv(io.BytesIO(content))
                else:
                    df = pd.read_excel(io.BytesIO(content))
            except Exception as e:
                raise AppException(code="FILE_PARSING_ERROR", message=f"Failed to parse uploaded spreadsheet: {str(e)}")

            df.columns = [self._normalize_column_name(c) for c in df.columns]
            aliases = {
                "epic_no": "voter_id_number",
                "epic_number": "voter_id_number",
                "epic_id": "voter_id_number",
                "voter_id": "voter_id_number",
                "voter_id_no": "voter_id_number",
                "id_number": "voter_id_number",
                "serial_no": "voter_id_number",
                "serial_number": "voter_id_number",
                "s_no": "voter_id_number",
                "sr_no": "voter_id_number",
                "no": "voter_id_number",
                "elector_name": "first_name",
                "voter_name": "first_name",
                "full_name": "first_name",
                "electors_name": "first_name",
                "surname": "last_name",
                "family_name": "last_name",
                "father_name": "father_or_spouse_name",
                "husband_name": "father_or_spouse_name",
                "father_husband_name": "father_or_spouse_name",
                "relative_name": "father_or_spouse_name",
                "sex": "gender",
                "mobile": "phone_number",
                "mobile_number": "phone_number",
                "phone": "phone_number",
                "contact_number": "phone_number",
                "house_no": "house_number",
                "address_line": "address",
                "ward": "ward_name",
                "ward_no": "ward_name",
            }
            df = df.rename(columns={column: aliases.get(column, column) for column in df.columns})

            required_columns = ["voter_id_number", "first_name"]
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

        source_rows = enumerate(pdf_records) if ext == ".pdf" else df.iterrows()
        total_rows = len(pdf_records) if ext == ".pdf" else len(df)
        for idx, row in source_rows:
            row_num = idx + 2 # Excel row index
            raw_voter_id = str(row.get("voter_id_number", "")).strip().upper()
            first_name = str(row.get("first_name", "")).strip()
            last_name = str(row.get("last_name", "")).strip()
            if last_name == "NAN":
                last_name = ""
            if first_name and " " in first_name and not last_name:
                name_parts = first_name.split()
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])

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
                "last_name": last_name,
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

        job.total_rows = total_rows
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
            total_rows=total_rows,
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

    @staticmethod
    def _normalize_column_name(value: object) -> str:
        import re

        normalized = str(value).strip().lower()
        normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
        return normalized

    @staticmethod
    def _parse_pdf_rows(text: str) -> list[dict]:
        """Parse common text-based electoral-roll lines into the import schema."""
        import re

        records = []
        voter_id_pattern = re.compile(r"\b[A-Z]{2,5}[0-9]{5,}|\b[0-9]{6,16}\b")
        phone_pattern = re.compile(r"\b(?:\+?91[- ]?)?[6-9][0-9]{9}\b")
        age_pattern = re.compile(r"\b(?:age|उम्र|वय)\s*[:=-]?\s*(\d{1,3})\b", re.IGNORECASE)
        gender_pattern = re.compile(r"\b(MALE|FEMALE|OTHER|पुरुष|महिला|अन्य|M|F)\b", re.IGNORECASE)
        for raw_line in text.splitlines():
            line = " ".join(raw_line.split())
            if not line:
                continue
            voter_match = voter_id_pattern.search(line.upper())
            if not voter_match:
                continue
            voter_id = voter_match.group(0)
            before_id = line[:voter_match.start()].strip(" -:|,.")
            after_id = line[voter_match.end():].strip(" -:|,.")
            name_text = after_id if before_id.isdigit() else (before_id or after_id)
            name_text = re.sub(r"^(?:name|नाम|मतदाता)\s*[:=-]?\s*", "", name_text, flags=re.IGNORECASE).strip()
            name_text = re.split(r"\b(?:age|उम्र|वय|male|female|पुरुष|महिला|other|अन्य)\b", name_text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -:|,.")
            name_parts = name_text.split()
            if not name_parts:
                continue
            age_match = age_pattern.search(line)
            gender_match = gender_pattern.search(line)
            phone_match = phone_pattern.search(line)
            records.append({
                "voter_id_number": voter_id,
                "first_name": name_parts[0],
                "last_name": " ".join(name_parts[1:]),
                "age": int(age_match.group(1)) if age_match else None,
                "gender": gender_match.group(1) if gender_match else None,
                "phone_number": phone_match.group(0) if phone_match else None,
            })
        return records

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

    async def cancel_import(self, request: Request, job_id: str, current_user: User) -> None:
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise ResourceNotFoundException("ImportJob", job_id)
        if job.organization_id != current_user.organization_id:
            raise AppException(code="IMPORT_ACCESS_DENIED", message="You cannot cancel this import preview.")
        if job.status != ImportStatus.PREVIEW_READY:
            raise AppException(code="INVALID_JOB_STATUS", message="Only an unconfirmed import preview can be cancelled.")

        await self.db.delete(job)
        await self.db.commit()
        await record_audit_log(
            self.db,
            request,
            action="voter.import_cancelled",
            resource_type="import_job",
            resource_id=job_id,
            current_user=current_user,
        )
