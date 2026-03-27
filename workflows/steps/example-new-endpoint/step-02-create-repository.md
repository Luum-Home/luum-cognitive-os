# Step 02: Create Repository Interface and Implementation

## Status
PENDING

## Objective
Define the repository interface in domain layer and implement it in infrastructure layer.

## Inputs
- Entity from step-01
- Required query methods from spec

## Actions
1. Create repository interface at `internal/domain/{entity_name}_repository.go`
2. Extend `RepositoryInterface[Entity, uuid.UUID]` from `pkg/tools/repositories`
3. Add custom query methods to interface
4. Create implementation at `internal/infrastructure/repositories/{entity_name}_repository.go`
5. Implement all interface methods using GORM

## Outputs
- `internal/domain/{entity_name}_repository.go` — repository interface
- `internal/infrastructure/repositories/{entity_name}_repository.go` — implementation

## Success Criteria
- [ ] Interface defined in domain layer
- [ ] Implementation compiles and satisfies interface
- [ ] No business logic in repository (pure data access)
- [ ] Domain layer has no GORM imports

## Notes
