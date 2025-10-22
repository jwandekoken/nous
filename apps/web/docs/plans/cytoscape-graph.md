**Goal:** Replace the (currently non-visualizing) part of `HomeView.vue` with a Cytoscape.js instance that displays the graph data fetched by `useFindEntityByIdentifier`.

---

### Plan: Integrating Cytoscape.js into `HomeView.vue`

#### 1\. Install Cytoscape.js

In your `apps/web` directory (or from the monorepo root using `--filter web`), add Cytoscape.js and its types:

```bash
# From monorepo root
pnpm --filter web add cytoscape
pnpm --filter web add -D @types/cytoscape
```

#### 2\. Modify `HomeView.vue`

This component will be responsible for:

- Providing a DOM element for Cytoscape to render in.
- Initializing the Cytoscape instance when the component mounts.
- Transforming your API data (`GetEntityResponse`) into Cytoscape's element format.
- Watching for changes in the API data and updating the Cytoscape graph accordingly.
- Cleaning up the Cytoscape instance when the component unmounts.

<!-- end list -->

```vue
<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from "vue";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape"; // Import Cytoscape

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Navigation } from "@/components/layout/navigation";
import { useFindEntityByIdentifier } from "@/features/graph/api/graphApi";
import type { GetEntityResponse } from "@/types/api";

// --- Refs for Cytoscape ---
const cyContainer = ref<HTMLDivElement | null>(null); // Ref for the container div
const cyInstance = ref<Core | null>(null); // Ref to hold the Cytoscape instance

// --- API Data ---
// Keep track of the parameters passed to the API composable
const searchParams = ref({ type: "", value: "" });
// Use the API composable. It provides reactive data, fetching state, and errors.
const {
  data: entityData, // This ref holds the GetEntityResponse | null
  isFetching: isSearching, // Rename isFetching for clarity
  error: searchError,
  execute: executeSearch, // Function to trigger the fetch
} = useFindEntityByIdentifier(searchParams);

// --- Search Logic ---
const searchTypeInput = ref("email"); // Bind input fields
const searchValueInput = ref("");

const handleSearch = () => {
  if (!searchTypeInput.value || !searchValueInput.value) {
    console.warn("Please fill in both type and value");
    // Optionally show an error message in the UI
    return;
  }
  // Update the searchParams ref. This will trigger the useFindEntityByIdentifier
  // composable to refetch IF its url computed property changes.
  // We'll call execute manually to ensure it runs even if params are the same.
  searchParams.value = {
    type: searchTypeInput.value,
    value: searchValueInput.value,
  };
  // Explicitly trigger the fetch
  executeSearch();
};

// --- Cytoscape Data Transformation ---
// Computed property to transform API data into Cytoscape elements
const cytoscapeElements = computed<ElementDefinition[]>(() => {
  if (!entityData.value) {
    return []; // Return empty array if no data
  }

  const { entity, identifier, facts } = entityData.value;
  const elements: ElementDefinition[] = [];

  // 1. Add Entity Node
  elements.push({
    group: "nodes",
    data: {
      id: entity.id, // Use the UUID as the Cytoscape ID
      label: `Entity\n(${identifier.identifier.type})`,
      type: "Entity", // Custom property for styling/filtering
      ...entity, // Include full entity data if needed
    },
  });

  // 2. Add Identifier Node
  const identifierId = `identifier-${identifier.identifier.value}`;
  elements.push({
    group: "nodes",
    data: {
      id: identifierId,
      label: identifier.identifier.value,
      type: "Identifier",
      ...identifier.identifier,
    },
  });
  // Edge: Entity -> Identifier
  elements.push({
    group: "edges",
    data: {
      id: `e-${entity.id}-${identifierId}`,
      source: entity.id, // Source is the Entity node's ID
      target: identifierId, // Target is the Identifier node's ID
      label: "HAS_IDENTIFIER",
      ...identifier.relationship, // Include relationship data
    },
  });

  // 3. Add Fact and Source Nodes and Edges
  facts.forEach((factWithSource, index) => {
    const { fact, relationship, source } = factWithSource;
    // Use the backend's fact_id if available, otherwise generate one
    const factId = fact.fact_id || `fact-${fact.type}-${fact.name}-${index}`;

    // Add Fact Node
    elements.push({
      group: "nodes",
      data: {
        id: factId,
        label: `${fact.type}\n${fact.name}`,
        type: "Fact",
        ...fact,
      },
    });

    // Edge: Entity -> Fact
    elements.push({
      group: "edges",
      data: {
        id: `e-${entity.id}-${factId}`,
        source: entity.id,
        target: factId,
        label: relationship.verb,
        ...relationship,
      },
    });

    // Add Source Node (if it exists)
    if (source) {
      const sourceId = `source-${source.id}`;
      // Add Source Node (only if not already added by another fact)
      if (!elements.some((el) => el.data.id === sourceId)) {
        elements.push({
          group: "nodes",
          data: {
            id: sourceId,
            label: `Source\n(${source.content.substring(0, 15)}...)`,
            type: "Source",
            ...source,
          },
        });
      }

      // Edge: Fact -> Source
      elements.push({
        group: "edges",
        data: {
          id: `e-${factId}-${sourceId}`,
          source: factId, // Fact is the source
          target: sourceId, // Source is the target
          label: "DERIVED_FROM",
          // Add any relevant data for the DERIVED_FROM relationship if needed
        },
      });
    }
  });

  return elements;
});

// --- Cytoscape Initialization and Updates ---
onMounted(() => {
  if (cyContainer.value) {
    cyInstance.value = cytoscape({
      container: cyContainer.value,
      elements: [], // Start with an empty graph

      // Basic styling (customize significantly later)
      style: [
        {
          selector: "node",
          style: {
            "background-color": "#666",
            label: "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": "10px",
            "text-wrap": "wrap",
            "text-max-width": "80px",
            width: "60px",
            height: "60px",
          },
        },
        {
          selector: "edge",
          style: {
            width: 2,
            "line-color": "#ccc",
            "target-arrow-color": "#ccc",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": "8px",
            "text-rotation": "autorotate",
            "text-margin-y": -10,
          },
        },
        // Example: Style nodes by type
        {
          selector: "node[type='Entity']",
          style: { "background-color": "#3b82f6" /* Blue */ },
        },
        {
          selector: "node[type='Fact']",
          style: { "background-color": "#10b981" /* Green */ },
        },
        {
          selector: "node[type='Identifier']",
          style: { "background-color": "#f97316" /* Orange */ },
        },
        {
          selector: "node[type='Source']",
          style: { "background-color": "#a855f7" /* Purple */ },
        },
      ],

      // Initial layout (can be changed later)
      layout: {
        name: "grid", // Start with grid, apply better layout after data loads
      },
    });
  }
});

onUnmounted(() => {
  // Destroy the Cytoscape instance on component unmount to prevent memory leaks
  cyInstance.value?.destroy();
});

// Watch for changes in the transformed elements and update Cytoscape
watch(cytoscapeElements, (newElements) => {
  const cy = cyInstance.value;
  if (!cy) return;

  // Update the graph
  cy.elements().remove(); // Clear previous elements
  cy.add(newElements); // Add new elements

  // Apply a layout (cose is good for exploring relationships)
  const layout = cy.layout({
    name: "cose", // Concentric layout is another option
    fit: true, // Fit the viewport to the graph
    padding: 30, // Padding around the graph
    animate: true, // Animate the layout change
    animationDuration: 500,
  });
  layout.run(); // Run the layout
});
</script>

<template>
  <div class="min-h-screen bg-background">
    <Navigation />

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
              Type
            </label>
            <Input
              id="search-type"
              v-model="searchTypeInput"
              placeholder="e.g., email, phone"
              class="w-full text-foreground"
            />
          </div>

          <div class="flex flex-col gap-2">
            <label
              for="search-value"
              class="text-sm font-medium text-foreground"
            >
              Value
            </label>
            <Input
              id="search-value"
              v-model="searchValueInput"
              placeholder="Enter search value"
              class="w-full text-foreground"
            />
          </div>

          <Button
            @click="handleSearch"
            :disabled="isSearching"
            class="w-full md:w-auto h-10"
          >
            <span v-if="isSearching">Searching...</span>
            <span v-else>Search</span>
          </Button>
        </div>
        <!-- Display Search Error -->
        <p v-if="searchError" class="text-destructive mt-4 text-sm">
          Error searching: {{ searchError.message || "Failed to fetch data." }}
        </p>
      </div>

      <!-- Cytoscape Graph Visualization Area -->
      <div
        class="bg-card rounded-lg shadow-md border border-border overflow-hidden"
        style="height: 600px"
      >
        <!-- This div is where Cytoscape will render -->
        <div ref="cyContainer" class="w-full h-full"></div>
      </div>
    </main>
  </div>
</template>

<style>
/* You might need some global styles for Cytoscape if specific elements need it,
   but most styling is done via the 'style' option in the constructor. */
</style>
```

