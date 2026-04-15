package transformer

import (
	"context"
	"fmt"
	"strings"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// ResultTruncator is a post-transformer that truncates large tool output to
// keep response payloads within reasonable bounds. It preserves the head and
// tail of the output so the agent sees both the beginning (context) and end
// (final results) of long outputs.
type ResultTruncator struct {
	// MaxChars is the character threshold above which truncation applies.
	MaxChars int
	// HeadChars is the number of leading characters to preserve.
	HeadChars int
	// TailChars is the number of trailing characters to preserve.
	TailChars int
	// NeverTruncate contains substring patterns; if any pattern matches the
	// response, truncation is skipped entirely.
	NeverTruncate []string
}

var _ Transformer = (*ResultTruncator)(nil)

// Name returns the transformer identifier.
func (r *ResultTruncator) Name() string { return "result-truncator" }

// Phase returns PhasePost — truncation happens after validation on the response.
func (r *ResultTruncator) Phase() Phase { return PhasePost }

// Priority returns 10 — runs early in post-phase so subsequent transformers
// work with already-truncated data.
func (r *ResultTruncator) Priority() int { return 10 }

// TransformPre is a no-op for this post-phase transformer.
func (r *ResultTruncator) TransformPre(_ context.Context, hookCtx *hook.Context) (*hook.Context, error) {
	return hookCtx, nil
}

// TransformPost truncates the response if it is a string exceeding MaxChars.
// Non-string responses are returned unchanged. If the response matches any
// NeverTruncate pattern, it is returned unchanged.
func (r *ResultTruncator) TransformPost(_ context.Context, _ *hook.Context, _ []*ValidationError, response any) (any, error) {
	text, ok := response.(string)
	if !ok {
		return response, nil
	}

	if len(text) <= r.MaxChars {
		return response, nil
	}

	for _, pattern := range r.NeverTruncate {
		if strings.Contains(text, pattern) {
			return response, nil
		}
	}

	head := r.HeadChars
	tail := r.TailChars

	// Guard against misconfiguration where head+tail >= MaxChars.
	if head+tail >= len(text) {
		return response, nil
	}

	omitted := len(text) - head - tail
	truncated := text[:head] +
		fmt.Sprintf("\n\n... [%d characters truncated] ...\n\n", omitted) +
		text[len(text)-tail:]

	return truncated, nil
}
