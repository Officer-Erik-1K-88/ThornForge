ThornForge
==========

ThornForge builds versioned static documentation sites for Python projects.
It discovers a repository's Sphinx documentation, builds one or more versions,
adds shared navigation and version-switching assets, and writes a static site
tree that can be published directly.

The tool is intended for projects that already keep documentation in Sphinx but
want a repeatable site layout with version aliases, shared styling, project
metadata pages, and lightweight GitHub Pages-friendly output.

Features
--------

- Build documentation from a local repository or a supported GitHub repository
  URL.
- Discover common Sphinx layouts such as ``docs/`` and ``docs/source/``.
- Build tagged releases under stable ``docs/<version>/`` paths.
- Publish a moving ``docs/latest`` alias to the newest build.
- Reuse canonical build outputs when different versions produce identical
  documentation inputs.
- Render top-level project files such as ``README.rst`` and ``CHANGELOG.rst``
  as root-level site pages.
- Publish an optional ``info/`` subtree as a lightweight project website.
- Copy bundled CSS, JavaScript, and templates into generated sites so the
  output is self-contained.

Project Status
--------------

ThornForge is currently alpha-quality software. The package metadata marks it
as ``Development Status :: 3 - Alpha``. The public CLI and generated output
layout are usable, but they may still change while the project settles.

Requirements
------------

ThornForge requires Python 3.12 or newer.

Runtime dependencies are declared in ``pyproject.toml`` and include:

- Sphinx
- docutils
- packaging
- rich
- requests
- id

Installation
------------

Install from a local checkout in editable mode:

.. code-block:: console

   python -m pip install -e .

Install the development/build dependencies used by this repository:

.. code-block:: console

   python -m pip install -r requirements.txt

Verify that the command is available:

.. code-block:: console

   thornforge --version

Quickstart
----------

Build this repository's documentation site into a temporary output directory:

.. code-block:: console

   thornforge buildsite --source . --output /tmp/thornforge-site

Open ``/tmp/thornforge-site/index.html`` after the build completes.

Build another local repository:

.. code-block:: console

   thornforge buildsite --source ../some-project --output /tmp/some-project-site

Build a GitHub repository:

.. code-block:: console

   thornforge buildsite \
     --source https://github.com/example/project.git \
     --output /tmp/project-site

Remote builds require Git and network access in the environment running the
command.

CLI
---

Top-level command:

.. code-block:: console

   thornforge [--version] [--no-color] <command> [args...]

Options:

``--version``
   Print ThornForge's version and dependency versions.

``--no-color``
   Disable rich terminal colors.

Available command:

.. code-block:: console

   thornforge buildsite --source . --output /tmp/site

``--source``
   Local repository path or supported GitHub repository URL.

``--output``
   Required destination directory. Existing contents are removed before a new
   site is written.

The build command can also be run as a module:

.. code-block:: console

   python -m thornforge.buildsite --source . --output /tmp/site

Source Repository Discovery
---------------------------

ThornForge is designed to build repositories without requiring a
ThornForge-specific configuration file.

Documentation source discovery searches for a Sphinx ``conf.py`` in this order:

1. ``docs/``
2. ``docs/source/``
3. ``doc/``
4. ``doc/source/``
5. ``documentation/``
6. ``documentation/source/``

If none of those paths contains ``conf.py``, ThornForge recursively searches for
the shallowest remaining ``conf.py`` while skipping transient directories such
as ``.git``, virtual environments, build outputs, and caches.

Project names are discovered from:

1. ``[project].name`` in ``pyproject.toml``
2. ``[tool.poetry].name`` in ``pyproject.toml``
3. ``name`` in ``package.json``
4. The repository directory name

Version Selection
-----------------

Git repositories are built from tags matching ``v*`` when such tags exist. Tags
are sorted using PEP 440 version parsing after the leading ``v`` is removed.

Repositories without matching tags get one build using a fallback label:

1. ``[project].version`` in ``pyproject.toml``
2. ``git describe --tags --always``
3. ``current``

Generated Output
----------------

The output directory is deleted and recreated for every build. A typical output
tree looks like this:

.. code-block:: text

   site/
   |-- .nojekyll
   |-- index.html
   |-- readme.html
   |-- changelog.html
   |-- site-nav.json
   |-- assets/
   |   |-- scripts/
   |   |-- style/
   |   `-- templates/
   `-- docs/
       |-- index.html
       |-- latest -> <latest-version>
       |-- versions.json
       |-- _builds/
       |   `-- <digest>/
       `-- <version> -> _builds/<digest>

Each public version path under ``docs/`` is a symlink to a canonical build under
``docs/_builds``. The canonical directory name is a short content digest derived
from documentation inputs, project metadata, and ThornForge's bundled assets.

If multiple versions produce the same digest, their public version paths reuse
the same canonical build output.

Publishing
----------

The output directory is a static site tree. For GitHub Pages, publish the full
contents of the output directory. ThornForge writes ``.nojekyll`` so paths such
as ``docs/_builds`` are served as normal static files.

Development
-----------

Run the regression tests:

.. code-block:: console

   python -m unittest tests.test_build_system

Build the Python distributions:

.. code-block:: console

   python -m build

Check the generated distributions:

.. code-block:: console

   python -m twine check dist/*

Build the Sphinx docs directly:

.. code-block:: console

   python -m sphinx -b html docs docs/_build/html

Build the full ThornForge-generated documentation site:

.. code-block:: console

   thornforge buildsite --source . --output /tmp/thornforge-site

Package Contents
----------------

The Python package includes the build pipeline under ``thornforge.buildsite``
and bundled site assets under ``thornforge/assets``. The bundled assets are
included in wheels so an installed ``thornforge buildsite`` command can copy
templates, stylesheets, and scripts into generated sites.

License
-------

ThornForge is distributed under the Apache License 2.0. See ``LICENSE`` for the
full license text.
