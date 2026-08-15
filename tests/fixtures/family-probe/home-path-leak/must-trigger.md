# Must trigger

An operator home path committed as text. Every member of this family exists to
stop this line reaching a commit:

    the build wrote its output to [[HOME]]/[[PROBE_USER]]/Projects/luum/luum-agent-os/build/out.log

`[[PROBE_USER]]` is expanded to a plain synthetic account name when the probe
writes this file into its sandbox. It is stored as a bracketed token on purpose:
the brackets make this repository's own guards read the segment as a description
of a username rather than an instance of one (the `describes_a_username` rule
from commit 3a6e737b), which is the only way a fixture whose job is to trip
those guards can live in the repository they protect.

That substitution is the probe's one concession to being hosted inside its own
subject matter, and it is why the token is a single documented string rather
than a template language.
