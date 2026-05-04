Repository Discovery
====================

Module: :mod:`thornforge.buildsite.repository`

Overview
--------

Repository discovery resolves the Sphinx source directory, project display name,
project metadata pages, hash inputs, fallback version label, and Git capability
for a source repository.

Important API
-------------

``RepositoryProfile``
   Dataclass describing all discovered build inputs.

``discover_repository_profile(repo_root)``
   Return the complete repository profile.

``discover_docs_dir(repo_root)``
   Locate the most likely Sphinx source directory.

``materialize_source(source)``
   Context manager that yields a local repository path for local or remote
   sources.

Autodoc
-------

.. automodule:: thornforge.buildsite.repository
   :no-index:
   :members:
   :undoc-members:
