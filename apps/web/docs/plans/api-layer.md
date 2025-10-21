# API Layer Implementation Plan

## 1. Objective

This document outlines the plan to implement the API communication layer for the Vue.js frontend, connecting it to our FastAPI backend. We will use the `@vueuse/core` library, specifically its `useFetch` composable, to handle all HTTP requests in a reactive and efficient manner.

The goal is to create a clean, reusable, and type-safe API layer.

## 2. Core Utility: `createFetch`

To avoid repeating configuration and to establish a consistent base for all API calls, we will use `createFetch`. This utility allows us to create a custom, pre-configured instance of `useFetch`.

We will create this instance in `apps/web/src/api/useApiFetch.ts`.

**Key Configurations:**

- **`baseUrl`**: All requests will be automatically prefixed with the API base URL (`http://localhost:8000/api/v1`).
- **`fetchOptions`**: We will set default headers, such as `Content-Type: application/json`.
- **Error Handling**: A default `onFetchError` handler will be configured to centrally manage and log API errors.

**`apps/web/src/api/useApiFetch.ts`**

```typescript
import { createFetch } from "@vueuse/core";

const BASE_URL = "http://localhost:8000/api/v1"; // Or from .env

export const useApiFetch = createFetch({
  baseUrl: BASE_URL,
  options: {
    // Standard hooks that run before every fetch call
    async beforeFetch({ options }) {
      // Here you could add authentication tokens to headers
      // const myAuthToken = '...'
      // options.headers.Authorization = `Bearer ${myAuthToken}`
      return { options };
    },
  },
  // Default options for the fetch request itself
  fetchOptions: {
    headers: {
      "Content-Type": "application/json",
    },
  },
});
```

## 3. API Function Implementations

All API functions related to the `graph` feature will be located in `apps/web/src/features/graph/api/graphApi.ts`. These functions will encapsulate the logic for each endpoint, providing a clean interface for our Vue components and Pinia stores.

They are designed as "composables" (and named with a `use` prefix) that return the entire reactive `UseFetchReturn` object from `@vueuse/core`. This gives you direct, reactive access to `data`, `isFetching`, `error`, and other properties.

### 3.1. Looking up an Entity (Reactive Composable)

This composable will fetch an entity and its related facts. It's designed to be fully reactive: if you pass it a `ref` for its parameters, it will automatically refetch when the parameters change.

- **Endpoint**: `GET /graph/entities/lookup`
- **Method**: `GET`
- **Query Parameters**: `type: string`, `value: string`

**`apps/web/src/features/graph/api/graphApi.ts`**

```typescript
import { useApiFetch } from "@/api";
import type { GetEntityResponse } from "@/types/api";
import { computed, toValue, type MaybeRefOrGetter } from "vue";

export interface FindEntityParams {
  type: string;
  value: string;
}

export const useFindEntityByIdentifier = (
  params: MaybeRefOrGetter<FindEntityParams>
) => {
  // The URL is a computed property, reacting to changes in `params`
  const url = computed(() => {
    const resolvedParams = toValue(params);
    // Return empty string to prevent invalid requests, let consumers handle empty state
    if (!resolvedParams || !resolvedParams.value) {
      return "";
    }
    return `/graph/entities/lookup?type=${resolvedParams.type}&value=${resolvedParams.value}`;
  });

  // The full reactive useFetch object is returned.
  return useApiFetch(url, {
    refetch: true,
    immediate: false, // Don't execute immediately, let consumers control execution
  })
    .get()
    .json<GetEntityResponse>();
};
```

### 3.2. Assimilating Knowledge (Action Trigger)

This function will send new content to the backend. Since this is a `POST` request (a mutation), it's designed to be called explicitly as an action, rather than reacting to changes. You can still access `isFetching` and `error` states after calling it.

- **Endpoint**: `POST /graph/entities/assimilate`
- **Method**: `POST`
- **Request Body**: `AssimilateKnowledgeRequest`

**`apps/web/src/features/graph/api/graphApi.ts` (continued)**

```typescript
// ... imports
import type {
  AssimilateKnowledgeRequest,
  AssimilateKnowledgeResponse,
} from "@/types/api";

// ... useFindEntityByIdentifier function

export const useAssimilateKnowledge = (payload: AssimilateKnowledgeRequest) => {
  const url = "/graph/entities/assimilate";

  // Use the .post() convenience method, passing the payload.
  // This returns the reactive useFetch object, which you can `await` or
  // use to track the state of the POST request.
  return useApiFetch(url).post(payload).json<AssimilateKnowledgeResponse>();
};
```

## 4. TypeScript Types

To ensure type safety across the application, we will define TypeScript interfaces that mirror the Pydantic DTOs from the backend. These will reside in `apps/web/src/types/api.ts`.

**`apps/web/src/types/api.ts`**

```typescript
// Base DTOs
export interface IdentifierDto {
  value: string;
  type: string;
}

export interface EntityDto {
  id: string; // UUID is a string in TS
  created_at: string; // ISO date string
  metadata?: Record<string, string> | null;
}

export interface FactDto {
  name: string;
  type: string;
  fact_id?: string | null;
}

export interface SourceDto {
  id: string; // UUID
  content: string;
  timestamp: string; // ISO date string
}

export interface HasFactDto {
  verb: string;
  confidence_score: number;
  created_at: string; // ISO date string
}

// Request Payloads
export interface AssimilateKnowledgeRequest {
  identifier: IdentifierDto;
  content: string;
  timestamp?: string | null; // ISO date string
  history?: string[] | null;
}

// API Responses
export interface AssimilatedFactDto {
  fact: FactDto;
  relationship: HasFactDto;
}

export interface AssimilateKnowledgeResponse {
  entity: EntityDto;
  source: SourceDto;
  assimilated_facts: AssimilatedFactDto[];
}

export interface HasIdentifierDto {
  is_primary: boolean;
  created_at: string; // ISO date string
}

export interface IdentifierWithRelationshipDto {
  identifier: IdentifierDto;
  relationship: HasIdentifierDto;
}

export interface FactWithSourceDto {
  fact: FactDto;
  relationship: HasFactDto;
  source?: SourceDto | null;
}

export interface GetEntityResponse {
  entity: EntityDto;
  identifier: IdentifierWithRelationshipDto;
  facts: FactWithSourceDto[];
}
```

## 5. Reactive Usage in a Pinia Store

With the reactive `useFindEntityByIdentifier` composable, our Pinia store becomes much simpler and more powerful. We no longer need to manage our own `isLoading` or `error` refs, as the composable provides them for us.

**Example: `apps/web/src/features/graph/store.ts` (Pinia Store)**

```typescript
import { defineStore } from "pinia";
import { ref } from "vue";
import { useFindEntityByIdentifier } from "@/api/graphApi";
import type { FindEntityParams } from "@/api/graphApi";

export const useGraphStore = defineStore("graph", () => {
  // A ref to hold the search parameters. Our API composable will react to this.
  const searchParams = ref<FindEntityParams>({ type: "email", value: "" });

  // Call the composable. It's that simple.
  // `data`, `isFetching`, and `error` are all reactive refs.
  const { data, isFetching, error } = useFindEntityByIdentifier(searchParams);

  // An action that simply updates the search parameters.
  // The `useFindEntityByIdentifier` composable will automatically
  // detect the change and trigger a new API call.
  function searchEntity(params: FindEntityParams) {
    searchParams.value = params;
  }

  // Expose the reactive state and the action to the components.
  return { data, isFetching, error, searchEntity };
});
```
