---
title: Quick Start
description: Get started quickly with Nous by setting up authentication and making your first API calls
---

Now that you have Nous installed and running, this guide will walk you through the initial setup, creating your first tenant, and making API calls.

## 1. Initial Setup

### Create Super Admin
1. Navigate to the **Web Dashboard** at [http://localhost:5173](http://localhost:5173).
2. Since this is your first time accessing the system, you will be automatically redirected to the **Setup** page.
3. Create your **Super Admin** account by providing an email and password.

### Login
Once the admin account is created, you will be redirected to the login page. Log in with your new credentials.

## 2. Create a Tenant

As a Super Admin, your primary role is to manage tenants (organizations or workspaces).

1. After logging in, you will be on the **Tenants Management** page (`/tenants`).
2. Click the **"Create Tenant"** button.
3. Fill in the details for the new tenant and its administrator:
   - **Tenant Name** (e.g., "My Organization")
   - **Admin Email** (for the tenant admin)
   - **Admin Password**
4. Click **Create Tenant**. This creates the organization and its first admin user simultaneously.

## 3. Generate an API Key

To use the Nous API programmatically, you need an API key.

1. **Log out** of the Super Admin account.
2. **Log in** using the **Tenant Admin** credentials you just created (the email and password from step 2).
3. Navigate to the **API Keys** section (`/api-keys`) using the sidebar.
4. Click **"Create API Key"**.
5. Give your key a name (e.g., "Development Key").
6. **Copy the key immediately**. You won't be able to see it again.

## 4. Use the API

With your API Key, you can now interact with the Nous brain. The API is available at `http://localhost:8000`.

### Assimilate Information (Write)

The `assimilate` endpoint allows you to feed text into the knowledge graph. Nous will extract facts and associate them with an entity identified by an external identifier (like email).

```bash
curl -X POST "http://localhost:8000/api/v1/graph/entities/assimilate" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": {
      "type": "email",
      "value": "alice@example.com"
    },
    "content": "Alice is a software engineer living in New York. She works at TechCorp and loves hiking."
  }'
```

### Lookup Information (Read)

The `lookup` endpoint allows you to retrieve entity information using an identifier (e.g., email, phone).

```bash
curl -X GET "http://localhost:8000/api/v1/graph/entities/lookup?type=email&value=alice@example.com" \
  -H "X-API-Key: YOUR_API_KEY"
```

You can also use semantic search with the `rag_query` parameter:

```bash
curl -X GET "http://localhost:8000/api/v1/graph/entities/lookup?type=email&value=alice@example.com&rag_query=Where%20does%20Alice%20work" \
  -H "X-API-Key: YOUR_API_KEY"
```

### Explore the Graph

Back in the Web Dashboard, you can visualize the data you just added:
1. Go to the **Graph Explorer** (`/graph`).
2. You should see nodes representing "Alice", "TechCorp", "New York", etc., and the relationships connecting them.

## Next Steps

- Read the [Deployment Guide](/getting-started/deployment/) to learn how to deploy Nous to production.
- Check out the full [API Documentation](http://localhost:8000/docs) (Swagger UI).

