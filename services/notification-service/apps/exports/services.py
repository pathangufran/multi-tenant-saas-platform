import csv
import os
from uuid import UUID
from datetime import datetime,timezone
from typing import Iterable
from django.db import transaction
from django.utils.text import slugify
from .models import Export
from .storage import ExportStorage
import io

class ExportService:
    
    SUPPORTED_EXPORT_TYPES = {
        Export.ExportType.PROJECTS,
        Export.ExportType.USERS,
        Export.ExportType.TASKS,
        Export.ExportType.AUDIT_LOGS,
    }
    
    @staticmethod
    def validate_export_type(
        *,
        export_type: str,
    ) -> None:
        
        if export_type not in ExportService.SUPPORTED_EXPORT_TYPES:
            raise ValueError(
                f"Unsupported export type: {export_type}"
            ) 
            
    @staticmethod
    @transaction.atomic
    def create_export(
        *,
        tenant_id: UUID,
        user_id: UUID,
        export_type: str,
    ) -> Export:
        
        ExportService.validate_export_type(
            export_type=export_type,
        )
        
        return Export.objects.create(
            tenant_id=tenant_id,
            requested_by=user_id,
            export_type=export_type,
            status=Export.Status.PENDING,
        )
        
    @staticmethod
    def list_exports(
        *,
        tenant_id: UUID,
        user_id=None,
    ):
        
        queryset = Export.objects.filter(
            tenant_id=tenant_id,
        )
        if user_id is not None:
            queryset = queryset.filter(
                requested_by=user_id,
            )
            
        return queryset.order_by(
            "-created_at",
        )

    @staticmethod
    def get_export(
        *,
        tenant_id,
        export_id,
    ) -> Export:

        try:
            return Export.objects.get(
                tenant_id=tenant_id,
                id=export_id,
            )
        except Export.DoesNotExist:
            raise ValueError(
                "Export not found."
            )
        
    @staticmethod
    def build_csv(
        *,
        rows: Iterable[dict],
    ) -> tuple[bytes,int]:
        
        rows = list(rows)
        
        if not rows:
            output = io.StringIO()
            
            writer = csv.writer(output)
            writer.writerow(["message"])
            writer.writerow(["No records found"])
            
            return (
                output.getvalue().encode("utf-8"),
                0,
            )
            
        field_names = []
        
        for row in rows:
            for key in row.keys():
                field_names.append(key)
                
        output = io.StringIO(newline="",)

        writer = csv.DictWriter(
            output,
            fieldnames=field_names,
            extrasaction="ignore",
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(row)

        return (
            output.getvalue().encode("utf-8"),
            len(rows),
        )
        
    @staticmethod
    def generate_file_name(
        *,
        export: Export,
    ) -> str:

        timestamp = datetime.now(
            timezone.utc,
        ).strftime(
            "%Y%m%d_%H%M%S",
        )

        export_type = slugify(
            export.export_type.lower(),
        )

        return (
            f"{export_type}_"
            f"{export.id}_"
            f"{timestamp}.csv"
        )

    @staticmethod
    @transaction.atomic
    def mark_processing(
        *,
        export: Export,
    ) -> Export:
        
        export.status = Export.Status.PROCESSING
        export.error_message = ""
        
        export.save(
            update_fields=[
                "status","error_message",
            ],
        )

        return export

    @staticmethod
    @transaction.atomic
    def complete_export(
        *,
        export: Export,
        file_name: str,
        storage_key: str,
        row_count: int,
    ) -> Export:
        
        export.status = Export.Status.COMPLETED
        export.file_name = file_name
        export.storage_key = storage_key
        export.row_count = row_count
        export.completed_at = datetime.now(
            timezone.utc,
        )
        
        export.save(
            update_fields=[
                "status",
                "file_name",
                "storage_key",
                "row_count",
                "error_message",
                "completed_at",
            ],
        )

        return export
    
    @staticmethod
    @transaction.atomic
    def fail_export(
        *,
        export: Export,
        error_message: str,
    ) -> Export:

        export.status = Export.Status.FAILED
        export.error_message = error_message

        export.save(
            update_fields=[
                "status","error_message",
            ],
        )

        return export
    
    @staticmethod
    def generate_export(
        *,
        export: Export,
        rows: Iterable[dict],
    ) -> Export:
        
        ExportService.mark_processing(
            export=export,
        )
        
        try:
            content, row_count = (
                ExportService.build_csv(
                    rows=rows,
                )
            )
            file_name = (
                ExportService.generate_file_name(
                    export=export,
                )
            )
            storage_key = (
                f"exports/"
                f"{export.tenant_id}/"
                f"{file_name}"
            )
            saved_key = ExportStorage.save(
                key=storage_key,
                content=content,
            )
            
            return ExportService.complete_export(
                export=export,
                file_name=file_name,
                storage_key=saved_key,
                row_count=row_count,
            )
            
        except Exception as exc:
            ExportService.fail_export(
                export=export,
                error_message=str(exc),
            )
    
    @staticmethod
    def get_download_url(
        *,
        export: Export,
    ) -> str:

        if export.status != Export.Status.COMPLETED:
            raise ValueError(
                "Export is not ready for download."
            )

        if not export.storage_key:
            raise ValueError(
                "Export file is unavailable."
            )

        try:
            return ExportStorage.get_download_url(
                key=export.storage_key,
            )
        except ValueError as exc:
            raise ValueError(
                f"detail: {str(exc)}",
            )