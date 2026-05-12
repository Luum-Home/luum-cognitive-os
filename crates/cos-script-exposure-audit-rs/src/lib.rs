use anyhow::{anyhow, Context, Result};
use json::{array, object, JsonValue};
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use yaml_rust2::{Yaml, YamlLoader};

pub const SCHEMA_VERSION: &str = "script-exposure-audit/v1";
pub const DEFAULT_LEDGER: &str = "docs/reports/primitive-readiness-ledger-scripts-latest.json";
pub const DEFAULT_DISPOSITIONS: &str = "manifests/script-exposure-dispositions.yaml";

const PRIORITIES: [&str; 5] = ["P0", "P1", "P2", "P3", "OK"];
const ALLOWED_NO_SKILL_ROLES: [&str; 3] = ["lab", "migration-only", "driver-specific"];
const COMMAND_ROUTER_CONSUMER_PATHS: [&str; 1] = ["scripts/cos"];

#[derive(Debug, Clone, Default)]
pub struct Disposition {
    pub resolution: String,
    pub fields: BTreeMap<String, String>,
}

fn str_field(row: &JsonValue, key: &str, default: &str) -> String {
    row[key].as_str().unwrap_or(default).to_string()
}

fn int_field(row: &JsonValue, key: &str) -> i64 {
    row[key].as_i64().unwrap_or(0)
}

fn bool_field(row: &JsonValue, key: &str) -> bool {
    row[key].as_bool().unwrap_or(false)
}

fn clone_or_null(row: &JsonValue, key: &str) -> JsonValue {
    if row[key].is_null() {
        JsonValue::Null
    } else {
        row[key].clone()
    }
}

fn clone_or_array(row: &JsonValue, key: &str) -> JsonValue {
    if row[key].is_array() {
        row[key].clone()
    } else {
        array![]
    }
}

fn family_count(row: &JsonValue, family: &str) -> i64 {
    row["consumer_families"][family].as_i64().unwrap_or(0)
}

fn consumers(row: &JsonValue) -> JsonValue {
    let mut out = array![];
    if let Some(items) = row["consumers"].members().next() {
        let _ = items;
    }
    if row["consumers"].is_array() {
        for consumer in row["consumers"].members() {
            let family = consumer["family"].as_str().unwrap_or("unknown");
            let path = consumer["path"].as_str().unwrap_or("");
            out.push(object! { family: family, path: path })
                .expect("array push cannot fail");
        }
    }
    out
}

fn router_consumers(row: &JsonValue) -> i64 {
    if !row["consumers"].is_array() {
        return 0;
    }
    row["consumers"]
        .members()
        .filter(|consumer| {
            let path = consumer["path"].as_str().unwrap_or("");
            path.starts_with("cmd/") || COMMAND_ROUTER_CONSUMER_PATHS.contains(&path)
        })
        .count() as i64
}

fn channels(row: &JsonValue) -> JsonValue {
    object! {
        skill: int_field(row, "skill_consumers"),
        hook: family_count(row, "hook"),
        router: router_consumers(row),
        script: family_count(row, "script"),
        test: family_count(row, "test"),
        doc: family_count(row, "doc"),
        config: family_count(row, "config"),
    }
}

fn channel(channels: &JsonValue, key: &str) -> i64 {
    channels[key].as_i64().unwrap_or(0)
}

fn disposition_field(disposition: Option<&Disposition>, key: &str, default: &str) -> String {
    disposition
        .and_then(|d| d.fields.get(key))
        .cloned()
        .unwrap_or_else(|| default.to_string())
}

