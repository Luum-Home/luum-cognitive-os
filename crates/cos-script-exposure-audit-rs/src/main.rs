use anyhow::Result;
use clap::Parser;
use cos_script_exposure_audit_rs::{build_audit, render_markdown};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Parser)]
#[command(about = "Rust parity CLI for ADR-283 script exposure audit")]
struct Args {
    #[arg(long, default_value = ".")]
    project_dir: PathBuf,
    #[arg(long)]
    ledger: Option<PathBuf>,
    #[arg(long)]
    dispositions: Option<PathBuf>,
    #[arg(long, value_parser = ["markdown", "json"], default_value = "markdown")]
    format: String,
    #[arg(long = "json")]
    json: bool,
    #[arg(long)]
    limit_per_priority: Option<usize>,
    #[arg(long)]
    json_out: Option<PathBuf>,
    #[arg(long)]
    md_out: Option<PathBuf>,
    #[arg(long)]
    fail_p0: bool,
}

fn main() -> Result<std::process::ExitCode> {
    let args = Args::parse();
    let output_format = if args.json {
        "json"
    } else {
        args.format.as_str()
    };
    let project_dir = args.project_dir.canonicalize().unwrap_or(args.project_dir);
    let report = build_audit(
        &project_dir,
        args.ledger,
        args.dispositions,
        args.limit_per_priority,
    )?;

    if let Some(path) = args.json_out {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(path, json::stringify_pretty(report.clone(), 2) + "\n")?;
    }
    if let Some(path) = args.md_out {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(path, render_markdown(&report)?)?;
    }

    if output_format == "json" {
        println!("{}", json::stringify_pretty(report.clone(), 2));
    } else {
        print!("{}", render_markdown(&report)?);
    }

    let p0 = report["summary"]["by_priority"]["P0"].as_i64().unwrap_or(0);
    Ok(if args.fail_p0 && p0 > 0 {
        std::process::ExitCode::from(2)
    } else {
        std::process::ExitCode::SUCCESS
    })
}
