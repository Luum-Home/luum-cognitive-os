#!/usr/bin/env node
// SCOPE: os-only
// semantic-lookup.mjs — Vector similarity search for error patterns
// Requires: npm install @zvec/zvec (optional, falls back to TF-IDF)

import { readFileSync } from 'fs';
import { argv } from 'process';

// Parse args
const args = {};
for (let i = 2; i < argv.length; i += 2) {
  args[argv[i].replace('--', '')] = argv[i + 1];
}

const registryPath = args.registry;
const query = args.query;
const threshold = parseFloat(args.threshold || '0.75');

if (!registryPath || !query) {
  console.error('Usage: semantic-lookup.mjs --registry <path> --query <text> [--threshold 0.75]');
  process.exit(1);
}

// Read registry
const lines = readFileSync(registryPath, 'utf-8').trim().split('\n').filter(Boolean);
if (lines.length === 0) process.exit(1);

// Simple TF-IDF based similarity (no zvec dependency required)
function tokenize(text) {
  return text.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter(t => t.length > 2);
}

function cosineSimilarity(a, b) {
  const tokensA = tokenize(a);
  const tokensB = tokenize(b);
  const vocab = new Set([...tokensA, ...tokensB]);

  const vecA = [...vocab].map(t => tokensA.filter(x => x === t).length);
  const vecB = [...vocab].map(t => tokensB.filter(x => x === t).length);

  let dot = 0, magA = 0, magB = 0;
  for (let i = 0; i < vecA.length; i++) {
    dot += vecA[i] * vecB[i];
    magA += vecA[i] ** 2;
    magB += vecB[i] ** 2;
  }

  return magA && magB ? dot / (Math.sqrt(magA) * Math.sqrt(magB)) : 0;
}

// Find best match
let bestMatch = null;
let bestScore = 0;

for (const line of lines) {
  try {
    const entry = JSON.parse(line);
    if (!entry.auto_applicable) continue;

    const score = cosineSimilarity(query, entry.error_pattern || '');
    if (score > bestScore && score >= threshold) {
      bestScore = score;
      bestMatch = entry;
    }
  } catch {}
}

if (bestMatch) {
  console.log(JSON.stringify({
    fix_type: bestMatch.fix_type,
    fix_command: bestMatch.fix_command,
    fix_diff: bestMatch.fix_diff || null,
    confidence: bestMatch.confidence * bestScore,
    times_applied: bestMatch.times_applied,
    fingerprint: bestMatch.fingerprint,
    match_type: 'semantic',
    similarity: Math.round(bestScore * 100) / 100
  }));
  process.exit(0);
} else {
  process.exit(1);
}
