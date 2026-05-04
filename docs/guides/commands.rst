Commands
========

Top-level command
-----------------

.. code-block:: console

   thornforge [--version] [--no-color] <command> [args...]

Options:

``--version``
   Print ThornForge's version and dependency versions.

``--no-color``
   Disable rich terminal colors.

Commands are discovered through the ``thornforge.registered_commands`` entry
point group.

``buildsite``
-------------

.. code-block:: console

   thornforge buildsite --source . --output /tmp/site

The ``buildsite`` command assembles a versioned static documentation site.

``--source``
   Local repository path or supported GitHub repository URL. When omitted by the
   module entrypoint, the default is the ThornForge package checkout.

``--repo-root``
   Hidden compatibility alias for ``--source``.

``--output``
   Required destination directory. Existing contents are removed before a new
   site is written.

Module entrypoint
-----------------

The build command can also be run without the top-level command dispatcher:

.. code-block:: console

   python -m thornforge.buildsite --source . --output /tmp/site
