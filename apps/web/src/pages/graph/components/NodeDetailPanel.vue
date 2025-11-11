<script setup lang="ts">
import { computed } from "vue";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

interface SelectedElement {
  type: "node" | "edge";
  data: Record<string, any>;
}

interface Props {
  selectedElement: SelectedElement | null;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  close: [];
}>();

const elementType = computed(() => {
  if (!props.selectedElement) return null;
  if (props.selectedElement.type === "edge") return "Edge";
  return props.selectedElement.data.type || "Unknown";
});

const badgeVariant = computed(() => {
  if (!elementType.value) return "default";
  const variants: Record<string, any> = {
    Entity: "default",
    Fact: "secondary",
    Identifier: "outline",
    Source: "destructive",
    Edge: "default",
  };
  return variants[elementType.value] || "default";
});

// Format date strings
const formatDate = (dateString: string | undefined) => {
  if (!dateString) return "N/A";
  try {
    return new Date(dateString).toLocaleString();
  } catch {
    return dateString;
  }
};

// Format JSON for display
const formatJSON = (obj: any) => {
  if (!obj) return "N/A";
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
};
</script>

<template>
  <div
    v-if="selectedElement"
    class="h-full flex flex-col bg-background border-l border-border"
  >
    <!-- Header -->
    <div
      class="flex items-center justify-between px-6 py-4 border-b border-border bg-card"
    >
      <div class="flex items-center gap-3">
        <Badge :variant="badgeVariant">{{ elementType }}</Badge>
        <h2 class="text-lg font-semibold text-card-foreground">
          {{
            selectedElement.type === "node" ? "Node Details" : "Edge Details"
          }}
        </h2>
      </div>
      <Button variant="ghost" size="icon" @click="emit('close')">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </Button>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto px-6 py-4 space-y-6">
      <!-- Entity Node -->
      <template v-if="elementType === 'Entity'">
        <Card>
          <CardHeader>
            <CardTitle>Entity Information</CardTitle>
          </CardHeader>
          <CardContent class="space-y-4">
            <div>
              <Label class="text-sm font-medium text-muted-foreground"
                >ID</Label
              >
              <p class="mt-1 text-sm font-mono text-foreground break-all">
                {{ selectedElement.data.id }}
              </p>
            </div>

            <div v-if="selectedElement.data.created_at">
              <Label class="text-sm font-medium text-muted-foreground"
                >Created At</Label
              >
              <p class="mt-1 text-sm text-foreground">
                {{ formatDate(selectedElement.data.created_at) }}
              </p>
            </div>

            <div v-if="selectedElement.data.metadata">
              <Label class="text-sm font-medium text-muted-foreground"
                >Metadata</Label
              >
              <pre
                class="mt-1 text-xs bg-muted p-3 rounded-md overflow-x-auto text-foreground"
                >{{ formatJSON(selectedElement.data.metadata) }}</pre
              >
            </div>
          </CardContent>
        </Card>
      </template>

      <!-- Fact Node -->
      <template v-if="elementType === 'Fact'">
        <Card>
          <CardHeader>
            <CardTitle>Fact Information</CardTitle>
          </CardHeader>
          <CardContent class="space-y-4">
            <div>
              <Label class="text-sm font-medium text-muted-foreground"
                >Name</Label
              >
              <p class="mt-1 text-sm text-foreground">
                {{ selectedElement.data.name || "N/A" }}
              </p>
            </div>

            <div>
              <Label class="text-sm font-medium text-muted-foreground"
                >Fact Type</Label
              >
              <p class="mt-1 text-sm text-foreground">
                {{ selectedElement.data.fact_type || "N/A" }}
              </p>
            </div>

            <div v-if="selectedElement.data.fact_id">
              <Label class="text-sm font-medium text-muted-foreground"
                >Fact ID</Label
              >
              <p class="mt-1 text-sm font-mono text-foreground break-all">
                {{ selectedElement.data.fact_id }}
              </p>
            </div>

            <div>
              <Label class="text-sm font-medium text-muted-foreground"
                >Node ID</Label
              >
              <p class="mt-1 text-sm font-mono text-foreground break-all">
                {{ selectedElement.data.id }}
              </p>
            </div>
          </CardContent>
        </Card>
      </template>

      <!-- Identifier Node -->
      <template v-if="elementType === 'Identifier'">
        <Card>
          <CardHeader>
            <CardTitle>Identifier Information</CardTitle>
          </CardHeader>
          <CardContent class="space-y-4">
            <div>
              <Label class="text-sm font-medium text-muted-foreground"
                >Value</Label
              >
              <p class="mt-1 text-sm text-foreground break-all">
                {{ selectedElement.data.value || "N/A" }}
              </p>
            </div>

            <div>
              <Label class="text-sm font-medium text-muted-foreground"
                >Type</Label
              >
              <p class="mt-1 text-sm text-foreground">
                {{ selectedElement.data.identifier_type || "N/A" }}
              </p>
            </div>

            <div>
              <Label class="text-sm font-medium text-muted-foreground"
                >Node ID</Label
              >
              <p class="mt-1 text-sm font-mono text-foreground break-all">
                {{ selectedElement.data.id }}
              </p>
            </div>
          </CardContent>
        </Card>
      </template>

      <!-- Source Node -->
      <template v-if="elementType === 'Source'">
        <Card>
          <CardHeader>
            <CardTitle>Source Information</CardTitle>
          </CardHeader>
          <CardContent class="space-y-4">
            <div v-if="selectedElement.data.source_id">
              <Label class="text-sm font-medium text-muted-foreground"
                >Source ID</Label
              >
              <p class="mt-1 text-sm font-mono text-foreground break-all">
                {{ selectedElement.data.source_id }}
              </p>
            </div>

            <div v-if="selectedElement.data.timestamp">
              <Label class="text-sm font-medium text-muted-foreground"
                >Timestamp</Label
              >
              <p class="mt-1 text-sm text-foreground">
                {{ formatDate(selectedElement.data.timestamp) }}
              </p>
            </div>

            <div v-if="selectedElement.data.content">
              <Label class="text-sm font-medium text-muted-foreground"
                >Content</Label
              >
              <div
                class="mt-1 text-sm text-foreground bg-muted p-3 rounded-md max-h-64 overflow-y-auto whitespace-pre-wrap"
              >
                {{ selectedElement.data.content }}
              </div>
            </div>

            <div>
              <Label class="text-sm font-medium text-muted-foreground"
                >Node ID</Label
              >
              <p class="mt-1 text-sm font-mono text-foreground break-all">
                {{ selectedElement.data.id }}
              </p>
            </div>
          </CardContent>
        </Card>
      </template>

      <!-- Edge -->
      <template v-if="selectedElement.type === 'edge'">
        <Card>
          <CardHeader>
            <CardTitle>Edge Information</CardTitle>
          </CardHeader>
          <CardContent class="space-y-4">
            <div>
              <Label class="text-sm font-medium text-muted-foreground"
                >Label</Label
              >
              <p class="mt-1 text-sm text-foreground">
                {{ selectedElement.data.label || "N/A" }}
              </p>
            </div>

            <div>
              <Label class="text-sm font-medium text-muted-foreground"
                >Source</Label
              >
              <p class="mt-1 text-sm font-mono text-foreground break-all">
                {{ selectedElement.data.source }}
              </p>
            </div>

            <div>
              <Label class="text-sm font-medium text-muted-foreground"
                >Target</Label
              >
              <p class="mt-1 text-sm font-mono text-foreground break-all">
                {{ selectedElement.data.target }}
              </p>
            </div>

            <div>
              <Label class="text-sm font-medium text-muted-foreground"
                >Edge ID</Label
              >
              <p class="mt-1 text-sm font-mono text-foreground break-all">
                {{ selectedElement.data.id }}
              </p>
            </div>
          </CardContent>
        </Card>

        <!-- Additional Edge Properties -->
        <Card v-if="Object.keys(selectedElement.data).length > 4">
          <CardHeader>
            <CardTitle>Additional Properties</CardTitle>
          </CardHeader>
          <CardContent>
            <pre
              class="text-xs bg-muted p-3 rounded-md overflow-x-auto text-foreground"
              >{{ formatJSON(selectedElement.data) }}</pre
            >
          </CardContent>
        </Card>
      </template>

      <!-- All Raw Data (Debug) -->
      <Card>
        <CardHeader>
          <CardTitle>Raw Data</CardTitle>
          <CardDescription>Complete element data structure</CardDescription>
        </CardHeader>
        <CardContent>
          <pre
            class="text-xs bg-muted p-3 rounded-md overflow-x-auto text-foreground max-h-96"
            >{{ formatJSON(selectedElement.data) }}</pre
          >
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<style scoped>
/* Additional custom styles if needed */
</style>
