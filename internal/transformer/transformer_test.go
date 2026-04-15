package transformer

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// --- helpers ----------------------------------------------------------------

// stubTransformer is a configurable test double.
type stubTransformer struct {
	name     string
	phase    Phase
	priority int
	preFn    func(ctx context.Context, hookCtx *hook.Context) (*hook.Context, error)
	postFn   func(ctx context.Context, hookCtx *hook.Context, errs []*ValidationError, resp any) (any, error)
}

func (s *stubTransformer) Name() string  { return s.name }
func (s *stubTransformer) Phase() Phase  { return s.phase }
func (s *stubTransformer) Priority() int { return s.priority }

func (s *stubTransformer) TransformPre(ctx context.Context, hookCtx *hook.Context) (*hook.Context, error) {
	if s.preFn != nil {
		return s.preFn(ctx, hookCtx)
	}
	return hookCtx, nil
}

func (s *stubTransformer) TransformPost(ctx context.Context, hookCtx *hook.Context, errs []*ValidationError, resp any) (any, error) {
	if s.postFn != nil {
		return s.postFn(ctx, hookCtx, errs, resp)
	}
	return resp, nil
}

func makeContext(filePath string) *hook.Context {
	return &hook.Context{
		Event:    hook.CanonicalEventBeforeTool,
		ToolName: hook.ToolWrite,
		ToolInput: hook.ToolInput{
			FilePath: filePath,
		},
	}
}

// --- Pipeline tests ---------------------------------------------------------

func TestPipelineOrderByPriority(t *testing.T) {
	p := NewPipeline()
	var order []string

	for _, prio := range []int{30, 10, 20} {
		prio := prio
		name := fmt.Sprintf("p%d", prio)
		p.Register(&stubTransformer{
			name:     name,
			phase:    PhasePre,
			priority: prio,
			preFn: func(_ context.Context, hc *hook.Context) (*hook.Context, error) {
				order = append(order, name)
				return hc, nil
			},
		}, nil)
	}

	_, err := p.RunPre(context.Background(), makeContext("/tmp/test.txt"))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	expected := "p10,p20,p30" // sorted by priority ascending
	got := strings.Join(order, ",")
	if got != expected {
		t.Errorf("execution order = %q, want %q", got, expected)
	}
}

func TestPredicateFiltering(t *testing.T) {
	p := NewPipeline()
	var ran []string

	// This transformer runs only for Bash tools.
	p.Register(&stubTransformer{
		name:     "bash-only",
		phase:    PhasePre,
		priority: 10,
		preFn: func(_ context.Context, hc *hook.Context) (*hook.Context, error) {
			ran = append(ran, "bash-only")
			return hc, nil
		},
	}, func(hc *hook.Context) bool {
		return hc.ToolName == hook.ToolBash
	})

	// This transformer runs on everything.
	p.Register(&stubTransformer{
		name:     "always",
		phase:    PhasePre,
		priority: 20,
		preFn: func(_ context.Context, hc *hook.Context) (*hook.Context, error) {
			ran = append(ran, "always")
			return hc, nil
		},
	}, nil)

	// Send a Write event — bash-only should be skipped.
	_, err := p.RunPre(context.Background(), makeContext("/tmp/test.txt"))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(ran) != 1 || ran[0] != "always" {
		t.Errorf("ran = %v, want [always]", ran)
	}
}

func TestPreTransformerChaining(t *testing.T) {
	p := NewPipeline()

	// First transformer sets a metadata key.
	p.Register(&stubTransformer{
		name:     "enricher",
		phase:    PhasePre,
		priority: 10,
		preFn: func(_ context.Context, hc *hook.Context) (*hook.Context, error) {
			hc.SetMetadata("enriched", true)
			return hc, nil
		},
	}, nil)

	// Second transformer reads the key set by the first.
	p.Register(&stubTransformer{
		name:     "reader",
		phase:    PhasePre,
		priority: 20,
		preFn: func(_ context.Context, hc *hook.Context) (*hook.Context, error) {
			if hc.Metadata["enriched"] != true {
				return nil, errors.New("expected enriched=true from previous transformer")
			}
			hc.SetMetadata("chained", true)
			return hc, nil
		},
	}, nil)

	result, err := p.RunPre(context.Background(), makeContext("/tmp/test.txt"))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Metadata["chained"] != true {
		t.Error("chaining failed: chained metadata not set")
	}
}

