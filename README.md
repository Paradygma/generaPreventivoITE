# Automazione Preventivi ID&A

Bottone su Notion (DB "📄 ODA - ITE") → webhook → Vercel (Python) → copia il
template Google Doc, sostituisce i placeholder `«Campo»` coi dati della
pagina Notion, esporta PDF, e riscrive i link su Notion.

## Setup

### 1. Notion

1. Aggiungi (o usa un'integration esistente con accesso al workspace
   Paradygma) un **internal integration token** → `NOTION_TOKEN`.
2. Condividi il DB "📄 ODA - ITE" con l'integration.
3. Aggiungi la property `Documento DOC generato` (type **URL**) al DB.
4. Converti `Documento PDF generato` da `file` a **URL**.
5. Su una property bottone (nuova o esistente) configura un'automation:
   **Send webhook** → URL = endpoint Vercel (`https://<progetto>.vercel.app/api/genera_preventivo`)
   → body JSON personalizzato: `{"page_id": "{{Page ID}}", "secret": "<WEBHOOK_SHARED_SECRET>"}`.

### 2. Google Cloud

1. Crea (o riusa) un **service account** con Drive API + Docs API abilitate.
2. Scarica la chiave JSON, incollala come stringa unica in
   `GOOGLE_SERVICE_ACCOUNT_JSON`.
3. Condividi con l'email del service account (permesso **Editor**):
   - il file template (`TEMPLATE_DOC_ID`)
   - la cartella di output (`DRIVE_OUTPUT_FOLDER_ID`) — oggi cartella
     personale, in futuro cartella condivisa cliente: basta cambiare l'ID.

### 3. Vercel

```
vercel link
vercel env add NOTION_TOKEN
vercel env add GOOGLE_SERVICE_ACCOUNT_JSON
vercel env add TEMPLATE_DOC_ID
vercel env add DRIVE_OUTPUT_FOLDER_ID
vercel env add WEBHOOK_SHARED_SECRET   # opzionale ma consigliato
vercel deploy
```

## Verifica

1. Crea un record di test in "ODA - ITE" con tutti i campi obbligatori
   (`Cliente`, `Descrizione Attività`, `Totale Preventivo`) valorizzati.
2. Premi il bottone → controlla `vercel logs <deployment-url>`.
3. Apri Doc e PDF generati nella cartella di output, verifica che non resti
   nessun placeholder `«...»` non sostituito.
4. Verifica che i link siano scritti su `Documento DOC generato` e
   `Documento PDF generato` nel record Notion.

## Note aperte

- La riga "compenso a vacazione secondo A.Q." (visibile solo se
  `Metodo calcolo = Accordo Quadro`) resta sempre nel documento, col
  placeholder valorizzato o vuoto — nascondere/rimuovere il paragrafo intero
  è rimandato a dopo l'allineamento col cliente.
- Cartella di output oggi è il Drive personale di Mirko: quando sarà pronta
  la cartella condivisa cliente, basta aggiornare `DRIVE_OUTPUT_FOLDER_ID`.
