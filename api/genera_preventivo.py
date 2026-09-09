import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib import drive_client, docs_client, notion_client, notion_props
from lib.logging_utils import log, log_error
from lib.mapping import PLACEHOLDER_MAP, REQUIRED_PROPERTIES, TEMPLATE_ENV_BY_TIPO_ODA

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


def _find_page_object(node):
    """Notion's webhook payload embeds a resolved snapshot of the page
    (data.properties) that already has relation-based formulas computed.
    A fresh pages.retrieve call can return null for those same formulas
    (observed on the classic 2022-06-28 API version), so prefer this
    embedded snapshot over re-fetching when it's present."""
    if isinstance(node, dict):
        if node.get("object") == "page" and isinstance(node.get("properties"), dict):
            return node
        for value in node.values():
            found = _find_page_object(value)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_page_object(item)
            if found:
                return found
    return None


def _check_shared_secret(headers):
    expected = os.environ.get("WEBHOOK_SHARED_SECRET")
    if not expected:
        log("secret_check_skipped", reason="WEBHOOK_SHARED_SECRET not set")
        return
    if headers.get("X-Webhook-Secret") != expected:
        log("secret_check_failed")
        raise PermissionError("secret webhook non valido")
    log("secret_check_ok")


def _build_values(page):
    props = page.get("properties", {})
    values = {}
    raw_debug = {}
    for placeholder, (notion_prop_name, formatter) in PLACEHOLDER_MAP.items():
        raw = notion_props.property_value(props.get(notion_prop_name))
        raw_debug[notion_prop_name] = raw
        values[placeholder] = formatter(raw)
    log("values_built", placeholders=len(values), raw=raw_debug, formatted=values)
    return values


