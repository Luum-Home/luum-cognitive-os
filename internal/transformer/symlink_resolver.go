package transformer

import (
	"context"
	"os"
	"path/filepath"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// SymlinkResolver is a pre-transformer that resolves symlinks in the tool
// input's file path. This ensures validators and downstream logic operate on
// the real (canonical) path rather than a symlink, preventing bypass attacks
// and path-confusion bugs.
type SymlinkResolver struct{}

var _ Transformer = (*SymlinkResolver)(nil)

// Name returns the transformer identifier.
func (s *SymlinkResolver) Name() string { return "symlink-resolver" }

// Phase returns PhasePre — symlinks must be resolved before validation.
func (s *SymlinkResolver) Phase() Phase { return PhasePre }

// Priority returns 20 — runs early but after any context-enrichment
// transformers that might populate FilePath.
func (s *SymlinkResolver) Priority() int { return 20 }

// TransformPre resolves symlinks in hookCtx.ToolInput.FilePath. If the path
// is empty or not a symlink, the context is returned unchanged. Resolution
// errors for non-existent paths are silently ignored (the path may not exist
// yet for Write operations).
func (s *SymlinkResolver) TransformPre(ctx context.Context, hookCtx *hook.Context) (*hook.Context, error) {
	fp := hookCtx.ToolInput.FilePath
	if fp == "" {
		return hookCtx, nil
	}

	resolved, err := filepath.EvalSymlinks(fp)
	if err != nil {
		// Path may not exist yet (e.g., a Write to a new file).
		// In that case, leave the path as-is.
		if os.IsNotExist(err) {
			return hookCtx, nil
		}
		return hookCtx, nil
	}

	hookCtx.ToolInput.FilePath = resolved
	return hookCtx, nil
}

// TransformPost is a no-op for this pre-phase transformer.
func (s *SymlinkResolver) TransformPost(_ context.Context, _ *hook.Context, _ []*ValidationError, response any) (any, error) {
	return response, nil
}
