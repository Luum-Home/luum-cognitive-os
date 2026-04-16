package impl

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/luum/cos-dispatch/pkg/hook"
)

func TestSecretDetector_PassesWhenAllDefined(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, ".env.example"),
		[]byte("API_KEY=\nDB_URL=\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	v := NewSecretDetectorValidator(dir)
	src := `package main
import "os"
func main() {
	_ = os.Getenv("API_KEY")
	_ = os.Getenv("DB_URL")
}`
	hookCtx := &hook.Context{
		ToolName:  hook.ToolWrite,
		ToolInput: hook.ToolInput{FilePath: filepath.Join(dir, "main.go"), Content: src},
	}

	r := v.Validate(context.Background(), hookCtx)
	if !r.Passed {
		t.Fatalf("expected pass when all vars defined: %s", r.Message)
	}
}

func TestSecretDetector_WarnsOnMissingVar(t *testing.T) {
	dir := t.TempDir()
	v := NewSecretDetectorValidator(dir)

	src := `func handler() {
	_ = os.Getenv("MISSING_TOKEN")
}`
	hookCtx := &hook.Context{
		ToolName:  hook.ToolWrite,
		ToolInput: hook.ToolInput{FilePath: filepath.Join(dir, "handler.go"), Content: src},
	}
	r := v.Validate(context.Background(), hookCtx)
	if r.Passed {
		t.Fatal("expected warn for missing env var")
	}
	if r.ShouldBlock {
		t.Fatal("secret-detector must be advisory (non-blocking)")
	}
	if !strings.Contains(r.Message, "MISSING_TOKEN") {
		t.Errorf("expected MISSING_TOKEN in message, got: %s", r.Message)
	}
}

func TestSecretDetector_DetectsNodePattern(t *testing.T) {
	dir := t.TempDir()
	v := NewSecretDetectorValidator(dir)

	src := `const k = process.env.SECRET_KEY;`
	hookCtx := &hook.Context{
		ToolName:  hook.ToolWrite,
		ToolInput: hook.ToolInput{FilePath: filepath.Join(dir, "app.ts"), Content: src},
	}
	r := v.Validate(context.Background(), hookCtx)
	if r.Passed {
		t.Fatal("expected warn for process.env reference")
	}
	if !strings.Contains(r.Message, "SECRET_KEY") {
		t.Errorf("expected SECRET_KEY in message, got: %s", r.Message)
	}
}

func TestSecretDetector_SkipsExcludedExtensions(t *testing.T) {
	dir := t.TempDir()
	v := NewSecretDetectorValidator(dir)

	for _, name := range []string{"README.md", "config.yaml", "package.lock"} {
		hookCtx := &hook.Context{
			ToolName: hook.ToolWrite,
			ToolInput: hook.ToolInput{
				FilePath: filepath.Join(dir, name),
				Content:  `os.Getenv("FOO_BAR")`,
			},
		}
		r := v.Validate(context.Background(), hookCtx)
		if !r.Passed {
			t.Errorf("expected skip for %s, got: %s", name, r.Message)
		}
	}
}

func TestSecretDetector_SkipsCognitiveOSPath(t *testing.T) {
	dir := t.TempDir()
	v := NewSecretDetectorValidator(dir)

	hookCtx := &hook.Context{
		ToolName: hook.ToolWrite,
		ToolInput: hook.ToolInput{
			FilePath: filepath.Join(dir, ".cognitive-os", "state.go"),
			Content:  `os.Getenv("FOO_BAR")`,
		},
	}
	r := v.Validate(context.Background(), hookCtx)
	if !r.Passed {
		t.Fatal("expected skip for .cognitive-os/* paths")
	}
}

func TestSecretDetector_NilContext(t *testing.T) {
	v := NewSecretDetectorValidator(t.TempDir())
	if r := v.Validate(context.Background(), nil); !r.Passed {
		t.Fatal("nil context should pass")
	}
}