def _is_missing(value):
    """0 is a valid required value (e.g. a legitimately free ODA); only None
    and blank strings count as missing."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _validate_required(values_by_notion_prop_name):
    missing = [name for name in REQUIRED_PROPERTIES if _is_missing(values_by_notion_prop_name.get(name))]
    if missing:
        log("required_validation_failed", missing=missing, values=values_by_notion_prop_name)
        raise ValueError(f"Campi obbligatori mancanti: {', '.join(missing)}")
    log("required_validation_ok")


_COMPUTED_PROPERTY_TYPES = ("formula", "rollup")


def _computed_value_is_null(prop):
    """True if prop is an unresolved formula/rollup (the classic 2022-06-28
    API bug: relation-based computed properties can come back null on a
    fresh pages.retrieve)."""
    if not prop or prop.get("type") not in _COMPUTED_PROPERTY_TYPES:
        return False
    computed = prop.get(prop["type"], {})
    ctype = computed.get("type")
    return computed.get(ctype) is None


def _merge_page_properties(api_page, embedded_page):
    """Live API data is the source of truth (Notion's webhook snapshot has been
    observed serving a stale/cached page state for plain properties). The one
    exception is formulas/rollups: the classic API can serve a stale/uncomputed
    result for relation-based computed properties on a fresh retrieve -
    sometimes null, but also observed silently returning 0 for a currency
    formula that the Notion UI (which recomputes client-side) shows as
    non-zero. Since the webhook fires at button-click time with Notion's own
    resolved snapshot, always prefer it for formula/rollup properties over the
    live API value when it has a value."""
    if not embedded_page:
        return api_page
    api_props = api_page.get("properties", {})
    embedded_props = embedded_page.get("properties", {})
    for name, embedded_prop in embedded_props.items():
        api_prop = api_props.get(name)
        if (
            embedded_prop
            and embedded_prop.get("type") in _COMPUTED_PROPERTY_TYPES
            and not _computed_value_is_null(embedded_prop)
            and api_prop != embedded_prop
        ):
            log(
                "computed_property_backfilled_from_webhook_snapshot",
                property=name,
                api_was_null=_computed_value_is_null(api_prop),
            )
            api_props[name] = embedded_prop
    return api_page


def _now_it():
    return datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")


def _log_to_notion(page_id, message):
    """Best-effort: never let a logging failure mask the original error."""
    if not page_id:
        return
    try:
        notion_client.update_page_log(page_id, message)
    except Exception as exc:  # noqa: BLE001
        log_error("log_to_notion_failed", exc, page_id=page_id)


def _pick_template_id(props):
    tipo_oda = notion_props.property_value(props.get("Tipo ODA"))
    env_var = TEMPLATE_ENV_BY_TIPO_ODA.get(tipo_oda)
    if not env_var:
        log("tipo_oda_not_recognized", tipo_oda=tipo_oda)
        raise ValueError(f"Tipo ODA non riconosciuto: {tipo_oda!r}")
    template_id = os.environ[env_var]
    log("template_picked", tipo_oda=tipo_oda, env_var=env_var, template_id=template_id)
    return template_id


def genera_preventivo(payload, headers):
    _check_shared_secret(headers)
    page_id = _extract_page_id(payload)
    log("page_id_extracted", page_id=page_id)

    log("fetching_page_from_notion_api", page_id=page_id)
    page = notion_client.get_page(page_id)
    embedded_page = _find_page_object(payload)
    page = _merge_page_properties(page, embedded_page)
    props = page.get("properties", {})

    raw_by_name = {name: notion_props.property_value(props.get(name)) for name in REQUIRED_PROPERTIES}
    _validate_required(raw_by_name)

    values = _build_values(page)

    codice_oda = notion_props.property_value(props.get("ODA")) or "SN"
    cliente = values.get("Cliente") or "Cliente"
    base_name = f"{codice_oda} - {cliente}".strip()
    log("base_name_computed", base_name=base_name)

    template_id = _pick_template_id(props)
    folder_id = os.environ["DRIVE_OUTPUT_FOLDER_ID"]

    log("drive_copy_start", template_id=template_id, folder_id=folder_id)
    doc_id, doc_link = drive_client.copy_template(template_id, base_name, folder_id)
    log("drive_copy_done", doc_id=doc_id, doc_link=doc_link)

    log("docs_replace_start", doc_id=doc_id)
    docs_client.replace_placeholders(doc_id, values)
    log("docs_replace_done", doc_id=doc_id)

    log("pdf_export_start", doc_id=doc_id)
    pdf_id, pdf_link = drive_client.export_pdf_and_upload(doc_id, f"{base_name}.pdf", folder_id)
    log("pdf_export_done", pdf_id=pdf_id, pdf_link=pdf_link)

    log("notion_patch_start", page_id=page_id)
    notion_client.update_page_urls(page_id, doc_url=doc_link, pdf_url=pdf_link)
    log("notion_patch_done", page_id=page_id)

    log("genera_preventivo_ok", page_id=page_id, doc_id=doc_id, pdf_id=pdf_id)
    _log_to_notion(page_id, f"✅ Preventivo generato il {_now_it()}. Doc: {doc_link} — PDF: {pdf_link}")
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
        log("request_received", path=self.path, content_length=length)

        try:
            payload = json.loads(raw_body or b"{}")
        except json.JSONDecodeError as exc:
            log_error("body_not_json", exc, raw_body=raw_body.decode("utf-8", "replace"))
            self._respond(400, {"ok": False, "error": "body non è JSON valido", "raw_body": raw_body.decode("utf-8", "replace")})
            return

        try:
            page_id_for_log = _extract_page_id(payload)
        except Exception:  # noqa: BLE001 - best-effort, only used to target the Notion log write
            page_id_for_log = None

        try:
            result = genera_preventivo(payload, self.headers)
            self._respond(200, result)
        except PermissionError as exc:
            log_error("request_failed_401", exc)
            _log_to_notion(page_id_for_log, f"❌ Generazione fallita il {_now_it()}: {exc}")
            self._respond(401, {"ok": False, "error": str(exc)})
        except ValueError as exc:
            log_error("request_failed_400", exc)
            _log_to_notion(page_id_for_log, f"❌ Generazione fallita il {_now_it()}: {exc}")
            self._respond(400, {"ok": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - report unexpected errors to caller/logs
            log_error("request_failed_500", exc)
            _log_to_notion(page_id_for_log, f"❌ Errore imprevisto il {_now_it()}: {exc}")
            self._respond(500, {"ok": False, "error": str(exc)})

    def _respond(self, status, body):
        log("responding", status=status, ok=body.get("ok"))
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode("utf-8"))
