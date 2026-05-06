# cosd standalone service templates

These templates make the ADR-184 daemon deployable outside an IDE session.

- `systemd/cosd.service` runs the file-queue arbitration loop as a user service.
- `k8s/cosd-local.yaml` exposes the local HTTP API added by ADR-193 for cluster drills.

Operators must set the workspace mount and binary path for their install layout.
The templates intentionally use local filesystem state; provider credentials are
not mounted by default.
