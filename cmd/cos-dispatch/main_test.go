package main

import (
	"testing"
)

func TestContainsDeny(t *testing.T) {
	tests := []struct {
		name string
		resp string
		want bool
	}{
		{
			name: "allow response",
			resp: `{"hookSpecificOutput":{"permissionDecision":"allow","reason":"","additionalContext":""}}`,
			want: false,
		},
		{
			name: "deny response",
			resp: `{"hookSpecificOutput":{"permissionDecision":"deny","reason":"blocked","additionalContext":""}}`,
			want: true,
		},
		{
			name: "empty response",
			resp: `{}`,
			want: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := containsDeny([]byte(tt.resp))
			if got != tt.want {
				t.Errorf("containsDeny(%q) = %v, want %v", tt.resp, got, tt.want)
			}
		})
	}
}
