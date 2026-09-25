CHAPTER_SYSTEM = """You create concise learning summaries using only the supplied book text.
Never invent facts or rely on outside knowledge. If the source is insufficient, say so.
Use plain text with these headings: Overview, Key ideas, Important concepts, What to remember."""

BOOK_SYSTEM = """You combine supplied chapter or section summaries into one grounded book summary.
Use only the supplied material and do not invent missing claims.
Use plain text with these headings: Overview, Key ideas, Important concepts, What to remember."""


def source_prompt(title: str, source: str, *, spoiler_free: bool) -> str:
    spoiler = (
        "This is fiction. Avoid revealing endings, twists, character fates, or later plot outcomes."
        if spoiler_free
        else "Preserve the important concepts and their relationships."
    )
    return f"Title: {title}\nConstraint: {spoiler}\n\nSOURCE\n{source}"


def merge_prompt(title: str, summaries: str, *, spoiler_free: bool) -> str:
    spoiler = (
        "Keep the result spoiler-free and do not add plot details absent from these summaries."
        if spoiler_free
        else "Combine overlaps without dropping distinct important concepts."
    )
    return f"Title: {title}\nConstraint: {spoiler}\n\nPARTIAL SUMMARIES\n{summaries}"
