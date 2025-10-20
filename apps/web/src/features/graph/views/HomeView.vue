<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const router = useRouter();

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

const handleLogout = () => {
  // Clear authentication state
  localStorage.removeItem("isLoggedIn");

  // Redirect to login page
  router.push("/login");
};
</script>

<template>
  <div class="min-h-screen bg-background">
    <!-- Navigation Header -->
    <header class="bg-card shadow-sm border-b border-border">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <!-- Logo/Brand -->
          <div class="flex items-center">
            <h1 class="text-xl font-semibold text-card-foreground">Nous</h1>
          </div>

          <!-- Logout Button -->
          <Button
            @click="handleLogout"
            variant="outline"
            size="sm"
            class="text-muted-foreground hover:text-foreground"
          >
            Logout
          </Button>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="mb-8 lg:mb-12">
        <h1
          class="text-2xl sm:text-3xl lg:text-4xl font-bold text-foreground mb-4"
        >
          Welcome back!
        </h1>
        <p class="text-base sm:text-lg text-muted-foreground max-w-3xl">
          You've successfully logged in! This is the main application area.
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
              Type
            </label>
            <Input
              id="search-type"
              v-model="searchType"
              placeholder="e.g., email, name, phone"
              class="w-full"
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
              v-model="searchValue"
              placeholder="Enter search value"
              class="w-full"
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
      </div>

      <router-view />
    </main>
  </div>
</template>

<style scoped>
/* Additional custom styles if needed */
</style>
