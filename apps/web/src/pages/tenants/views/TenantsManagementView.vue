<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
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
import {
  listTenants,
  createTenant,
  updateTenant,
  deleteTenant,
  type TenantSummary,
  type CreateTenantRequest,
  type UpdateTenantRequest,
} from "@/services/tenants";
import { toast } from "vue-sonner";

// State
const tenants = ref<TenantSummary[]>([]);
const isLoading = ref(false);
const currentPage = ref(1);
const pageSize = ref(50);
const totalPages = ref(1);
const totalTenants = ref(0);
const searchQuery = ref("");
const sortBy = ref<"name" | "created_at">("created_at");
const sortOrder = ref<"asc" | "desc">("desc");

// Dialog states
const isCreateDialogOpen = ref(false);
const isEditDialogOpen = ref(false);
const isDeleteDialogOpen = ref(false);

// Form states
const createForm = ref<CreateTenantRequest>({
  name: "",
  email: "",
  password: "",
});

const editForm = ref<UpdateTenantRequest>({
  name: "",
});

const selectedTenant = ref<TenantSummary | null>(null);

// Computed
const displayedTenants = computed(() => tenants.value);

// Methods
const loadTenants = async () => {
  isLoading.value = true;
  try {
    const { execute, data, error, statusCode } = listTenants({
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value || undefined,
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
    });

    await execute();

    if (statusCode.value === 200 && data.value) {
      tenants.value = data.value.tenants;
      totalTenants.value = data.value.total;
      totalPages.value = data.value.total_pages;
      currentPage.value = data.value.page;
      pageSize.value = data.value.page_size;
    } else {
      toast.error("Failed to load tenants", {
        description: error.value?.message || "An error occurred",
      });
    }
  } catch (err) {
    toast.error("Failed to load tenants", {
      description: err instanceof Error ? err.message : "An error occurred",
    });
  } finally {
    isLoading.value = false;
  }
};

const handleSearch = () => {
  currentPage.value = 1; // Reset to first page on search
  loadTenants();
};

const handleSort = (column: "name" | "created_at") => {
  if (sortBy.value === column) {
    sortOrder.value = sortOrder.value === "asc" ? "desc" : "asc";
  } else {
    sortBy.value = column;
    sortOrder.value = "asc";
  }
  loadTenants();
};

const openCreateDialog = () => {
  createForm.value = {
    name: "",
    email: "",
    password: "",
  };
  isCreateDialogOpen.value = true;
};

const handleCreate = async () => {
  isLoading.value = true;
  try {
    const { execute, data, error, statusCode } = createTenant(createForm.value);

    await execute();

    if (statusCode.value === 200 && data.value) {
      toast.success("Tenant created successfully", {
        description: `Tenant ${createForm.value.name} has been created`,
      });
      isCreateDialogOpen.value = false;
      await loadTenants();
    } else {
      toast.error("Failed to create tenant", {
        description: error.value?.message || "An error occurred",
      });
    }
  } catch (err) {
    toast.error("Failed to create tenant", {
      description: err instanceof Error ? err.message : "An error occurred",
    });
  } finally {
    isLoading.value = false;
  }
};

const openEditDialog = (tenant: TenantSummary) => {
  selectedTenant.value = tenant;
  editForm.value = {
    name: tenant.name,
  };
  isEditDialogOpen.value = true;
};

const handleEdit = async () => {
  if (!selectedTenant.value) return;

  isLoading.value = true;
  try {
    const { execute, data, error, statusCode } = updateTenant(
      selectedTenant.value.id,
      editForm.value
    );

    await execute();

    if (statusCode.value === 200 && data.value) {
      toast.success("Tenant updated successfully", {
        description: `Tenant has been renamed to ${editForm.value.name}`,
      });
      isEditDialogOpen.value = false;
      await loadTenants();
    } else {
      toast.error("Failed to update tenant", {
        description: error.value?.message || "An error occurred",
      });
    }
  } catch (err) {
    toast.error("Failed to update tenant", {
      description: err instanceof Error ? err.message : "An error occurred",
    });
  } finally {
    isLoading.value = false;
  }
};

