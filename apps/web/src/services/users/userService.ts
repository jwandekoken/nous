import { useApiFetch } from "@/services/shared";
import type {
  CreateUserRequest,
  CreateUserResponse,
  UpdateUserRequest,
  UpdateUserResponse,
  DeleteUserResponse,
  ListUsersRequest,
  ListUsersResponse,
  GetUserResponse,
} from "./types";

/**
 * Creates a new user within the tenant.
 */
export const createUser = (request: CreateUserRequest) => {
  return useApiFetch("/auth/users", {
    immediate: false,
  })
    .post(request)
    .json<CreateUserResponse>();
};

/**
 * Lists all users within the tenant with pagination and filtering.
 */
export const listUsers = (request?: ListUsersRequest) => {
  const params = new URLSearchParams();
  if (request?.page) params.append("page", request.page.toString());
  if (request?.page_size)
    params.append("page_size", request.page_size.toString());
  if (request?.search) params.append("search", request.search);
  if (request?.sort_by) params.append("sort_by", request.sort_by);
  if (request?.sort_order) params.append("sort_order", request.sort_order);

  const queryString = params.toString();
  const url = queryString ? `/auth/users?${queryString}` : "/auth/users";

  return useApiFetch(url, {
    immediate: false,
  })
    .get()
    .json<ListUsersResponse>();
};

/**
 * Gets a single user by ID.
 */
export const getUser = (userId: string) => {
  return useApiFetch(`/auth/users/${userId}`, {
    immediate: false,
  })
    .get()
    .json<GetUserResponse>();
};

/**
 * Updates a user's information.
 */
export const updateUser = (userId: string, request: UpdateUserRequest) => {
  return useApiFetch(`/auth/users/${userId}`, {
    immediate: false,
  })
    .patch(request)
    .json<UpdateUserResponse>();
};

/**
 * Deletes a user and all associated data.
 */
export const deleteUser = (userId: string) => {
  return useApiFetch(`/auth/users/${userId}`, {
    immediate: false,
  })
    .delete()
    .json<DeleteUserResponse>();
};
