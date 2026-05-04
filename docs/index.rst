ThornForge Documentation
========================

ThornForge builds versioned static documentation sites for Python projects. It
finds a repository's Sphinx sources, builds one or more documentation versions,
adds shared navigation and version-switching assets, and writes a ready-to-publish
site tree.

This documentation is organized as a manual first and a detailed API reference
second. The guide pages describe how to shape a source repository and publish
the generated output, while the API pages document the build pipeline modules
that make those workflows work.

Core capabilities
-----------------

- Build documentation from a local repository or a supported GitHub repository URL.
- Discover common Sphinx layouts such as ``docs/`` and ``docs/source/``.
- Build tagged releases under stable version paths.
- Publish a moving ``docs/latest`` alias to the newest build.
- Reuse canonical build outputs when different versions share identical inputs.
- Render top-level project files such as ``README.rst`` and ``CHANGELOG.rst`` as
  site pages.
- Publish an optional ``info/`` subtree as a lightweight project website.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   quickstart

.. toctree::
   :maxdepth: 2
   :caption: Guides

   guides/index

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api

.. toctree::
   :maxdepth: 1
   :caption: Documentation Infrastructure

   building

Highlights
----------

``thornforge.buildsite``
   Repository discovery, Git materialization, Sphinx builds, static site
   assembly, and runtime navigation metadata.

``thornforge.cli``
   Top-level command dispatch, terminal configuration, and dependency reporting.

``thornforge/assets/``
   Shared templates, stylesheets, and JavaScript copied into generated sites.

Project Status
--------------

The project metadata currently marks ThornForge as alpha-quality software. The
test suite is the most reliable source for expected behavior, and these docs are
based on the package implementation and regression tests in this repository.
