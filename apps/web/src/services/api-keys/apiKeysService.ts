import { useApiFetch } from "@/services/shared";
import type {
  CreateApiKeyRequest,
  CreateApiKeyResponse,
  DeleteApiKeyResponse,
  ListApiKeysResponse,
} from "./types";

/**
 * Create a new API key for the current tenant.
 */
export const createApiKey = (request: CreateApiKeyRequest) => {
  return useApiFetch("/auth/api-keys", {
    immediate: false,
  })
    .post(request)
    .json<CreateApiKeyResponse>();
};

/**
 * List all API keys for the current tenant.
 */
export const listApiKeys = () => {
  return useApiFetch("/auth/api-keys", {
    immediate: false,
  })
    .get()
    .json<ListApiKeysResponse>();
};

/**
 * Delete an API key by ID.
 */
export const deleteApiKey = (apiKeyId: string) => {
  return useApiFetch(`/auth/api-keys/${apiKeyId}`, {
    immediate: false,
  })
    .delete()
    .json<DeleteApiKeyResponse>();
};
