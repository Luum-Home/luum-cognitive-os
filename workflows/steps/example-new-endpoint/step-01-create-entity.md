# Step 01: Create Domain Entity

## Status
PENDING

## Objective
Define the domain entity with GORM tags and table name method.

## Inputs
- Entity name and fields from the spec
- Database table name from the design document

## Actions
1. Create entity file at `internal/domain/{entity_name}_entity.go`
2. Embed `entities.EntityWithID` for UUID primary key
3. Define all fields with `gorm:"column:..."` tags
4. Implement `TableName()` method
5. Use pointer types for nullable columns

## Outputs
- `internal/domain/{entity_name}_entity.go` — domain entity file

## Success Criteria
- [ ] Entity file compiles without errors
- [ ] Entity embeds EntityWithID
- [ ] All fields have explicit GORM column tags
- [ ] TableName() method returns correct table name
- [ ] No imports from application or infrastructure layers

## Notes
