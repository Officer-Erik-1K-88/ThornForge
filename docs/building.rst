Building The Docs
=================

The documentation sources live directly in the ``docs/`` directory and are
structured for Sphinx.

Sphinx Configuration
--------------------

The Sphinx configuration file is ``docs/conf.py``.

It currently enables:

* ``sphinx.ext.autodoc``
* ``sphinx.ext.napoleon``

Suggested build commands
------------------------

From the repository root, build the docs directly with Sphinx:

.. code-block:: console

   python -m sphinx -b html docs docs/_build/html

Build the full ThornForge-generated site:

.. code-block:: console

   thornforge buildsite --source . --output /tmp/thornforge-site

Versioned static site behavior
==============================

ThornForge publishes documentation under ``/docs/`` and keeps each built version
at ``/docs/<version>/``. The moving ``/docs/latest/`` alias points to the newest
version, and ``/docs/`` redirects to that alias.

If a repository contains matching ``v*`` tags, ThornForge rebuilds all matching
versions. Otherwise it builds the current tree once.

Deduplication
-------------

The build hashes repository inputs and ThornForge-owned assets. If two versions
produce the same hash, ThornForge builds that documentation tree once under
``docs/_builds/<hash>/`` and publishes the version paths as symbolic links to
that shared build.