pub fn classify_script(row: &JsonValue, disposition: Option<&Disposition>) -> JsonValue {
    let path = str_field(row, "path", "");
    let role = str_field(row, "role", "unknown");
    let skill_consumers = int_field(row, "skill_consumers");
    let total_consumers = int_field(row, "total_consumers");
    let channels = channels(row);
    let has_agent_facing_route = channel(&channels, "skill") > 0
        || channel(&channels, "hook") > 0
        || channel(&channels, "router") > 0;
    let resolution = disposition.map(|d| d.resolution.as_str()).unwrap_or("");

    let (priority, finding, exposure_class, recommendation, rationale) = if [
        "agentic-primitive",
        "maintainer-tool",
    ]
    .contains(&role.as_str())
        && skill_consumers == 0
        && resolution == "documented_route"
    {
        let route = disposition_field(disposition, "route", "documented route");
        (
            "OK".to_string(),
            "documented-route".to_string(),
            "OK-documented-route".to_string(),
            "no-action".to_string(),
            format!("Manual ADR-283 disposition records an equivalent route: {route}."),
        )
    } else if role == "maintainer-tool" && skill_consumers == 0 && resolution == "internal_backend"
    {
        let owner = disposition_field(disposition, "owner", "script orchestration");
        (
            "OK".to_string(),
            "maintainer-tool-internal-backend".to_string(),
            "OK-internal-backend".to_string(),
            "no-action".to_string(),
            format!("Manual ADR-283 disposition classifies this as an internal backend owned by {owner}."),
        )
    } else if role == "maintainer-tool" && skill_consumers == 0 && resolution == "operator_workflow"
    {
        let owner = disposition_field(disposition, "owner", "maintainer/operator workflow");
        (
            "OK".to_string(),
            "maintainer-tool-operator-workflow".to_string(),
            "OK-operator-workflow".to_string(),
            "no-action".to_string(),
            format!("Manual ADR-283 disposition classifies this as an operator workflow owned by {owner}."),
        )
    } else if role == "maintainer-tool"
        && skill_consumers == 0
        && resolution == "documented_maintainer_tool"
    {
        let evidence = disposition_field(disposition, "evidence", "docs/tests evidence");
        (
            "OK".to_string(),
            "maintainer-tool-documented".to_string(),
            "OK-documented-maintainer".to_string(),
            "no-action".to_string(),
            format!("Manual ADR-283 disposition keeps this as a documented maintainer tool based on {evidence}."),
        )
    } else if role == "maintainer-tool" && skill_consumers == 0 && resolution == "test_fixture" {
        (
            "OK".to_string(),
            "maintainer-tool-test-fixture".to_string(),
            "OK-test-fixture".to_string(),
            "no-action".to_string(),
            "Manual ADR-283 disposition classifies this as a test fixture or smoke target; no skill required by default.".to_string(),
        )
    } else if role == "agentic-primitive" && skill_consumers == 0 {
        if channel(&channels, "hook") > 0 || channel(&channels, "router") > 0 {
            (
                "P0".to_string(),
                "agentic-primitive-without-skill-consumer".to_string(),
                "P0-route-undocumented".to_string(),
                "document-equivalent-agent-route-or-add-skill-consumer".to_string(),
                "This agentic primitive has no skill consumer, but it is reachable through a hook or command router. Document that equivalent route or add a skill so agents can discover it without rereading ledgers.".to_string(),
            )
        } else if channel(&channels, "script") > 0
            || channel(&channels, "test") > 0
            || channel(&channels, "doc") > 0
            || channel(&channels, "config") > 0
        {
            (
                "P0".to_string(),
                "agentic-primitive-without-skill-consumer".to_string(),
                "P0-promotion-candidate".to_string(),
                "add-skill-consumer-or-explicit-demotion".to_string(),
                "This agentic primitive is evidenced by docs/tests/config/scripts but has no direct agent-facing route. Promote it through a skill/router or demote it out of agentic-primitive status.".to_string(),
            )
        } else {
            (
                "P0".to_string(),
                "agentic-primitive-without-skill-consumer".to_string(),
                "P0-unrouted".to_string(),
                "wire-skill-hook-router-or-demote".to_string(),
                "This agentic primitive has no skill consumer and no observed hook/router/script/doc/test/config consumers. It is a likely orphan unless deliberately demoted or wired.".to_string(),
            )
        }
    } else if role == "maintainer-tool" && total_consumers == 0 {
        (
            "P1".to_string(),
            "maintainer-tool-with-zero-consumers".to_string(),
            "P1-zero-consumers".to_string(),
            "archive-register-or-wire-maintainer-entrypoint".to_string(),
            "Maintainer tools with no observed consumers are likely loose tools unless deliberately registered.".to_string(),
        )
    } else if role == "maintainer-tool" && skill_consumers == 0 {
        let role_source = str_field(row, "role_source", "");
        let is_explicit_internal = !row["lifecycle_id"].is_null()
            || !row["override_rationale"].is_null()
            || ["override", "lifecycle"].contains(&role_source.as_str());
        if is_explicit_internal {
            (
                "OK".to_string(),
                "maintainer-tool-explicitly-classified".to_string(),
                "OK-classified-maintainer".to_string(),
                "no-action".to_string(),
                "This maintainer tool has explicit lifecycle or override classification, so it does not need a skill consumer by default.".to_string(),
            )
        } else {
            let (exposure_class, rationale) = if channel(&channels, "hook") > 0
                || channel(&channels, "router") > 0
            {
                (
                    "P2-runtime-route-undocumented",
                    "Maintainer tool has hook/router exposure but no explicit internal classification or skill consumer.",
                )
            } else if channel(&channels, "script") > 0 {
                (
                    "P2-script-orchestrated",
                    "Maintainer tool is orchestrated by scripts but lacks explicit internal classification or skill consumer.",
                )
            } else if channel(&channels, "test") > 0 && channel(&channels, "doc") > 0 {
                (
                    "P2-evidence-only",
                    "Maintainer tool has docs/tests evidence but no runtime route, explicit internal classification, or skill consumer.",
                )
            } else if channel(&channels, "test") > 0 {
                (
                    "P2-test-only",
                    "Maintainer tool is only test-referenced and needs classification as internal/test fixture or promotion.",
                )
            } else if channel(&channels, "doc") > 0 {
                (
                    "P2-doc-only",
                    "Maintainer tool is only doc-referenced and needs classification as internal, stale, or promotion.",
                )
            } else if channel(&channels, "config") > 0 {
                (
                    "P2-config-only",
                    "Maintainer tool is only config-referenced and needs explicit internal classification or promotion.",
                )
            } else {
                (
                    "P2-other-consumer",
                    "Maintainer tool has consumers but no skill consumer or explicit internal classification.",
                )
            };
            (
                "P2".to_string(),
                "maintainer-tool-without-skill-consumer".to_string(),
                exposure_class.to_string(),
                "classify-internal-or-add-skill-consumer".to_string(),
                rationale.to_string(),
            )
        }
    } else if ALLOWED_NO_SKILL_ROLES.contains(&role.as_str()) && skill_consumers == 0 {
        (
            "P3".to_string(),
            "role-allows-no-skill-consumer".to_string(),
            "P3-role-exception".to_string(),
            "keep-role-exception-if-lifecycle-is-correct".to_string(),
            "Lab, migration-only, and driver-specific scripts may intentionally have no skill consumer.".to_string(),
        )
    } else {
        (
            "OK".to_string(),
            "exposure-accounted-for".to_string(),
            "OK-accounted".to_string(),
            "no-action".to_string(),
            "Observed exposure is consistent with the declared role.".to_string(),
        )
    };

    let mut disposition_json = JsonValue::Null;
    if let Some(disposition) = disposition {
        disposition_json = object! { resolution: disposition.resolution.clone() };
        for (key, value) in &disposition.fields {
            disposition_json[key] = value.clone().into();
        }
    }

    object! {
        path: path,
        role: role,
        priority: priority,
        finding: finding,
        exposure_class: exposure_class,
        recommendation: recommendation,
        rationale: rationale,
        channels: channels,
        has_agent_facing_route: has_agent_facing_route,
        skill_consumers: skill_consumers,
        total_consumers: total_consumers,
        consumer_accessibility: clone_or_null(row, "consumer_accessibility"),
        consumer_access_next_action: clone_or_null(row, "consumer_access_next_action"),
        lifecycle_id: clone_or_null(row, "lifecycle_id"),
        lifecycle_state: clone_or_null(row, "lifecycle_state"),
        role_source: str_field(row, "role_source", ""),
        override_rationale: clone_or_null(row, "override_rationale"),
        wrapper_for: clone_or_null(row, "wrapper_for"),
        protected_install_surface: bool_field(row, "protected_install_surface"),
        supported_harnesses: clone_or_array(row, "supported_harnesses"),
        evidence: clone_or_array(row, "evidence"),
        consumers: consumers(row),
        disposition: disposition_json,
    }
}

