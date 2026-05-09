from dataclasses import dataclass

from app.services.pdf_parser import Section


@dataclass
class Chunk:
    content: str
    chunk_index: int
    page_number: int
    section_title: str | None = None


def chunk_sections(sections: list[Section], chunk_size: int = 800, overlap: int = 100) -> list[Chunk]:
    # 合并所有页文本，记录每页起始 offset
    full_text = ""
    page_offsets: list[tuple[int, int]] = []  # (start_offset, page_number)
    for s in sections:
        page_offsets.append((len(full_text), s.page_number))
        full_text += s.text + "\n"

    if not full_text.strip():
        return []

    step = chunk_size - overlap  # 700
    chunks = []
    chunk_index = 0

    for chunk_start in range(0, len(full_text), step):
        chunk_text = full_text[chunk_start : chunk_start + chunk_size]
        if not chunk_text.strip():
            continue

        # 找 chunk_start 落在哪一页
        page = 1
        section_title = None
        for offset, p in page_offsets:
            if offset <= chunk_start:
                page = p
            else:
                break

        chunks.append(Chunk(
            content=chunk_text.strip(),
            chunk_index=chunk_index,
            page_number=page,
            section_title=section_title,
        ))
        chunk_index += 1

    return chunks
