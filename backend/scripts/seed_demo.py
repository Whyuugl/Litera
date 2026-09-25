from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO
from textwrap import wrap
from urllib.request import Request, urlopen

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

from app.core.database import get_engine
from app.core.security import hash_password
from app.models import (
    AccessLevel,
    Author,
    Book,
    BookCopy,
    BookStatus,
    BookType,
    Category,
    DigitalFile,
    DocumentPage,
    Edition,
    Loan,
    LoanStatus,
    Membership,
    MembershipStatus,
    ProcessingStatus,
    Reservation,
    ReservationStatus,
    User,
    UserRole,
)
from app.schemas.circulation import CheckoutRequest, ReservationCreate
from app.services import digital
from app.services.circulation import checkout, create_reservation
from app.services.storage import storage


PASSWORD = "LiteraDemo123!"
GUTENBERG_TEXT = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
GUTENBERG_COVER = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.cover.medium.jpg"
SEED_FORMAT = 3


@dataclass(frozen=True)
class PublicDomainBook:
    gutenberg_id: int
    title: str
    slug: str
    author: str
    category: str
    book_type: BookType
    publication_year: int | None
    description: str


LIBRARY = (
    PublicDomainBook(11, "Alice's Adventures in Wonderland", "alice-in-wonderland", "Lewis Carroll", "Classic Fiction", BookType.FICTION, 1865, "Alice follows a white rabbit into a playful world ruled by curious logic."),
    PublicDomainBook(1342, "Pride and Prejudice", "pride-and-prejudice", "Jane Austen", "Classic Fiction", BookType.FICTION, 1813, "Elizabeth Bennet and Mr. Darcy confront pride, judgment, class, and love."),
    PublicDomainBook(1661, "The Adventures of Sherlock Holmes", "adventures-of-sherlock-holmes", "Arthur Conan Doyle", "Classic Fiction", BookType.FICTION, 1892, "Twelve mysteries showcasing Sherlock Holmes's observation and deduction."),
    PublicDomainBook(84, "Frankenstein", "frankenstein", "Mary Wollstonecraft Shelley", "Classic Fiction", BookType.FICTION, 1818, "A scientist creates life and faces the human cost of ambition and rejection."),
    PublicDomainBook(345, "Dracula", "dracula", "Bram Stoker", "Classic Fiction", BookType.FICTION, 1897, "Letters and journals chronicle the struggle against Count Dracula."),
    PublicDomainBook(35, "The Time Machine", "the-time-machine", "H. G. Wells", "Classic Fiction", BookType.FICTION, 1895, "A Victorian inventor journeys into humanity's distant future."),
    PublicDomainBook(55, "The Wonderful Wizard of Oz", "wonderful-wizard-of-oz", "L. Frank Baum", "Classic Fiction", BookType.FICTION, 1900, "Dorothy and her companions cross Oz in search of home, courage, heart, and wisdom."),
    PublicDomainBook(46, "A Christmas Carol", "a-christmas-carol", "Charles Dickens", "Classic Fiction", BookType.FICTION, 1843, "Ebenezer Scrooge is challenged to reconsider how he lives and treats others."),
    PublicDomainBook(2701, "Moby-Dick", "moby-dick", "Herman Melville", "Classic Fiction", BookType.FICTION, 1851, "Ishmael recounts Captain Ahab's relentless pursuit of the white whale."),
    PublicDomainBook(1497, "The Republic", "the-republic", "Plato", "Philosophy", BookType.EDUCATIONAL, None, "A foundational dialogue about justice, education, leadership, and society."),
    PublicDomainBook(132, "The Art of War", "the-art-of-war", "Sun Tzu", "Philosophy", BookType.EDUCATIONAL, None, "A classic study of strategy, preparation, leadership, and conflict."),
    PublicDomainBook(1228, "On the Origin of Species", "on-the-origin-of-species", "Charles Darwin", "Science & Nature", BookType.EDUCATIONAL, 1859, "Darwin presents the evidence and reasoning behind evolution by natural selection."),
    PublicDomainBook(205, "Walden", "walden", "Henry David Thoreau", "Philosophy", BookType.NON_FICTION, 1854, "Reflections on simple living, nature, work, and individual purpose."),
    PublicDomainBook(23, "Narrative of the Life of Frederick Douglass", "narrative-frederick-douglass", "Frederick Douglass", "History & Society", BookType.NON_FICTION, 1845, "Douglass's autobiography bears witness to slavery and the pursuit of freedom."),
    PublicDomainBook(1404, "The Federalist Papers", "the-federalist-papers", "Alexander Hamilton, John Jay, and James Madison", "History & Society", BookType.REFERENCE, 1788, "Essays explaining and defending the proposed United States Constitution."),
    PublicDomainBook(408, "The Souls of Black Folk", "the-souls-of-black-folk", "W. E. B. Du Bois", "History & Society", BookType.NON_FICTION, 1903, "Essays examining race, citizenship, education, and life after emancipation."),
)


