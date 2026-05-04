Build Orchestration
===================

Module: :mod:`thornforge.buildsite.build_site`

Overview
--------

This module coordinates the full static site build: source materialization,
repository discovery, version selection, Sphinx builds, asset injection, site
page rendering, and runtime metadata embedding.

Important API
-------------

``build_versioned_site(source, output_dir)``
   Build a complete static site from a local repository path or supported GitHub
   URL into ``output_dir``.

``collect_build_versions(repo_root, default_version_name, is_git_repo)``
   Return the ordered documentation versions ThornForge should build.

``collect_tags(repo_root)``
   Return matching release tags sorted by PEP 440 version rules.

Autodoc
-------

.. automodule:: thornforge.buildsite.build_site
   :no-index:
   :members:
   :undoc-members:
