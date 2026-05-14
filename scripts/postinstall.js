#!/usr/bin/env node
// SCOPE: os-only
// postinstall.js — Show instructions after npm install

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
