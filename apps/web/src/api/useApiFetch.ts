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
