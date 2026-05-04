Info Site
=========

The optional ``info/`` directory is treated as the non-documentation portion of
the generated static site.

Behavior
--------

* ``.rst`` files under ``info/`` are rendered to ``.html`` pages.
* ``.txt`` files are rendered as plain-text pages inside the shared site chrome.
* ``.html`` files are wrapped with the shared navigation shell.
* Other files are copied byte-for-byte.
* ``info/index.rst``, ``info/index.txt``, or ``info/index.html`` can become the
  site homepage.

Reserved paths
--------------

``info/docs`` is reserved because generated documentation is always published
under ``/docs/``.

Conflicting inputs fail the build. For example, ``info/about.rst`` and
``info/about.html`` both target ``about.html`` and cannot be published together.
