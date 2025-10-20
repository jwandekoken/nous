<template>
  <div class="min-h-screen bg-gray-50">
    <Menubar />

    <main class="container mx-auto px-4 py-8">
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-800 mb-4">Welcome to Nous</h1>
        <p class="text-gray-600">
          You've successfully logged in! This is the main application area.
        </p>
      </div>

      <!-- Search Entity Section -->
      <div class="bg-white rounded-lg shadow-md p-6 mb-8">
        <h2 class="text-2xl font-semibold text-gray-800 mb-6">Search Entity</h2>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div class="flex flex-col gap-2">
            <label for="search-type" class="text-sm font-medium text-gray-700">
              Type
            </label>
            <InputText
              id="search-type"
              v-model="searchType"
              placeholder="e.g., email, name, phone"
              class="w-full"
            />
          </div>

          <div class="flex flex-col gap-2">
            <label for="search-value" class="text-sm font-medium text-gray-700">
              Value
            </label>
            <InputText
              id="search-value"
              v-model="searchValue"
              placeholder="Enter search value"
              class="w-full"
            />
          </div>

          <Button
            label="Search"
            icon="pi pi-search"
            :loading="isSearching"
            @click="handleSearch"
            class="w-full md:w-auto"
          />
        </div>
      </div>

      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import Menubar from "@/components/ui/Menubar.vue";
import InputText from "primevue/inputtext";
import Button from "primevue/button";

// Reactive data for search functionality
const searchType = ref("");
const searchValue = ref("");
const isSearching = ref(false);

// Methods
const handleSearch = async () => {
  if (!searchType.value || !searchValue.value) {
    // TODO: Show error message
    console.log("Please fill in both type and value");
    return;
  }

  isSearching.value = true;

  try {
    // TODO: Implement actual search logic
    console.log("Searching for entity:", {
      type: searchType.value,
      value: searchValue.value,
    });

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));

    // TODO: Handle search results
  } catch (error) {
    console.error("Search failed:", error);
  } finally {
    isSearching.value = false;
  }
};
</script>

<style scoped>
/* Additional custom styles if needed */
</style>
