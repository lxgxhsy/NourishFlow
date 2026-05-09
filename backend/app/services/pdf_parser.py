from dataclasses import dataclass

import pdfplumber


@dataclass
class Section:
    text: str
    page_number: int
    section_title: str | None = None


def parse_pdf(path: str) -> list[Section]:
    sections = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text:
                sections.append(Section(text=text, page_number=i))
    return sections
