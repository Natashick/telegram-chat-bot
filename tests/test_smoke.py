# test_smoke.py
import os
import asyncio

from vector_store import vector_store
from retrieval import get_best_chunks_for_document, build_combined_excerpts


def list_pdfs(pdf_root: str) -> list[str]:
    try:
        return [
            os.path.join(pdf_root, f)
            for f in os.listdir(pdf_root)
            if f.lower().endswith(".pdf")
        ]
    except Exception:
        return []


async def main() -> None:
    pdf_root = os.getenv("PDF_DIR", "/app/pdfs")
    if not os.path.isdir(pdf_root):
        pdf_root = "/app/pdfs"

    pdfs = list_pdfs(pdf_root)
    print("PDFS:", pdfs)

    info = vector_store.get_document_info()
    print("INFO:", info)

    missing = [p for p in pdfs if not vector_store.has_document(p)]
    print("MISSING_INDEX:", len(missing), missing[:3])

    queries = [
        "was ist das ISO/SAE 21434?",
        "was ist das RASIC?",
        "was ist das CAN?",
        "was ist das CAN-FD?",
        "G20",
        "ISO 9001",
    ]

    for q in queries:
        all_chunks = []
        for doc in pdfs:
            try:
                ch = await get_best_chunks_for_document(q, doc, max_chunks=6)
            except Exception:
                ch = []
            if ch:
                all_chunks.extend(ch)

        # deduplicate
        seen = set()
        uniq = []
        for c in all_chunks:
            key = f"{c.get('chunk_id')}|{(c.get('text') or '')[:32]}"
            if key in seen:
                continue
            seen.add(key)
            uniq.append(c)

        top = sorted(uniq, key=lambda x: x.get("similarity_score", 0.0), reverse=True)[
            :6
        ]
        excerpt = build_combined_excerpts(top) if top else ""

        print("----")
        print("Q:", q)
        print("CHUNKS:", len(top), "EXCERPT_LEN:", len(excerpt))
        if top:
            preview = excerpt[:400].replace("\n", " ")
            if len(excerpt) > 400:
                preview += "…"
            print("EXCERPT_PREVIEW:", preview)
        else:
            print("NOINFO")


if __name__ == "__main__":
    asyncio.run(main())

