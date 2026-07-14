import os

import requests

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"


class NotionError(Exception):
    pass


def _headers():
    token = os.environ["NOTION_TOKEN"]
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def get_page(page_id):
    resp = requests.get(f"{BASE_URL}/pages/{page_id}", headers=_headers(), timeout=15)
    if not resp.ok:
        raise NotionError(f"GET page {page_id} failed: {resp.status_code} {resp.text}")
    return resp.json()


def update_page_urls(page_id, doc_url=None, pdf_url=None):
    """PATCH the generated-document links back onto the page."""
    properties = {}
    if doc_url is not None:
        properties["Documento DOC generato"] = {"url": doc_url}
    if pdf_url is not None:
        properties["Documento PDF generato"] = {"url": pdf_url}
    if not properties:
        return None

    resp = requests.patch(
        f"{BASE_URL}/pages/{page_id}",
        headers=_headers(),
        json={"properties": properties},
        timeout=15,
    )
    if not resp.ok:
        raise NotionError(f"PATCH page {page_id} failed: {resp.status_code} {resp.text}")
    return resp.json()
