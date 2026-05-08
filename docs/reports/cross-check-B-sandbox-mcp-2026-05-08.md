# Cross-check Part B: Sandbox & MCP (2026-05-08)

Phase: reconstruction. Veredictos directos por ítem; foco en delta real vs claim.

---

## 🔍4 Bubblewrap / sandbox-exec

**Veredicto:** IGUAL (delta plumbing menor, sin ventaja técnica sobre upstream)

**Nuestra lógica actual:**
- `packages/agent-lifecycle/lib/sandbox_adapter.py` (146 LOC) — selecciona backend por `platform.system()`, construye argv para `bwrap` (Linux) o `sandbox-exec` (macOS), expone `SandboxPlan` dataclass + `run_sandboxed()` envoltorio sobre `subprocess.run`.
- Wiring en `lib/dispatch.py` (~line 580) gateado por `skill_requirements.require_sandbox=true`. Default = sandbox OFF.
- `scripts/cos-sandbox-run` CLI dry-run/JSON.
- microvm/contree → `adapter_contract` puro (sin runtime), requiere env `COS_SANDBOX_MICROVM_RUNNER`.
- E2B: `packages/e2b-sandbox/` listado como thin_wrapper; no apareció en grep — confirmado que no hay wiring real a E2B.

Política bubblewrap aplicada:
```
bwrap --ro-bind / / --dev /dev --proc /proc --chdir <ws> [--unshare-net] --bind <writable> <writable>
```
sandbox-exec genera profile inline `(deny default)(allow process*)(allow file-read*)(allow file-write* (subpath ...))[(allow network*)]`.

**Lo que research prometió (ADR-232):** "Slices A–E implementadas (2026-05-07)". Adapter dependency-free, opt-in native-only, no fallback implícito, microvm/contree contract-only.

**Realidad en código:** Slice A–B verificada en código (adapter + dispatch preflight + manifest contract test). Slice E no la audité, pero la base existe. **NO es aspirational** — el módulo existe, es funcional, está wired a dispatch. Lo que sí es importante: este código NO "adopta" bubblewrap como dependencia — es un argv-builder de ~50 líneas alrededor de `bwrap`/`sandbox-exec` invocados como subprocess. Es exactamente lo que el research recomienda (host-native, no embed).

Comparado con upstream (`containers/bubblewrap`): bwrap es un binario CLI de C bajo LGPL-2.1; nadie lo "adopta" como librería. La forma idiomática de usarlo ES via subprocess argv. Nuestra implementación es estándar y coincide con el patrón usado por flatpak/toolbox.

**Aislamiento real provisto vs prometido:**
- Linux: equivalente a flatpak-spawn básico. `--ro-bind /` deja todo el FS host visible read-only (no es un chroot real). Network unshared OK. Falta: `--die-with-parent`, `--new-session`, namespaces UID/PID, seccomp filter. Para un agente write-capable, cubre filesystem, no provee defense-in-depth contra exfil via syscalls raros o lectura sensible.
- macOS: profile Seatbelt mínimo. `(allow process*)` permite `fork/exec` de cualquier binario. Sin restricción de mach IPC, sin restricción de keychain. Profile bastante laxo.

Research prometió "permission boundaries below the prompt layer" — sí, los provee. NO prometió hardening tipo gVisor, así que el gap entre claim y código es chico.

**Recomendación:** Código está OK como Slice A. Mejoras concretas (no rewrites):
1. Agregar `--die-with-parent --new-session --cap-drop ALL` al argv bwrap (1 línea).
2. Cerrar Seatbelt profile (`(deny process-fork)` salvo allowlist).
3. Auditar que `e2b-sandbox/` thin_wrapper no esté listado como activo en manifests si no tiene wiring.

**Esfuerzo:** S (1-2h) para hardening del argv. Cualquier cosa adicional (Landlock, seccomp BPF, microvm real) → M-L y fuera de scope reconstruction.

---

## 🔍5 fastmcp (jlowin/fastmcp)

**Veredicto:** MEJOR_EXTERNO en lo que delegamos (decorator + transport stdio); IGUAL en superficie expuesta. NO reimplementamos fastmcp — lo usamos.

**Nuestra lógica actual:**
- `mcp-server/cos_mcp.py` (870 LOC) y `packages/mcp-server/cos_mcp.py` (symlink, 870 LOC) — **importa `from fastmcp import FastMCP`** y registra 8 tools con `@mcp.tool`. Transport `mcp.run()` delegado a fastmcp.
- `packages/advisor-mcp/advisor_server.py` (577 LOC) — mismo patrón: `FastMCP("advisor")` + `@mcp.tool consult_advisor`.
- `packages/advisor-mcp/requirements.txt`: `fastmcp>=2.0.0`.
- `cos-package.yaml` declara dependency `fastmcp` con `install: pip install fastmcp`.
- `_FastMCPCompat`: stub local de ~15 LOC SOLO para que tests unitarios corran sin instalar fastmcp; `run()` raisea `RuntimeError("fastmcp is required")`. NO es una reimplementación, es un test seam.

**Lo que research prometió (ADR-231):** "MCP server surface adopted, Slices A–C". Reusar el server pre-existente, agregar package symlink, manifest, contract tests.

**Realidad en código:** Coincide con el claim. ADR-231 es transparente: dice "predates ADR-231" (es decir, el server ya existía y solo se formalizó el package). 8 tools expuestos: engram_search, engram_save, task_state, rules_lookup, metrics_summary, quality_check, skill_suggest, cos_status (según ADR §A). Hay symlink real `mcp-server/cos_mcp.py` ↔ `packages/mcp-server/cos_mcp.py` (ambos 870 LOC idénticos).

**Lo que NO tenemos vs upstream fastmcp** (según el README de jlowin/fastmcp 2.x):
- No usamos `@mcp.resource` ni `@mcp.prompt` (solo `@mcp.tool`). Fastmcp soporta los tres tipos.
- No usamos auth integrada de fastmcp 2.x (OAuth, bearer).
- No usamos transport SSE/HTTP — solo stdio. Fastmcp soporta ambos.
- No usamos `FastMCP.from_openapi()` ni el Client. Solo server stdio.

Esto es subset razonable; no es deuda crítica.

**Recomendación:**
1. Subir version pin (`fastmcp>=2.0.0` es lax — pinear a `>=2.x,<3` en advisor-mcp; el otro server ni declara version).
2. Considerar exponer Engram como `@mcp.resource` en vez de `@mcp.tool engram_search` (resources cachean del lado cliente, mejor UX en Claude Code).
3. NO reescribir nada custom; fastmcp upstream cubre todo lo razonable.

**Esfuerzo:** S (30 min) para version pin. M (medio día) para migrar a resources/prompts si hay valor concreto.

---

## 🔍7 Deferred tool loading + ToolSearch (ADR-236)

**Veredicto:** MEJOR_NUESTRO en governance/audit; IGUAL_O_INFERIOR en mecanismo runtime (Claude Code ya lo hace nativo). El delta real es manifest-driven planning + change detection, no el deferring en sí.

**Nuestra lógica actual:**
- `packages/agent-lifecycle/lib/deferred_tool_loading.py` (177 LOC) — manifest YAML driven (`manifests/deferred-tool-loading.yaml`), planificador `plan_tool_loading()` que decide visible/deferred según threshold de tokens, `toolsearch_index()` que devuelve metadata compacta, `list_changed()` con hash sha256 + estado persistido en `.cognitive-os/metrics/deferred-tool-loading-state.json`.
- `provider_native_defer_payload()` — gate explícito en env `COS_NATIVE_DEFER_LOADING_PROVIDERS`. Por default returns `native_defer_loading_supported=false` con razón "provider_api_not_available". **Es honesto: no pretende implementar el protocolo MCP `notifications/tools/list_changed` — solo lo prepara.**
- Wiring en `lib/dispatch.py:109` y `lib/dispatch.py:620` — usa `plan_tool_loading()` para decidir si emitir el payload con index al provider.
- CLI `scripts/cos-deferred-tool-plan`.

