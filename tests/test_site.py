from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
PRIVACY = (ROOT / "privacy" / "index.html").read_text(encoding="utf-8")
TERMS = (ROOT / "terms" / "index.html").read_text(encoding="utf-8")


class SiteTests(unittest.TestCase):
    def test_home_has_social_metadata(self) -> None:
        for token in (
            'property="og:title"',
            'property="og:description"',
            'property="og:image"',
            'name="twitter:card"',
        ):
            self.assertIn(token, INDEX)

    def test_home_has_structured_data(self) -> None:
        self.assertIn('type="application/ld+json"', INDEX)
        self.assertIn('"@type": "SoftwareApplication"', INDEX)

    def test_home_has_trust_copy(self) -> None:
        self.assertRegex(INDEX, r"not affiliated", re.IGNORECASE)
        self.assertRegex(INDEX, r"informational only", re.IGNORECASE)

    def test_home_has_app_landing_sections(self) -> None:
        for section_id in ("features", "how-it-works", "pricing", "faq"):
            self.assertIn(f'id="{section_id}"', INDEX)

    def test_home_has_real_screenshot_gallery(self) -> None:
        shots = re.findall(r'assets/screens/[^"]+\.(?:png|jpg|jpeg|webp)', INDEX)
        self.assertGreaterEqual(len(shots), 4)

    def test_screenshot_section_has_stable_visual_bounds(self) -> None:
        self.assertIn("object-fit: cover;", INDEX)
        self.assertRegex(INDEX, r"\.screen-card img \{[^}]*height: clamp", re.DOTALL)

    def test_home_has_no_template_references(self) -> None:
        for forbidden in ("AppNest", "pawantech12", "Modern Life", "Lorem"):
            self.assertNotIn(forbidden, INDEX)

    def test_home_uses_en_gb(self) -> None:
        self.assertIn('<html lang="en-GB">', INDEX)

    def test_legal_pages_have_specific_descriptions(self) -> None:
        self.assertIn("privacy policy", PRIVACY.lower())
        self.assertIn("terms of service", TERMS.lower())
        self.assertNotEqual(
            re.search(r'<meta name="description" content="([^"]+)"', PRIVACY).group(1),
            re.search(r'<meta name="description" content="([^"]+)"', TERMS).group(1),
        )

    def test_robots_and_sitemap_exist(self) -> None:
        robots = ROOT / "robots.txt"
        sitemap = ROOT / "sitemap.txt"
        self.assertTrue(robots.exists())
        self.assertTrue(sitemap.exists())
        self.assertIn("Sitemap: https://teslatlas.eu/sitemap.txt", robots.read_text(encoding="utf-8"))
        sitemap_text = sitemap.read_text(encoding="utf-8")
        self.assertIn("https://teslatlas.eu/", sitemap_text)
        self.assertIn("https://teslatlas.eu/privacy/", sitemap_text)
        self.assertIn("https://teslatlas.eu/terms/", sitemap_text)


if __name__ == "__main__":
    unittest.main()
