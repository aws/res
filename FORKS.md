# Forks

2026.09 is the final AWS release of Research and Engineering Studio. This repository's contents stay
available to read, clone, and fork.

RES can be developed further in a fork.

## Finding a fork that is still maintained

This file names no forks. Use this repository's fork network on GitHub, which is live data. From the
repository page, open the fork list and sort by recent activity: a fork with recent commits is
being worked on.

## Evaluating a fork

Appearing in the fork network says nothing about a fork's quality, security, licensing practice, or
longevity. Assess it yourself. Questions to ask:

- When was the last commit, and does the history show ongoing work or a single import?
- Does it publish releases, or only a branch?
- Does it say who maintains it and how to report a vulnerability?
- Has it refreshed the pinned AMI tables in `source/idea/infrastructure/resources/config/`? Those age
  from the 2026.09 release date onwards, and a fork that has not touched them is running the pins RES
  shipped with. A deprecated AMI still launches. A deregistered one does not.
- Does its build succeed from a clean clone?

## License

RES is licensed under the Apache License 2.0, which permits forking, modification, and redistribution
subject to its terms. See [`LICENSE.txt`](./LICENSE.txt). A fork is responsible for its own compliance,
including the third-party notices in [`THIRD_PARTY_LICENSES.txt`](./THIRD_PARTY_LICENSES.txt).
