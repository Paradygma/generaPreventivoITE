import json
import os
import re
import sys
import traceback
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib import drive_client, docs_client, notion_client, notion_props
from lib.mapping import PLACEHOLDER_MAP, REQUIRED_PROPERTIES

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$", re.IGNORECASE
)


def _find_id_recursive(node, preferred_keys=("page_id", "id", "pageId")):
    """Notion's native 'Send webhook' payload shape isn't officially documented,
    so walk the JSON looking for a UUID-looking value, preferring keys named
    like an id."""
    if isinstance(node, dict):
        for key in preferred_keys:
            value = node.get(key)
            if isinstance(value, str) and UUID_RE.match(value):
                return value
        for value in node.values():
            found = _find_id_recursive(value, preferred_keys)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_id_recursive(item, preferred_keys)
            if found:
                return found
    return None


def _extract_page_id(payload):
    page_id = _find_id_recursive(payload)
    if not page_id:
        raise ValueError("page_id non trovato nel body del webhook")
    return page_id


def _check_shared_secret(headers):
    expected = os.environ.get("WEBHOOK_SHARED_SECRET")
    if not expected:
        return
    if headers.get("X-Webhook-Secret") != expected:
        raise PermissionError("secret webhook non valido")


def _build_values(page):
    props = page.get("properties", {})
    values = {}
    for placeholder, (notion_prop_name, formatter) in PLACEHOLDER_MAP.items():
        raw = notion_props.property_value(props.get(notion_prop_name))
        values[placeholder] = formatter(raw)
    return values


def _validate_required(values_by_notion_prop_name):
    missing = [name for name in REQUIRED_PROPERTIES if not values_by_notion_prop_name.get(name)]
    if missing:
        raise ValueError(f"Campi obbligatori mancanti: {', '.join(missing)}")


def genera_preventivo(payload, headers):
    _check_shared_secret(headers)
    page_id = _extract_page_id(payload)

    page = notion_client.get_page(page_id)
    props = page.get("properties", {})

    raw_by_name = {name: notion_props.property_value(props.get(name)) for name in REQUIRED_PROPERTIES}
    _validate_required(raw_by_name)

    values = _build_values(page)

    codice = values.get("# Preventivo") or "SN"
    cliente = values.get("Cliente") or "Cliente"
    base_name = f"{codice} - {cliente}".strip()

    template_id = os.environ["TEMPLATE_DOC_ID"]
    folder_id = os.environ["DRIVE_OUTPUT_FOLDER_ID"]

    doc_id, doc_link = drive_client.copy_template(template_id, base_name, folder_id)
    docs_client.replace_placeholders(doc_id, values)
    pdf_id, pdf_link = drive_client.export_pdf_and_upload(doc_id, f"{base_name}.pdf", folder_id)

    notion_client.update_page_urls(page_id, doc_url=doc_link, pdf_url=pdf_link)

    return {
        "ok": True,
        "page_id": page_id,
        "doc_id": doc_id,
        "doc_url": doc_link,
        "pdf_id": pdf_id,
        "pdf_url": pdf_link,
    }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw_body or b"{}")
        except json.JSONDecodeError:
            self._respond(400, {"ok": False, "error": "body non è JSON valido"})
            return

        try:
            result = genera_preventivo(payload, self.headers)
            self._respond(200, result)
        except PermissionError as exc:
            self._respond(401, {"ok": False, "error": str(exc)})
        except ValueError as exc:
            self._respond(400, {"ok": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - report unexpected errors to caller/logs
            traceback.print_exc()
            self._respond(500, {"ok": False, "error": str(exc)})

    def _respond(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode("utf-8"))
