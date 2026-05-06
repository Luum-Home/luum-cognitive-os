package tui

import (
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
)

func TestProofModelUsesBubbleTeaContract(t *testing.T) {
	model := NewProofModel("Surface 5")
	if model.Init() != nil {
		t.Fatalf("proof model init must not start background work")
	}
	updated, cmd := model.Update(tea.KeyMsg{})
	if cmd == nil {
		t.Fatalf("key update must return a quit command")
	}
	proof, ok := updated.(ProofModel)
	if !ok {
		t.Fatalf("updated model type = %T, want ProofModel", updated)
	}
	if !proof.Done {
		t.Fatalf("proof model did not record completion")
	}
	if !strings.Contains(proof.View(), "Surface 5") {
		t.Fatalf("view did not include message: %q", proof.View())
	}
}
