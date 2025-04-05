# DataPuur Ingestion API Documentation

This document describes the new API structure for the DataPuur ingestion functionality.

## Overview

The new API structure is designed as a wrapper around the existing functionality, providing a more structured and RESTful API design. It's organized into two main resource categories:

1. Sources API (`/api/datapuur/sources/...`) - For raw data acquisition and management
2. Datasets API (`/api/datapuur/datasets/...`) - For processed data (after ingestion)

## API Endpoints

### Sources API

These endpoints handle raw data acquisition and management before processing:

#### Upload & Source Management

- `POST /api/datapuur/sources/upload` - Upload a source file (CSV/JSON)
- `POST /api/datapuur/sources/upload-chunk` - Upload a chunk of a large file
- `POST /api/datapuur/sources/complete-upload` - Complete a chunked upload
- `GET /api/datapuur/sources/` - List all source files with filtering/pagination
- `GET /api/datapuur/sources/files` - Get history of uploaded files with pagination
- `GET /api/datapuur/sources/{source_id}` - Get detailed info about a source
- `DELETE /api/datapuur/sources/{source_id}` - Delete a source file

#### Source Preview & Inspection

- `GET /api/datapuur/sources/{source_id}/preview` - Preview source data
- `GET /api/datapuur/sources/{source_id}/schema` - Get schema of source data
- `GET /api/datapuur/sources/{source_id}/download` - Download original source

#### Ingestion History & Jobs

- `GET /api/datapuur/sources/history` - Get a paginated list of ingestion operations
- `GET /api/datapuur/sources/jobs/{job_id}` - Get status of a specific ingestion job
- `POST /api/datapuur/sources/jobs/{job_id}/cancel` - Cancel an ongoing ingestion job

#### Database Connection Support

- `POST /api/datapuur/sources/db-connect` - Create database connection source
- `GET /api/datapuur/sources/db-test` - Test database connection
- `GET /api/datapuur/sources/db-schema` - Get schema from database connection

### Dataset API

These endpoints handle processed datasets (after ingestion):

#### Dataset Creation & Management

- `POST /api/datapuur/datasets/create` - Create dataset from source (starts ingestion)
- `GET /api/datapuur/datasets/` - List all datasets with filtering/pagination
- `GET /api/datapuur/datasets/{dataset_id}` - Get dataset details
- `DELETE /api/datapuur/datasets/{dataset_id}` - Delete a dataset

#### Dataset Operations

- `GET /api/datapuur/datasets/{dataset_id}/preview` - Preview dataset
- `GET /api/datapuur/datasets/{dataset_id}/schema` - Get dataset schema
- `GET /api/datapuur/datasets/{dataset_id}/statistics` - Get dataset statistics
- `GET /api/datapuur/datasets/{dataset_id}/download` - Download dataset (with format options)

#### Processing Control

- `GET /api/datapuur/datasets/jobs/{job_id}` - Get ingestion job status
- `POST /api/datapuur/datasets/jobs/{job_id}/cancel` - Cancel ingestion job

## Implementation Details

The new API structure wraps around the existing functionality in the `datapuur.py` file. It provides:

1. Improved response models with consistent structure
2. Better URL organization following RESTful principles
3. Proper error handling and status codes
4. Integration with the existing permission system

## Permissions

The APIs maintain the existing hierarchical permission structure:

- `datapuur:read` - Required for read operations (GET)
- `datapuur:write` - Required for write operations (POST, PUT)
- `datapuur:manage` - Required for delete operations and sensitive actions

## Database Models

The implementation uses two main database models:

1. `Source` - Represents raw data uploaded or connected to the system
2. `Dataset` - Represents processed data after ingestion

These models serve as wrappers around the existing `UploadedFile` and `IngestionJob` models to maintain backward compatibility.

## Using the New APIs

To use the new APIs, simply make requests to the endpoints listed above. The existing endpoints continue to work for backward compatibility, but new implementations should use the new API structure.

The implementation doesn't disturb existing frontend components and backend functionality, allowing for a smooth transition.
