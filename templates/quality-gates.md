<!-- SCOPE: both -->

# Quality Gates

Before marking work complete, verify ALL of these:

1. **Build**: Code compiles without errors (`go build ./...` or framework equivalent)
2. **Tests**: All tests pass (`go test ./...` or `bun test` / `bun run test`)
3. **Coverage**: Meets or exceeds threshold from cognitive-os.yaml
4. **Lint**: No lint errors (`golangci-lint run` or `bun run lint`)
5. **Architecture**: Domain layer has no infrastructure imports. Controllers contain no business logic. Cross-service calls use sdks only.

If any gate fails, fix before returning. Do not skip gates.
