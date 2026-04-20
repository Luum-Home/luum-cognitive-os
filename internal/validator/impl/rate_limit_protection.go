package impl

// RateLimitProtectionValidator is a deprecated alias for TokenBudgetMonitorValidator.
//
// This struct was renamed to TokenBudgetMonitorValidator because the module
// monitors API *token consumption* (budget), not action-count rate limits.
// The name collided with the rate-limiter validator, causing confusion.
//
// Deprecated: use TokenBudgetMonitorValidator and NewTokenBudgetMonitorValidator.
type RateLimitProtectionValidator = TokenBudgetMonitorValidator

// NewRateLimitProtectionValidator is a deprecated alias for NewTokenBudgetMonitorValidator.
//
// Deprecated: use NewTokenBudgetMonitorValidator.
func NewRateLimitProtectionValidator(costEventsPath string, hourlyTokens int64, agentsPerHour int) *TokenBudgetMonitorValidator {
	return NewTokenBudgetMonitorValidator(costEventsPath, hourlyTokens, agentsPerHour)
}