func TestPostTransformerChaining(t *testing.T) {
	p := NewPipeline()

	// First post-transformer wraps the response.
	p.Register(&stubTransformer{
		name:     "wrapper",
		phase:    PhasePost,
		priority: 10,
		postFn: func(_ context.Context, _ *hook.Context, _ []*ValidationError, resp any) (any, error) {
			return "wrapped:" + resp.(string), nil
		},
	}, nil)

	// Second post-transformer appends to the wrapped response.
	p.Register(&stubTransformer{
		name:     "appender",
		phase:    PhasePost,
		priority: 20,
		postFn: func(_ context.Context, _ *hook.Context, _ []*ValidationError, resp any) (any, error) {
			return resp.(string) + ":appended", nil
		},
	}, nil)

	result, err := p.RunPost(context.Background(), makeContext("/tmp/test.txt"), nil, "original")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result != "wrapped:original:appended" {
		t.Errorf("result = %q, want %q", result, "wrapped:original:appended")
	}
}

func TestNilReturnSkipsEvent(t *testing.T) {
	p := NewPipeline()
	secondRan := false

	// First transformer returns nil to skip.
	p.Register(&stubTransformer{
		name:     "skipper",
		phase:    PhasePre,
		priority: 10,
		preFn: func(_ context.Context, _ *hook.Context) (*hook.Context, error) {
			return nil, nil
		},
	}, nil)

	// Second transformer should never run.
	p.Register(&stubTransformer{
		name:     "after-skip",
		phase:    PhasePre,
		priority: 20,
		preFn: func(_ context.Context, hc *hook.Context) (*hook.Context, error) {
			secondRan = true
			return hc, nil
		},
	}, nil)

	result, err := p.RunPre(context.Background(), makeContext("/tmp/test.txt"))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result != nil {
		t.Error("expected nil result for skipped event")
	}
	if secondRan {
		t.Error("transformer after skip should not have run")
	}
}

func TestErrorPropagation(t *testing.T) {
	p := NewPipeline()

	p.Register(&stubTransformer{
		name:     "failing",
		phase:    PhasePre,
		priority: 10,
		preFn: func(_ context.Context, _ *hook.Context) (*hook.Context, error) {
			return nil, errors.New("boom")
		},
	}, nil)

	_, err := p.RunPre(context.Background(), makeContext("/tmp/test.txt"))
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !strings.Contains(err.Error(), "transformer failing") {
		t.Errorf("error should contain transformer name, got: %v", err)
	}
	if !strings.Contains(err.Error(), "boom") {
		t.Errorf("error should contain cause, got: %v", err)
	}
}

func TestPostErrorPropagation(t *testing.T) {
	p := NewPipeline()

	p.Register(&stubTransformer{
		name:     "post-fail",
		phase:    PhasePost,
		priority: 10,
		postFn: func(_ context.Context, _ *hook.Context, _ []*ValidationError, _ any) (any, error) {
			return nil, errors.New("post-boom")
		},
	}, nil)

	_, err := p.RunPost(context.Background(), makeContext("/tmp/test.txt"), nil, "resp")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !strings.Contains(err.Error(), "transformer post-fail") {
		t.Errorf("error should contain transformer name, got: %v", err)
	}
}

func TestEmptyPipeline(t *testing.T) {
	p := NewPipeline()
	hc := makeContext("/tmp/test.txt")

	result, err := p.RunPre(context.Background(), hc)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result != hc {
		t.Error("empty pipeline should return original context")
	}

	resp, err := p.RunPost(context.Background(), hc, nil, "hello")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp != "hello" {
		t.Errorf("empty pipeline should return original response, got %v", resp)
	}
}

// --- SymlinkResolver tests --------------------------------------------------

