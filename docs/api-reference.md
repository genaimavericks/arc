# API Reference

- [Home](./index.md)
- [Getting Started](./getting-started.md)
- [Djinni Assistant](./djinni-assistant.md)
- Tools
  - [DataPuur](./datapuur.md)
  - [KGInsights](./kginsights.md)
- [API Reference](./api-reference.md) (You are here)

## Table of Contents
- [Introduction](#introduction)
- [API Overview](#api-overview)
- [Authentication](#authentication)
  - [Obtaining Access Tokens](#obtaining-access-tokens)
  - [Refreshing Tokens](#refreshing-tokens)
  - [Password Reset](#password-reset)
- [User Management API](#user-management-api)
- [DataPuur API](#datapuur-api)
- [KGInsights API](#kginsights-api)
- [Factory Dashboard API](#factory-dashboard-api)
- [Admin API](#admin-api)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [API Versioning](#api-versioning)

## Introduction

The RSW platform provides a comprehensive set of RESTful APIs that allow developers to interact with all aspects of the system. This API reference documents the available endpoints, request/response formats, authentication requirements, and examples.

## API Overview

- **Base URL**: `https://your-rsw-instance.com/api/v1`
- **Authentication**: JWT token-based
- **Response Format**: JSON
- **Error Handling**: Standard HTTP status codes with error messages

## Authentication

All protected API endpoints require authentication using JWT tokens. The authentication flow is as follows:

### Obtaining Access Tokens

**Endpoint**: `POST /auth/token`

**Request Body**:
```json
{
  "username": "string",
  "password": "string"
}
```

**Response**:
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "string",
  "user": {
    "id": "string",
    "username": "string",
    "email": "string",
    "roles": ["string"],
    "permissions": ["string"]
  }
}
```

**Status Codes**:
- `200 OK`: Successful authentication
- `401 Unauthorized`: Invalid credentials

**Example**:
```bash
curl -X POST https://your-rsw-instance.com/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

### Refreshing Tokens

**Endpoint**: `POST /auth/refresh`

**Request Body**:
```json
{
  "refresh_token": "string"
}
```

**Response**: Same as token endpoint

**Status Codes**:
- `200 OK`: Token refreshed successfully
- `401 Unauthorized`: Invalid refresh token

**Example**:
```bash
curl -X POST https://your-rsw-instance.com/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "your-refresh-token"}'
```

### Password Reset

**Endpoint**: `POST /auth/password-reset-request`

**Request Body**:
```json
{
  "email": "string"
}
```

**Response**:
```json
{
  "message": "Password reset email sent"
}
```

**Status Codes**:
- `200 OK`: Reset email sent
- `404 Not Found`: Email not found

**Example**:
```bash
curl -X POST https://your-rsw-instance.com/api/v1/auth/password-reset-request \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

## User Management API

### Get Current User

**Endpoint**: `GET /users/me`

**Headers**:
- `Authorization: Bearer {access_token}`

**Response**:
```json
{
  "id": "string",
  "username": "string",
  "email": "string",
  "roles": ["string"],
  "permissions": ["string"],
  "created_at": "string",
  "last_login": "string"
}
```

**Status Codes**:
- `200 OK`: Success
- `401 Unauthorized`: Invalid or expired token

**Example**:
```bash
curl -X GET https://your-rsw-instance.com/api/v1/users/me \
  -H "Authorization: Bearer your-access-token"
```

### List Users

**Endpoint**: `GET /users`

**Headers**:
- `Authorization: Bearer {access_token}`

**Query Parameters**:
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 10)
- `search`: Search term for username or email

**Response**:
```json
{
  "items": [
    {
      "id": "string",
      "username": "string",
      "email": "string",
      "role": "string",
      "status": "active",
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 0,
  "page": 1,
  "limit": 10,
  "pages": 1
}
```

**Required Permission**: `admin:read`

**Example**:
```bash
curl -X GET "https://your-rsw-instance.com/api/v1/users?page=1&limit=10" \
  -H "Authorization: Bearer your-access-token"
```

### Create User

**Endpoint**: `POST /users`

**Headers**:
- `Authorization: Bearer {access_token}`

**Request Body**:
```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "role_id": "string"
}
```

**Response**:
```json
{
  "id": "string",
  "username": "string",
  "email": "string",
  "role": "string",
  "status": "active",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

**Required Permission**: `admin:write`

**Example**:
```bash
curl -X POST https://your-rsw-instance.com/api/v1/users \
  -H "Authorization: Bearer your-access-token" \
  -H "Content-Type: application/json" \
  -d '{"username": "newuser", "email": "newuser@example.com", "password": "password123", "role_id": "analyst"}'
```

## DataPuur API

### List Datasets

**Endpoint**: `GET /datapuur/datasets`

**Headers**:
- `Authorization: Bearer {access_token}`

**Query Parameters**:
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 10)
- `search`: Search term for dataset name
- `status`: Filter by status
- `type`: Filter by dataset type

**Response**:
```json
{
  "items": [
    {
      "id": "string",
      "name": "string",
      "dataset": "string",
      "type": "string",
      "last_updated": "2025-01-01T00:00:00Z",
      "status": "string",
      "uploaded_by": "string",
      "file_size": 0,
      "row_count": 0,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 0,
  "page": 1,
  "limit": 10,
  "pages": 1
}
```

**Required Permission**: `datapuur:read`

**Example**:
```bash
curl -X GET "https://your-rsw-instance.com/api/v1/datapuur/datasets?page=1&limit=10" \
  -H "Authorization: Bearer your-access-token"
```

### Upload Dataset

**Endpoint**: `POST /datapuur/datasets`

**Headers**:
- `Authorization: Bearer {access_token}`

**Request Body** (multipart/form-data):
- `file`: File to upload
- `name`: Dataset name

**Response**:
```json
{
  "id": "string",
  "name": "string",
  "dataset": "string",
  "type": "string",
  "last_updated": "2025-01-01T00:00:00Z",
  "status": "processing",
  "uploaded_by": "string",
  "file_size": 0,
  "created_at": "2025-01-01T00:00:00Z"
}
```

**Required Permission**: `datapuur:write`

**Example**:
```bash
curl -X POST https://your-rsw-instance.com/api/v1/datapuur/datasets \
  -H "Authorization: Bearer your-access-token" \
  -F "file=@/path/to/file.csv" \
  -F "name=My Dataset"
```

## KGInsights API

### Get Graph Data

**Endpoint**: `GET /kginsights/graph/{graph_id}`

**Headers**:
- `Authorization: Bearer {access_token}`

**Response**:
```json
{
  "nodes": [
    {
      "id": 0,
      "label": "string",
      "type": "string",
      "color": "string",
      "x": 0,
      "y": 0
    }
  ],
  "edges": [
    {
      "id": 0,
      "from_node": 0,
      "to_node": 0,
      "label": "string"
    }
  ]
}
```

**Required Permission**: `kginsights:read`

**Example**:
```bash
curl -X GET https://your-rsw-instance.com/api/v1/kginsights/graph/123 \
  -H "Authorization: Bearer your-access-token"
```

### Create Graph

**Endpoint**: `POST /kginsights/graph`

**Headers**:
- `Authorization: Bearer {access_token}`

**Request Body**:
```json
{
  "name": "string",
  "dataset_id": "string",
  "config": {
    "entity_types": ["string"],
    "relationship_types": ["string"]
  }
}
```

**Response**:
```json
{
  "id": "string",
  "name": "string",
  "status": "processing",
  "created_at": "2025-01-01T00:00:00Z"
}
```

**Required Permission**: `kginsights:write`

**Example**:
```bash
curl -X POST https://your-rsw-instance.com/api/v1/kginsights/graph \
  -H "Authorization: Bearer your-access-token" \
  -H "Content-Type: application/json" \
  -d '{"name": "Customer Relationships", "dataset_id": "abc123", "config": {"entity_types": ["Customer", "Product"], "relationship_types": ["Purchased"]}}'
```

## Factory Dashboard API

### Get Factory Metrics

**Endpoint**: `GET /factory/metrics`

**Headers**:
- `Authorization: Bearer {access_token}`

**Query Parameters**:
- `factory_id`: Optional factory ID to filter by
- `start_date`: Start date for metrics (YYYY-MM-DD)
- `end_date`: End date for metrics (YYYY-MM-DD)

**Response**:
```json
{
  "total_production": 18650000,
  "total_revenue": 11770010000,
  "average_quality": 90.4,
  "downtime_loss": 268197.4,
  "production_trend": [
    {
      "date": "2025-01-01",
      "value": 620000
    }
  ],
  "performance_metrics": {
    "quality_pass_rate": 95.2,
    "low_defects": 87.5,
    "profit_margin": 76.8,
    "machine_utilization": 82.3,
    "production_volume": 91.7
  }
}
```

**Required Permission**: `factory:read`

**Example**:
```bash
curl -X GET "https://your-rsw-instance.com/api/v1/factory/metrics?start_date=2025-01-01&end_date=2025-06-30" \
  -H "Authorization: Bearer your-access-token"
```

## Admin API

### Get Activity Logs

**Endpoint**: `GET /admin/activity-logs`

**Headers**:
- `Authorization: Bearer {access_token}`

**Query Parameters**:
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 10)
- `user_id`: Filter by user ID
- `action`: Filter by action type
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)

**Response**:
```json
{
  "items": [
    {
      "id": "string",
      "user_id": "string",
      "username": "string",
      "action": "string",
      "details": "string",
      "timestamp": "2025-01-01T00:00:00Z",
      "ip_address": "string"
    }
  ],
  "total": 0,
  "page": 1,
  "limit": 10,
  "pages": 1
}
```

**Required Permission**: `admin:read`

**Example**:
```bash
curl -X GET "https://your-rsw-instance.com/api/v1/admin/activity-logs?page=1&limit=10" \
  -H "Authorization: Bearer your-access-token"
```

## Error Handling

All API endpoints use standard HTTP status codes:

- `200 OK`: Request succeeded
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

Error responses follow this format:

```json
{
  "detail": "Error message",
  "code": "ERROR_CODE",
  "params": {}
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse:

- Standard users: 100 requests per minute
- Admin users: 300 requests per minute

Rate limit headers are included in all responses:

- `X-RateLimit-Limit`: Maximum requests per minute
- `X-RateLimit-Remaining`: Remaining requests in the current window
- `X-RateLimit-Reset`: Time when the rate limit resets (Unix timestamp)

When rate limit is exceeded, the API returns:

- Status code: `429 Too Many Requests`
- Response body: `{"detail": "Rate limit exceeded. Try again in X seconds"}`

## API Versioning

The RSW API uses URL versioning:

- Current version: `/api/v1/`
- Future versions: `/api/v2/`, etc.

API changes follow these guidelines:
- **Major version changes**: Breaking changes (v1 → v2)
- **Minor version changes**: Non-breaking additions (documented in release notes)
- **Patch changes**: Bug fixes and minor improvements (no API changes)

---

*Previous: [Dashboard Creator](./dashboard-creator.md)*

*Last updated: July 6, 2025*
