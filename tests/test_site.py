from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
PRIVACY = (ROOT / "privacy" / "index.html").read_text(encoding="utf-8")
TERMS = (ROOT / "terms" / "index.html").read_text(encoding="utf-8")
ALL_PAGES = (INDEX, PRIVACY, TERMS)


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

    def test_pages_use_system_font_stack_only(self) -> None:
        expected_stack = '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif'
        for page in ALL_PAGES:
            font_stacks = re.findall(r"font-family:\s*([^;]+);", page)
            self.assertTrue(font_stacks)
            self.assertTrue(all(stack in (expected_stack, "inherit") for stack in font_stacks))
            for forbidden in ("@font-face", "fonts.googleapis", "fonts.gstatic", "font-display"):
                self.assertNotIn(forbidden, page)

    def test_home_has_trust_copy(self) -> None:
        self.assertRegex(INDEX, r"informational only", re.IGNORECASE)
        self.assertIn("Is Teslatlas affiliated with Tesla?", INDEX)
        self.assertNotIn('class="legal-note"', INDEX)

    def test_home_has_app_landing_sections(self) -> None:
        for section_id in ("features", "pricing", "faq"):
            self.assertIn(f'id="{section_id}"', INDEX)
        self.assertNotIn('id="how-it-works"', INDEX)
        self.assertNotIn("Connect. Sync. Read.", INDEX)

    def test_home_has_real_screenshot_gallery(self) -> None:
        shots = re.findall(r'assets/screens/[^"]+\.(?:png|jpg|jpeg|webp)', INDEX)
        self.assertGreaterEqual(len(shots), 4)
        gallery_match = re.search(r'<div class="screens"[\s\S]*?</div>', INDEX)
        self.assertIsNotNone(gallery_match)
        self.assertIn('/assets/screens/overview-20260602.webp', gallery_match.group(0).split('<figure class="screen-card">', 2)[1])

    def test_screenshot_section_has_stable_visual_bounds(self) -> None:
        self.assertRegex(INDEX, r"\.screen-card img \{[^}]*aspect-ratio: 1320 / 2868", re.DOTALL)
        self.assertIn("border-radius: 20px", INDEX)
        self.assertRegex(INDEX, r"\.preview \{[^}]*background: transparent;", re.DOTALL)
        self.assertNotRegex(INDEX, r"\.preview \{[^}]*border:", re.DOTALL)
        self.assertNotIn("<figcaption>", INDEX)

    def test_home_has_no_top_nav_download_button(self) -> None:
        self.assertNotIn('class="nav-cta"', INDEX)
        self.assertNotIn("See features", INDEX)
        self.assertRegex(INDEX, r"\.nav-links \{[^}]*justify-content: flex-end;", re.DOTALL)

    def test_home_hero_uses_one_screenshot(self) -> None:
        hero_match = re.search(r'<div class="hero-visual"[\s\S]*?</div>\s*</div>\s*</section>', INDEX)
        self.assertIsNotNone(hero_match)
        self.assertEqual(hero_match.group(0).count("<img "), 1)
        self.assertNotIn("preview-stack", INDEX)
        self.assertNotIn('class="eyebrow"', INDEX)
        self.assertNotIn("Version 3.1.1 live", INDEX)

    def test_home_brand_text_is_single_colour(self) -> None:
        self.assertIn("<span>Teslatlas</span>", INDEX)
        self.assertNotIn("Tesl<span>atlas</span>", INDEX)
        self.assertNotIn('class="accent"', INDEX)
        self.assertNotIn("Local-first TeslaMate viewer by Magrathean UK.", INDEX)

    def test_footer_copyright_logo_matches_app_icon_size(self) -> None:
        self.assertRegex(INDEX, r"\.brand img \{[^}]*width: 2rem;[^}]*height: 2rem;", re.DOTALL)
        self.assertRegex(INDEX, r"\.copyright img \{[^}]*width: 2rem;[^}]*height: 2rem;", re.DOTALL)
        self.assertNotRegex(INDEX, r"\.copyright \{[^}]*border-top:", re.DOTALL)
        footer = re.search(r"<footer>[\s\S]*?</footer>", INDEX).group(0)
        self.assertNotIn('aria-label="Teslatlas home"', footer)
        self.assertRegex(INDEX, r"\.footer-grid \{[^}]*grid-template-columns: repeat\(3, minmax\(0, 1fr\)\);", re.DOTALL)

    def test_home_pricing_uses_plain_platform_sentence(self) -> None:
        self.assertIn("7 day trial", INDEX)
        self.assertIn("$9.99 /year", INDEX)
        self.assertNotIn("Yearly", INDEX)
        self.assertNotIn("via App Store", INDEX)
        self.assertIn("Available on iPhone, iPad, and Mac.", INDEX)
        self.assertNotIn('class="check-list"', INDEX)
        self.assertNotIn('content: "✓"', INDEX)
        self.assertNotIn("Apple shows current price", INDEX)
        self.assertNotIn("The important limits are simple.", INDEX)
        self.assertNotIn('class="cta"', INDEX)
        self.assertNotIn("Make TeslaMate easier to read.", INDEX)

    def test_home_clarifies_no_automatic_diagnostics(self) -> None:
        self.assertIn("automatic crash diagnostics", INDEX)
        self.assertNotIn("Not by default. The app connects from your device to your configured source.", INDEX)

    def test_home_has_no_pill_shaped_ui(self) -> None:
        self.assertNotIn("999px", INDEX)
        self.assertNotIn('class="pill"', INDEX)
        self.assertNotIn("999px", PRIVACY)
        self.assertNotIn("999px", TERMS)

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

    def test_privacy_keeps_vehicle_data_boundaries(self) -> None:
        for token in (
            "Vehicle-data sensitivity",
            "Vehicle history can reveal precise locations",
            "Cloudflare Access credentials",
            "public share files",
            "unless you deliberately send material to us",
            "StoreKit and subscription state",
        ):
            self.assertIn(token, PRIVACY)
        self.assertNotIn("We do not collect, store, or share personal data from the App", PRIVACY)

    def test_terms_keep_public_subscription_and_safety_boundaries(self) -> None:
        self.assertIn("authorised review/test", TERMS)
        self.assertNotIn("development", TERMS)
        for token in (
            "Diagnostic information only",
            "Read-only TeslaMate posture",
            "Battery-health predictions",
            "not a diagnostic report",
            "does not write back to TeslaMate by default",
            "does not send Tesla vehicle commands",
            "Acceptable use",
            "access a TeslaMate database, MyTeslaMate endpoint, vehicle-history source, Cloudflare proxy, or API endpoint without authorisation",
            "bypass authentication, security controls, subscription controls, rate limits, or provider terms",
            "send or attempt to send Tesla commands through the app",
        ):
            self.assertIn(token, TERMS)

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
