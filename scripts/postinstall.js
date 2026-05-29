#!/usr/bin/env node
// SCOPE: os-only
// postinstall.js — Show instructions after explicit operator invocation.
// Bun is the canonical package manager for this repository and
// `install.ignoreScripts = true` prevents this file from running implicitly.

console.log(`
╔══════════════════════════════════════════════════╗
║           Cognitive OS installed!                ║
╠══════════════════════════════════════════════════╣
║                                                  ║
║  Quick start:                                    ║
║    npx cognitive-os init                         ║
║    claude                                        ║
║    > /cognitive-os-init                          ║
║                                                  ║
║  Docs: github.com/luum-home/luum-cognitive-os    ║
╚══════════════════════════════════════════════════╝
`);
