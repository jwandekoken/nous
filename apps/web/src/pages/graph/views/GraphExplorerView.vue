<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from "vue";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Navigation } from "@/components/layout/navigation";
import {
  useFindEntityByIdentifier,
  type FindEntityParams,
} from "@/services/graph";
import NodeDetailPanel from "../components/NodeDetailPanel.vue";

// --- Cytoscape Refs ---
const cyContainer = ref<HTMLDivElement | null>(null);
const cyInstance = ref<Core | null>(null);

// --- Search State ---
const searchTypeInput = ref("email");
const searchValueInput = ref("");
const searchParams = ref<FindEntityParams>({ type: "", value: "" });

// --- Selected Element State ---
interface SelectedElement {
  type: "node" | "edge";
  data: Record<string, any>;
}

const selectedElement = ref<SelectedElement | null>(null);
const isPanelOpen = computed(() => selectedElement.value !== null);

// --- API Data ---
const {
  data: entityData,
  isFetching: isSearching,
  error: searchError,
  execute: executeSearch,
} = useFindEntityByIdentifier(searchParams);
watch(entityData, (newValue) => {
  console.log("entityData has changed to:", newValue);
});

// --- Search Logic ---
const handleSearch = () => {
  if (!searchTypeInput.value.trim() || !searchValueInput.value.trim()) {
    console.warn("Please fill in both type and value");
    return;
  }

  searchParams.value = {
    type: searchTypeInput.value.trim(),
    value: searchValueInput.value.trim(),
  };

  // Force a refetch even if parameters haven't changed
  executeSearch();
};

// --- Panel Logic ---
const handleClosePanel = () => {
  selectedElement.value = null;
};

// --- Cytoscape Data Transformation ---
const cytoscapeElements = computed<ElementDefinition[]>(() => {
  if (!entityData.value) {
    return [];
  }

  const { entity, identifier, facts } = entityData.value;
  const elements: ElementDefinition[] = [];
  const processedSources = new Set<string>();

  // 1. Add Entity Node
  elements.push({
    group: "nodes",
    data: {
      id: entity.id,
      label: `Entity\n(${identifier.identifier.type})`,
      type: "Entity",
      created_at: entity.created_at,
      metadata: entity.metadata,
    },
  });

  // 2. Add Identifier Node
  const identifierId = `identifier-${identifier.identifier.type}-${identifier.identifier.value}`;
  elements.push({
    group: "nodes",
    data: {
      id: identifierId,
      label: identifier.identifier.value,
      type: "Identifier",
      value: identifier.identifier.value,
      identifier_type: identifier.identifier.type,
    },
  });

  // Edge: Entity -> Identifier
  elements.push({
    group: "edges",
    data: {
      id: `edge-entity-identifier-${entity.id}-${identifierId}`,
      source: entity.id,
      target: identifierId,
      label: "HAS_IDENTIFIER",
      ...identifier.relationship,
    },
  });

  // 3. Add Fact and Source Nodes and Edges
  facts.forEach((factWithSource, factIndex) => {
    const { fact, relationship, source } = factWithSource;

    // Generate unique fact ID
    const factId =
      fact.fact_id ||
      `fact-${entity.id}-${fact.type}-${fact.name}-${factIndex}`;

    // Add Fact Node
    elements.push({
      group: "nodes",
      data: {
        id: factId,
        label: `${fact.type}\n${fact.name}`,
        type: "Fact",
        name: fact.name,
        fact_type: fact.type,
        fact_id: fact.fact_id,
      },
    });

    // Edge: Entity -> Fact
    elements.push({
      group: "edges",
      data: {
        id: `edge-entity-fact-${entity.id}-${factId}`,
        source: entity.id,
        target: factId,
        label: relationship.verb,
        ...relationship,
      },
    });

    // Add Source Node (if it exists and not already processed)
    if (source && !processedSources.has(source.id)) {
      processedSources.add(source.id);
      const sourceId = `source-${source.id}`;

      elements.push({
        group: "nodes",
        data: {
          id: sourceId,
          label: `Source\n(${source.content.substring(0, 20)}...)`,
          type: "Source",
          content: source.content,
          timestamp: source.timestamp,
          source_id: source.id,
        },
      });

      // Edge: Fact -> Source
      elements.push({
        group: "edges",
        data: {
          id: `edge-fact-source-${factId}-${sourceId}`,
          source: factId,
          target: sourceId,
          label: "DERIVED_FROM",
        },
      });
    }
  });

  return elements;
});

