#########
Changelog
#########

This project follows a simple release-oriented changelog. Entries describe the
changes shipped in each tagged version.

It is structured where the most recent changes and versions are at the top of their
respective sections.

When making new tags (including prereleases),
any change content in the `Active` section should be moved to it's respective section
before the new tag is commited and pushed. Meaning the last commit in any tag should
be ``Moved active changes to {version tag}`` or when moving prerelease logs to a
release log, the commit then should be ``Moved prerelease logs of {version tag} into publish``.
Or you can use the broader commit message of ``Moved all logged changes for {version tag} into publish``,
this one is recommended to only be used when there are changes in both Active and PreReleases sections.

Active
======

Here is what has been pushed into the *main* branch of the repository,
but has yet to be released as a version.

Changes:

- Added the initial ThornForge build pipeline for generating versioned static
  documentation sites from local repositories or supported GitHub sources.
- Added repository discovery helpers that locate Sphinx docs, infer project
  metadata, select project pages, and choose fallback version labels.
- Added Git-aware version collection and canonical build reuse so identical
  version inputs can share one generated docs build.
- Added shared site asset handling, docs runtime injection, top navigation, and
  version-switcher support for generated pages.
- Added project-page rendering for files such as ``CHANGELOG.rst`` and support
  for optional ``info/`` site content rendered into the final output tree.
- Added regression coverage for repository discovery, non-Git builds, generated
  site outputs, and duplicate runtime-script prevention.
- Added the initial HTML and reStructuredText templates, styling assets, and
  test build command used by the project.

PreReleases
===========

Here you'll find what is in prerelease tags.
This is cleared when the official release of the
prereleases arrives.
This is mainly for organization purposes.

No prerelease tags have been created yet.

Published
=========

Here are the changes made in each version that has a public release.
These will never change.

No public release tags have been created yet.
