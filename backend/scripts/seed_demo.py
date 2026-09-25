from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_engine
from app.core.security import hash_password
from app.models import (
    Author,
    Book,
    BookCopy,
    BookStatus,
    BookType,
    Category,
    Edition,
    Loan,
    LoanStatus,
    Membership,
    MembershipStatus,
    Reservation,
    ReservationStatus,
    User,
    UserRole,
)
from app.schemas.circulation import CheckoutRequest, ReservationCreate
from app.services.circulation import checkout, create_reservation


PASSWORD = "LiteraDemo123!"


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


def book(
    session: Session,
    admin: User,
    category: Category,
    author: Author,
    *,
    title: str,
    slug: str,
    isbn: str,
    barcode: str,
    cover_url: str,
) -> tuple[Book, Edition, BookCopy]:
    item = session.scalar(select(Book).where(Book.slug == slug))
    if not item:
        item = Book(
            category=category,
            authors=[author],
            title=title,
            slug=slug,
            description="A demo title for exploring Litera's online reading and learning experience.",
            language="en",
            cover_url=cover_url,
            book_type=BookType.EDUCATIONAL,
            status=BookStatus.PUBLISHED,
            created_by=admin.id,
        )
        session.add(item)
        session.flush()
    item.description = "A demo title for exploring Litera's online reading and learning experience."
    edition = session.scalar(select(Edition).where(Edition.isbn == isbn))
    if not edition:
        edition = Edition(
            book_id=item.id,
            isbn=isbn,
            publisher="Litera Demo Press",
            edition_number="1",
            publication_year=2024,
            language="en",
        )
        session.add(edition)
        session.flush()
    copy = session.scalar(select(BookCopy).where(BookCopy.barcode == barcode))
    if not copy:
        copy = BookCopy(edition_id=edition.id, barcode=barcode, shelf_location="DEMO-A1")
        session.add(copy)
    session.commit()
    return item, edition, copy


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

        category = session.scalar(select(Category).where(Category.slug == "demo-learning"))
        if not category:
            category = Category(name="Demo Learning", slug="demo-learning", description="Books used for the local Litera demo.")
            session.add(category)
        author = session.scalar(select(Author).where(Author.name == "Litera Demo Author"))
        if not author:
            author = Author(name="Litera Demo Author", bio="A local development author.")
            session.add(author)
        session.commit()

        _, clean_edition, _ = book(
            session, admin, category, author,
            title="Clean Code", slug="demo-clean-code", isbn="DEMO-9780132350884",
            barcode="LIT-DEMO-001", cover_url="https://covers.openlibrary.org/b/isbn/9780132350884-L.jpg",
        )
        _, atomic_edition, atomic_copy = book(
            session, admin, category, author,
            title="Atomic Habits", slug="demo-atomic-habits", isbn="DEMO-9780735211292",
            barcode="LIT-DEMO-002", cover_url="https://covers.openlibrary.org/b/isbn/9780735211292-L.jpg",
        )
        book(
            session, admin, category, author,
            title="The Little Prince", slug="demo-little-prince", isbn="DEMO-9780156012195",
            barcode="LIT-DEMO-003", cover_url="https://covers.openlibrary.org/b/isbn/9780156012195-L.jpg",
        )

        active_loan = session.scalar(
            select(Loan).where(
                Loan.user_id == member.id,
                Loan.book_copy_id == atomic_copy.id,
                Loan.status.in_([LoanStatus.BORROWED, LoanStatus.OVERDUE]),
            )
        )
        if not active_loan:
            checkout(
                session,
                CheckoutRequest(user_id=member.id, book_copy_id=atomic_copy.id),
                admin,
            )
        active_reservation = session.scalar(
            select(Reservation).where(
                Reservation.user_id == member.id,
                Reservation.edition_id == clean_edition.id,
                Reservation.status.in_([ReservationStatus.WAITING, ReservationStatus.READY]),
            )
        )
        if not active_reservation:
            create_reservation(session, ReservationCreate(edition_id=clean_edition.id), member)

    print("Demo data ready: admin.demo@example.com, member.demo@example.com, user.demo@example.com")
    print(f"Password for all demo accounts: {PASSWORD}")


if __name__ == "__main__":
    main()