fn yaml_string(value: &Yaml) -> Option<String> {
    value.as_str().map(ToString::to_string)
}

pub fn load_dispositions(path: &Path) -> Result<BTreeMap<String, Disposition>> {
    if !path.exists() {
        return Ok(BTreeMap::new());
    }
    let raw = fs::read_to_string(path)
        .with_context(|| format!("reading dispositions {}", path.display()))?;
    let docs = YamlLoader::load_from_str(&raw)
        .with_context(|| format!("parsing dispositions {}", path.display()))?;
    let root = docs
        .first()
        .ok_or_else(|| anyhow!("empty dispositions file: {}", path.display()))?;
    let mut out = BTreeMap::new();
    for section in ["routes", "scripts"] {
        if let Some(rows) = root[section].as_vec() {
            for row in rows {
                let Some(path_value) = yaml_string(&row["path"]) else {
                    continue;
                };
                let mut fields = BTreeMap::new();
                for key in ["path", "route", "rationale", "owner", "evidence"] {
                    if let Some(value) = yaml_string(&row[key]) {
                        fields.insert(key.to_string(), value);
                    }
                }
                let resolution = yaml_string(&row["resolution"]).unwrap_or_default();
                out.insert(path_value, Disposition { resolution, fields });
            }
        }
    }
    Ok(out)
}

