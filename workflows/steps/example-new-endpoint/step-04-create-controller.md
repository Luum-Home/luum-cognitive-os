# Step 04: Create Controller and Wire Dependencies

## Status
PENDING

## Objective
Create the HTTP controller and wire all dependencies in main.go.

## Inputs
- Use case from step-03
- Endpoint path and HTTP method from design

## Actions
1. Create controller at `internal/infrastructure/controllers/{entity}_controller.go`
2. Implement `models.ControllerInterface` (BasePath + Routes)
3. Use `handlers.CreateHandler()` for request handling
4. Wire dependencies in `cmd/main.go`: repository -> use case -> controller
5. Register controller with `ginext.NewServiceBuilder()`

## Outputs
- `internal/infrastructure/controllers/{entity}_controller.go`
- Updated `cmd/main.go` with dependency wiring

## Success Criteria
- [ ] Controller implements ControllerInterface
- [ ] Handler uses CreateHandler, not raw c.JSON()
- [ ] Dependencies injected via constructor (not global state)
- [ ] Service compiles and starts successfully

## Notes