const openDeleteDialog = (tenant: TenantSummary) => {
  selectedTenant.value = tenant;
  isDeleteDialogOpen.value = true;
};

const handleDelete = async () => {
  if (!selectedTenant.value) return;

  isLoading.value = true;
  try {
    const { execute, data, error, statusCode } = deleteTenant(
      selectedTenant.value.id
    );

    await execute();

    if (statusCode.value === 200 && data.value) {
      toast.success("Tenant deleted successfully", {
        description: `Tenant ${selectedTenant.value.name} and all its data have been removed`,
      });
      isDeleteDialogOpen.value = false;
      await loadTenants();
    } else {
      toast.error("Failed to delete tenant", {
        description: error.value?.message || "An error occurred",
      });
    }
  } catch (err) {
    toast.error("Failed to delete tenant", {
      description: err instanceof Error ? err.message : "An error occurred",
    });
  } finally {
    isLoading.value = false;
  }
};

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++;
    loadTenants();
  }
};

const previousPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--;
    loadTenants();
  }
};

// Lifecycle
onMounted(() => {
  loadTenants();
});
</script>

<template>
  <div class="min-h-screen bg-background">
    <Navigation />

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-foreground mb-4">
          Tenant Management
        </h1>
        <p class="text-lg text-muted-foreground">
          Manage all tenants in the system
        </p>
      </div>

      <!-- Actions Bar -->
      <div
        class="mb-6 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between"
      >
        <div class="flex gap-2 w-full sm:w-auto">
          <Input
            v-model="searchQuery"
            placeholder="Search tenants by name..."
            class="w-full sm:w-80 text-foreground"
            @keyup.enter="handleSearch"
          />
          <Button @click="handleSearch" variant="secondary"> Search </Button>
        </div>
        <Button @click="openCreateDialog"> Create Tenant </Button>
      </div>

      <!-- Tenants Table -->
      <div
        class="bg-card rounded-lg shadow-md border border-border overflow-hidden"
      >
        <div v-if="isLoading" class="p-8 text-center">
          <p class="text-muted-foreground">Loading tenants...</p>
        </div>

        <div v-else-if="displayedTenants.length === 0" class="p-8 text-center">
          <p class="text-muted-foreground">No tenants found</p>
        </div>

        <Table v-else>
          <TableHeader>
            <TableRow>
              <TableHead
                class="cursor-pointer hover:bg-muted/50"
                @click="handleSort('name')"
              >
                <div class="flex items-center gap-2">
                  Name
                  <span v-if="sortBy === 'name'" class="text-xs">
                    {{ sortOrder === "asc" ? "↑" : "↓" }}
                  </span>
                </div>
              </TableHead>
              <TableHead>Graph Name</TableHead>
              <TableHead>Users</TableHead>
              <TableHead
                class="cursor-pointer hover:bg-muted/50"
                @click="handleSort('created_at')"
              >
                <div class="flex items-center gap-2">
                  Created At
                  <span v-if="sortBy === 'created_at'" class="text-xs">
                    {{ sortOrder === "asc" ? "↑" : "↓" }}
                  </span>
                </div>
              </TableHead>
              <TableHead class="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="tenant in displayedTenants" :key="tenant.id">
              <TableCell class="font-medium text-muted-foreground">{{
                tenant.name
              }}</TableCell>
              <TableCell>
                <code
                  class="text-xs bg-muted px-2 py-1 rounded text-muted-foreground"
                  >{{ tenant.age_graph_name }}</code
                >
              </TableCell>
              <TableCell>
                <Badge variant="secondary">{{ tenant.user_count }}</Badge>
              </TableCell>
              <TableCell class="text-sm text-muted-foreground">
                {{ formatDate(tenant.created_at) }}
              </TableCell>
              <TableCell class="text-right">
                <div class="flex gap-2 justify-end">
                  <Button
                    @click="openEditDialog(tenant)"
                    variant="secondary"
                    size="sm"
                  >
                    Edit
                  </Button>
                  <Button
                    @click="openDeleteDialog(tenant)"
                    variant="destructive"
                    size="sm"
                  >
                    Delete
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>

        <!-- Pagination -->
        <div
          v-if="totalPages > 1"
          class="px-6 py-4 border-t border-border flex items-center justify-between"
        >
          <p class="text-sm text-muted-foreground">
            Page {{ currentPage }} of {{ totalPages }} ({{ totalTenants }}
            total)
          </p>
          <div class="flex gap-2">
            <Button
              @click="previousPage"
              variant="outline"
              size="sm"
              :disabled="currentPage === 1"
            >
              Previous
            </Button>
            <Button
              @click="nextPage"
              variant="outline"
              size="sm"
              :disabled="currentPage === totalPages"
            >
              Next
            </Button>
          </div>
        </div>
      </div>
    </main>

    <!-- Create Tenant Dialog -->
    <Dialog v-model:open="isCreateDialogOpen">
      <DialogContent class="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create New Tenant</DialogTitle>
          <DialogDescription>
            Create a new tenant with an initial admin user and dedicated graph
            database.
          </DialogDescription>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <Label for="create-name">Tenant Name</Label>
            <Input
              id="create-name"
              v-model="createForm.name"
              placeholder="Acme Corporation"
            />
          </div>
          <div class="grid gap-2">
            <Label for="create-email">Admin Email</Label>
            <Input
              id="create-email"
              v-model="createForm.email"
              type="email"
              placeholder="admin@acme.com"
            />
          </div>
          <div class="grid gap-2">
            <Label for="create-password">Admin Password</Label>
            <Input
              id="create-password"
              v-model="createForm.password"
              type="password"
              placeholder="••••••••"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            @click="isCreateDialogOpen = false"
            variant="outline"
            :disabled="isLoading"
          >
            Cancel
          </Button>
          <Button @click="handleCreate" :disabled="isLoading">
            {{ isLoading ? "Creating..." : "Create Tenant" }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Edit Tenant Dialog -->
    <Dialog v-model:open="isEditDialogOpen">
      <DialogContent class="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Edit Tenant</DialogTitle>
          <DialogDescription>
            Update the tenant's name. This will not affect users or data.
          </DialogDescription>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <Label for="edit-name">Tenant Name</Label>
            <Input
              id="edit-name"
              v-model="editForm.name"
              placeholder="Acme Corporation"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            @click="isEditDialogOpen = false"
            variant="outline"
            :disabled="isLoading"
          >
            Cancel
          </Button>
          <Button @click="handleEdit" :disabled="isLoading">
            {{ isLoading ? "Saving..." : "Save Changes" }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Delete Tenant Dialog -->
    <Dialog v-model:open="isDeleteDialogOpen">
      <DialogContent class="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Delete Tenant</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete
            <strong>{{ selectedTenant?.name }}</strong
            >?
          </DialogDescription>
        </DialogHeader>
        <div class="py-4">
          <div
            class="rounded-md bg-destructive/10 border border-destructive/20 p-4"
          >
            <p class="text-sm text-destructive font-medium mb-2">
              ⚠️ This action cannot be undone
            </p>
            <p class="text-sm text-muted-foreground">
              This will permanently delete:
            </p>
            <ul class="text-sm text-muted-foreground mt-2 ml-4 list-disc">
              <li>The tenant record</li>
              <li>All {{ selectedTenant?.user_count }} users</li>
              <li>All API keys</li>
              <li>
                The entire graph database ({{ selectedTenant?.age_graph_name }})
              </li>
            </ul>
          </div>
        </div>
        <DialogFooter>
          <Button
            @click="isDeleteDialogOpen = false"
            variant="outline"
            :disabled="isLoading"
          >
            Cancel
          </Button>
          <Button
            @click="handleDelete"
            variant="destructive"
            :disabled="isLoading"
          >
            {{ isLoading ? "Deleting..." : "Delete Tenant" }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
