import { useApiFetch } from "@/services/shared";
import type {
  CreateTenantRequest,
  CreateTenantResponse,
  UpdateTenantRequest,
  UpdateTenantResponse,
  DeleteTenantResponse,
  ListTenantsRequest,
  ListTenantsResponse,
} from "./types";

/**
 * Creates a new tenant with an initial user.
 */
export const createTenant = (request: CreateTenantRequest) => {
  return useApiFetch("/auth/tenants", {
    immediate: false,
  })
    .post(request)
    .json<CreateTenantResponse>();
};

/**
 * Lists all tenants with pagination and filtering.
 */
export const listTenants = (request?: ListTenantsRequest) => {
  const params = new URLSearchParams();
  if (request?.page) params.append("page", request.page.toString());
  if (request?.page_size)
    params.append("page_size", request.page_size.toString());
  if (request?.search) params.append("search", request.search);
  if (request?.sort_by) params.append("sort_by", request.sort_by);
  if (request?.sort_order) params.append("sort_order", request.sort_order);

  const queryString = params.toString();
  const url = queryString ? `/auth/tenants?${queryString}` : "/auth/tenants";

  return useApiFetch(url, {
    immediate: false,
  })
    .get()
    .json<ListTenantsResponse>();
};

/**
 * Updates a tenant's name.
 */
export const updateTenant = (
  tenantId: string,
  request: UpdateTenantRequest
) => {
  return useApiFetch(`/auth/tenants/${tenantId}`, {
    immediate: false,
  })
    .patch(request)
    .json<UpdateTenantResponse>();
};

/**
 * Deletes a tenant and all associated data.
 */
export const deleteTenant = (tenantId: string) => {
  return useApiFetch(`/auth/tenants/${tenantId}`, {
    immediate: false,
  })
    .delete()
    .json<DeleteTenantResponse>();
};
