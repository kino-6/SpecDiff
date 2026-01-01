"""Configuration loading for CrossSpec."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional
from crossspec.pydantic_compat import BaseModel, Field, field_validator

from crossspec.yaml_utils import load_yaml


class ProjectConfig(BaseModel):
    name: str
    repo_root: str


class OutputConfig(BaseModel):
    claims_dir: str
    jsonl_filename: str


class XlsxTableConfig(BaseModel):
    sheet: str
    text_columns: List[str]
    authority_by: Optional[Dict[str, Dict[str, str]]] = None


class XlsxConfig(BaseModel):
    tables: List[XlsxTableConfig]


class PptxConfig(BaseModel):
    unit: Literal["slide"] = "slide"
    include_notes: bool = False


class MailConfig(BaseModel):
    include_headers: List[str] = Field(default_factory=list)


class KnowledgeSource(BaseModel):
    name: str
    type: Literal["pdf", "xlsx", "pptx", "eml"]
    authority: Literal[
        "normative",
        "approved_interpretation",
        "informative",
        "unverified",
    ]
    paths: List[str]
    xlsx: Optional[XlsxConfig] = None
    pptx: Optional[PptxConfig] = None
    mail: Optional[MailConfig] = None


class TaggingOutput(BaseModel):
    facets_key: str = "facets"


class TaggingLlm(BaseModel):
    model: str
    base_url: str
    api_key: str
    temperature: float = 0.0


class TaggingConfig(BaseModel):
    enabled: bool = False
    provider: Literal["llm"] = "llm"
    taxonomy_path: str
    llm: TaggingLlm
    output: TaggingOutput = TaggingOutput()


class CrossspecConfig(BaseModel):
    version: int
    project: ProjectConfig
    outputs: OutputConfig
    knowledge_sources: List[KnowledgeSource]
    tagging: Optional[TaggingConfig] = None

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError("Only version 1 config is supported")
        return value


def load_config(path: str) -> CrossspecConfig:
    payload = load_yaml(path)
    return CrossspecConfig(**_coerce_payload(payload))


def _coerce_payload(payload: dict) -> dict:
    project = payload.get("project")
    if isinstance(project, dict):
        payload["project"] = ProjectConfig(**project)
    outputs = payload.get("outputs")
    if isinstance(outputs, dict):
        payload["outputs"] = OutputConfig(**outputs)
    sources = []
    for source in payload.get("knowledge_sources", []):
        if not isinstance(source, dict):
            sources.append(source)
            continue
        xlsx = source.get("xlsx")
        if isinstance(xlsx, dict) and "tables" in xlsx:
            tables = [XlsxTableConfig(**table) for table in xlsx.get("tables", [])]
            source["xlsx"] = XlsxConfig(tables=tables)
        pptx = source.get("pptx")
        if isinstance(pptx, dict):
            source["pptx"] = PptxConfig(**pptx)
        mail = source.get("mail")
        if isinstance(mail, dict):
            source["mail"] = MailConfig(**mail)
        sources.append(KnowledgeSource(**source))
    payload["knowledge_sources"] = sources
    tagging = payload.get("tagging")
    if isinstance(tagging, dict):
        llm = tagging.get("llm")
        if isinstance(llm, dict):
            tagging["llm"] = TaggingLlm(**llm)
        output = tagging.get("output")
        if isinstance(output, dict):
            tagging["output"] = TaggingOutput(**output)
        payload["tagging"] = TaggingConfig(**tagging)
    return payload
