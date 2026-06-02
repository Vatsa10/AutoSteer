"""Google Docs/Sheets integration (stub until OAuth/service account configured)."""

import csv
import io
import json

from src.integrations.credentials import get_credential


async def gdocs_export(
    title: str,
    content: str,
    session=None,
    workspace_id: str = "default",
) -> str:
    creds = await get_credential("google", session, workspace_id)
    if not creds:
        return json.dumps({
            "error": "Google Docs not configured.",
            "hint": "Set GOOGLE_SERVICE_ACCOUNT_JSON env var or connect Google in Settings → Integrations. "
                    "Full Google Docs API requires a service account with Docs API enabled.",
            "title": title,
        })
    return json.dumps({
        "error": "Google Docs export requires service account setup (Phase B). Credentials detected but API client not yet wired.",
        "title": title,
    })


async def spreadsheet_export(
    filename: str,
    rows: list[list[str]],
    format: str = "csv",
    session=None,
    workspace_id: str = "default",
) -> str:
    """Export tabular data as CSV (Google Sheets API optional)."""
    if format == "csv" or not await get_credential("google", session, workspace_id):
        output = io.StringIO()
        writer = csv.writer(output)
        for row in rows:
            writer.writerow(row)
        csv_content = output.getvalue()
        return json.dumps({
            "ok": True,
            "format": "csv",
            "filename": filename if filename.endswith(".csv") else f"{filename}.csv",
            "content": csv_content,
            "row_count": len(rows),
        })

    return json.dumps({
        "error": "Google Sheets upload not yet implemented. Use format='csv' for CSV export.",
    })
