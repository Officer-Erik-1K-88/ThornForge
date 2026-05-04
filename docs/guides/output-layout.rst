Output Layout
=============

The output directory is deleted and recreated for every build. The resulting
tree is deterministic for a given source and ThornForge asset set.

Typical output
--------------

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

Documentation paths
-------------------

Each public version path under ``docs/`` is a symlink to a canonical build under
``docs/_builds``. The canonical directory name is a short content digest derived
from the source documentation inputs, project metadata, and ThornForge's shared
assets.

If multiple versions produce the same digest, their public version paths reuse
the same canonical build output.

Runtime metadata
----------------

``site-nav.json``
   Lists root-level pages and the latest documentation target for the top
   navigation script.

``docs/versions.json``
   Lists available documentation versions, the latest version, and the digest
   backing each version path.

Both payloads are embedded into generated HTML pages so navigation and version
menus can work without relying on extra network requests.

Shared assets
-------------

ThornForge copies its bundled ``thornforge/assets/`` tree to the site root and
to each canonical documentation build. Generated docs pages are post-processed
to reference the shared CSS and JavaScript assets exactly once.
