import io
import os

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from lib.google_auth import get_credentials
from lib.logging_utils import log, log_error

PDF_MIME = "application/pdf"


def _service():
    return build("drive", "v3", credentials=get_credentials())


def copy_template(template_id, new_name, folder_id):
    try:
        service = _service()
        body = {"name": new_name, "parents": [folder_id]}
        copied = (
            service.files()
            .copy(fileId=template_id, body=body, fields="id, webViewLink", supportsAllDrives=True)
            .execute()
        )
        log("drive_copy_template_ok", file_id=copied["id"])
        return copied["id"], copied["webViewLink"]
    except Exception as exc:
        log_error("drive_copy_template_failed", exc, template_id=template_id, folder_id=folder_id)
        raise


def get_web_view_link(file_id):
    try:
        service = _service()
        meta = service.files().get(fileId=file_id, fields="webViewLink", supportsAllDrives=True).execute()
        return meta["webViewLink"]
    except Exception as exc:
        log_error("drive_get_web_view_link_failed", exc, file_id=file_id)
        raise


def export_pdf_and_upload(doc_id, pdf_name, folder_id):
    """Export a Google Doc as PDF and upload it as a new Drive file. Returns (file_id, web_view_link)."""
    try:
        service = _service()

        request = service.files().export_media(fileId=doc_id, mimeType=PDF_MIME)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buffer.seek(0)
        log("drive_pdf_export_ok", doc_id=doc_id)

        from googleapiclient.http import MediaIoBaseUpload

        media = MediaIoBaseUpload(buffer, mimetype=PDF_MIME, resumable=False)
        body = {"name": pdf_name, "parents": [folder_id]}
        uploaded = (
            service.files()
            .create(body=body, media_body=media, fields="id, webViewLink", supportsAllDrives=True)
            .execute()
        )
        log("drive_pdf_upload_ok", file_id=uploaded["id"])
        return uploaded["id"], uploaded["webViewLink"]
    except Exception as exc:
        log_error("drive_export_pdf_and_upload_failed", exc, doc_id=doc_id, pdf_name=pdf_name, folder_id=folder_id)
        raise
