import io
import os

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from lib.google_auth import get_credentials

PDF_MIME = "application/pdf"


def _service():
    return build("drive", "v3", credentials=get_credentials(), cacheDiscovery=False)


def copy_template(template_id, new_name, folder_id):
    service = _service()
    body = {"name": new_name, "parents": [folder_id]}
    copied = service.files().copy(fileId=template_id, body=body, fields="id, webViewLink").execute()
    return copied["id"], copied["webViewLink"]


def get_web_view_link(file_id):
    service = _service()
    meta = service.files().get(fileId=file_id, fields="webViewLink").execute()
    return meta["webViewLink"]


def export_pdf_and_upload(doc_id, pdf_name, folder_id):
    """Export a Google Doc as PDF and upload it as a new Drive file. Returns (file_id, web_view_link)."""
    service = _service()

    request = service.files().export_media(fileId=doc_id, mimeType=PDF_MIME)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buffer.seek(0)

    from googleapiclient.http import MediaIoBaseUpload

    media = MediaIoBaseUpload(buffer, mimetype=PDF_MIME, resumable=False)
    body = {"name": pdf_name, "parents": [folder_id]}
    uploaded = service.files().create(body=body, media_body=media, fields="id, webViewLink").execute()
    return uploaded["id"], uploaded["webViewLink"]