**Lo que research prometió (ADR-236):** "Slices A–D implementadas, 85% token reduction". El "85%" no aparece en el código; es un claim del research no del ADR (el ADR no afirma ese número).

**Realidad en código:** Slices A–D existen como helpers planning + change detection. Slice E (transport real `notifications/tools/list_changed`) explícitamente listada como NOT implemented en el ADR (línea 54): *"Real MCP notifications/tools/list_changed transport emission; local detection is implemented and ready to feed it when host APIs expose the hook."* Eso es honesto, no aspirational.

**Comparación con ToolSearch nativo de Claude Code (visible en este mismo prompt):**
- Claude Code expone deferred tools en `<system-reminder>` con sus nombres y un `ToolSearch` tool nativo que carga schemas via `select:`/keyword query. Funciona ya, sin manifest nuestro.
- Nuestro código NO sustituye eso — lo complementa para casos donde el provider NO sea Claude Code (Cursor, Windsurf, futuros providers).

**Delta real que aportamos sobre ToolSearch nativo:**
1. **Manifest-driven policy** — `always_available`, `load_mode: eager|deferred`, `category` declaradas en YAML, no hardcoded en cliente. Claude Code decide solo.
2. **Change detection con hash** — `list_changed()` permite que un orquestador externo sepa cuándo el set cambió sin re-listar.
3. **Provider-agnóstico** — el payload se puede emitir a cualquier MCP host vía COS_NATIVE_DEFER_LOADING_PROVIDERS.
4. **Token threshold gate** — el bundle solo se difiere si supera `toolsearch_threshold_tokens` (default 10k). Claude Code aplica heurística propia.

**Lo que NO es delta real:**
- El "deferring" en sí ya existe nativo en Claude Code (este prompt es prueba). En sesiones Claude Code, nuestro `provider_native_defer_payload()` retorna `supported=false` por default, así que el manifest queda como blueprint informativo, no operativo.
- "85% token reduction" — no está medido en este repo (no encontré métricas calibradas en `.cognitive-os/metrics/`). Es un claim del research, no respaldado por evidencia local. **Marcar como ASPIRATIONAL CLAIM en research, NO en ADR-236**.

**Recomendación:**
1. Mantener `deferred_tool_loading.py` como capa de governance multi-provider (vale la pena).
2. Documentar explícito en ADR-236: "en Claude Code el módulo es no-op (host hace el deferring); valor real surge cuando se integre con Cursor/Windsurf u host MCP propio".
3. NO publicar el "85% reduction" sin medir. Correr una prueba con/sin manifest en Cursor (que tiene MCP nativo limitado) y publicar el delta real.
4. Eliminar el "85%" del research si no se mide o calibrarlo.

**Esfuerzo:** S (15 min) para clarificar status en ADR. M (1 día) para benchmark real de reducción.

---

## Resumen ejecutivo

| Ítem | Veredicto | Aspirational? | Acción |
|---|---|---|---|
| 🔍4 Bubblewrap/sandbox-exec | IGUAL | No (Slice A–B verificadas) | Hardening argv (1-2h) |
| 🔍5 fastmcp | MEJOR_EXTERNO + IGUAL en lo nuestro | No (lo usamos genuino) | Pin version, opcional resources |
| 🔍7 Deferred tool loading | MEJOR_NUESTRO en governance | "85%" sí — claim no medido | Documentar status, medir o eliminar número |

**Hallazgos cruzados:**
- Los 3 ADRs (231/232/236) tienen status honesto: declaran qué Slices están y cuáles NO. Ninguno es aspirational en el sentido de "claim sin código".
- El claim aspirational está en el **research narrative externo** ("85% token reduction", "adopt-code via subprocess implica más profundidad de integración de la real"). El código y los ADRs son más conservadores que cómo el research los vende.
- Patrón: COS está usando bubblewrap/fastmcp/ToolSearch como **adapters/governance layers**, no como reimplementaciones. Eso es correcto técnicamente. La narrativa de "adopt-code" sobreestima la profundidad.

**Riesgo principal:** publicar el número "85% reduction" sin medirlo erosiona credibilidad. El resto del código sostiene los claims.