// --- Cytoscape Initialization ---
onMounted(() => {
  if (cyContainer.value) {
    cyInstance.value = cytoscape({
      container: cyContainer.value,
      elements: [],

      style: [
        {
          selector: "node",
          style: {
            "background-color": "#999",
            label: "data(label)",
            color: "#ffffff",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": "10px",
            "text-wrap": "wrap",
            "text-max-width": "80px",
            width: "60px",
            height: "60px",
            "border-width": 2,
            "border-color": "#fff",
          },
        },
        {
          selector: "edge",
          style: {
            width: 2,
            "line-color": "#bbb",
            "target-arrow-color": "#bbb",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            color: "#f5c842",
            "font-size": "8px",
            "text-rotation": "autorotate",
            "text-margin-y": -10,
          },
        },
        // Node type styling
        {
          selector: "node[type='Entity']",
          style: { "background-color": "#3b82f6" },
        },
        {
          selector: "node[type='Fact']",
          style: { "background-color": "#10b981" },
        },
        {
          selector: "node[type='Identifier']",
          style: { "background-color": "#f97316" },
        },
        {
          selector: "node[type='Source']",
          style: { "background-color": "#a855f7" },
        },
        // Selection styling
        {
          selector: "node:selected",
          style: {
            "border-width": 4,
            "border-color": "#fbbf24",
            "overlay-opacity": 0.2,
            "overlay-color": "#fbbf24",
          },
        },
        {
          selector: "edge:selected",
          style: {
            width: 4,
            "line-color": "#fbbf24",
            "target-arrow-color": "#fbbf24",
            "overlay-opacity": 0.2,
            "overlay-color": "#fbbf24",
          },
        },
      ],

      layout: {
        name: "grid",
      },
    });

    // Setup event listeners for node/edge selection
    if (cyInstance.value) {
      // Handle node clicks
      cyInstance.value.on("tap", "node", (event) => {
        const node = event.target;
        selectedElement.value = {
          type: "node",
          data: node.data(),
        };
      });

      // Handle edge clicks
      cyInstance.value.on("tap", "edge", (event) => {
        const edge = event.target;
        selectedElement.value = {
          type: "edge",
          data: edge.data(),
        };
      });

      // Handle background clicks to deselect
      cyInstance.value.on("tap", (event) => {
        if (event.target === cyInstance.value) {
          selectedElement.value = null;
        }
      });
    }
  }
});

onUnmounted(() => {
  cyInstance.value?.destroy();
});

// --- Cytoscape Updates ---
watch(cytoscapeElements, (newElements, oldElements) => {
  const cy = cyInstance.value;
  if (!cy) return;

  // If this is the first load or elements changed significantly, replace all
  if (!oldElements || oldElements.length === 0) {
    cy.elements().remove();
    cy.add(newElements);

    // Apply layout with animation for new data
    const layout = cy.layout({
      name: "cose",
      fit: true,
      padding: 30,
      animate: true,
      animationDuration: 500,
    });
    layout.run();
  } else {
    // For updates, we could implement more granular updates here
    // For now, we'll do a full replacement but this could be optimized
    cy.elements().remove();
    cy.add(newElements);

    // Apply layout without animation for updates
    const layout = cy.layout({
      name: "cose",
      fit: true,
      padding: 30,
      animate: false,
    });
    layout.run();
  }
});
</script>

