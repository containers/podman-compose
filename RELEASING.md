Creating a release
==================

This file contains instructions for maintainers on how to release new versions of podman-compose.

Step 1: Initialize variables for subsequent steps
-------------------------------------------------

```
export VERSION=1.2.3
```

Step 2: Release notes PR
------------------------

Open a new branch (e.g. `release`) and run the following:

```
./scripts/make_release_notes.sh $VERSION
```

This collects the release notes using the `towncrier` tool and then commits the result.
This step is done as a PR so that CI can check for spelling errors and similar issues.

Certain file names are not properly supported by the `towncrier` tool and it ignores them.
Check `newsfragments` directory for any forgotten release notes

Step 3: Merge the release notes PR
----------------------------------

Step 4: Perform actual release
------------------------------

Pull the merge commit created on the `main` branch during the step 2.
Then run:

```
./scripts/make_release.sh
```

This will create release commit, tag and push everything.

Step 5: Create a release on Github
----------------------------------

The release notes must be added manually by drafting a release on the GitHub UI at
https://github.com/containers/podman-compose/releases.
