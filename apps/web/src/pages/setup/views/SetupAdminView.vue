<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { toast } from "vue-sonner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const router = useRouter();
const authStore = useAuthStore();

// Form data
const email = ref("");
const password = ref("");
const confirmPassword = ref("");

const handleSetup = async () => {
  if (!email.value || !password.value || !confirmPassword.value) {
    toast.error("Please fill in all fields");
    return;
  }

  if (password.value !== confirmPassword.value) {
    toast.error("Passwords do not match");
    return;
  }

  const success = await authStore.setupAdmin({
    email: email.value,
    password: password.value,
  });
  console.log("success: ", success);

  if (success) {
    toast.success("Admin created successfully. Please log in.");
    router.push("/login");
  } else {
    toast.error(authStore.error || "Setup failed");
  }
};
</script>

<template>
  <div class="flex justify-center items-center min-h-screen bg-background p-8">
    <Card class="w-full max-w-sm">
      <CardHeader>
        <CardTitle>Welcome to Nous</CardTitle>
        <CardDescription
          >Create your first admin account to get started.</CardDescription
        >
      </CardHeader>
      <CardContent>
        <form @submit.prevent="handleSetup" class="flex flex-col gap-6">
          <div class="flex flex-col gap-2">
            <label for="email">Email</label>
            <Input
              id="email"
              v-model="email"
              type="email"
              placeholder="Enter your email"
              class="w-full"
              required
            />
          </div>

          <div class="flex flex-col gap-2">
            <label for="password">Password</label>
            <Input
              id="password"
              v-model="password"
              type="password"
              placeholder="Create a password"
              class="w-full"
              required
            />
          </div>

          <div class="flex flex-col gap-2">
            <label for="confirmPassword">Confirm Password</label>
            <Input
              id="confirmPassword"
              v-model="confirmPassword"
              type="password"
              placeholder="Confirm your password"
              class="w-full"
              required
            />
          </div>

          <Button type="submit" :disabled="authStore.isLoading" size="lg">
            <span v-if="authStore.isLoading">Creating Admin...</span>
            <span v-else>Create Admin</span>
          </Button>
        </form>
      </CardContent>
    </Card>
  </div>
</template>
