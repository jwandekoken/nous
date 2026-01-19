<script setup lang="ts">
import { Button } from "@/components/ui/button";
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  navigationMenuTriggerStyle,
} from "@/components/ui/navigation-menu";
import { useAuthStore } from "@/stores/auth";
import { useRoute } from "vue-router";
import { watch, onMounted, computed, ref } from "vue";

const authStore = useAuthStore();
const route = useRoute();
const isMobileMenuOpen = ref(false);

watch(
  () => authStore.currentUser,
  (newUser) => {
    console.log("🔐 Navigation - currentUser changed:", newUser);
  },
  { immediate: true },
);

onMounted(() => {
  console.log("🚀 Navigation component mounted");
  console.log("🔐 Initial auth state:", {
    currentUser: authStore.currentUser,
    isAuthenticated: authStore.isAuthenticated,
    userRole: authStore.userRole,
  });
});

// Role-based navigation items
const navigationItems = computed(() => {
  const userRole = authStore.currentUser?.role;

  if (!userRole) return [];

  const items = [
    {
      label: "Tenants Management",
      to: "/tenants",
      roles: ["super_admin"],
    },
    {
      label: "Users Management",
      to: "/users",
      roles: ["tenant_admin"],
    },
    {
      label: "API Keys",
      to: "/api-keys",
      roles: ["tenant_admin"],
    },
    {
      label: "Usage",
      to: "/usage",
      roles: ["tenant_admin", "tenant_user"],
    },
    {
      label: "Graph Explorer",
      to: "/graph",
      roles: ["tenant_admin", "tenant_user"],
    },
  ];

  return items.filter((item) => item.roles.includes(userRole));
});

// Check if route is active
const isActive = (path: string) => {
  return route.path === path;
};

const handleLogout = async () => {
  isMobileMenuOpen.value = false;
  await authStore.logout();
};

const toggleMobileMenu = () => {
  isMobileMenuOpen.value = !isMobileMenuOpen.value;
};

const closeMobileMenu = () => {
  isMobileMenuOpen.value = false;
};
</script>

<template>
  <header class="bg-card shadow-sm border-b border-border">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center h-16">
        <!-- Logo/Brand -->
        <div class="flex items-center">
          <router-link
            to="/"
            class="text-xl font-semibold text-card-foreground hover:text-primary transition-colors"
          >
            Nous
          </router-link>
        </div>

        <!-- Desktop Navigation Menu -->
        <NavigationMenu v-if="authStore.isAuthenticated" class="hidden md:flex">
          <NavigationMenuList>
            <NavigationMenuItem v-for="item in navigationItems" :key="item.to">
              <router-link :to="item.to" custom v-slot="{ navigate, href }">
                <NavigationMenuLink
                  :href="href"
                  @click="navigate"
                  :class="navigationMenuTriggerStyle()"
                  :data-active="isActive(item.to)"
                  class="data-[active=true]:bg-accent data-[active=true]:text-accent-foreground cursor-pointer text-foreground font-medium hover:text-primary"
                >
                  {{ item.label }}
                </NavigationMenuLink>
              </router-link>
            </NavigationMenuItem>
          </NavigationMenuList>
        </NavigationMenu>

        <!-- Desktop Logout Button -->
        <Button
          v-if="authStore.isAuthenticated"
          @click="handleLogout"
          variant="outline"
          size="sm"
          class="hidden md:flex text-muted-foreground hover:text-foreground"
        >
          Logout
        </Button>

        <!-- Mobile Menu Button -->
        <Button
          v-if="authStore.isAuthenticated"
          @click="toggleMobileMenu"
          variant="outline"
          size="sm"
          class="md:hidden text-foreground hover:bg-accent"
          aria-label="Toggle menu"
        >
          <svg
            v-if="!isMobileMenuOpen"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="2"
            stroke="currentColor"
            class="w-6 h-6"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
            />
          </svg>
          <svg
            v-else
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="2"
            stroke="currentColor"
            class="w-6 h-6"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </Button>
      </div>

      <!-- Mobile Menu -->
      <div
        v-if="authStore.isAuthenticated && isMobileMenuOpen"
        class="md:hidden py-4 border-t border-border"
      >
        <nav class="flex flex-col space-y-2">
          <router-link
            v-for="item in navigationItems"
            :key="item.to"
            :to="item.to"
            @click="closeMobileMenu"
            :class="[
              'px-4 py-2 rounded-md text-foreground font-medium transition-colors',
              isActive(item.to)
                ? 'bg-accent text-accent-foreground'
                : 'hover:bg-accent hover:text-accent-foreground',
            ]"
          >
            {{ item.label }}
          </router-link>
          <Button
            @click="handleLogout"
            variant="outline"
            size="sm"
            class="mx-4 text-muted-foreground hover:text-foreground"
          >
            Logout
          </Button>
        </nav>
      </div>
    </div>
  </header>
</template>