#### 3\. Key Changes and Explanations

1.  **Imports:** `cytoscape` and its types are imported.
2.  **Refs:**
    - `cyContainer`: A template ref attached to the `<div>` where Cytoscape will mount.
    - `cyInstance`: Stores the initialized Cytoscape `Core` object.
3.  **API Data Handling:**
    - We now use the `data`, `isFetching`, `error`, and `execute` returned by `useFindEntityByIdentifier`.
    - `searchParams` is a `ref` holding the _parameters_ for the API call. The `useFindEntityByIdentifier` composable watches this internally (due to its `computed` URL).
    - `handleSearch` now updates `searchParams` and calls `executeSearch` explicitly to trigger the fetch.
4.  **`cytoscapeElements` Computed Property:**
    - This is the core transformation logic. It takes the reactive `entityData.value` (from the API composable) and maps it to Cytoscape's `ElementDefinition[]` format.
    - It handles nodes (`group: 'nodes'`) and edges (`group: 'edges'`).
    - **IDs are crucial:** Ensure node IDs are unique and consistent so edges can reference them correctly (`source` and `target` in edge data). We use API UUIDs and generate unique IDs for identifiers/sources/facts.
    - The full API data (`entity`, `fact`, `source`, `relationship`) is often spread into the `data` property of the elements for potential use in styling or event handlers.