<template>
  <div class="min-h-screen bg-background">
    <Navigation />

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="mb-8 lg:mb-12">
        <h1
          class="text-2xl sm:text-3xl lg:text-4xl font-bold text-foreground mb-4"
        >
          Knowledge Graph Explorer
        </h1>
        <p class="text-base sm:text-lg text-muted-foreground max-w-3xl">
          Search for entities by their identifiers and explore their
          relationships, facts, and sources.
        </p>
      </div>

      <!-- Search Entity Section -->
      <div
        class="bg-card rounded-lg shadow-md p-4 sm:p-6 lg:p-8 mb-8 lg:mb-12 border border-border"
      >
        <h2 class="text-xl sm:text-2xl font-semibold text-card-foreground mb-6">
          Search Entity
        </h2>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 lg:gap-6 items-end">
          <div class="flex flex-col gap-2">
            <label
              for="search-type"
              class="text-sm font-medium text-foreground"
            >
              Identifier Type
            </label>
            <Input
              id="search-type"
              v-model="searchTypeInput"
              placeholder="e.g., email, phone, name"
              class="w-full text-foreground"
            />
          </div>

          <div class="flex flex-col gap-2">
            <label
              for="search-value"
              class="text-sm font-medium text-foreground"
            >
              Identifier Value
            </label>
            <Input
              id="search-value"
              v-model="searchValueInput"
              placeholder="Enter search value"
              class="w-full text-foreground"
              @keyup.enter="handleSearch"
            />
          </div>

          <Button
            @click="handleSearch"
            :disabled="
              isSearching || !searchTypeInput.trim() || !searchValueInput.trim()
            "
            class="w-full md:w-auto h-10"
          >
            <span v-if="isSearching">Searching...</span>
            <span v-else>Search</span>
          </Button>
        </div>

        <!-- Display Search Error -->
        <div
          v-if="searchError"
          class="mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded-md"
        >
          <p class="text-destructive text-sm">
            Search failed:
            {{ searchError.message || "An error occurred while searching." }}
          </p>
        </div>
      </div>

      <!-- Graph and Panel Container -->
      <div class="flex gap-4">
        <!-- Cytoscape Graph Visualization Area -->
        <div
          :class="[
            'bg-card rounded-lg shadow-md border border-border overflow-hidden relative transition-all duration-300',
            isPanelOpen ? 'flex-1' : 'w-full',
          ]"
          style="height: 600px"
        >
          <!-- Loading overlay -->
          <div
            v-if="isSearching"
            class="absolute inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-10"
          >
            <div class="text-center">
              <div
                class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"
              ></div>
              <p class="text-sm text-muted-foreground">Loading graph data...</p>
            </div>
          </div>

          <!-- Cytoscape container -->
          <div ref="cyContainer" class="w-full h-full"></div>

          <!-- Empty state -->
          <div
            v-if="!isSearching && !entityData && !searchError"
            class="absolute inset-0 flex items-center justify-center"
          >
            <div class="text-center text-muted-foreground">
              <p class="text-lg mb-2">No data to display</p>
              <p class="text-sm">
                Search for an entity to visualize its knowledge graph
              </p>
            </div>
          </div>
        </div>

        <!-- Detail Panel -->
        <transition
          enter-active-class="transition-all duration-300 ease-out"
          leave-active-class="transition-all duration-300 ease-in"
          enter-from-class="opacity-0 translate-x-4"
          enter-to-class="opacity-100 translate-x-0"
          leave-from-class="opacity-100 translate-x-0"
          leave-to-class="opacity-0 translate-x-4"
        >
          <div v-if="isPanelOpen" class="w-96 shrink-0" style="height: 600px">
            <NodeDetailPanel
              :selected-element="selectedElement"
              @close="handleClosePanel"
            />
          </div>
        </transition>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* Additional custom styles if needed */
</style>
