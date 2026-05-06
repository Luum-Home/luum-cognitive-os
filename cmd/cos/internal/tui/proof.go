package tui

import tea "github.com/charmbracelet/bubbletea"

// ProofModel is the minimal Bubble Tea model used to prove the Surface 5
// substrate compiles inside the cos Go module before full-screen UX work grows.
type ProofModel struct {
	Message string
	Done    bool
}

func NewProofModel(message string) ProofModel {
	if message == "" {
		message = "Cognitive OS"
	}
	return ProofModel{Message: message}
}

func (m ProofModel) Init() tea.Cmd {
	return nil
}

func (m ProofModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg.(type) {
	case tea.KeyMsg:
		m.Done = true
		return m, tea.Quit
	default:
		return m, nil
	}
}

func (m ProofModel) View() string {
	if m.Done {
		return m.Message + "\n"
	}
	return m.Message + " — press any key to exit\n"
}
