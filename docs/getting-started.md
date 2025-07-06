# Getting Started with RSW

- [Home](./index.md)
- [Getting Started](./getting-started.md) (You are here)
- [Djinni Assistant](./djinni-assistant.md)
- Tools
  - [DataPuur](./datapuur.md)
  - [KGInsights](./kginsights.md)
- [API Reference](./api-reference.md)

## Table of Contents
- [Introduction](#introduction)
- [System Requirements](#system-requirements)
- [Installation](#installation)
  - [Development Environment Setup](#development-environment-setup)
  - [Environment Configuration](#environment-configuration)
- [Initial Setup](#initial-setup)
  - [First-time Login](#first-time-login)
  - [Creating Users and Roles](#creating-users-and-roles)
  - [Setting Up Permissions](#setting-up-permissions)
- [Navigation Overview](#navigation-overview)
- [Basic Usage Workflow](#basic-usage-workflow)
- [Troubleshooting](#troubleshooting)
- [Getting Help](#getting-help)

## Introduction

Welcome to the RSW Smart Data Intelligence (SDI) platform! This guide will help you set up and start using the platform efficiently. RSW combines data processing, knowledge graph insights, factory analytics, and AI assistance in a unified interface.

## System Requirements

### Server Requirements
- Python 3.8+ for backend services
- Node.js 16+ for frontend development
- PostgreSQL 13+ for database
- 8GB RAM minimum (16GB recommended)
- 4 CPU cores minimum

### Client Requirements
- Modern web browser (Chrome, Firefox, Edge, Safari)
- Minimum screen resolution: 1366x768 (1920x1080 recommended)

## Installation

### Development Environment Setup

1. **Clone the Repository**

```bash
git clone https://github.com/your-organization/rsw.git
cd rsw
```

2. **Install Backend Dependencies**

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

3. **Install Frontend Dependencies**

```bash
# Install dependencies
npm install
```

### Environment Configuration

Create a `.env` file in the root directory with the following variables:

```
# Database
DATABASE_URL=sqlite:///./test.db
# For production, use PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost/rsw

# Authentication
SECRET_KEY=your_secret_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# OpenAI (for Djinni Assistant)
OPENAI_API_KEY=your_openai_api_key_here

# CORS settings (for development)
CORS_ORIGINS=http://localhost:3000
```

4. **Initialize the Database**

```bash
# Run database migrations
python -m api.scripts.create_db
```

5. **Start the Application**

```bash
# Start the backend server
uvicorn api.main:app --reload

# In a separate terminal, start the frontend
npm run dev
```

6. **Access the Application**

Open your browser and navigate to `http://localhost:3000`

## Initial Setup

### First-time Login

When you first access the application, use the default admin credentials:

- **Username**: admin
- **Password**: admin

You will be prompted to change the password on first login.

![Admin Login Screen](./img/admin-login.png)

### Creating Users and Roles

1. Navigate to the Admin Dashboard by clicking on "Admin" in the sidebar
2. Select the "Users" tab
3. Click "Add User" to create new user accounts
4. Assign appropriate roles and permissions based on user responsibilities

![User Management Screen](./img/admin-dashboard.png)

### Setting Up Permissions

RSW uses a hierarchical permission system:

- **DataPuur**: datapuur:read, datapuur:write, datapuur:manage
- **KGInsights**: kginsights:read, kginsights:write, kginsights:manage
- **Factory Dashboard**: factory:read, factory:write, factory:manage
- **Admin**: admin:read, admin:write, admin:manage

Assign these permissions based on user roles and responsibilities.

## Navigation Overview

The RSW platform is organized into several main sections:

### Command Centers
- **Factory Dashboard**: Access factory performance metrics and analytics
  - Performance Overview
  - Operations & Maintenance
  - Workforce & Resources

### Personal Dashboard
- **My Dashboards**: View your saved custom dashboards
- **Dashboard Creator**: Create and edit custom dashboards
- **Recent Activity**: View your recent actions in the system

### Djinni
- **Djinni Assistant**: Interact with the AI assistant for data insights
- **Conversations**: View your conversation history with Djinni

### Tools
- **DataPuur**: Data ingestion, processing, and analytics
  - Dashboard: Overview of data metrics
  - Ingestion: Upload and manage data sources
  - AI Profile: Automated data profiling
  - AI Transformation: AI-powered data transformations
  - Data Catalog: Browse available datasets
  - Export: Download processed data
- **K-Graff**: Knowledge graph management
  - K-Graff Dashboard: Overview of graph metrics
  - Generate Graph: Create new knowledge graphs
  - Manage K-Graff: Manage existing graphs
  - K-Graff Insights: View insights derived from graphs

### System
- **Settings**: Configure application settings
- **Help**: Access documentation and support

## Basic Usage Workflow

### 1. Data Ingestion
- Navigate to DataPuur > Ingestion
- Upload data files or connect to databases
- Configure ingestion parameters
- Start ingestion process

### 2. Data Analysis
- Navigate to DataPuur > Dashboard
- View data metrics and visualizations
- Use AI Profile for automated insights

### 3. Knowledge Graph Creation
- Navigate to K-Graff > Generate Graph
- Select data sources
- Configure graph parameters
- Generate knowledge graph

### 4. Factory Analytics
- Navigate to Factory Dashboard
- View performance metrics
- Analyze production trends
- Monitor machine utilization

![Factory Dashboard](./img/factory-dashboard.png)

### 5. AI Assistance
- Navigate to Djinni Assistant
- Ask questions in natural language
- View visualizations and insights

## Troubleshooting

### Login Issues
- Verify username and password
- Check if account is active
- Clear browser cache and cookies

### Data Upload Failures
- Verify file format and size
- Check network connection
- Review error messages in logs

### Performance Issues
- Check server resources
- Optimize database queries
- Clear browser cache

### Permission Errors
- Verify user role and permissions
- Contact administrator for access

## Getting Help

- In-app help: Click the Help icon in the sidebar
- Documentation: Available at `/docs` endpoint
- Support: Contact support@rsw-platform.com

---

*Next: [Djinni Assistant](./djinni-assistant.md)*

*Last updated: July 6, 2025*
