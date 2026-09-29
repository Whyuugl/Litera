import argparse
import asyncio
import json
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.database import get_engine
from app.services import rag


async def evaluate(edition_id: uuid.UUID, fixture: Path, top_k: int) -> None:
    cases = json.loads(fixture.read_text(encoding="utf-8"))
    hits = 0
    with Session(get_engine(), expire_on_commit=False) as session:
        for case in cases:
            results = await rag.search(session, edition_id, case["question"], top_k=top_k)
            expected = case["expected"].lower()
            hit = any(
                expected in item["content"].lower()
                or expected in ((item["chapter"] or {}).get("title") or "").lower()
                for item in results
            )
            hits += hit
            print(f"{'HIT ' if hit else 'MISS'} | {case['question']}")
            for item in results:
                chapter = (item["chapter"] or {}).get("title", "Document")
                print(f"  {item['score']:.3f} | {chapter} | pages {item['page_start']}-{item['page_end']}")
    print(f"Hit@{top_k}: {hits}/{len(cases)} ({hits / len(cases):.1%})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Litera semantic retrieval with a small JSON fixture")
    parser.add_argument("edition_id", type=uuid.UUID)
    parser.add_argument("fixture", type=Path, help='JSON list of {"question": "...", "expected": "chapter or topic"}')
    parser.add_argument("--top-k", type=int, default=5, choices=range(1, 11))
    args = parser.parse_args()
    asyncio.run(evaluate(args.edition_id, args.fixture, args.top_k))
