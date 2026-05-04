Architecture
============

The build pipeline is intentionally split into small filesystem-oriented
modules. The high-level orchestration lives in
``thornforge.buildsite.build_site``.

Build flow
----------

1. Materialize the source repository. Local paths are used directly; supported
   GitHub URLs are cloned into a temporary directory.
2. Discover the repository profile: docs directory, project name, project pages,
   version fallback, Git capability, and hash input paths.
3. Choose build versions from ``v*`` Git tags, or fall back to one current-tree
   build.
4. Copy or archive each version into a temporary worktree.
5. Patch the Sphinx ``conf.py`` with ThornForge's version-switcher sidebar
   configuration.
6. Run ``python -m sphinx -b html``.
7. Copy shared assets and inject navigation/runtime references into generated
   HTML.
8. Write public version symlinks, ``latest``, JSON manifests, project pages, and
   inline runtime payloads.

Module boundaries
-----------------

``thornforge.buildsite.repository``
   Discovers source repository structure and metadata.

``thornforge.buildsite.git``
   Wraps Git commands, source materialization, and content hashing.

``thornforge.buildsite.builder``
   Runs Sphinx and post-processes documentation build outputs.

``thornforge.buildsite.site``
   Writes generated site pages, docs helper files, and runtime JSON payloads.

``thornforge.buildsite.info_site``
   Publishes optional ``info/`` content into the root of the generated site.

``thornforge.buildsite.nav``
   Normalizes HTML fragments and injects shared navigation placeholders, CSS,
   and JavaScript references.
