<script setup lang="ts">
import Menubar from "primevue/menubar";
import Button from "primevue/button";
import type { MenuItem } from "primevue/menuitem";
import { useRouter } from "vue-router";

const router = useRouter();

const menuItems: MenuItem[] = [
  {
    label: "Home",
    route: "/",
    icon: "pi pi-home",
  },
];

const handleLogout = () => {
  // Clear authentication state
  localStorage.removeItem("isLoggedIn");

  // Redirect to login
  router.push("/login");
};
</script>

<template>
  <Menubar :model="menuItems">
    <template #start>
      <div class="flex items-center">
        <h1 class="text-xl font-bold">Nous</h1>
      </div>
    </template>
    <template #end>
      <Button
        @click="handleLogout"
        label="Logout"
        icon="pi pi-sign-out"
        severity="danger"
        text
        rounded
      />
    </template>
  </Menubar>
</template>
