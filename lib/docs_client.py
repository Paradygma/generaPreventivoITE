from googleapiclient.discovery import build

from lib.google_auth import get_credentials
from lib.logging_utils import log, log_error


def _service():
    return build("docs", "v1", credentials=get_credentials())


def replace_placeholders(doc_id, values_by_placeholder):
    """values_by_placeholder: {"Cliente": "Acme Srl", ...}. Wraps each key in
    the template's guillemet marker («Cliente») before searching."""
    requests_batch = []
    for placeholder, value in values_by_placeholder.items():
        requests_batch.append(
            {
                "replaceAllText": {
                    "containsText": {
                        "text": f"«{placeholder}»",
                        "matchCase": True,
                    },
                    "replaceText": value,
                }
            }
        )

    try:
        service = _service()
        service.documents().batchUpdate(
            documentId=doc_id, body={"requests": requests_batch}
        ).execute()
        log("docs_replace_placeholders_ok", doc_id=doc_id, placeholders=len(requests_batch))
    except Exception as exc:
        log_error("docs_replace_placeholders_failed", exc, doc_id=doc_id)
        raise
