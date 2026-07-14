"""Placeholder (exact text between « ») -> Notion property name + formatter.

Placeholder text must match the template literally (case/spacing) because
Google Docs replaceAllText does a literal substring match.
"""

from lib import formatters as fmt

# placeholder_text: (notion_property_name, formatter)
PLACEHOLDER_MAP = {
    "# Preventivo": ("# Preventivo", fmt.as_text),
    "Revisione": ("Revisione", fmt.as_text),
    "Data preventivo": ("Data Preventivo", fmt.as_date_it),
    "Cliente": ("Cliente", fmt.as_text),
    "Indirizzo": ("Indirizzo", fmt.as_text),
    "CF Azienda": ("CF Azienda", fmt.as_text),
    "Contatto": ("Contatto", fmt.as_text),
    "Descrizione Opportunità": ("Descrizione Opportunità", fmt.as_text),
    "Luogo Destinazione": ("Luogo Destinazione", fmt.as_text),
    "Descrizione Attività": ("Descrizione Attività", fmt.as_text),
    "Compenso Orario": ("Compenso Orario", fmt.as_euro),
    "Ore Stimate": ("Ore Stimate", fmt.as_number),
    "Compenso Comprese Spese": ("Compenso Comprese Spese", fmt.as_euro),
    "Imponibile Totale": ("Imponibile Totale", fmt.as_euro),
    "Totale Preventivo": ("Totale Preventivo", fmt.as_euro),
    "Consegna Elaborati": ("Consegna Elaborati", fmt.as_text),
    "Modalità Consegna": ("Modalità Consegna", fmt.as_text),
    "Condizioni Pagamento Descrizione": ("Condizioni Pagamento Descrizione", fmt.as_text),
    "Modalità Pagamento": ("Modalità Pagamento", fmt.as_text),
    "Condizioni Pagamento": ("Condizioni Pagamento", fmt.as_text),
    "Condizioni Offerta": ("Condizioni Offerta", fmt.as_text),
    # footer "Roma, «Data»" reuses the same quote date, different placeholder text
    "Data": ("Data Preventivo", fmt.as_date_it),
}

# Fields that must be non-empty before generating the document.
REQUIRED_PROPERTIES = [
    "Cliente",
    "Descrizione Attività",
    "Totale Preventivo",
]
