# Step 05: Write Tests

## Status
PENDING

## Objective
Write unit tests for use case and integration tests for the endpoint.

## Inputs
- Use case from step-03
- Controller from step-04
- Acceptance criteria from spec

## Actions
1. Create use case unit test with mocked repository
2. Create controller integration test
3. Verify all acceptance criteria from spec are covered
4. Run tests and ensure they pass
5. Check coverage meets 80% minimum

## Outputs
- `internal/application/usecases/{operation}_{entity}_usecase_test.go`
- `internal/infrastructure/controllers/{entity}_controller_test.go`

## Success Criteria
- [ ] Unit tests cover happy path and error cases
- [ ] Integration test hits the endpoint and validates response
- [ ] All tests pass
- [ ] Coverage >= 80% for new code

## Notes
