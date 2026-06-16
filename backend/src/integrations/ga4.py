"""Google Analytics 4 Data API integration (beta)."""

import json

from src.integrations.credentials import get_credential, get_credential_metadata


async def ga4_read(
    property_id: str | None = None,
    metric: str = "activeUsers",
    days: int = 7,
    session=None,
    workspace_id: str = "default",
) -> str:
    creds = await get_credential("google", session, workspace_id)
    meta = await get_credential_metadata("google", session, workspace_id)
    ga_property = property_id or meta.get("ga4_property_id", "")

    if not creds or not ga_property:
        return json.dumps({
            "status": "beta",
            "error": "GA4 not fully configured.",
            "hint": (
                "Set GOOGLE_SERVICE_ACCOUNT_JSON with Analytics Data API access and connect "
                'with metadata {"ga4_property_id": "properties/123456789"}. '
                "Beta: returns stub summary until credentials are configured."
            ),
            "stub_summary": {
                "property_id": ga_property or "not_set",
                "metric": metric,
                "days": days,
                "activeUsers": None,
                "sessions": None,
                "note": "Connect Google service account + GA4 property for live data.",
            },
        })

    try:
        from google.oauth2 import service_account
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
    except ImportError:
        return json.dumps({
            "status": "beta",
            "error": "google-analytics-data package not installed. pip install google-analytics-data",
            "property_id": ga_property,
        })

    try:
        info = json.loads(creds) if creds.strip().startswith("{") else {"type": "service_account"}
        if creds.strip().startswith("{"):
            credentials = service_account.Credentials.from_service_account_info(
                info, scopes=["https://www.googleapis.com/auth/analytics.readonly"]
            )
        else:
            return json.dumps({"error": "GOOGLE_SERVICE_ACCOUNT_JSON must be JSON for GA4."})

        client = BetaAnalyticsDataClient(credentials=credentials)
        request = RunReportRequest(
            property=ga_property if ga_property.startswith("properties/") else f"properties/{ga_property}",
            dimensions=[Dimension(name="date")],
            metrics=[Metric(name=metric), Metric(name="sessions")],
            date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        )
        response = client.run_report(request)
        rows = [
            {
                "date": r.dimension_values[0].value,
                metric: r.metric_values[0].value,
                "sessions": r.metric_values[1].value if len(r.metric_values) > 1 else None,
            }
            for r in response.rows
        ]
        return json.dumps({"property_id": ga_property, "metric": metric, "days": days, "rows": rows}, indent=2)
    except Exception as exc:
        return json.dumps({
            "status": "beta",
            "error": f"GA4 query failed: {exc}",
            "property_id": ga_property,
        })


async def test_connection(session=None, workspace_id: str = "default") -> dict:
    creds = await get_credential("google", session, workspace_id)
    meta = await get_credential_metadata("google", session, workspace_id)
    ga_property = meta.get("ga4_property_id", "")
    if not creds:
        return {"ok": False, "error": "Google service account not configured"}
    if not ga_property:
        return {
            "ok": False,
            "error": 'GA4 property id missing. Connect with metadata {"ga4_property_id": "properties/123456789"}',
        }
    return {"ok": True, "message": "Google credentials + GA4 property configured", "property_id": ga_property}
