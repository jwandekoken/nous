<template>
  <div class="main-layout">
    <header class="app-header">
      <nav>
        <router-link to="/">Home</router-link>
        <router-link to="/login">Login</router-link>
        <router-link to="/graph/search">Entity Search</router-link>
      </nav>
    </header>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
// MainLayout component logic will go here
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background-color: #f8f9fa;
  padding: 1rem;
  border-bottom: 1px solid #dee2e6;
}

.app-header nav {
  display: flex;
  gap: 1rem;
}

.app-header a {
  text-decoration: none;
  color: #007bff;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.app-header a:hover,
.app-header a.router-link-active {
  background-color: #e9ecef;
}

.main-content {
  flex: 1;
  padding: 2rem;
}
</style>
