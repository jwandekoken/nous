<script setup lang="ts">
import { Navigation } from "@/components/layout/navigation";
</script>

<template>
  <div class="min-h-screen bg-background">
    <Navigation />

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-foreground mb-4">User Management</h1>
        <p class="text-lg text-muted-foreground">Manage users in your tenant</p>
      </div>

      <div class="bg-card rounded-lg shadow-md p-6 border border-border">
        <p class="text-muted-foreground">
          User management table will be implemented here
        </p>
        <!-- TODO: Add user table with CRUD operations -->
      </div>
    </main>
  </div>
</template>