5.  **`onMounted`:**
    - Initializes Cytoscape using the `cyContainer` ref.
    - Sets up basic `style` (colors, labels, arrows). This is highly customizable.
    - Sets an initial simple `layout` (`grid`).
6.  **`onUnmounted`:**
    - Calls `cyInstance.value?.destroy()` to properly clean up Cytoscape and prevent memory leaks. **This is essential.**
7.  **`watch(cytoscapeElements, ...)`:**
    - This is the reactive link. Whenever `entityData` changes, `cytoscapeElements` recalculates.
    - The watcher detects this change.
    - It gets the `cy` instance.
    - It removes _all_ existing elements (`cy.elements().remove()`).
    - It adds the _new_ set of elements (`cy.add(newElements)`).
    - It runs a more appropriate layout (like `cose`) to arrange the new graph nicely. `fit: true` adjusts the zoom.
8.  **Template:**
    - A `<div>` with `ref="cyContainer"` is added. **It must have explicit dimensions (e.g., `height: 600px`)** for Cytoscape to render correctly.
    - Error display logic is added using `searchError`.

#### 4\. Next Steps & Considerations

- **Styling:** The provided style is basic. Explore Cytoscape's rich styling options: [https://js.cytoscape.org/\#style](https://www.google.com/search?q=https://js.cytoscape.org/%23style). You can style based on data attributes (e.g., `node[type='Fact']`, `edge[verb='lives_in']`).
- **Layouts:** `cose` is good for exploring structure. Other useful layouts include `breadthfirst` (for trees), `concentric`, `dagre` (for directed graphs, requires an extension: `cytoscape-dagre`). Experiment to find what works best. [https://js.cytoscape.org/\#layouts](https://www.google.com/search?q=https://js.cytoscape.org/%23layouts)
- **Interactivity:** Add event listeners (`cy.on('tap', 'node', (event) => { ... })`) to handle clicks/taps on nodes or edges, perhaps to show more details.
- **Performance:** For very large graphs, Cytoscape offers performance optimizations (e.g., batching updates, using simpler styles).
- **Error Handling:** Improve UI feedback for API errors (`searchError`).
- **Loading State:** You can use `isSearching` to show a loading indicator over the Cytoscape container while data is fetching.

This plan provides a robust way to integrate Cytoscape directly, leveraging Vue's reactivity system effectively.