def _pdf_escape(value: str) -> bytes:
    return value.encode("cp1252", "replace").replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _make_pdf(text: str) -> tuple[bytes, int]:
    pages = _text_pages(text)
    page_lines = [page.splitlines() for page in pages]
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman /Encoding /WinAnsiEncoding >>",
    }
    kids = []
    for index, lines in enumerate(page_lines):
        page_id = 4 + index * 2
        content_id = page_id + 1
        kids.append(f"{page_id} 0 R")
        content = b"BT\n/F1 10 Tf\n48 748 Td\n12 TL\n" + b"\n".join(
            b"(" + _pdf_escape(line) + b") Tj\nT*" for line in lines
        ) + b"\nET"
        objects[page_id] = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode()
        objects[content_id] = f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream"
    objects[2] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>".encode()

    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id in range(1, max(objects) + 1):
        offsets.append(len(document))
        document.extend(f"{object_id} 0 obj\n".encode() + objects[object_id] + b"\nendobj\n")
    xref = len(document)
    document.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    document.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    document.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(document), len(pages)


def _text_pages(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.expandtabs(4).splitlines():
        lines.extend(wrap(raw.strip(), width=88, replace_whitespace=True) or [""])
    return ["\n".join(lines[index:index + 54]) for index in range(0, len(lines), 54)] or [""]


def _store_source_text(session: Session, file_id, text: str) -> int:
    source_pages = _text_pages(text)
    pages = list(session.scalars(
        select(DocumentPage)
        .where(DocumentPage.digital_file_id == file_id)
        .order_by(DocumentPage.page_number)
    ).all())
    if len(pages) != len(source_pages):
        raise RuntimeError("Extracted page count does not match source pagination")
    for page, content in zip(pages, source_pages):
        page.content = content
    session.commit()
    return len(source_pages)


def _download_text(gutenberg_id: int) -> str:
    request = Request(
        GUTENBERG_TEXT.format(id=gutenberg_id),
        headers={"User-Agent": "Litera local development seed (https://github.com/Whyuugl/Litera)"},
    )
    with urlopen(request, timeout=60) as response:
        return response.read(10 * 1024 * 1024).decode("utf-8-sig", "replace")


def user(session: Session, email: str, name: str, role: UserRole = UserRole.USER) -> User:
    account = session.scalar(select(User).where(User.email == email))
    if not account:
        account = User(name=name, email=email, password_hash="", role=role)
        session.add(account)
    account.name = name
    account.role = role
    account.is_active = True
    account.password_hash = hash_password(PASSWORD)
    session.commit()
    return account


def _category(session: Session, name: str) -> Category:
    slug = name.lower().replace(" & ", "-").replace(" ", "-")
    item = session.scalar(select(Category).where(Category.slug == slug))
    if not item:
        item = Category(name=name, slug=slug, description=f"Public-domain titles in {name.lower()}.")
        session.add(item)
        session.flush()
    return item


def _author(session: Session, name: str) -> Author:
    item = session.scalar(select(Author).where(Author.name == name))
    if not item:
        item = Author(name=name, bio="Author of works available in the public domain.")
        session.add(item)
        session.flush()
    return item


def _seed_book(session: Session, admin: User, spec: PublicDomainBook, number: int) -> tuple[Edition, BookCopy]:
    item = session.scalar(select(Book).where(Book.slug == spec.slug))
    category = _category(session, spec.category)
    author = _author(session, spec.author)
    if not item:
        item = Book(slug=spec.slug, created_by=admin.id)
        session.add(item)
    item.category = category
    item.authors = [author]
    item.title = spec.title
    item.description = f"{spec.description} Full public-domain text supplied by Project Gutenberg."
    item.language = "en"
    item.cover_url = GUTENBERG_COVER.format(id=spec.gutenberg_id)
    item.book_type = spec.book_type
    item.status = BookStatus.PUBLISHED
    session.flush()

    isbn = f"PG-{spec.gutenberg_id}"
    edition = session.scalar(select(Edition).where(Edition.isbn == isbn))
    if not edition:
        edition = Edition(book_id=item.id, isbn=isbn)
        session.add(edition)
    edition.publisher = "Project Gutenberg"
    edition.edition_number = "Public domain digital edition"
    edition.publication_year = spec.publication_year
    edition.language = "en"
    session.flush()

    barcode = f"LIT-PD-{number:03d}"
    copy = session.scalar(select(BookCopy).where(BookCopy.barcode == barcode))
    if not copy:
        shelf = f"{spec.category[:3].upper()}-{number:02d}"
        copy = BookCopy(edition_id=edition.id, barcode=barcode, shelf_location=shelf, condition="Good")
        session.add(copy)
    session.commit()

    filename = f"{spec.slug}-reader-v{SEED_FORMAT}.pdf"
    file = session.scalar(select(DigitalFile).where(DigitalFile.edition_id == edition.id))
    if not file or file.processing_status != ProcessingStatus.READY:
        if file:
            digital.delete_file(session, file.id)
        print(f"Downloading {spec.title}...")
        source = _download_text(spec.gutenberg_id)
        pdf, page_count = _make_pdf(source)
        upload = UploadFile(
            BytesIO(pdf),
            filename=filename,
            headers=Headers({"content-type": "application/pdf"}),
        )
        file = digital.upload_pdf(session, edition.id, upload, AccessLevel.PUBLIC, True, admin)
        edition.page_count = _store_source_text(session, file.id, source)
        session.commit()
    elif file.original_filename != filename and file.storage_key:
        print(f"Refreshing typography for {spec.title}...")
        source = _download_text(spec.gutenberg_id)
        pdf, page_count = _make_pdf(source)
        if edition.page_count != page_count:
            raise RuntimeError(f"Page count changed while refreshing {spec.title}")
        storage.path(file.storage_key).write_bytes(pdf)
        file.original_filename = filename
        file.file_size = len(pdf)
        _store_source_text(session, file.id, source)
        session.commit()
    return edition, copy


def main() -> None:
    now = datetime.now(timezone.utc)
    with Session(get_engine(), expire_on_commit=False) as session:
        for old, new in {
            "admin@litera.local": "admin.demo@example.com",
            "member@litera.local": "member.demo@example.com",
            "user@litera.local": "user.demo@example.com",
        }.items():
            account = session.scalar(select(User).where(User.email == old))
            if account:
                account.email = new
        session.commit()

        admin = user(session, "admin.demo@example.com", "Litera Admin", UserRole.ADMIN)
        member = user(session, "member.demo@example.com", "Maya Member")
        user(session, "user.demo@example.com", "Raka Reader")

        membership = session.scalar(select(Membership).where(Membership.user_id == member.id))
        if not membership:
            membership = Membership(user_id=member.id)
            session.add(membership)
        membership.status = MembershipStatus.ACTIVE
        membership.member_number = "LIT-DEMO-001"
        membership.approved_at = now
        membership.approved_by = admin.id
        membership.expires_at = now + timedelta(days=365)
        membership.rejection_reason = None
        membership.suspension_reason = None

        old_demos = session.scalars(select(Book).where(Book.slug.in_({
            "demo-clean-code", "demo-atomic-habits", "demo-little-prince",
        }))).all()
        for item in old_demos:
            item.status = BookStatus.ARCHIVED
        session.commit()

        seeded = [_seed_book(session, admin, spec, index) for index, spec in enumerate(LIBRARY, 1)]
        _, loan_copy = seeded[0]
        reservation_edition, _ = seeded[1]
        active_loan = session.scalar(select(Loan).where(
            Loan.user_id == member.id,
            Loan.book_copy_id == loan_copy.id,
            Loan.status.in_([LoanStatus.BORROWED, LoanStatus.OVERDUE]),
        ))
        if not active_loan:
            checkout(session, CheckoutRequest(user_id=member.id, book_copy_id=loan_copy.id), admin)
        active_reservation = session.scalar(select(Reservation).where(
            Reservation.user_id == member.id,
            Reservation.edition_id == reservation_edition.id,
            Reservation.status.in_([ReservationStatus.WAITING, ReservationStatus.READY]),
        ))
        if not active_reservation:
            create_reservation(session, ReservationCreate(edition_id=reservation_edition.id), member)

    print(f"Demo ready with {len(LIBRARY)} readable public-domain books.")
    print("Accounts: admin.demo@example.com, member.demo@example.com, user.demo@example.com")
    print(f"Password for all demo accounts: {PASSWORD}")


if __name__ == "__main__":
    main()
