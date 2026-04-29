package cli

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"

	"luum-agent-os/cmd/cos/internal/project"
)

func runProjectPythonScript(scriptRel string, args ...string) error {
	projectRoot := project.FindRootOrCwd()
	script := filepath.Join(projectRoot, scriptRel)
	cmdArgs := append([]string{script, "--project-dir", projectRoot}, args...)
	cmd := exec.Command("python3", cmdArgs...)
	cmd.Dir = projectRoot
	cmd.Env = append(os.Environ(), fmt.Sprintf("PYTHONPATH=%s", projectRoot))
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}
