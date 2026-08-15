# Must not trigger — the discriminator

A document ABOUT leaked home paths, not a leaked home path. This is the fixture
that separates a member which enforces the rule from a member which enforces the
regex, and it is copied from the four real lines that blocked their own commit
on 2026-08-15 (repaired in 3a6e737b):

    git grep -nI -E '[[HOME]]/[a-zA-Z0-9._-]+' -- '*.py' '*.sh' '*.go' '*.yaml' | wc -l
    git grep -lI -E '[[HOME]]/[a-zA-Z0-9._-]+' -- '*.py' '*.sh' '*.go' '*.yaml'
    git grep -nI -E '[[HOME]]/[a-z0-9._-]+/Projects/' -- '*.md'

The third line is not redundant. Members of this family do not share one regex:
some match `home prefix + account segment`, others additionally match
`home prefix + segment + /Projects/`. A discriminator that instantiates only the
first form leaves the second branch unexercised, and a member whose defect lives
there is scored CONFORMING for a reason that has nothing to do with
discrimination. Measured on 2026-08-15: with only the first two lines,
`hooks/research-compliance-guard.sh` came back CONFORMING at a revision where it
was known to be broken.

| Check | Hits | Command |
|-------|------|---------|
| Home literals | 4 | `git grep -nI -E '"[[LINUX_HOME]]/[a-z]\|"/opt/[a-z]'` |

Every username segment above contains a character that is illegal in a POSIX or
macOS account name, so each is describing usernames rather than being one. A
member that blocks this file is measuring shape instead of meaning: it would
force an audit report on privacy hygiene to be edited until it stopped matching,
which changes what is measured instead of what is wrong.

Without this second fixture, a candidate that refuses everything is
indistinguishable from a candidate that refuses correctly, and the whole
partition collapses.
