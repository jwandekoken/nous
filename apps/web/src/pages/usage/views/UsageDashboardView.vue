<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { Navigation } from "@/components/layout/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { fetchUsageEvents, fetchUsageSummary } from "@/services/usage";
import type {
  UsageEvent,
  UsageSummaryResponse,
  PaginationMeta,
} from "@/services/usage";
import { toast } from "vue-sonner";

// =============================================================================
// State
// =============================================================================

const events = ref<UsageEvent[]>([]);
const summary = ref<UsageSummaryResponse | null>(null);
const pagination = ref<PaginationMeta>({ page: 1, limit: 50, total: 0 });

const isFetchingEvents = ref(false);
const isFetchingSummary = ref(false);
const errorMessage = ref<string | null>(null);

// Filters (use "all" instead of "" for Select compatibility)
const filters = ref({
  from: getDefaultFromDate(),
  to: getDefaultToDate(),
  operation: "all",
  status: "all",
});

// =============================================================================
// Computed
// =============================================================================

const isLoading = computed(
  () => isFetchingEvents.value || isFetchingSummary.value,
);

const totalPages = computed(() =>
  Math.ceil(pagination.value.total / pagination.value.limit),
);

const hasNextPage = computed(() => pagination.value.page < totalPages.value);

const hasPrevPage = computed(() => pagination.value.page > 1);

// =============================================================================
// Helpers
// =============================================================================

function getDefaultFromDate(): string {
  const date = new Date();
  date.setDate(date.getDate() - 30);
  return date.toISOString().split("T")[0]!;
}

function getDefaultToDate(): string {
  return new Date().toISOString().split("T")[0]!;
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatCost(value: number | string | null): string {
  if (value === null || value === undefined) return "—";
  const numValue = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(numValue)) return "—";
  return `$${numValue.toFixed(4)}`;
}

function formatTokens(value: number | string | null): string {
  if (value === null || value === undefined) return "—";
  const numValue = typeof value === "string" ? parseInt(value, 10) : value;
  if (isNaN(numValue)) return "—";
  return numValue.toLocaleString();
}

function getStatusVariant(status: string): "default" | "destructive" {
  return status === "ok" ? "default" : "destructive";
}

// =============================================================================
// Data Fetching
// =============================================================================

async function loadSummary() {
  isFetchingSummary.value = true;
  try {
    const { execute, data, error, statusCode } = fetchUsageSummary({
      from: filters.value.from,
      to: filters.value.to,
      operation:
        filters.value.operation === "all" ? undefined : filters.value.operation,
    });

    await execute();

    if (statusCode.value === 200 && data.value) {
      summary.value = data.value;
    } else {
      toast.error("Failed to load usage summary", {
        description: error.value?.message || "Unexpected error occurred",
      });
    }
  } catch (err) {
    toast.error("Failed to load usage summary", {
      description:
        err instanceof Error ? err.message : "Unexpected error occurred",
    });
  } finally {
    isFetchingSummary.value = false;
  }
}

async function loadEvents(page = 1) {
  isFetchingEvents.value = true;
  errorMessage.value = null;

  try {
    const { execute, data, error, statusCode } = fetchUsageEvents({
      from: filters.value.from,
      to: filters.value.to,
      operation:
        filters.value.operation === "all" ? undefined : filters.value.operation,
      status: filters.value.status === "all" ? undefined : filters.value.status,
      page,
      limit: pagination.value.limit,
    });

    await execute();

    if (statusCode.value === 200 && data.value) {
      events.value = data.value.events;
      pagination.value = data.value.pagination;
    } else {
      errorMessage.value =
        error.value?.message || "Failed to load usage events";
      toast.error("Failed to load usage events", {
        description: error.value?.message || "Unexpected error occurred",
      });
    }
  } catch (err) {
    errorMessage.value =
      err instanceof Error ? err.message : "Unexpected error occurred";
    toast.error("Failed to load usage events", {
      description:
        err instanceof Error ? err.message : "Unexpected error occurred",
    });
  } finally {
    isFetchingEvents.value = false;
  }
}

async function applyFilters() {
  await Promise.all([loadSummary(), loadEvents(1)]);
}

async function goToPage(page: number) {
  await loadEvents(page);
}

// =============================================================================
// Lifecycle
// =============================================================================

onMounted(() => {
  applyFilters();
});
</script>

