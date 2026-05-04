Contributing
============

Development setup
-----------------

Install the project in editable mode:

.. code-block:: console

   python -m pip install -e .

Install Node dependencies only when working on the browser-facing tests:

.. code-block:: console

   npm install --prefix node

Running tests
-------------

Run the Python regression tests:

.. code-block:: console

   python -m unittest discover tests

Run the browser UI tests when Node dependencies are available:

.. code-block:: console

   npm test --prefix node

Changelog workflow
------------------

Add unreleased changes to the ``Active`` section of ``CHANGELOG.rst``. Before
creating a release tag, move the relevant entries into the appropriate published
version section.

Implementation notes
--------------------

* Keep build behavior deterministic. Output should not depend on filesystem
  ordering, timestamps, or stale files from previous builds.
* Preserve idempotency in HTML post-processing. Running an injection step twice
  should not duplicate shared assets or runtime scripts.
* Add focused regression tests for repository discovery, generated output shape,
  version handling, and HTML injection behavior.
