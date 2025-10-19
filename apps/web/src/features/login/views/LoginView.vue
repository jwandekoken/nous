<script setup lang="ts">
import { ref } from "vue";
import Card from "primevue/card";
import InputText from "primevue/inputtext";
import Password from "primevue/password";
import Button from "primevue/button";
import Message from "primevue/message";

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

    // For now, just show success message
    alert("Login successful! (This is a placeholder)");
  } catch (error) {
    errorMessage.value = "Login failed. Please try again.";
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <div class="flex justify-center items-center min-h-screen p-8">
    <Card class="w-full max-w-sm">
      <template #title>
        <h2>Welcome Back</h2>
      </template>

      <template #content>
        <form @submit.prevent="handleLogin" class="flex flex-col gap-6">
          <div class="flex flex-col gap-2">
            <label for="email">Email</label>
            <InputText
              id="email"
              v-model="email"
              type="email"
              placeholder="Enter your email"
              class="w-full"
              :class="{ 'p-invalid': errorMessage }"
              required
            />
          </div>

          <div class="flex flex-col gap-2">
            <label for="password">Password</label>
            <Password
              id="password"
              v-model="password"
              placeholder="Enter your password"
              class="w-full"
              :class="{ 'p-invalid': errorMessage }"
              :feedback="false"
              toggleMask
              required
            />
          </div>

          <Message v-if="errorMessage" severity="error" :closable="false">
            {{ errorMessage }}
          </Message>

          <Button
            type="submit"
            label="Sign In"
            :loading="loading"
            size="large"
          />
        </form>
      </template>
    </Card>
  </div>
</template>
