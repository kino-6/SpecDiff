"""EML extractor."""

from __future__ import annotations

from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Iterable, List, Optional

from crossspec.claims import Authority
from crossspec.config import MailConfig
from crossspec.extract.base import ExtractedClaim, Extractor


class EmlExtractor(Extractor):
    def __init__(self, path: Path, authority: Authority, config: MailConfig) -> None:
        self.path = path
        self.authority = authority
        self.config = config

    def extract(self) -> Iterable[ExtractedClaim]:
        message = BytesParser(policy=policy.default).parsebytes(self.path.read_bytes())
        headers = {name: message.get(name) for name in self.config.include_headers}
        body, body_type = self._extract_body(message)
        provenance = {
            "message_id": message.get("Message-ID"),
            "from": message.get("From"),
            "to": message.get("To"),
            "date": message.get("Date"),
            "subject": message.get("Subject"),
            "body_type": body_type,
        }
        text_raw = self._format_text(headers, body)
        yield ExtractedClaim(
            text_raw=text_raw,
            source_type="eml",
            source_path=str(self.path),
            authority=self.authority,
            provenance=provenance,
        )

    @staticmethod
    def _format_text(headers: dict, body: str) -> str:
        header_lines = [f"{key}: {value}" for key, value in headers.items() if value]
        if header_lines:
            return "\n".join(header_lines + ["", body])
        return body

    @staticmethod
    def _extract_body(message) -> tuple[str, str]:
        if message.is_multipart():
            plain = EmlExtractor._find_part(message, "text/plain")
            if plain is not None:
                return plain, "text/plain"
            html = EmlExtractor._find_part(message, "text/html")
            if html is not None:
                return html, "text/html"
            return "", "unknown"
        return message.get_content() or "", message.get_content_type()

    @staticmethod
    def _find_part(message, mime_type: str) -> Optional[str]:
        for part in message.walk():
            if part.get_content_type() == mime_type:
                return part.get_content() or ""
        return None
