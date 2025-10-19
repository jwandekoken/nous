<template>
  <div class="main-layout">
    <header class="app-header">
      <nav>
        <router-link to="/" class="text-red-500 m-3">Home</router-link>
        <router-link to="/login">Login</router-link>
        <router-link to="/graph/search">Entity Search</router-link>
      </nav>
    </header>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts"></script>

<style scoped></style>