func TestSymlinkResolverResolvesSymlink(t *testing.T) {
	tmp := t.TempDir()
	realFile := filepath.Join(tmp, "real.txt")
	linkFile := filepath.Join(tmp, "link.txt")

	if err := os.WriteFile(realFile, []byte("content"), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(realFile, linkFile); err != nil {
		t.Fatal(err)
	}

	sr := &SymlinkResolver{}
	hc := makeContext(linkFile)

	result, err := sr.TransformPre(context.Background(), hc)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Resolve both to canonical form to handle /private/var vs /var on macOS.
	expectedResolved, _ := filepath.EvalSymlinks(realFile)
	if result.ToolInput.FilePath != expectedResolved {
		t.Errorf("FilePath = %q, want %q", result.ToolInput.FilePath, expectedResolved)
	}
}

func TestSymlinkResolverEmptyPath(t *testing.T) {
	sr := &SymlinkResolver{}
	hc := makeContext("")

	result, err := sr.TransformPre(context.Background(), hc)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.ToolInput.FilePath != "" {
		t.Errorf("expected empty path, got %q", result.ToolInput.FilePath)
	}
}

func TestSymlinkResolverNonExistentPath(t *testing.T) {
	sr := &SymlinkResolver{}
	hc := makeContext("/nonexistent/path/file.txt")

	result, err := sr.TransformPre(context.Background(), hc)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.ToolInput.FilePath != "/nonexistent/path/file.txt" {
		t.Errorf("expected unchanged path for non-existent file, got %q", result.ToolInput.FilePath)
	}
}

func TestSymlinkResolverRegularFile(t *testing.T) {
	tmp := t.TempDir()
	realFile := filepath.Join(tmp, "real.txt")
	if err := os.WriteFile(realFile, []byte("content"), 0644); err != nil {
		t.Fatal(err)
	}

	sr := &SymlinkResolver{}
	hc := makeContext(realFile)

	result, err := sr.TransformPre(context.Background(), hc)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Resolve to handle macOS /private/var -> /var.
	expectedResolved, _ := filepath.EvalSymlinks(realFile)
	if result.ToolInput.FilePath != expectedResolved {
		t.Errorf("FilePath = %q, want %q", result.ToolInput.FilePath, expectedResolved)
	}
}

// --- ResultTruncator tests --------------------------------------------------

func TestResultTruncatorTruncatesLargeOutput(t *testing.T) {
	rt := &ResultTruncator{
		MaxChars:  100,
		HeadChars: 20,
		TailChars: 20,
	}

	longText := strings.Repeat("x", 200)
	result, err := rt.TransformPost(context.Background(), makeContext(""), nil, longText)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	s := result.(string)
	if !strings.Contains(s, "truncated") {
		t.Error("expected truncation marker in output")
	}
	if !strings.HasPrefix(s, strings.Repeat("x", 20)) {
		t.Error("expected head to be preserved")
	}
	if !strings.HasSuffix(s, strings.Repeat("x", 20)) {
		t.Error("expected tail to be preserved")
	}
}

func TestResultTruncatorSmallOutput(t *testing.T) {
	rt := &ResultTruncator{
		MaxChars:  100,
		HeadChars: 20,
		TailChars: 20,
	}

	result, err := rt.TransformPost(context.Background(), makeContext(""), nil, "short")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result != "short" {
		t.Errorf("expected unchanged output, got %v", result)
	}
}

func TestResultTruncatorNeverTruncatePattern(t *testing.T) {
	rt := &ResultTruncator{
		MaxChars:      50,
		HeadChars:     10,
		TailChars:     10,
		NeverTruncate: []string{"IMPORTANT"},
	}

	longText := strings.Repeat("x", 100) + "IMPORTANT" + strings.Repeat("x", 100)
	result, err := rt.TransformPost(context.Background(), makeContext(""), nil, longText)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result != longText {
		t.Error("expected output to be unchanged when NeverTruncate pattern matches")
	}
}

func TestResultTruncatorNonStringResponse(t *testing.T) {
	rt := &ResultTruncator{
		MaxChars:  10,
		HeadChars: 5,
		TailChars: 5,
	}

	input := map[string]string{"key": "value"}
	result, err := rt.TransformPost(context.Background(), makeContext(""), nil, input)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result == nil {
		t.Error("expected non-string response to be returned unchanged, got nil")
	}
}

func TestResultTruncatorInterface(t *testing.T) {
	rt := &ResultTruncator{}
	if rt.Name() != "result-truncator" {
		t.Errorf("Name() = %q, want %q", rt.Name(), "result-truncator")
	}
	if rt.Phase() != PhasePost {
		t.Errorf("Phase() = %v, want PhasePost", rt.Phase())
	}
	if rt.Priority() != 10 {
		t.Errorf("Priority() = %d, want 10", rt.Priority())
	}
}

func TestSymlinkResolverInterface(t *testing.T) {
	sr := &SymlinkResolver{}
	if sr.Name() != "symlink-resolver" {
		t.Errorf("Name() = %q, want %q", sr.Name(), "symlink-resolver")
	}
	if sr.Phase() != PhasePre {
		t.Errorf("Phase() = %v, want PhasePre", sr.Phase())
	}
	if sr.Priority() != 20 {
		t.Errorf("Priority() = %d, want 20", sr.Priority())
	}
}
