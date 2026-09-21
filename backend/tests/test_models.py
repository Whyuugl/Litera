import unittest

from sqlalchemy.orm import configure_mappers

from app.core.database import Base
import app.models  # noqa: F401


class ModelConfigurationTest(unittest.TestCase):
    def test_phase_three_metadata_and_mappers(self) -> None:
        configure_mappers()
        self.assertEqual(
            set(Base.metadata.tables),
            {
                "users",
                "memberships",
                "categories",
                "authors",
                "books",
                "book_authors",
                "editions",
                "digital_files",
                "book_copies",
                "refresh_sessions",
            },
        )


if __name__ == "__main__":
    unittest.main()
