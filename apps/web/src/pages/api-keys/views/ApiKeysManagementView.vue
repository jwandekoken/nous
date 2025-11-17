<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Navigation } from "@/components/layout/navigation";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { createApiKey, deleteApiKey, listApiKeys } from "@/services/api-keys";
import type { ApiKeySummary, CreateApiKeyResponse } from "@/services/api-keys";
import { toast } from "vue-sonner";

const apiKeys = ref<ApiKeySummary[]>([]);
const isFetching = ref(false);
const isProcessing = ref(false);

const isCreateDialogOpen = ref(false);
const isDeleteDialogOpen = ref(false);

const createForm = ref({
  name: "",
});

const createdKey = ref<CreateApiKeyResponse | null>(null);
const selectedKey = ref<ApiKeySummary | null>(null);

const loadApiKeys = async () => {
  isFetching.value = true;
  try {
    const { execute, data, error, statusCode } = listApiKeys();
    await execute();

    if (statusCode.value === 200 && data.value) {
      apiKeys.value = data.value.api_keys;
    } else {
      toast.error("Failed to load API keys", {
        description: error.value?.message || "Unexpected error occurred",
      });
    }
  } catch (err) {
    toast.error("Failed to load API keys", {
      description:
        err instanceof Error ? err.message : "Unexpected error occurred",
    });
  } finally {
    isFetching.value = false;
  }
};

const openCreateDialog = () => {
  createForm.value.name = "";
  createdKey.value = null;
  isCreateDialogOpen.value = true;
};

const closeCreateDialog = () => {
  isCreateDialogOpen.value = false;
  createdKey.value = null;
  createForm.value.name = "";
};

const handleCreateApiKey = async () => {
  if (!createForm.value.name.trim()) {
    toast.error("API key name is required");
    return;
  }

  isProcessing.value = true;
  try {
    const { execute, data, error, statusCode } = createApiKey({
      name: createForm.value.name.trim(),
    });

    await execute();

    if (statusCode.value === 200 && data.value) {
      createdKey.value = data.value;
      toast.success("API key created", {
        description: "Copy the secret now. It won't be shown again.",
      });
      await loadApiKeys();
    } else {
      toast.error("Failed to create API key", {
        description: error.value?.message || "Unexpected error occurred",
      });
    }
  } catch (err) {
    toast.error("Failed to create API key", {
      description:
        err instanceof Error ? err.message : "Unexpected error occurred",
    });
  } finally {
    isProcessing.value = false;
  }
};

const openDeleteDialog = (apiKey: ApiKeySummary) => {
  selectedKey.value = apiKey;
  isDeleteDialogOpen.value = true;
};

const handleDeleteApiKey = async () => {
  if (!selectedKey.value) return;

  isProcessing.value = true;
  try {
    const { execute, data, error, statusCode } = deleteApiKey(
      selectedKey.value.id
    );
    await execute();

    if (statusCode.value === 200 && data.value) {
      toast.success("API key deleted", {
        description: selectedKey.value.name,
      });
      isDeleteDialogOpen.value = false;
      selectedKey.value = null;
      await loadApiKeys();
    } else {
      toast.error("Failed to delete API key", {
        description: error.value?.message || "Unexpected error occurred",
      });
    }
  } catch (err) {
    toast.error("Failed to delete API key", {
      description:
        err instanceof Error ? err.message : "Unexpected error occurred",
    });
  } finally {
    isProcessing.value = false;
  }
};

