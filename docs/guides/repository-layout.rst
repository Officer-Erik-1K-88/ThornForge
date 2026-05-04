Repository Layout
=================

ThornForge is designed to build other repositories without requiring a
ThornForge-specific configuration file. Discovery is based on conventional file
locations and project metadata.

Documentation source discovery
------------------------------

The builder searches for a Sphinx ``conf.py`` in this order:

1. ``docs/``
2. ``docs/source/``
3. ``doc/``
4. ``doc/source/``
5. ``documentation/``
6. ``documentation/source/``

If none of those paths contains ``conf.py``, ThornForge recursively searches for
the shallowest remaining ``conf.py`` while skipping transient directories such as
``.git``, virtual environments, build outputs, and caches.

Project name discovery
----------------------

The display name comes from the first available source:

1. ``[project].name`` in ``pyproject.toml``
2. ``[tool.poetry].name`` in ``pyproject.toml``
3. ``name`` in ``package.json``
4. The repository directory name

Version discovery
-----------------

Git repositories are built from tags matching ``v*`` when such tags exist. Tags
are sorted using PEP 440 version parsing after the leading ``v`` is removed.

Repositories without matching tags get one build using a fallback label:

1. ``[project].version`` in ``pyproject.toml``
2. ``git describe --tags --always``
3. ``current``

Project pages
-------------

Known top-level metadata files are rendered as root-level pages in the generated
site. Supported candidates include ``README.rst``, ``README.txt``,
``README.html``, ``CHANGELOG.rst``, ``HISTORY.rst``, and ``RELEASES.rst``.
