Quickstart
==========

Build this repository's documentation site into a temporary output directory:

.. code-block:: console

   thornforge buildsite --source . --output /tmp/thornforge-site

Open ``/tmp/thornforge-site/index.html`` in a browser after the build completes.
The generated site includes the homepage, project metadata pages, version
manifests, shared assets, and documentation under ``docs/``.

Build another local repository
==============================

Point ``--source`` at the repository root and ``--output`` at the desired site
directory:

.. code-block:: console

   thornforge buildsite --source ../some-project --output /tmp/some-project-site

The source repository must contain a Sphinx ``conf.py`` in one of the supported
documentation source locations.

Build a GitHub repository
=========================

ThornForge can clone supported GitHub URLs before building:

.. code-block:: console

   thornforge buildsite \
     --source https://github.com/example/project.git \
     --output /tmp/project-site

Remote builds require Git and network access in the environment running the
command.

Publish the output
==================

The output directory is a static site tree. For GitHub Pages, publish the full
contents of the output directory. ThornForge writes ``.nojekyll`` so directories
such as ``_builds`` are served as normal static files.
