# RSW Platform Documentation

Welcome to the RSW Smart Data Intelligence (SDI) platform documentation. This guide will help you understand and use the platform effectively.

## Documentation Sections

- [Getting Started](./getting-started.md)
- [Djinni Assistant](./djinni-assistant.md)
- Tools
  - [DataPuur](./datapuur.md)
  - [KGInsights](./kginsights.md)
- [API Reference](./api-reference.md)

## About RSW Platform

RSW is a comprehensive Smart Data Intelligence (SDI) platform built as a GenAI-first application. It leverages the power of generative AI throughout its architecture to automate complex data tasks and increase productivity across the entire data lifecycle.

### GenAI-Powered Intelligence

RSW uses advanced generative AI to:

- **Automate Data Engineering**: Automatically handle data ingestion, cleaning, transformation, and integration tasks that traditionally require significant manual effort
- **Accelerate Data Science**: Perform automated feature engineering, pattern detection, and insight generation without requiring deep technical expertise
- **Simplify Analytics**: Generate visualizations, reports, and dashboards based on natural language requests
- **Enable Conversational Interaction**: Allow users to interact with data through natural language via the Djinni Assistant

By embedding AI throughout the platform, RSW dramatically reduces the technical barriers to working with complex data, allowing domain experts to focus on business outcomes rather than technical implementation details.

The platform consists of several integrated modules:

1. **DataPuur**: Data acquisition, processing, profiling, transformation, and analytics
2. **KGInsights**: Knowledge graph management, visualization, schema management, and insights
3. **Factory Dashboard**: Factory performance metrics and analytics
4. **Djinni Assistant**: AI-powered conversational assistant
5. **Admin Dashboard**: User and permission management

The platform is built with a modern tech stack including Next.js with TypeScript for the frontend and Python FastAPI for the backend. It implements a robust authentication system with JWT tokens and a hierarchical permission model.

## Technical Architecture

### Backend Architecture
- **Framework**: Python FastAPI
- **Authentication**: JWT token-based
- **Authorization**: Hierarchical permission system
- **Database**: SQLAlchemy ORM
- **API Structure**: RESTful endpoints organized by functionality

### Frontend Architecture
- **Framework**: Next.js with TypeScript and React
- **Routing**: App Router pattern
- **Authentication**: Context-based auth with localStorage token management
- **UI Components**: Custom components with responsive design
- **Navigation**: Hierarchical sidebar navigation with collapsible sections

## AI-Driven Productivity

RSW's GenAI capabilities deliver significant productivity benefits:

- **Reduced Manual Work**: Tasks that previously took days or weeks can be completed in minutes or hours
- **Democratized Data Access**: Non-technical users can perform complex data operations through natural language
- **Accelerated Insights**: Automatic pattern detection and anomaly identification surface insights that might otherwise be missed
- **Consistent Quality**: AI-driven validation and quality checks ensure reliable data processing
- **Continuous Learning**: The platform improves over time as it learns from user interactions and feedback

## Need Help?

If you need additional assistance:

- Check the [Troubleshooting](./getting-started.md#troubleshooting) section
- Contact support at support@rsw.com
- Visit our [GitHub repository](https://github.com/your-organization/rsw)

---

*Last updated: July 6, 2025*
