"""Generic Notion property -> plain text/value extraction."""


def _rich_text_to_plain(rich_text_list):
    return "".join(rt.get("plain_text", "") for rt in rich_text_list or [])


def _formula_value(formula):
    ftype = formula.get("type")
    if ftype == "string":
        return formula.get("string") or ""
    if ftype == "number":
        return formula.get("number")
    if ftype == "boolean":
        return formula.get("boolean")
    if ftype == "date":
        date_obj = formula.get("date")
        return date_obj.get("start") if date_obj else ""
    return ""


def property_value(prop):
    """Return the raw python value of a Notion property (str/float/None/dict)."""
    if prop is None:
        return None
    ptype = prop.get("type")
    if ptype == "title":
        return _rich_text_to_plain(prop.get("title"))
    if ptype == "rich_text":
        return _rich_text_to_plain(prop.get("rich_text"))
    if ptype == "text":
        return _rich_text_to_plain(prop.get("text"))
    if ptype == "number":
        return prop.get("number")
    if ptype == "select":
        sel = prop.get("select")
        return sel.get("name") if sel else ""
    if ptype == "status":
        st = prop.get("status")
        return st.get("name") if st else ""
    if ptype == "date":
        d = prop.get("date")
        return d.get("start") if d else ""
    if ptype == "formula":
        return _formula_value(prop.get("formula", {}))
    if ptype == "url":
        return prop.get("url") or ""
    if ptype == "checkbox":
        return prop.get("checkbox")
    raise ValueError(f"Unsupported Notion property type: {ptype}")
