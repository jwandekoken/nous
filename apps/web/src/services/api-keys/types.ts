export interface CreateApiKeyRequest {
  name: string;
}

export interface CreateApiKeyResponse {
  message: string;
  api_key: string;
  key_prefix: string;
  expires_at: string | null;
}

export interface ApiKeySummary {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  expires_at: string | null;
  last_used_at: string | null;
}

export interface ListApiKeysResponse {
  api_keys: ApiKeySummary[];
}

export interface DeleteApiKeyResponse {
  message: string;
}