fn display_path(project_dir: &Path, path: &Path, require_exists_for_relative: bool) -> String {
    if (!require_exists_for_relative || path.exists()) && path.starts_with(project_dir) {
        path.strip_prefix(project_dir)
            .unwrap_or(path)
            .display()
            .to_string()
    } else {
        path.display().to_string()
    }
}

fn resolve_path(project_dir: &Path, path: Option<PathBuf>, default: &str) -> PathBuf {
    let selected = path.unwrap_or_else(|| PathBuf::from(default));
    if selected.is_absolute() {
        selected
    } else {
        project_dir.join(selected)
    }
}

pub fn build_audit(
    project_dir: &Path,
    ledger_path: Option<PathBuf>,
    dispositions_path: Option<PathBuf>,
    limit_per_priority: Option<usize>,
) -> Result<JsonValue> {
    let ledger_file = resolve_path(project_dir, ledger_path, DEFAULT_LEDGER);
    let raw = fs::read_to_string(&ledger_file)
        .with_context(|| format!("scripts ledger not found: {}", ledger_file.display()))?;
    let ledger = json::parse(&raw).with_context(|| {
        format!(
            "scripts ledger must be valid JSON: {}",
            ledger_file.display()
        )
    })?;
    if !ledger.is_object() {
        return Err(anyhow!(
            "scripts ledger must be a JSON object: {}",
            ledger_file.display()
        ));
    }
    if !ledger["scripts"].is_array() {
        return Err(anyhow!(
            "scripts ledger has no scripts list: {}",
            ledger_file.display()
        ));
    }

    let disposition_file = resolve_path(project_dir, dispositions_path, DEFAULT_DISPOSITIONS);
    let dispositions = load_dispositions(&disposition_file)?;

    let mut findings: Vec<JsonValue> = ledger["scripts"]
        .members()
        .filter(|row| row.is_object())
        .map(|row| classify_script(row, dispositions.get(row["path"].as_str().unwrap_or(""))))
        .collect();
    findings.sort_by(|a, b| {
        let ap = PRIORITIES
            .iter()
            .position(|p| *p == a["priority"].as_str().unwrap_or(""))
            .unwrap_or(99);
        let bp = PRIORITIES
            .iter()
            .position(|p| *p == b["priority"].as_str().unwrap_or(""))
            .unwrap_or(99);
        ap.cmp(&bp).then_with(|| {
            a["path"]
                .as_str()
                .unwrap_or("")
                .cmp(b["path"].as_str().unwrap_or(""))
        })
    });

    let total_scripts = findings.len() as i64;
    let mut by_priority: BTreeMap<String, i64> =
        PRIORITIES.iter().map(|p| (p.to_string(), 0)).collect();
    let mut by_role: BTreeMap<String, i64> = BTreeMap::new();
    let mut by_exposure_class: BTreeMap<String, i64> = BTreeMap::new();
    let mut agentic_without_skill = 0;
    let mut maintainer_zero_consumers = 0;
    let mut maintainer_without_skill_with_consumers = 0;
    let mut allowed_no_skill_roles = 0;

    for finding in &findings {
        let priority = finding["priority"].as_str().unwrap_or("").to_string();
        let role = finding["role"].as_str().unwrap_or("").to_string();
        let exposure_class = finding["exposure_class"].as_str().unwrap_or("").to_string();
        *by_priority.entry(priority).or_insert(0) += 1;
        *by_role.entry(role).or_insert(0) += 1;
        *by_exposure_class.entry(exposure_class).or_insert(0) += 1;
        match finding["finding"].as_str().unwrap_or("") {
            "agentic-primitive-without-skill-consumer" => agentic_without_skill += 1,
            "maintainer-tool-with-zero-consumers" => maintainer_zero_consumers += 1,
            "maintainer-tool-without-skill-consumer" => {
                maintainer_without_skill_with_consumers += 1
            }
            "role-allows-no-skill-consumer" => allowed_no_skill_roles += 1,
            _ => {}
        }
    }

    let mut report_findings = array![];
    if let Some(limit) = limit_per_priority {
        for priority in PRIORITIES {
            for finding in findings
                .iter()
                .filter(|f| f["priority"].as_str().unwrap_or("") == priority)
                .take(limit)
            {
                report_findings
                    .push(finding.clone())
                    .expect("array push cannot fail");
            }
        }
    } else {
        for finding in findings {
            report_findings
                .push(finding)
                .expect("array push cannot fail");
        }
    }

    let p0_count = *by_priority.get("P0").unwrap_or(&0);
    Ok(object! {
        schema_version: SCHEMA_VERSION,
        adr: "ADR-283",
        status: if p0_count > 0 { "warn" } else { "pass" },
        ledger_path: display_path(project_dir, &ledger_file, false),
        ledger_schema_version: if ledger["schema_version"].is_null() { JsonValue::Null } else { ledger["schema_version"].clone() },
        dispositions_path: display_path(project_dir, &disposition_file, true),
        summary: object! {
            total_scripts: total_scripts,
            by_priority: map_to_object(&by_priority),
            by_role: map_to_object(&by_role),
            agentic_without_skill: agentic_without_skill,
            maintainer_zero_consumers: maintainer_zero_consumers,
            maintainer_without_skill_with_consumers: maintainer_without_skill_with_consumers,
            allowed_no_skill_roles: allowed_no_skill_roles,
            by_exposure_class: map_to_object(&by_exposure_class),
        },
        findings: report_findings,
    })
}

