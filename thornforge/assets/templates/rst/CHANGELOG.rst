#########
Changelog
#########

[IN THIS TEMPLATE ANY CONTENT INSIDE OF {} SHOULD BE TREATED AS PLACE HOLDERS
THE ONLY PLACE THAT THEY ARE NOT PLACEHOLDERS ARE THE VERSION COMMIT MESSAGE
SECTION, THE PLACEHOLDERS DEFINED THERE ARE TO BE CHANGED WHEN MAKING THE
COMMIT MESSAGE]

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

{Put changes here.}

PreReleases
===========

Here you'll find what is in prerelease tags.
This is cleared when the official release of the
prereleases arrives.
This is mainly for organization purposes.

{
0.2.0rc1
^^^^^^^^

Put changes in this version here.
}

Published
=========

Here are the changes made in each version that has a public release.
These will never change.

{
1.0.0
-----

Major release 1, project is stable.

Release info goes here.
}

{
0.1.1
-----

Put any unique changes to versions here, otherwise the rest should be
categorized under this versions prereleases.


0.1.1rc1
^^^^^^^^

Put changes in this version here.
Prereleases should always be subsection under it full release.
This should be in the PreReleases section when it doesn't have
a full release yet.
}

{
0.1.0
-----

Initial public release.

Highlights:

This is where you should put the info on what is in the first initial release.
}
