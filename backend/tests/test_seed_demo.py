import unittest
from io import BytesIO

from pypdf import PdfReader

from scripts.seed_demo import LIBRARY, _make_pdf


class DemoLibraryTests(unittest.TestCase):
    def test_public_domain_catalog_and_pdf_generation(self):
        self.assertGreaterEqual(len(LIBRARY), 12)
        self.assertEqual(len({book.slug for book in LIBRARY}), len(LIBRARY))

        document, page_count = _make_pdf("A real first page.\n" * 60)
        reader = PdfReader(BytesIO(document))

        self.assertEqual(len(reader.pages), page_count)
        self.assertIn("A real first page.", reader.pages[0].extract_text())


if __name__ == "__main__":
    unittest.main()
