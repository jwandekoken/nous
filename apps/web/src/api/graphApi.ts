import { useApiFetch } from "@/api";
import type {
  GetEntityResponse,
  AssimilateKnowledgeRequest,
  AssimilateKnowledgeResponse,
} from "@/types/api";
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
    refetch: false, // Disable automatic refetching when URL changes
    immediate: false, // Don't execute immediately, let consumers control execution
  })
    .get()
    .json<GetEntityResponse>();
};

export const useAssimilateKnowledge = (payload: AssimilateKnowledgeRequest) => {
  const url = "/graph/entities/assimilate";

  // Use the .post() convenience method, passing the payload.
  // This returns the reactive useFetch object, which you can `await` or
  // use to track the state of the POST request.
  return useApiFetch(url).post(payload).json<AssimilateKnowledgeResponse>();
};
