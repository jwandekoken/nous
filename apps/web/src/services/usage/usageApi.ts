/**
 * Usage API service functions.
 * Provides fetch functions for /usage/events and /usage/summary endpoints.
 */

import { useApiFetch } from "@/services/shared";
import type {
  UsageEventsParams,
  UsageEventsResponse,
  UsageSummaryParams,
  UsageSummaryResponse,
} from "./types";

/**
 * Builds a query string from the given parameters.
 * Filters out undefined values.
 */
const buildQueryString = (
  params: Record<string, string | number | undefined>,
): string => {
  const searchParams = new URLSearchParams();

  const keys = Object.keys(params);
  for (const key of keys) {
    const value = params[key];
    if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  }

  return searchParams.toString();
};

/**
 * Fetch paginated usage events for the current tenant.
 *
 * @param params - Query parameters including date range and optional filters
 * @returns The usage events response with pagination metadata
 */
export const fetchUsageEvents = (params: UsageEventsParams) => {
  const queryString = buildQueryString({
    from: params.from,
    to: params.to,
    operation: params.operation,
    model: params.model,
    actor_type: params.actor_type,
    status: params.status,
    page: params.page,
    limit: params.limit,
  });

  return useApiFetch(`/usage/events?${queryString}`, {
    immediate: false,
  })
    .get()
    .json<UsageEventsResponse>();
};

/**
 * Fetch aggregated usage summary for the current tenant.
 *
 * @param params - Query parameters including date range and optional filters
 * @returns The usage summary response with totals and breakdowns
 */
export const fetchUsageSummary = (params: UsageSummaryParams) => {
  const queryString = buildQueryString({
    from: params.from,
    to: params.to,
    operation: params.operation,
    model: params.model,
  });

  return useApiFetch(`/usage/summary?${queryString}`, {
    immediate: false,
  })
    .get()
    .json<UsageSummaryResponse>();
};
