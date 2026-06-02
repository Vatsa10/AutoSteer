"""Policy document generation using notion_export internally."""

import json

from src.integrations.notion import notion_export


POLICY_TEMPLATES = {
    "privacy": "# Privacy Policy\n\n## Data Collection\n{sections}\n\n## Contact\n{contact}",
    "security": "# Information Security Policy\n\n## Scope\n{sections}\n\n## Responsibilities\n{contact}",
    "acceptable_use": "# Acceptable Use Policy\n\n## Permitted Use\n{sections}\n\n## Violations\n{contact}",
}


async def policy_doc_generate(
    policy_type: str = "privacy",
    sections: str = "",
    contact: str = "legal@company.com",
    export_to_notion: bool = False,
    notion_title: str | None = None,
    session=None,
    workspace_id: str = "default",
    **_,
) -> str:
    template = POLICY_TEMPLATES.get(policy_type, POLICY_TEMPLATES["privacy"])
    content = template.format(sections=sections or "TBD — agent to fill based on company context.", contact=contact)
    title = notion_title or f"{policy_type.replace('_', ' ').title()} Policy Draft"

    result = {
        "type": "policy_draft",
        "policy_type": policy_type,
        "title": title,
        "content": content,
        "status": "draft",
        "note": "Review with legal counsel before publishing.",
    }

    if export_to_notion:
        notion_result = await notion_export(title, content, None, session, workspace_id)
        try:
            notion_data = json.loads(notion_result)
            result["notion_export"] = notion_data
        except json.JSONDecodeError:
            result["notion_export"] = notion_result

    return json.dumps(result, indent=2)
