use assert_cmd::Command;
use json::JsonValue;
use std::path::PathBuf;

fn fixture(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures")
        .join(name)
}

fn project_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|path| path.parent())
        .expect("crate should live under <repo>/crates/<crate>")
        .to_path_buf()
}

fn python_bin(root: &std::path::Path) -> PathBuf {
    if let Ok(path) = std::env::var("COS_PYTHON") {
        return PathBuf::from(path);
    }
    let venv_python = root.join(".venv/bin/python");
    if venv_python.exists() {
        return venv_python;
    }
    PathBuf::from("python3")
}

fn run_python_json(root: &std::path::Path, args: &[&str]) -> JsonValue {
    let output = std::process::Command::new(python_bin(root))
        .arg(root.join("scripts/cos-script-exposure-audit"))
        .args(args)
        .output()
        .expect("python script exposure audit should run");
    assert!(
        output.status.success(),
        "python audit failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    json::parse(std::str::from_utf8(&output.stdout).unwrap()).unwrap()
}

fn run_json(args: &[&str]) -> JsonValue {
    let output = Command::cargo_bin("cos-script-exposure-audit-rs")
        .unwrap()
        .args(args)
        .assert()
        .success()
        .get_output()
        .stdout
        .clone();
    json::parse(std::str::from_utf8(&output).unwrap()).unwrap()
}

#[test]
fn outputs_json_report_for_fixture() {
    let ledger = fixture("ledger.json");
    let ledger = ledger.to_str().unwrap();
    let report = run_json(&[
        "--project-dir",
        env!("CARGO_MANIFEST_DIR"),
        "--ledger",
        ledger,
        "--json",
    ]);
    assert_eq!(report["schema_version"], "script-exposure-audit/v1");
    assert_eq!(report["summary"]["by_priority"]["P0"], 1);
    assert_eq!(report["summary"]["by_exposure_class"]["P0-unrouted"], 1);
    assert_eq!(report["summary"]["by_priority"]["P2"], 3);
}

#[test]
fn fail_p0_exits_two() {
    let ledger = fixture("ledger.json");
    Command::cargo_bin("cos-script-exposure-audit-rs")
        .unwrap()
        .args(["--project-dir", env!("CARGO_MANIFEST_DIR"), "--ledger"])
        .arg(ledger)
        .args(["--fail-p0", "--json"])
        .assert()
        .code(2);
}

#[test]
fn accepts_dispositions_manifest() {
    let ledger = fixture("ledger.json");
    let dispositions = fixture("dispositions.yaml");
    let report = run_json(&[
        "--project-dir",
        env!("CARGO_MANIFEST_DIR"),
        "--ledger",
        ledger.to_str().unwrap(),
        "--dispositions",
        dispositions.to_str().unwrap(),
        "--json",
    ]);
    assert_eq!(report["summary"]["by_priority"]["P0"], 0);
    assert_eq!(report["summary"]["by_priority"]["P2"], 1);
    assert_eq!(
        report["summary"]["by_exposure_class"]["OK-documented-route"],
        1
    );
    assert_eq!(
        report["summary"]["by_exposure_class"]["OK-internal-backend"],
        1
    );
    assert_eq!(
        report["summary"]["by_exposure_class"]["OK-operator-workflow"],
        1
    );
}

#[test]
fn preserves_non_string_disposition_fields() {
    let ledger = fixture("ledger.json");
    let dispositions = fixture("dispositions.yaml");
    let report = run_json(&[
        "--project-dir",
        env!("CARGO_MANIFEST_DIR"),
        "--ledger",
        ledger.to_str().unwrap(),
        "--dispositions",
        dispositions.to_str().unwrap(),
        "--json",
    ]);
    let finding = report["findings"]
        .members()
        .find(|finding| finding["path"] == "scripts/internal-backend.py")
        .expect("internal backend fixture finding should exist");
    let disposition = &finding["disposition"];

    assert_eq!(disposition["resolution"], "internal_backend");
    assert_eq!(disposition["evidence"][0], "tests/parity.rs");
    assert_eq!(disposition["evidence"][1], "scripts/internal-wrapper");
    assert_eq!(disposition["metadata"]["nested_owner"]["team"], "synthetic");
    assert_eq!(disposition["metadata"]["priority"], 2);
    assert_eq!(disposition["audited"], true);
    assert_eq!(disposition["confidence"], 0.75);
}

#[test]
fn real_ledger_matches_python_report_exactly() {
    let root = project_root();
    let root_str = root.to_str().unwrap();
    let rust_report = run_json(&["--project-dir", root_str, "--json"]);
    let python_report = run_python_json(&root, &["--project-dir", root_str, "--json"]);

    assert_eq!(rust_report, python_report);
}
