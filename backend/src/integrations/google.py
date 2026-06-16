"""Google Docs / Sheets integration via service account credentials."""

import asyncio
import csv
import io
import json

from src.integrations.credentials import get_credential, get_credential_metadata

DOCS_SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]
SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _load_credentials(creds_json: str, scopes: list[str]):
    from google.oauth2 import service_account

    info = json.loads(creds_json)
    return service_account.Credentials.from_service_account_info(info, scopes=scopes)


def _maybe_share(drive, file_id: str, email: str | None) -> None:
    """Service-account-owned files are invisible to humans until shared."""
    if not email:
        return
    drive.permissions().create(
        fileId=file_id,
        body={"type": "user", "role": "writer", "emailAddress": email},
        sendNotificationEmail=False,
    ).execute()


async def gdocs_export(
    title: str,
    content: str,
    session=None,
    workspace_id: str = "default",
) -> str:
    creds_json = await get_credential("google", session, workspace_id)
    if not creds_json:
        return json.dumps({
            "error": "Google Docs not configured.",
            "hint": "Set GOOGLE_SERVICE_ACCOUNT_JSON or connect Google in Settings → Integrations.",
            "title": title,
        })
    if not creds_json.strip().startswith("{"):
        return json.dumps({"error": "GOOGLE_SERVICE_ACCOUNT_JSON must be the service account JSON."})

    try:
        from googleapiclient.discovery import build
    except ImportError:
        return json.dumps({
            "error": "google-api-python-client not installed. pip install google-api-python-client google-auth",
            "title": title,
        })

    meta = await get_credential_metadata("google", session, workspace_id)
    share_email = meta.get("share_email")

    def _create() -> dict:
        creds = _load_credentials(creds_json, DOCS_SCOPES)
        docs = build("docs", "v1", credentials=creds, cache_discovery=False)
        drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        doc = docs.documents().create(body={"title": title[:1000] or "Untitled"}).execute()
        doc_id = doc["documentId"]
        if content:
            docs.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
            ).execute()
        _maybe_share(drive, doc_id, share_email)
        return {
            "ok": True,
            "document_id": doc_id,
            "url": f"https://docs.google.com/document/d/{doc_id}/edit",
            "title": title,
            "shared_with": share_email,
        }

    try:
        result = await asyncio.to_thread(_create)
    except Exception as exc:
        return json.dumps({"error": f"Google Docs API failed: {exc}", "title": title})
    return json.dumps(result, indent=2)


async def spreadsheet_export(
    filename: str,
    rows: list[list[str]],
    format: str = "csv",
    session=None,
    workspace_id: str = "default",
) -> str:
    """Export tabular data. format='csv' (default, no creds) or 'sheets' (Google Sheets)."""
    creds_json = await get_credential("google", session, workspace_id)

    if format != "sheets" or not creds_json:
        output = io.StringIO()
        writer = csv.writer(output)
        for row in rows:
            writer.writerow(row)
        return json.dumps({
            "ok": True,
            "format": "csv",
            "filename": filename if filename.endswith(".csv") else f"{filename}.csv",
            "content": output.getvalue(),
            "row_count": len(rows),
        })

    if not creds_json.strip().startswith("{"):
        return json.dumps({"error": "GOOGLE_SERVICE_ACCOUNT_JSON must be the service account JSON."})

    try:
        from googleapiclient.discovery import build
    except ImportError:
        return json.dumps({
            "error": "google-api-python-client not installed. pip install google-api-python-client google-auth",
        })

    meta = await get_credential_metadata("google", session, workspace_id)
    share_email = meta.get("share_email")

    def _create() -> dict:
        creds = _load_credentials(creds_json, SHEETS_SCOPES)
        sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
        drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        ss = sheets.spreadsheets().create(body={"properties": {"title": filename or "Untitled"}}).execute()
        ss_id = ss["spreadsheetId"]
        if rows:
            sheets.spreadsheets().values().update(
                spreadsheetId=ss_id,
                range="A1",
                valueInputOption="RAW",
                body={"values": rows},
            ).execute()
        _maybe_share(drive, ss_id, share_email)
        return {
            "ok": True,
            "format": "sheets",
            "spreadsheet_id": ss_id,
            "url": f"https://docs.google.com/spreadsheets/d/{ss_id}/edit",
            "row_count": len(rows),
            "shared_with": share_email,
        }

    try:
        result = await asyncio.to_thread(_create)
    except Exception as exc:
        return json.dumps({"error": f"Google Sheets API failed: {exc}"})
    return json.dumps(result, indent=2)


async def test_connection(session=None, workspace_id: str = "default") -> dict:
    creds_json = await get_credential("google", session, workspace_id)
    if not creds_json:
        return {"ok": False, "error": "No Google service account configured"}
    if not creds_json.strip().startswith("{"):
        return {"ok": False, "error": "GOOGLE_SERVICE_ACCOUNT_JSON must be JSON"}
    try:
        info = json.loads(creds_json)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"Invalid service account JSON: {exc}"}
    try:
        import googleapiclient  # type: ignore  # noqa: F401
    except ImportError:
        return {"ok": False, "error": "google-api-python-client not installed"}
    return {"ok": True, "service_account": info.get("client_email")}