const formatDate = (value: string | null) => {
  if (!value) return "—";
  return new Date(value).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const copyCreatedKey = async () => {
  if (!createdKey.value?.api_key || !navigator?.clipboard) return;

  try {
    await navigator.clipboard.writeText(createdKey.value.api_key);
    toast.success("API key copied to clipboard");
  } catch (err) {
    toast.error("Failed to copy API key", {
      description:
        err instanceof Error ? err.message : "Clipboard not available",
    });
  }
};

onMounted(() => {
  loadApiKeys();
});
</script>

<template>
  <div class="min-h-screen bg-background">
    <Navigation />

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-foreground mb-4">
          API Key Management
        </h1>
        <p class="text-lg text-muted-foreground max-w-2xl">
          Create and manage API keys for programmatic access. Keep secrets
          secure and rotate them regularly.
        </p>
      </div>

      <div
        class="mb-6 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between"
      >
        <p class="text-sm text-muted-foreground">
          {{ apiKeys.length }} API key{{ apiKeys.length === 1 ? "" : "s" }} in
          your tenant
        </p>
        <Button @click="openCreateDialog"> Create API Key </Button>
      </div>

      <div
        class="bg-card rounded-lg shadow-md border border-border overflow-hidden"
      >
        <div v-if="isFetching" class="p-8 text-center">
          <p class="text-muted-foreground">Loading API keys...</p>
        </div>

        <div v-else-if="apiKeys.length === 0" class="p-8 text-center space-y-2">
          <p class="text-muted-foreground">No API keys yet</p>
          <p class="text-sm text-muted-foreground">
            Create your first API key to enable programmatic access.
          </p>
        </div>

        <Table v-else>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Key Prefix</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Last Used</TableHead>
              <TableHead>Expires</TableHead>
              <TableHead class="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="apiKey in apiKeys" :key="apiKey.id">
              <TableCell class="font-medium text-foreground">
                {{ apiKey.name }}
              </TableCell>
              <TableCell class="font-mono text-sm text-muted-foreground">
                {{ apiKey.key_prefix }}
              </TableCell>
              <TableCell class="text-sm text-muted-foreground">
                {{ formatDate(apiKey.created_at) }}
              </TableCell>
              <TableCell>
                <Badge :variant="apiKey.last_used_at ? 'default' : 'secondary'">
                  {{
                    apiKey.last_used_at
                      ? formatDate(apiKey.last_used_at)
                      : "Never used"
                  }}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge :variant="apiKey.expires_at ? 'secondary' : 'outline'">
                  {{
                    apiKey.expires_at
                      ? formatDate(apiKey.expires_at)
                      : "No expiry"
                  }}
                </Badge>
              </TableCell>
              <TableCell class="text-right">
                <Button
                  variant="destructive"
                  size="sm"
                  @click="openDeleteDialog(apiKey)"
                  :disabled="isProcessing"
                >
                  Delete
                </Button>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </main>

    <!-- Create API Key Dialog -->
    <Dialog v-model:open="isCreateDialogOpen">
      <DialogContent class="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>Create API Key</DialogTitle>
          <DialogDescription>
            Generate a new API key for integrations. The secret is shown only
            once after creation.
          </DialogDescription>
        </DialogHeader>

        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <Label for="api-key-name">Name</Label>
            <Input
              id="api-key-name"
              v-model="createForm.name"
              placeholder="Integration or service name"
              :disabled="!!createdKey"
            />
          </div>

          <div
            class="rounded-md border border-muted bg-muted/40 px-4 py-3 text-sm text-muted-foreground"
          >
            <p class="font-medium text-foreground mb-1">Security reminder</p>
            <p>
              Store the API key securely. Anyone with the secret has the same
              access as you grant here.
            </p>
          </div>

          <div
            v-if="createdKey"
            class="rounded-md border border-primary/40 bg-primary/5 px-4 py-3 space-y-2"
          >
            <div>
              <p class="text-sm font-medium text-primary">API Key (copy now)</p>
              <p class="text-xs text-muted-foreground">
                This is the only time the secret will be displayed.
              </p>
            </div>
            <div class="flex gap-2">
              <Input
                :value="createdKey.api_key"
                readonly
                class="font-mono text-xs flex-1 bg-card text-foreground"
              />
              <Button
                type="button"
                variant="secondary"
                size="sm"
                @click="copyCreatedKey"
              >
                Copy
              </Button>
            </div>
            <p class="text-xs text-muted-foreground">
              Key prefix:
              <span class="font-mono">{{ createdKey.key_prefix }}</span>
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            @click="
              createdKey ? closeCreateDialog() : (isCreateDialogOpen = false)
            "
            :disabled="isProcessing"
          >
            {{ createdKey ? "Close" : "Cancel" }}
          </Button>
          <Button
            @click="createdKey ? closeCreateDialog() : handleCreateApiKey()"
            :disabled="isProcessing || (!createdKey && !createForm.name.trim())"
          >
            {{
              createdKey
                ? "Done"
                : isProcessing
                ? "Creating..."
                : "Create API Key"
            }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Delete API Key Dialog -->
    <Dialog v-model:open="isDeleteDialogOpen">
      <DialogContent class="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>Delete API Key</DialogTitle>
          <DialogDescription>
            This action cannot be undone. The selected API key will lose access
            immediately.
          </DialogDescription>
        </DialogHeader>
        <div class="py-4 space-y-2">
          <p class="text-sm text-muted-foreground">
            Key: <span class="font-mono">{{ selectedKey?.key_prefix }}</span>
          </p>
          <p class="text-sm text-muted-foreground">
            Name: {{ selectedKey?.name }}
          </p>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            @click="isDeleteDialogOpen = false"
            :disabled="isProcessing"
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            @click="handleDeleteApiKey"
            :disabled="isProcessing"
          >
            {{ isProcessing ? "Deleting..." : "Delete API Key" }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
