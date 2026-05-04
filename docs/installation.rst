Installation
============

Requirements
============

ThornForge requires Python 3.12 or newer. Runtime dependencies are declared in
``pyproject.toml`` and include Sphinx, docutils, packaging, rich, requests, and
id.

Local development install
=========================

From a checkout of this repository, install ThornForge in editable mode:

.. code-block:: console

   python -m pip install -e .

If you only want to install dependencies into an existing environment, use the
requirements file:

.. code-block:: console

   python -m pip install -r requirements.txt

Verifying the install
=====================

The package exposes a top-level command:

.. code-block:: console

   thornforge --version

You can also run the buildsite module directly:

.. code-block:: console

   python -m thornforge.buildsite --help
