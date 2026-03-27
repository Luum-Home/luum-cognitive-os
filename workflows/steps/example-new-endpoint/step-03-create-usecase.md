# Step 03: Create Use Case

## Status
PENDING

## Objective
Implement the business logic use case in the application layer.

## Inputs
- Repository interface from step-02
- Business rules from spec
- Request/response DTOs from design

## Actions
1. Create DTOs at `internal/application/dtos/{operation}_{entity}_dto.go`
2. Create mapper at `internal/application/mappers/{entity}_mapper.go`
3. Create use case at `internal/application/usecases/{operation}_{entity}_usecase.go`
4. Implement `models.UseCaseInterface[Path, Query, Body, Headers, Res]`
5. Inject repository via constructor

## Outputs
- `internal/application/dtos/{operation}_{entity}_dto.go`
- `internal/application/mappers/{entity}_mapper.go`
- `internal/application/usecases/{operation}_{entity}_usecase.go`

## Success Criteria
- [ ] Use case implements UseCaseInterface
- [ ] DTOs are in application/dtos/ (NOT domain/dtos/)
- [ ] Mapper follows Map{Input}To{Output} naming
- [ ] One use case per file
- [ ] Constructor returns interface, not concrete type

## Notes
