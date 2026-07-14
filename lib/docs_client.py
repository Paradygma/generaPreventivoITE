from googleapiclient.discovery import build

from lib.google_auth import get_credentials


def _service():
    return build("docs", "v1", credentials=get_credentials(), cacheDiscovery=False)


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

    service = _service()
    service.documents().batchUpdate(
        documentId=doc_id, body={"requests": requests_batch}
    ).execute()
