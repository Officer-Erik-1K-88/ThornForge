from __future__ import annotations
"""Regression tests for repository discovery and the generated site layout.

These tests build minimal temporary repositories so the generic build pipeline
can be validated without depending on this repository's own layout.
"""

import json
from pathlib import Path
import tempfile
import unittest

from thornforge.buildsite.build_site import build_versioned_site
from thornforge.buildsite.repository import discover_repository_profile


class BuildSystemTests(unittest.TestCase):
    """Exercise the generic build pipeline against minimal temporary repositories.

    The tests focus on repository discovery and end-to-end build output shape,
    especially the parts that were recently generalized away from project-
    specific assumptions.
    """

    def test_discover_repository_profile_prefers_nested_docs_source(self) -> None:
        """Verify repository discovery preserves a nested ``docs/source`` layout.

        The temporary repository declares a basic ``pyproject.toml`` and a Sphinx
        ``conf.py`` under ``docs/source``. The expected result is that
        ``discover_repository_profile`` points at that nested directory and uses
        the project metadata for naming and version defaults.
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            # Provide the minimum project metadata needed for profile discovery.
            (repo_root / "pyproject.toml").write_text(
                "[project]\nname = 'sample-project'\nversion = '1.2.3'\n",
                encoding="utf-8",
            )
            docs_source = repo_root / "docs" / "source"
            docs_source.mkdir(parents=True)
            # The presence of conf.py is what makes this directory a docs root candidate.
            (docs_source / "conf.py").write_text("project = 'sample-project'\n", encoding="utf-8")

            profile = discover_repository_profile(repo_root)

            self.assertEqual(profile.docs_dir, docs_source)
            self.assertEqual(profile.project_name, "sample-project")
            self.assertEqual(profile.default_version_name, "1.2.3")
            self.assertIn("docs/source", profile.input_paths)

    def test_build_versioned_site_builds_non_git_repo(self) -> None:
        """Verify a plain non-Git directory still produces a complete site.

        The test creates a minimal local repository with Sphinx docs and no Git
        metadata. It then builds the site and checks that shared assets, docs
        output, generated JSON metadata, symlinks, and rendered project pages
        all exist in the expected locations.
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            repo_root = workspace / "repo"
            output_dir = workspace / "site"
            docs_source = repo_root / "docs"
            docs_source.mkdir(parents=True)

            # Build a small repository fixture with one docs page and one project metadata page.
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

            # Site root assets should exist because ThornForge copies its full asset tree there.
            self.assertTrue((output_dir / ".nojekyll").exists())
            self.assertTrue((output_dir / "assets" / "style" / "variables.css").exists())
            self.assertTrue((output_dir / "assets" / "style" / "style.css").exists())
            self.assertTrue((output_dir / "assets" / "style" / "nav.css").exists())
            self.assertTrue((output_dir / "assets" / "style" / "version.css").exists())
            self.assertTrue((output_dir / "assets" / "scripts" / "top-nav.js").exists())
            # The docs version directory should contain built HTML plus its own copied asset tree.
            self.assertTrue((output_dir / "docs" / "1.2.3" / "index.html").exists())
            self.assertTrue((output_dir / "docs" / "1.2.3" / "assets" / "style" / "variables.css").exists())
            # The generated docs page should reference all shared CSS and JS assets.
            index_html = (output_dir / "docs" / "1.2.3" / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="assets/style/variables.css"', index_html)
            self.assertIn('href="assets/style/style.css"', index_html)
            self.assertIn('href="assets/style/nav.css"', index_html)
            self.assertIn('href="assets/style/version.css"', index_html)
            self.assertIn('src="assets/scripts/top-nav.js"', index_html)
            self.assertIn('src="assets/scripts/version-switcher.js"', index_html)
            self.assertIn('"project_name": "sample-project"', index_html)
            self.assertTrue((output_dir / "docs" / "latest").exists())
            self.assertTrue((output_dir / "docs" / "versions.json").exists())
            site_nav = json.loads((output_dir / "site-nav.json").read_text(encoding="utf-8"))
            self.assertEqual(site_nav["project_name"], "sample-project")
            self.assertTrue((output_dir / "changelog.html").exists())
            changelog_html = (output_dir / "changelog.html").read_text(encoding="utf-8")
            self.assertIn('<h1 class="title">Changelog</h1>', changelog_html)

    def test_build_versioned_site_does_not_inject_duplicate_runtime_scripts(self) -> None:
        """Verify project-provided docs scripts are not duplicated by ThornForge.

        Some repositories already ship their own ``top-nav.js`` and
        ``version-switcher.js`` in Sphinx ``html_js_files``. ThornForge should
        not inject a second copy of those runtimes under ``assets/scripts``.
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            repo_root = workspace / "repo"
            output_dir = workspace / "site"
            docs_source = repo_root / "docs"
            static_dir = docs_source / "_static"
            templates_dir = docs_source / "_templates"
            static_dir.mkdir(parents=True)
            templates_dir.mkdir(parents=True)

            (repo_root / "pyproject.toml").write_text(
                "[project]\nname = 'sample-project'\nversion = '1.2.3'\n",
                encoding="utf-8",
            )
            (docs_source / "conf.py").write_text(
                "project = 'sample-project'\n"
                "master_doc = 'index'\n"
                "extensions = []\n"
                "templates_path = ['_templates']\n"
                "html_static_path = ['_static']\n"
                "html_js_files = ['top-nav.js', 'version-switcher.js']\n"
                "html_sidebars = {'**': ['versions.html']}\n",
                encoding="utf-8",
            )
            (docs_source / "index.rst").write_text(
                "Sample Project\n==============\n\nHello from ThornForge.\n",
                encoding="utf-8",
            )
            (static_dir / "top-nav.js").write_text("console.log('project top nav');\n", encoding="utf-8")
            (static_dir / "version-switcher.js").write_text(
                "console.log('project version switcher');\n",
                encoding="utf-8",
            )
            (templates_dir / "versions.html").write_text(
                "<div id=\"version-switcher\"><select id=\"version-select\"></select></div>\n",
                encoding="utf-8",
            )

            build_versioned_site(repo_root, output_dir)

            index_html = (output_dir / "docs" / "1.2.3" / "index.html").read_text(encoding="utf-8")
            self.assertIn('_static/top-nav.js', index_html)
            self.assertIn('_static/version-switcher.js', index_html)
            self.assertNotIn('assets/scripts/top-nav.js', index_html)
            self.assertNotIn('assets/scripts/version-switcher.js', index_html)


if __name__ == "__main__":
    unittest.main()
