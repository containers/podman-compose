This file provides guidance to agents when working with code in this repository.

Release notes
=============

For user-visible changes (bugs and new features are such) make sure to read newsfragments/README
and add a release note.

Tests
=====

Always check whether a particular function is tested in an existing test file. If such file
exists, add new tests there.

Prefer to not use separate variable for expected value. I.e. prefer this:

```
self.assertEqual(value, "expected-value")
```

instead of

```
expected = "expected-value"
self.assertEqual(value, expected)
```
