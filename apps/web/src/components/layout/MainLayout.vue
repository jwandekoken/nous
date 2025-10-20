<template>
  <div class="main-layout">
    <header class="app-header">
      <nav class="flex justify-between items-center p-4 bg-gray-100">
        <div class="flex gap-4">
          <router-link to="/" class="text-blue-600 hover:text-blue-800"
            >Home</router-link
          >
          <router-link
            to="/graph/search"
            class="text-blue-600 hover:text-blue-800"
            >Entity Search</router-link
          >
        </div>
        <button
          @click="handleLogout"
          class="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
        >
          Logout
        </button>
      </nav>
    </header>
    <main class="main-content p-8">
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-800 mb-4">Welcome to Nous</h1>
        <p class="text-gray-600">
          You've successfully logged in! This is the main application area.
        </p>
      </div>
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();

const handleLogout = () => {
  // Clear authentication state
  localStorage.removeItem("isLoggedIn");

  // Redirect to login
  router.push("/login");
};
</script>

<style scoped></style>
