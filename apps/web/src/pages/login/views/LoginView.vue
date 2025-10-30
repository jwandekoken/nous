<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuth } from "@/composables/useAuth";
import { fetchCurrentUser } from "@/api/authApi";
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
const { login, isLoading, error: authError } = useAuth();

// Form data
const email = ref("");
const password = ref("");

// Handle login submission with role-based redirect
const handleLogin = async () => {
  if (!email.value || !password.value) {
    toast.error("Please fill in all fields");
    return;
  }

  const success = await login({
    email: email.value,
    password: password.value,
  });

  if (success) {
    console.log("Login successful, redirecting...");

    // Fetch user and redirect based on role
    const user = await fetchCurrentUser();
    if (user) {
      switch (user.role) {
        case "super_admin":
          router.push("/tenants");
          break;
        case "tenant_admin":
          router.push("/users");
          break;
        default:
          router.push("/graph");
      }
    }
  } else {
    toast.error(authError.value || "Invalid credentials");
  }
};
</script>

<template>
  <div class="flex justify-center items-center min-h-screen bg-background p-8">
    <Card class="w-full max-w-sm">
      <CardHeader>
        <CardTitle>Welcome Back</CardTitle>
        <CardDescription>Enter your credentials to sign in.</CardDescription>
      </CardHeader>
      <CardContent>
        <form @submit.prevent="handleLogin" class="flex flex-col gap-6">
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
              placeholder="Enter your password"
              class="w-full"
              required
            />
          </div>

          <Button type="submit" :disabled="isLoading" size="lg">
            <span v-if="isLoading">Signing in...</span>
            <span v-else>Sign In</span>
          </Button>
        </form>
      </CardContent>
    </Card>
  </div>
</template>
