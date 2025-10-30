<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { useAuth } from "@/composables/useAuth";

const { logout } = useAuth();

const handleLogout = async () => {
  await logout();
};
</script>

<template>
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
</template>
