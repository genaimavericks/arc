# Smart Data Intelligence (SDI)

A comprehensive GenAI-based data intelligence platform that combines data processing with knowledge graph capabilities.

## Overview

Smart Data Intelligence (SDI) is a powerful application that integrates data ingestion, transformation, knowledge graph management, and AI-powered analytics capabilities to deliver intelligent data insights through various interfaces. The system architecture consists of two primary component groups:

1. **DataPuur** - Focused on intelligent data acquisition, transformation, profiling, and analytics
2. **KGInsight** - Specialized in knowledge graph generation, management, and exploration

Built with Next.js 15+ (React 19) for the frontend and Python FastAPI for the backend, this application provides a powerful foundation for advanced data intelligence operations.

## Key Features

- **Comprehensive Data Pipeline**: End-to-end data processing, from ingestion to visualization
- **Knowledge Graph Management**: Create, visualize, and query complex knowledge graphs
- **GenAI Integration**: LLMs, RAG, and specialized agents for various tasks:
  - Intelligent data transformation and profiling
  - Automated knowledge graph schema generation
  - AI-powered analytics dashboard creation
- **Interactive Chatbots**: Natural language interfaces for both data and knowledge graph queries
- **Role-based Access**: Tailored interfaces for administrators, data engineers/scientists, executives, HR personnel, and finance teams
- **Modern React Development**: Component-based UI with comprehensive component library
- **Responsive Design**: Fully responsive interfaces using Tailwind CSS

## Technology Stack

### Frontend
- React.js (v19) with component-based responsive design
- Next.js 15+ for server-side rendering and routing
- Tailwind CSS for styling
- Radix UI and custom components for UI elements
- Interactive data visualization tools

### Backend
- FastAPI with async capabilities
- Caddy as API gateway/reverse proxy
- RESTful API design

### Data Processing
- Pandas for data manipulation and analysis
- Architecture designed for future extensibility to distributed processing

### Databases
- Redis for vector database operations and semantic search
- MongoDB for raw data storage
- MySQL for processed data and metadata
- Neo4j for knowledge graph management

## User Interfaces

The application provides several key interfaces:

### Landing Screen
Entry point to the application offering navigation to DataPuur and KGInsights components

### DataPuur Interfaces
- **Dashboard**: Overview of all datasets in the system
- **Ingestion**: Data import from various sources
- **Profiling**: Data quality analysis and insights
- **Transformation**: AI-assisted data transformation
- **Export**: Data export capabilities
- **Insights**: AI-powered analytics and visualization

### KGInsights Interfaces
- **Dashboard**: Overview of all knowledge graphs
- **Generate Schema**: AI-powered schema recommendation
- **Manage Schema**: Visual schema editor
- **Explore**: Interactive knowledge graph visualization
- **Query**: Natural language interface for graph queries

## Getting Started

### Prerequisites

- Node.js (v18 or newer)
- Python 3.8+
- pnpm (recommended) or npm

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd rsw
   ```

2. Install frontend dependencies:
   ```bash
   pnpm install
   ```
   Or using npm:
   ```bash
   npm install
   ```

3. Install backend dependencies:
   ```bash
   pip install -r api/requirements.txt
   ```

### Running the Application

#### Development Mode

1. Start the backend API server:
   ```bash
   python run-api.py
   ```
   The API will be available at http://localhost:9090/api

2. In a separate terminal, start the frontend development server:
   ```bash
   pnpm dev
   ```
   Or using npm:
   ```bash
   npm run dev
   ```
   The frontend will be available at http://localhost:3000

#### Using Convenience Scripts

- On Unix/Linux/Mac:
  ```bash
  ./start.sh
  ```

- On Windows:
  ```bash
  start-windows.bat
  ```

### Testing

To test the API:
```bash
python test_api_ingestion.py
```

To run a mock API server for frontend development:
```bash
python mock_api_server.py
```

## System Architecture

### Data Flow

1. External data sources connect to the Data Acquisition & Ingestion component
2. Raw data is imported, validated, and stored in MongoDB
3. Data Xformer with GenAI agents performs transformation and enrichment
4. Data Profiler with GenAI analyzes and profiles the data
5. Processed data is stored in MySQL structured storage
6. Vector DB (Redis) stores embeddings for semantic search
7. KG Schema Generator with GenAI creates knowledge graph schemas
8. Knowledge graphs are built and stored in Neo4j
9. GenAI Dashboard and KG Dashboard Manager provide visualization
10. GenAI Data/KG Chatbots provide natural language interfaces
11. Users access insights through the React-based frontend

## Project Structure

```
rsw/
├── api/             # FastAPI backend
├── app/             # Next.js pages and routes
├── components/      # React components
├── hooks/           # Custom React hooks
├── lib/             # Shared utilities
├── styles/          # Global styles
└── public/          # Static assets
```

## Building for Production

1. Build the frontend:
   ```bash
   pnpm build
   ```
   Or using npm:
   ```bash
   npm run build
   ```

2. Start the production server:
   ```bash
   pnpm start
   ```
   Or using npm:
   ```bash
   npm run start
   ```

## Security Considerations

- User authentication with role-based access control
- API Gateway for centralized security management
- Containerized components for isolation
- Secure data processing and storage

## License

[Your license information here]

## Contributors

RSW Team