<template>
  <div class="min-h-screen bg-background">
    <Navigation />

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Header -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-foreground mb-4">Usage Dashboard</h1>
        <p class="text-lg text-muted-foreground max-w-2xl">
          Monitor your LLM and embedding token consumption, track costs over
          time, and analyze usage patterns.
        </p>
      </div>

      <!-- Filters -->
      <div class="mb-6 p-4 bg-card rounded-lg border border-border shadow-sm">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <div class="space-y-2">
            <Label for="filter-from">From</Label>
            <Input id="filter-from" type="date" v-model="filters.from" />
          </div>
          <div class="space-y-2">
            <Label for="filter-to">To</Label>
            <Input id="filter-to" type="date" v-model="filters.to" />
          </div>
          <div class="space-y-2">
            <Label for="filter-operation">Operation</Label>
            <Select v-model="filters.operation">
              <SelectTrigger id="filter-operation">
                <SelectValue placeholder="All operations" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All operations</SelectItem>
                <SelectItem value="fact_extract">Fact Extract</SelectItem>
                <SelectItem value="entity_summary">Entity Summary</SelectItem>
                <SelectItem value="semantic_memory_embed"
                  >Semantic Memory Embed</SelectItem
                >
                <SelectItem value="rag_query_embed">RAG Query Embed</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="space-y-2">
            <Label for="filter-status">Status</Label>
            <Select v-model="filters.status">
              <SelectTrigger id="filter-status">
                <SelectValue placeholder="All statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem value="ok">OK</SelectItem>
                <SelectItem value="error">Error</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="flex items-end">
            <Button @click="applyFilters" :disabled="isLoading" class="w-full">
              {{ isLoading ? "Loading..." : "Apply Filters" }}
            </Button>
          </div>
        </div>
      </div>

      <!-- Summary Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader class="pb-2">
            <CardTitle class="text-sm font-medium text-muted-foreground">
              Total Tokens
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div class="text-3xl font-bold text-foreground">
              <template v-if="isFetchingSummary">
                <span class="text-muted-foreground">Loading...</span>
              </template>
              <template v-else-if="summary">
                {{ formatTokens(summary.total_tokens) }}
              </template>
              <template v-else>—</template>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader class="pb-2">
            <CardTitle class="text-sm font-medium text-muted-foreground">
              Total Cost
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div class="text-3xl font-bold text-foreground">
              <template v-if="isFetchingSummary">
                <span class="text-muted-foreground">Loading...</span>
              </template>
              <template v-else-if="summary">
                {{ formatCost(summary.total_cost_usd) }}
              </template>
              <template v-else>—</template>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader class="pb-2">
            <CardTitle class="text-sm font-medium text-muted-foreground">
              Period
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div class="text-lg font-medium text-foreground">
              {{ filters.from }} — {{ filters.to }}
            </div>
            <p class="text-sm text-muted-foreground mt-1">
              {{ pagination.total }} event{{
                pagination.total === 1 ? "" : "s"
              }}
            </p>
          </CardContent>
        </Card>
      </div>

      <!-- Events Table -->
      <div
        class="bg-card rounded-lg shadow-md border border-border overflow-hidden"
      >
        <div class="px-4 py-3 border-b border-border">
          <h2 class="text-lg font-semibold text-foreground">Usage Events</h2>
        </div>

        <div v-if="isFetchingEvents" class="p-8 text-center">
          <p class="text-muted-foreground">Loading usage events...</p>
        </div>

        <div v-else-if="errorMessage" class="p-8 text-center">
          <p class="text-destructive">{{ errorMessage }}</p>
          <Button variant="outline" class="mt-4" @click="applyFilters">
            Retry
          </Button>
        </div>

        <div v-else-if="events.length === 0" class="p-8 text-center space-y-2">
          <p class="text-muted-foreground">No usage events found</p>
          <p class="text-sm text-muted-foreground">
            Try adjusting the date range or filters.
          </p>
        </div>

        <Table v-else>
          <TableHeader>
            <TableRow>
              <TableHead>Date/Time</TableHead>
              <TableHead>Operation</TableHead>
              <TableHead>Model</TableHead>
              <TableHead class="text-right">Prompt</TableHead>
              <TableHead class="text-right">Completion</TableHead>
              <TableHead class="text-right">Total</TableHead>
              <TableHead class="text-right">Cost</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="event in events" :key="event.id">
              <TableCell
                class="text-sm text-muted-foreground whitespace-nowrap"
              >
                {{ formatDate(event.created_at) }}
              </TableCell>
              <TableCell class="font-medium text-foreground">
                {{ event.operation }}
              </TableCell>
              <TableCell class="text-sm text-muted-foreground font-mono">
                {{ event.model || "—" }}
              </TableCell>
              <TableCell class="text-right text-sm tabular-nums">
                {{ formatTokens(event.prompt_tokens) }}
              </TableCell>
              <TableCell class="text-right text-sm tabular-nums">
                {{ formatTokens(event.completion_tokens) }}
              </TableCell>
              <TableCell class="text-right text-sm font-medium tabular-nums">
                {{ formatTokens(event.total_tokens) }}
              </TableCell>
              <TableCell class="text-right text-sm tabular-nums">
                {{ formatCost(event.cost_usd) }}
              </TableCell>
              <TableCell>
                <Badge :variant="getStatusVariant(event.status)">
                  {{ event.status }}
                </Badge>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>

        <!-- Pagination -->
        <div
          v-if="events.length > 0"
          class="px-4 py-3 border-t border-border flex items-center justify-between"
        >
          <p class="text-sm text-muted-foreground">
            Page {{ pagination.page }} of {{ totalPages }} ({{
              pagination.total
            }}
            total)
          </p>
          <div class="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              :disabled="!hasPrevPage || isFetchingEvents"
              @click="goToPage(pagination.page - 1)"
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              :disabled="!hasNextPage || isFetchingEvents"
              @click="goToPage(pagination.page + 1)"
            >
              Next
            </Button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
