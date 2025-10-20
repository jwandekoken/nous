<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

const router = useRouter();

// Reactive data
const email = ref("");
const password = ref("");
const loading = ref(false);
const errorMessage = ref("");

// Methods
const handleLogin = async () => {
  if (!email.value || !password.value) {
    errorMessage.value = "Please fill in all fields";
    return;
  }

  loading.value = true;
  errorMessage.value = "";

  try {
    // TODO: Implement actual login logic
    console.log("Login attempt:", {
      email: email.value,
      password: password.value,
    });

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 2000));

    // Mock successful login - set authentication state
    localStorage.setItem("isLoggedIn", "true");

    // Redirect to home after successful login
    router.push("/");
  } catch (error) {
    errorMessage.value = "Login failed. Please try again.";
  } finally {
    loading.value = false;
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

          <Alert v-if="errorMessage" variant="destructive">
            <AlertDescription>
              {{ errorMessage }}
            </AlertDescription>
          </Alert>

          <Button type="submit" :disabled="loading" size="lg">
            <span v-if="loading">Signing in...</span>
            <span v-else>Sign In</span>
          </Button>
        </form>
      </CardContent>
    </Card>
  </div>
</template>