fn map_to_object(map: &BTreeMap<String, i64>) -> JsonValue {
    let mut out = JsonValue::new_object();
    for (key, value) in map {
        out[key.as_str()] = (*value).into();
    }
    out
}

pub fn render_markdown(report: &JsonValue) -> Result<String> {
    let summary = &report["summary"];
    let mut lines = vec![
        "# Script Exposure Audit".to_string(),
        "".to_string(),
        format!(
            "Schema: `{}`  ",
            report["schema_version"].as_str().unwrap_or("")
        ),
        format!("ADR: `{}`  ", report["adr"].as_str().unwrap_or("")),
        format!("Status: `{}`  ", report["status"].as_str().unwrap_or("")),
        format!("Ledger: `{}`", report["ledger_path"].as_str().unwrap_or("")),
        "".to_string(),
        "## Summary".to_string(),
        "".to_string(),
        format!(
            "- Total scripts: {}",
            summary["total_scripts"].as_i64().unwrap_or(0)
        ),
        format!(
            "- P0 agentic primitives without skill consumer: {}",
            summary["by_priority"]["P0"].as_i64().unwrap_or(0)
        ),
        format!(
            "- P0 unrouted: {}",
            summary["by_exposure_class"]["P0-unrouted"]
                .as_i64()
                .unwrap_or(0)
        ),
        format!(
            "- P0 route undocumented: {}",
            summary["by_exposure_class"]["P0-route-undocumented"]
                .as_i64()
                .unwrap_or(0)
        ),
        format!(
            "- P0 promotion candidates: {}",
            summary["by_exposure_class"]["P0-promotion-candidate"]
                .as_i64()
                .unwrap_or(0)
        ),
        format!(
            "- P1 maintainer tools with zero consumers: {}",
            summary["by_priority"]["P1"].as_i64().unwrap_or(0)
        ),
        format!(
            "- P2 maintainer tools without skill consumer: {}",
            summary["by_priority"]["P2"].as_i64().unwrap_or(0)
        ),
        format!(
            "- P3 allowed no-skill roles: {}",
            summary["by_priority"]["P3"].as_i64().unwrap_or(0)
        ),
        "".to_string(),
        "## Findings".to_string(),
        "".to_string(),
    ];

    for priority in ["P0", "P1", "P2", "P3"] {
        let rows: Vec<&JsonValue> = report["findings"]
            .members()
            .filter(|finding| finding["priority"].as_str().unwrap_or("") == priority)
            .collect();
        if rows.is_empty() {
            continue;
        }
        lines.push(format!("### {priority}"));
        lines.push("".to_string());
        for row in rows {
            let channels = ["skill", "hook", "router", "script", "test", "doc", "config"]
                .into_iter()
                .filter_map(|key| {
                    let value = row["channels"][key].as_i64().unwrap_or(0);
                    if value > 0 {
                        Some(format!("{key}={value}"))
                    } else {
                        None
                    }
                })
                .collect::<Vec<_>>()
                .join(", ");
            let channels = if channels.is_empty() {
                "none".to_string()
            } else {
                channels
            };
            lines.push(format!(
                "- `{}` — {}; finding: {}; recommendation: `{}`; channels: {}",
                row["path"].as_str().unwrap_or(""),
                row["exposure_class"].as_str().unwrap_or(""),
                row["finding"].as_str().unwrap_or(""),
                row["recommendation"].as_str().unwrap_or(""),
                channels
            ));
        }
        lines.push("".to_string());
    }
    Ok(format!("{}\n", lines.join("\n").trim_end()))
}
