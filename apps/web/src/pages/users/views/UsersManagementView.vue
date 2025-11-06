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
  listUsers,
  createUser,
  updateUser,
  deleteUser,
  type UserRole,
  type UserSummary,
  type CreateUserRequest,
  type UpdateUserRequest,
} from "@/services/users";
import { toast } from "vue-sonner";
import { useAuthStore } from "@/stores/auth";

// Auth store
const authStore = useAuthStore();

// State
const users = ref<UserSummary[]>([]);
const isLoading = ref(false);
const currentPage = ref(1);
const pageSize = ref(50);
const totalPages = ref(1);
const totalUsers = ref(0);
const searchQuery = ref("");
const sortBy = ref<"email" | "created_at">("created_at");
const sortOrder = ref<"asc" | "desc">("desc");

// Dialog states
const isCreateDialogOpen = ref(false);
const isEditDialogOpen = ref(false);
const isDeleteDialogOpen = ref(false);

// Form states
const createForm = ref<CreateUserRequest>({
  email: "",
  password: "",
});

const editForm = ref<UpdateUserRequest>({
  email: undefined,
  is_active: undefined,
  role: undefined,
  password: undefined,
});

const selectedUser = ref<UserSummary | null>(null);

// Computed
const displayedUsers = computed(() => users.value);

// Methods
const loadUsers = async () => {
  isLoading.value = true;
  try {
    const { execute, data, error, statusCode } = listUsers({
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value || undefined,
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
    });

    await execute();

    if (statusCode.value === 200 && data.value) {
      users.value = data.value.users;
      totalUsers.value = data.value.total;
      totalPages.value = data.value.total_pages;
      currentPage.value = data.value.page;
      pageSize.value = data.value.page_size;
    } else {
      toast.error("Failed to load users", {
        description: error.value?.message || "An error occurred",
      });
    }
  } catch (err) {
    toast.error("Failed to load users", {
      description: err instanceof Error ? err.message : "An error occurred",
    });
  } finally {
    isLoading.value = false;
  }
};

const handleSearch = () => {
  currentPage.value = 1; // Reset to first page on search
  loadUsers();
};

const handleSort = (column: "email" | "created_at") => {
  if (sortBy.value === column) {
    sortOrder.value = sortOrder.value === "asc" ? "desc" : "asc";
  } else {
    sortBy.value = column;
    sortOrder.value = "asc";
  }
  loadUsers();
};

const openCreateDialog = () => {
  createForm.value = {
    email: "",
    password: "",
  };
  isCreateDialogOpen.value = true;
};

const handleCreate = async () => {
  isLoading.value = true;
  try {
    const { execute, data, error, statusCode } = createUser(createForm.value);

    await execute();

    if (statusCode.value === 201 && data.value) {
      toast.success("User created successfully", {
        description: `User ${createForm.value.email} has been created`,
      });
      isCreateDialogOpen.value = false;
      await loadUsers();
    } else {
      toast.error("Failed to create user", {
        description: error.value?.message || "An error occurred",
      });
    }
  } catch (err) {
    toast.error("Failed to create user", {
      description: err instanceof Error ? err.message : "An error occurred",
    });
  } finally {
    isLoading.value = false;
  }
};

const openEditDialog = (user: UserSummary) => {
  selectedUser.value = user;
  editForm.value = {
    email: user.email,
    is_active: user.is_active,
    role: user.role,
    password: undefined,
  };
  isEditDialogOpen.value = true;
};

const handleEdit = async () => {
  if (!selectedUser.value) return;

  isLoading.value = true;
  try {
    const { execute, data, error, statusCode } = updateUser(
      selectedUser.value.id,
      editForm.value
    );

    await execute();

    if (statusCode.value === 200 && data.value) {
      toast.success("User updated successfully", {
        description: `User has been updated`,
      });
      isEditDialogOpen.value = false;
      await loadUsers();
    } else {
      toast.error("Failed to update user", {
        description: error.value?.message || "An error occurred",
      });
    }
  } catch (err) {
    toast.error("Failed to update user", {
      description: err instanceof Error ? err.message : "An error occurred",
    });
  } finally {
    isLoading.value = false;
  }
};

const openDeleteDialog = (user: UserSummary) => {
  selectedUser.value = user;
  isDeleteDialogOpen.value = true;
};

const handleDelete = async () => {
  if (!selectedUser.value) return;

  isLoading.value = true;
  try {
    const { execute, data, error, statusCode } = deleteUser(
      selectedUser.value.id
    );

    await execute();

    if (statusCode.value === 200 && data.value) {
      toast.success("User deleted successfully", {
        description: `User ${selectedUser.value.email} and all associated data have been removed`,
      });
      isDeleteDialogOpen.value = false;
      await loadUsers();
    } else {
      toast.error("Failed to delete user", {
        description: error.value?.message || "An error occurred",
      });
    }
  } catch (err) {
    toast.error("Failed to delete user", {
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

const getRoleBadgeVariant = (role: UserRole) => {
  return role === "tenant_admin" ? "default" : "secondary";
};

const getRoleLabel = (role: UserRole) => {
  return role === "tenant_admin" ? "Admin" : "User";
};

const getStatusBadgeVariant = (isActive: boolean) => {
  return isActive ? "default" : "secondary";
};

const isCurrentUser = (userId: string) => {
  return authStore.currentUser?.id === userId;
};

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++;
    loadUsers();
  }
};

const previousPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--;
    loadUsers();
  }
};

// Lifecycle
onMounted(() => {
  loadUsers();
});
</script>

<template>
  <div class="min-h-screen bg-background">
    <Navigation />

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-foreground mb-4">User Management</h1>
        <p class="text-lg text-muted-foreground">Manage users in your tenant</p>
      </div>

      <!-- Actions Bar -->
      <div
        class="mb-6 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between"
      >
        <div class="flex gap-2 w-full sm:w-auto">
          <Input
            v-model="searchQuery"
            placeholder="Search users by email..."
            class="w-full sm:w-80 text-foreground"
            @keyup.enter="handleSearch"
          />
          <Button @click="handleSearch" variant="secondary"> Search </Button>
        </div>
        <Button @click="openCreateDialog"> Create User </Button>
      </div>

      <!-- Users Table -->
      <div
        class="bg-card rounded-lg shadow-md border border-border overflow-hidden"
      >
        <div v-if="isLoading" class="p-8 text-center">
          <p class="text-muted-foreground">Loading users...</p>
        </div>

        <div v-else-if="displayedUsers.length === 0" class="p-8 text-center">
          <p class="text-muted-foreground">No users found</p>
        </div>

        <Table v-else>
          <TableHeader>
            <TableRow>
              <TableHead
                class="cursor-pointer hover:bg-muted/50"
                @click="handleSort('email')"
              >
                <div class="flex items-center gap-2">
                  Email
                  <span v-if="sortBy === 'email'" class="text-xs">
                    {{ sortOrder === "asc" ? "↑" : "↓" }}
                  </span>
                </div>
              </TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
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
            <TableRow v-for="user in displayedUsers" :key="user.id">
              <TableCell class="font-medium text-muted-foreground">
                {{ user.email }}
                <span
                  v-if="isCurrentUser(user.id)"
                  class="ml-2 text-xs text-primary"
                  >(You)</span
                >
              </TableCell>
              <TableCell>
                <Badge :variant="getRoleBadgeVariant(user.role)">{{
                  getRoleLabel(user.role)
                }}</Badge>
              </TableCell>
              <TableCell>
                <Badge :variant="getStatusBadgeVariant(user.is_active)">
                  {{ user.is_active ? "Active" : "Inactive" }}
                </Badge>
              </TableCell>
              <TableCell class="text-sm text-muted-foreground">
                {{ formatDate(user.created_at) }}
              </TableCell>
              <TableCell class="text-right">
                <div class="flex gap-2 justify-end">
                  <Button
                    @click="openEditDialog(user)"
                    variant="secondary"
                    size="sm"
                  >
                    Edit
                  </Button>
                  <Button
                    @click="openDeleteDialog(user)"
                    variant="destructive"
                    size="sm"
                    :disabled="isCurrentUser(user.id)"
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
            Page {{ currentPage }} of {{ totalPages }} ({{ totalUsers }} total)
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

    <!-- Create User Dialog -->
    <Dialog v-model:open="isCreateDialogOpen">
      <DialogContent class="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create New User</DialogTitle>
          <DialogDescription>
            Create a new user within your tenant. The user will be assigned the
            tenant_user role by default.
          </DialogDescription>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <Label for="create-email">Email</Label>
            <Input
              id="create-email"
              v-model="createForm.email"
              type="email"
              placeholder="user@example.com"
            />
          </div>
          <div class="grid gap-2">
            <Label for="create-password">Password</Label>
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
            {{ isLoading ? "Creating..." : "Create User" }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Edit User Dialog -->
    <Dialog v-model:open="isEditDialogOpen">
      <DialogContent class="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Edit User</DialogTitle>
          <DialogDescription>
            Update the user's information. Leave password empty to keep it
            unchanged.
          </DialogDescription>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <Label for="edit-email">Email</Label>
            <Input
              id="edit-email"
              v-model="editForm.email"
              type="email"
              placeholder="user@example.com"
            />
          </div>
          <div class="grid gap-2">
            <Label for="edit-role">Role</Label>
            <select
              id="edit-role"
              v-model="editForm.role"
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <option value="tenant_admin">Admin</option>
              <option value="tenant_user">User</option>
            </select>
          </div>
          <div class="grid gap-2">
            <div class="flex items-center gap-2">
              <input
                id="edit-active"
                v-model="editForm.is_active"
                type="checkbox"
                class="h-4 w-4 rounded border-input"
              />
              <Label for="edit-active" class="cursor-pointer"
                >Active Status</Label
              >
            </div>
          </div>
          <div class="grid gap-2">
            <Label for="edit-password"
              >Password (leave empty to keep unchanged)</Label
            >
            <Input
              id="edit-password"
              v-model="editForm.password"
              type="password"
              placeholder="••••••••"
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

    <!-- Delete User Dialog -->
    <Dialog v-model:open="isDeleteDialogOpen">
      <DialogContent class="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Delete User</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete
            <strong>{{ selectedUser?.email }}</strong
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
              <li>The user record</li>
              <li>All refresh tokens associated with this user</li>
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
            {{ isLoading ? "Deleting..." : "Delete User" }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
