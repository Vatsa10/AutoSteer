from string import Formatter
from pydantic import BaseModel, Field, field_validator


class PromptTemplate(BaseModel):
    template: str
    allowed_placeholders: list[str] = ["text"]
    required_placeholders: list[str] = []

    @field_validator("template")
    @classmethod
    def validate_placeholders(cls, v, info):
        allowed = set(info.data.get("allowed_placeholders", ["text"]))
        fields = {fn for _, fn, _, _ in Formatter().parse(v) if fn is not None}
        unsupported = fields - allowed
        if unsupported:
            raise ValueError(
                f"unsupported placeholder(s): {', '.join(sorted(unsupported))}"
            )
        required = set(info.data.get("required_placeholders", []))
        missing = required - fields
        if missing:
            raise ValueError(
                f"missing required placeholder(s): {', '.join(sorted(missing))}"
            )
        return v

    def render(self, **kwargs) -> str:
        return self.template.format(**kwargs)
