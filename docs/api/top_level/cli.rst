CLI Dispatcher
==============

Module: :mod:`thornforge.cli`

Overview
--------

The CLI module configures rich terminal output, reports dependency versions, and
dispatches registered ThornForge commands through Python entry points.

Important functions
-------------------

``configure_output()``
   Configure Rich logging and console behavior.

``list_dependencies_and_versions()``
   Return the dependency/version pairs shown in ``thornforge --version``.

``dispatch(argv)``
   Parse top-level command arguments and invoke the matching registered command.

Autodoc
-------

.. automodule:: thornforge.cli
   :members:
   :undoc-members:
