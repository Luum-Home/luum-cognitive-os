package cli

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestE2E_ProvenanceScanCommand(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "cognitive-os.yaml"), []byte("project:\n  name: scan\n"), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(dir, ".cognitive-os"), 0755); err != nil {
		t.Fatal(err)
	}
	config := "schema_version: provenance-scan/v1\nprovenance:\n  forbidden_terms: [SecretOrigin]\n"
	if err := os.WriteFile(filepath.Join(dir, ".cognitive-os", "provenance-scan.yaml"), []byte(config), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "README.md"), []byte("SecretOrigin\n"), 0644); err != nil {
		t.Fatal(err)
	}

	out, exitCode := runCos(t, dir, "provenance", "scan", "--json", "README.md")
	if exitCode != 1 {
		t.Fatalf("expected exit 1, got %d. Output:\n%s", exitCode, out)
	}
	if !strings.Contains(out, "forbidden-term") {
		t.Fatalf("expected forbidden-term finding, got:\n%s", out)
	}
}
