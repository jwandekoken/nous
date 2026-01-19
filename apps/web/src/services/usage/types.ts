/**
 * TypeScript types for the Usage API.
 * These mirror the backend DTOs from apps/api/app/features/usage/dtos.py
 */

// =============================================================================
// Events Endpoint Types
// =============================================================================

/**
 * Single usage event from the events list.
 * Note: cost_usd comes as string from backend Decimal serialization.
 */
export interface UsageEvent {
  id: string;
  created_at: string;
  operation: string;
  model: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  cost_usd: string | null;
  status: string;
}

/**
 * Pagination metadata.
 */
export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
}

/**
 * Response from GET /usage/events.
 */
export interface UsageEventsResponse {
  pagination: PaginationMeta;
  events: UsageEvent[];
}

/**
 * Query parameters for GET /usage/events.
 */
export interface UsageEventsParams {
  from: string;
  to: string;
  operation?: string;
  model?: string;
  actor_type?: string;
  status?: string;
  page?: number;
  limit?: number;
}

// =============================================================================
// Summary Endpoint Types
// =============================================================================

/**
 * Period for the summary response.
 */
export interface UsageSummaryPeriod {
  from_date: string;
  to_date: string;
}

/**
 * Aggregated usage for a single day.
 * Note: cost_usd comes as string from backend Decimal serialization.
 */
export interface UsageSummaryByDay {
  date: string;
  tokens: number;
  cost_usd: string;
}

/**
 * Aggregated usage for a single operation.
 * Note: cost_usd comes as string from backend Decimal serialization.
 */
export interface UsageSummaryByOperation {
  operation: string;
  tokens: number;
  cost_usd: string;
}

/**
 * Response from GET /usage/summary.
 * Note: total_cost_usd comes as string from backend Decimal serialization.
 */
export interface UsageSummaryResponse {
  period: UsageSummaryPeriod;
  total_tokens: number;
  total_cost_usd: string;
  by_day: UsageSummaryByDay[];
  by_operation: UsageSummaryByOperation[];
}

/**
 * Query parameters for GET /usage/summary.
 */
export interface UsageSummaryParams {
  from: string;
  to: string;
  operation?: string;
  model?: string;
}
