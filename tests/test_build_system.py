from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from thornforge.build_versioned_docs import build_versioned_site
from thornforge.repository import discover_repository_profile


class BuildSystemTests(unittest.TestCase):
    def test_discover_repository_profile_prefers_nested_docs_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "pyproject.toml").write_text(
                "[project]\nname = 'sample-project'\nversion = '1.2.3'\n",
                encoding="utf-8",
            )
            docs_source = repo_root / "docs" / "source"
            docs_source.mkdir(parents=True)
            (docs_source / "conf.py").write_text("project = 'sample-project'\n", encoding="utf-8")

            profile = discover_repository_profile(repo_root)

            self.assertEqual(profile.docs_dir, docs_source)
            self.assertEqual(profile.project_name, "sample-project")
            self.assertEqual(profile.default_version_name, "1.2.3")
            self.assertIn("docs/source", profile.input_paths)

    def test_build_versioned_site_builds_non_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            repo_root = workspace / "repo"
            output_dir = workspace / "site"
            docs_source = repo_root / "docs"
            docs_source.mkdir(parents=True)

            (repo_root / "pyproject.toml").write_text(
                "[project]\nname = 'sample-project'\nversion = '1.2.3'\n",
                encoding="utf-8",
            )
            (repo_root / "CHANGELOG.rst").write_text("Changelog\n=========\n", encoding="utf-8")
            (docs_source / "conf.py").write_text(
                "project = 'sample-project'\n"
                "master_doc = 'index'\n"
                "extensions = []\n",
                encoding="utf-8",
            )
            (docs_source / "index.rst").write_text(
                "Sample Project\n==============\n\nHello from ThornForge.\n",
                encoding="utf-8",
            )

            build_versioned_site(repo_root, output_dir)

            self.assertTrue((output_dir / ".nojekyll").exists())
            self.assertTrue((output_dir / "assets" / "style" / "variables.css").exists())
            self.assertTrue((output_dir / "assets" / "style" / "style.css").exists())
            self.assertTrue((output_dir / "assets" / "style" / "nav.css").exists())
            self.assertTrue((output_dir / "assets" / "style" / "version.css").exists())
            self.assertTrue((output_dir / "assets" / "scripts" / "top-nav.js").exists())
            self.assertTrue((output_dir / "docs" / "1.2.3" / "index.html").exists())
            self.assertTrue((output_dir / "docs" / "1.2.3" / "assets" / "style" / "variables.css").exists())
            index_html = (output_dir / "docs" / "1.2.3" / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="assets/style/variables.css"', index_html)
            self.assertIn('href="assets/style/style.css"', index_html)
            self.assertIn('href="assets/style/nav.css"', index_html)
            self.assertIn('href="assets/style/version.css"', index_html)
            self.assertIn('src="assets/scripts/top-nav.js"', index_html)
            self.assertIn('src="assets/scripts/version-switcher.js"', index_html)
            self.assertTrue((output_dir / "docs" / "latest").exists())
            self.assertTrue((output_dir / "docs" / "versions.json").exists())
            self.assertTrue((output_dir / "changelog.html").exists())


if __name__ == "__main__":
    unittest.main()
