# Smart Data Intelligence (SDI) Application - UI Mock Screens

## Overview
This document contains UI mock screens for the Smart Data Intelligence (SDI) application, which consists of two main components:

1. **DataPuur**: For data acquisition, transformation, profiling, and analytics
2. **KGInsights**: For knowledge graph generation, management, and exploration

The application is built using:
- Frontend: React with component-based responsive design
- Backend: FastAPI with async capabilities
- Data Processing: Pandas, PySpark
- Databases: Redis (vector DB), MongoDB (raw storage), MySQL (processed data), Neo4j (knowledge graphs)
- GenAI: LLMs, RAG, and specialized agents for various tasks

Each screen in this document includes:
- ASCII diagram representation of the UI
- Key features and components
- Purpose and functionality explanation

## 1. Landing Screen
```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                     SMART DATA INTELLIGENCE                         │
│                   Unleash the Power of Your Data                    │
│                                                                     │
│   ┌───────────────────────────┐     ┌───────────────────────────┐   │
│   │                           │     │                           │   │
│   │        DataPuur           │     │        KGInsights         │   │
│   │                           │     │                           │   │
│   │  Data Ingestion,          │     │  Knowledge Graph          │   │
│   │  Profiling,               │     │  Management and           │   │
│   │  Transformation,          │     │  Insights                 │   │
│   │  and Insights             │     │                           │   │
│   │                           │     │                           │   │
│   │   ┌─────────────────┐     │     │   ┌─────────────────┐     │   │
│   │   │     ENTER       │     │     │   │     ENTER       │     │   │
│   │   └─────────────────┘     │     │   └─────────────────┘     │   │
│   │                           │     │                           │   │
│   └───────────────────────────┘     └───────────────────────────┘   │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                                                             │   │
│   │      [Data Visualization Showcase / Hero Image]             │   │
│   │                                                             │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Purpose**: The landing screen serves as the entry point to the application, providing clear navigation options for the two main components of the system.

**Key Features**:
- Application title and tagline
- Two main navigation cards for DataPuur and KGInsights 
- Brief descriptions of each component's functionality
- Visual data showcase to illustrate the application's capabilities
- Clean, simple design to facilitate easy navigation

**Functionality**:
- Users can click on either DataPuur or KGInsights to navigate to their respective dashboards
- The landing page establishes the application's identity and purpose
- Responsive design accommodates different screen sizes

## 2. DataPuur Dashboard
```
┌─────────────────────────────────────────────────────────────────────┐
│ DataPuur                                       👤 User ▼            │
├─────────────────────────────────────────────────────────────────────┤
│ [Dashboard] | Ingest | Profile | Transform | Export | Insights      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐  ┌───────────────────────┐                     │
│  │ + New Dataset   │  │ 🔍 Search Datasets... │                     │
│  └─────────────────┘  └───────────────────────┘                     │
│                                                                     │
│  Datasets                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Name        | Description      | Created      | Status    | Actions││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ Sales Q1    | Q1 sales data    | 2025-03-01   | Exported  | ••• ││
│  │             | across regions   |              |           |     ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ Customer DB | Customer profiles| 2025-02-15   | Profiled  | ••• ││
│  │             | and segments     |              |           |     ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ Inventory   | Current inventory| 2025-03-20   | Ingested  | ••• ││
│  │             | across warehouses|              |           |     ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ HR Data     | Employee         | 2025-01-10   | Transform | ••• ││
│  │             | information      |              |           |     ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Purpose**: The DataPuur dashboard provides an overview of all datasets in the system and serves as the central hub for data management activities.

**Key Features**:
- Top navigation bar with links to all DataPuur functions
- New dataset creation button
- Search functionality for datasets
- Dataset listing with key information (name, description, date, status)
- Action menu for each dataset

**Functionality**:
- Users can view all datasets at a glance
- Quick access to dataset creation, searching, and management
- Status indicators show the current processing stage of each dataset
- Action menu provides access to specific operations for each dataset
- Clean tabular layout for efficient information display

## 3. DataPuur Ingestion Screen
```
┌─────────────────────────────────────────────────────────────────────┐
│ Ingest Data                                    👤 User ▼            │
├─────────────────────────────────────────────────────────────────────┤
│ Dashboard | Ingest | Profile | Transform | Export | Insights      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────┐ ┌──────────────────┐ ┌───────────┐                     │
│  │ Upload  │ │ Database Connect │ │ History   │                     │
│  └─────────┘ └──────────────────┘ └───────────┘                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                                                                 ││
│  │  Data Source Type: [CSV____________▼]                           ││
│  │                                                                 ││
│  │  File Location:    [Browse or enter path_______________] [📁]   ││
│  │                                                                 ││
│  │  ┌───────────────┐         ┌───────────────┐                   ││
│  │  │ Upload Data   │         │ Cancel        │                   ││
│  │  └───────────────┘         └───────────────┘                   ││
│  │                                                                 ││
│  │  Upload Status:                                                 ││
│  │  ┌─────────────────────────────────────────────────────────┐   ││
│  │  │ Ready to upload                                         │   ││
│  │  └─────────────────────────────────────────────────────────┘   ││
│  │                                                                 ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Purpose**: The DataPuur Ingestion Screen enables users to upload data from various sources into the system for further processing.

**Key Features**:
- Tabbed interface for different ingestion methods (Upload, Database Connect, History)
- Data source type selection dropdown
- File browser/path entry field
- Upload controls with status indicators
- Cancel option for in-progress uploads

**Functionality**:
- Supports multiple data source types (CSV, etc.)
- Enables direct file uploads or database connections
- Provides real-time status feedback during the ingestion process
- History tab allows users to review previously ingested datasets
- Integrated with the Data Acquisition and Data Ingestor components defined in the system architecture

## 4. DataPuur Profiling Screen
```
┌─────────────────────────────────────────────────────────────────────┐
│ Profile Data                                   👤 User ▼            │
├─────────────────────────────────────────────────────────────────────┤
│ Dashboard | Ingest | [Profile] | Transform | Export | Insights      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Select Dataset: [Sales Q1_______▼]  ┌────────────────────┐         │
│                                      │ Save Profile Report│         │
│                                      └────────────────────┘         │
│  ┌───────────────────────┐  ┌─────────────────────────────────────┐ │
│  │                       │  │ Dataset Profile:                    │ │
│  │ GenAI Bot             │  │                                     │ │
│  │ ┌─────────────────┐   │  │ ┌─────────────────┐ ┌─────────────┐ │ │
│  │ │ Ask about your  │   │  │ │ Dataset Stats   │ │ Distribution│ │ │
│  │ │ data...         │   │  │ │ - Rows: 5,230   │ │ Charts      │ │ │
│  │ └─────────────────┘   │  │ │ - Columns: 12   │ │             │ │ │
│  │                       │  │ │ - Missing: 2.3% │ │ [Histogram] │ │ │
│  │ Bot Conversation:     │  │ │ - Data Types:   │ │             │ │ │
│  │ ┌─────────────────┐   │  │ │   • Numeric: 8  │ │ [Box Plot]  │ │ │
│  │ │ [AI]: What      │   │  │ │   • Categor.: 3 │ │             │ │ │
│  │ │ would you like  │   │  │ │   • Date: 1     │ │             │ │ │
│  │ │ to know about   │   │  │ └─────────────────┘ └─────────────┘ │ │
│  │ │ your data?      │   │  │                                     │ │
│  │ │                 │   │  │ ┌─────────────────────────────────┐ │ │
│  │ │ [User]: Tell me │   │  │ │ Correlation Matrix              │ │ │
│  │ │ about outliers  │   │  │ │                                 │ │ │
│  │ │ in the dataset. │   │  │ │ [Heatmap of correlations        │ │ │
│  │ │                 │   │  │ │  between variables]             │ │ │
│  │ │ [AI]: I've      │   │  │ │                                 │ │ │
│  │ │ analyzed your   │   │  │ │                                 │ │ │
│  │ │ data and found  │   │  │ │                                 │ │ │
│  │ │ several...      │   │  │ └─────────────────────────────────┘ │ │
│  │ └─────────────────┘   │  │                                     │ │
│  │                       │  │                                     │ │
│  └───────────────────────┘  └─────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────┐                                              │
│  │ Apply Profiling   │                                              │
│  └───────────────────┘                                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Purpose**: The DataPuur Profiling Screen provides statistical analysis and insights about a selected dataset to help users understand its characteristics.

**Key Features**:
- Dataset selection dropdown
- GenAI Bot section positioned on the left for interactive querying
- Dataset statistics display (rows, columns, missing values, data types)
- Distribution charts and visualizations
- Correlation matrix to show relationships between variables
- Save profile report and apply profiling buttons

**Functionality**:
- Automated statistical analysis of dataset properties
- Interactive data exploration through the GenAI Bot
- Visual representations of data distributions and relationships
- Ability to save insights as a report for future reference
- Integration with the Data Profiler component defined in the system architecture
- Uses pandas and statistical libraries for the analysis backend

## 5. DataPuur Transformation Screen
```
┌─────────────────────────────────────────────────────────────────────┐
│ Transform Data                                 👤 User ▼            │
├─────────────────────────────────────────────────────────────────────┤
│ Dashboard | Ingest | Profile | [Transform] | Export | Insights      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Select Dataset: [Sales Q1_______▼]  ┌────────────────────────┐     │
│                                      │ Save Transformation    │     │
│                                      └────────────────────────┘     │
│  ┌───────────────────────┐  ┌─────────────────────────────────────┐ │
│  │                       │  │ Recommended Transformations:        │ │
│  │ GenAI Bot             │  │                                     │ │
│  │ ┌─────────────────┐   │  │ ┌─────────────────────────────────┐ │ │
│  │ │ Ask about       │   │  │ │ ☑ Convert 'date' column to      │ │ │
│  │ │ transformations.│   │  │ │   datetime format               │ │ │
│  │ └─────────────────┘   │  │ │   ↳ Justification: Enables      │ │ │
│  │                       │  │ │     time-based analysis         │ │ │
│  │ Bot Conversation:     │  │ │                                 │ │ │
│  │ ┌─────────────────┐   │  │ │ ☑ Standardize 'region' values   │ │ │
│  │ │ [AI]: How can I │   │  │ │   (normalize case)              │ │ │
│  │ │ help with your  │   │  │ │   ↳ Justification: Found        │ │ │
│  │ │ data transform- │   │  │ │     inconsistent capitalization │ │ │
│  │ │ ation?          │   │  │ │                                 │ │ │
│  │ │                 │   │  │ │ ☑ Fill missing values in        │ │ │
│  │ │ [User]: What    │   │  │ │   'quantity' with mean          │ │ │
│  │ │ transformations │   │  │ │   ↳ Justification: 3.2% missing,│ │ │
│  │ │ would help with │   │  │ │     mean imputation recommended │ │ │
│  │ │ data quality?   │   │  │ │                                 │ │ │
│  │ │                 │   │  │ │ ☑ Create aggregated             │ │ │
│  │ │ [AI]: Based on  │   │  │ │   'total_sales' column          │ │ │
│  │ │ analyzing your  │   │  │ │   ↳ Justification: Simplifies   │ │ │
│  │ │ data, I would   │   │  │ │     reporting and analysis      │ │ │
│  │ │ recommend...    │   │  │ └─────────────────────────────────┘ │ │
│  │ └─────────────────┘   │  │                                     │ │
│  │                       │  │                                     │ │
│  └───────────────────────┘  └─────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────┐                                              │
│  │ Apply Transformation│                                            │
│  └───────────────────┘                                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Purpose**: The DataPuur Transformation Screen provides AI-powered recommendations for data transformations to improve data quality and usability.

**Key Features**:
- Dataset selection dropdown
- GenAI Bot section positioned on the left for interactive querying
- Recommended transformations list with checkboxes
- Justifications for each recommendation
- Save transformation and apply transformation buttons

**Functionality**:
- AI-powered analysis to identify potential transformations
- Checkbox selection to include/exclude specific transformations
- Justifications to explain the reasoning behind each recommendation
- Interactive GenAI Bot for custom transformation queries
- Integration with the Data Transformer component defined in the system architecture
- Backend powered by GenAI agents with pandas/PySpark for transformations

## 6. DataPuur Export Screen
```
┌─────────────────────────────────────────────────────────────────────┐
│ Export Data                                   👤 User ▼            │
├─────────────────────────────────────────────────────────────────────┤
│ Dashboard | Ingest | Profile | Transform | [Export] | Insights      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                                                                 ││
│  │  Select Dataset: [Sales Q1_______▼]                             ││
│  │                                                                 ││
│  │  🔍 Search datasets...                                          ││
│  │                                                                 ││
│  │  Export Format: [CSV____________▼]                              ││
│  │                                                                 ││
│  │  ┌───────────────────┐                                         ││
│  │  │ Download Data     │                                         ││
│  │  └───────────────────┘                                         ││
│  │                                                                 ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  Available Datasets:                                                │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ ● Sales Q1 (Transformed) - Last modified: 2025-03-15            ││
│  │ ● Customer DB (Profiled) - Last modified: 2025-02-18            ││
│  │ ● Inventory (Ingested) - Last modified: 2025-03-20              ││
│  │ ● HR Data (Transformed) - Last modified: 2025-01-15             ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Purpose**: The DataPuur Export Screen allows users to download processed datasets in various formats.

**Key Features**:
- Dataset selection dropdown with search functionality
- Export format selection dropdown (CSV, etc.)
- Download button
- Available datasets list with processing status and modification dates

**Functionality**:
- Selection from all processed datasets
- Multiple export format options
- Direct download capabilities
- Dataset filtering by processing status
- Integration with all data storage components (MongoDB, MySQL)
- Backend support for format conversion and data retrieval

## 7. DataPuur Insights Screen
```
┌─────────────────────────────────────────────────────────────────────┐
│ Insights                                      👤 User ▼            │
├─────────────────────────────────────────────────────────────────────┤
│ Dashboard | Ingest | Profile | Transform | Export | [Insights]      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Select Dataset: [Sales Q1_______▼]  ┌────────────────────┐         │
│                                      │ Save Insights      │         │
│                                      └────────────────────┘         │
│  ┌───────────────────────┐  ┌─────────────────────────────────────┐ │
│  │                       │  │ Insights Dashboard                  │ │
│  │ GenAI Bot             │  │                                     │ │
│  │ ┌─────────────────┐   │  │ ┌─────────────────┐ ┌─────────────┐ │ │
│  │ │ Ask about       │   │  │ │ Sales Trend     │ │ Regional    │ │ │
│  │ │ insights...     │   │  │ │                 │ │ Breakdown   │ │ │
│  │ └─────────────────┘   │  │ │ [Line Chart]    │ │ [Map Chart] │ │ │
│  │                       │  │ │                 │ │             │ │ │
│  │ Bot Conversation:     │  │ └─────────────────┘ └─────────────┘ │ │
│  │ ┌─────────────────┐   │  │                                     │ │
│  │ │ [AI]: What      │   │  │ ┌─────────────────┐ ┌─────────────┐ │ │
│  │ │ insights would  │   │  │ │ Top Products    │ │ Customer    │ │ │
│  │ │ you like to     │   │  │ │                 │ │ Segments    │ │ │
│  │ │ explore?        │   │  │ │ [Bar Chart]     │ │ [Pie Chart] │ │ │
│  │ │                 │   │  │ │                 │ │             │ │ │
│  │ │ [User]: What    │   │  │ └─────────────────┘ └─────────────┘ │ │
│  │ │ trends do you   │   │  │                                     │ │
│  │ │ see in Q1 sales?│   │  │ ┌─────────────────────────────────┐ │ │
│  │ │                 │   │  │ │ Key Performance Indicators      │ │ │
│  │ │ [AI]: Looking   │   │  │ │                                 │ │ │
│  │ │ at Q1 sales, I  │   │  │ │ [Data Table with KPIs]          │ │ │
│  │ │ can see a       │   │  │ │                                 │ │ │
│  │ │ consistent...   │   │  │ └─────────────────────────────────┘ │ │
│  │ └─────────────────┘   │  │                                     │ │
│  │                       │  │                                     │ │
│  └───────────────────────┘  └─────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────┐                                              │
│  │ Apply Insights    │                                              │
│  └───────────────────┘                                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Purpose**: The DataPuur Insights Screen leverages GenAI to generate comprehensive data insights and visualizations from processed datasets.

**Key Features**:
- Dataset selection dropdown
- GenAI Bot section positioned on the left for interactive querying
- Multi-visualization dashboard showing various data insights
- Save insights report and apply insights buttons
- Various chart types (line, map, bar, pie) and KPI tables

**Functionality**:
- AI-powered data analysis and insight generation
- Interactive exploration through natural language queries
- Multiple visualization types for different data aspects
- Ability to save insights as a report for future reference
- Integration with the GenAI Report Generator component from the system architecture
- Leverages React components for visualization rendering

## 8. KGInsights Dashboard
```
┌─────────────────────────────────────────────────────────────────────┐
│ KGInsights                                    👤 User ▼            │
├─────────────────────────────────────────────────────────────────────┤
│ [Dashboard] | Generate Schema | Manage Schema | Display KG | Insights│
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────┐  ┌───────────────────────┐                 │
│  │ + New Knowledge Graph│  │ 🔍 Search Graphs...   │                 │
│  └─────────────────────┘  └───────────────────────┘                 │
│                                                                     │
│  Knowledge Graphs                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Name        | Description      | Created      | Actions         ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ Customer    | Customer-product | 2025-03-05   | Manage Schema   ││
│  │ Relations   | relationships    |              | Insights        ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ Supply      | Supply chain     | 2025-02-20   | Manage Schema   ││
│  │ Chain       | network          |              | Insights        ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  Available Datasets for KG Generation                               │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Dataset    | Preview | Schema | Generate KG                     ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │ Sales Q1   |   👁️    |   📋   |    ➕                          ││
│  │ HR Data    |   👁️    |   📋   |    ➕                          ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Purpose**: The KGInsights Dashboard provides an overview of all knowledge graphs in the system and serves as the central hub for knowledge graph management.

**Key Features**:
- Top navigation bar with links to all KGInsights functions
- New knowledge graph creation button
- Search functionality for knowledge graphs
- Knowledge graph listing with key information and action buttons
- Available datasets section for new knowledge graph generation

**Functionality**:
- Overview of all knowledge graphs with creation dates and descriptions
- Quick access to management and insights for each knowledge graph
- Integration with the KG Management component from the system architecture
- Direct access to schema management and graph visualization
- Dataset selection for new knowledge graph creation
- Built on Neo4j as the underlying graph database

## 9. KGInsights Generate Schema Screen
```
┌─────────────────────────────────────────────────────────────────────┐
│ Generate Schema                                👤 User ▼            │
├─────────────────────────────────────────────────────────────────────┤
│ Dashboard | [Generate Schema] | Manage Schema | Insights            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Select Dataset: [Sales Q1_______▼]  ┌────────────────────┐         │
│                                      │ Save Schema Version│         │
│                                      └────────────────────┘         │
│  ┌───────────────────────┐  ┌─────────────────────────────────────┐ │
│  │                       │  │ Recommended Schema:                 │ │
│  │ GenAI Bot             │  │                                     │ │
│  │ ┌─────────────────┐   │  │ ┌─────────────────────────────────┐ │ │
│  │ │ Ask about       │   │  │ │                                 │ │ │
│  │ │ schema...       │   │  │ │ [Visualization of suggested     │ │ │
│  │ └─────────────────┘   │  │ │  graph schema with nodes        │ │ │
│  │                       │  │ │  and edges]                     │ │ │
│  │ Bot Conversation:     │  │ │                                 │ │ │
│  │ ┌─────────────────┐   │  │ │                                 │ │ │
│  │ │ [AI]: How can I │   │  │ └─────────────────────────────────┘ │ │
│  │ │ help with your  │   │  │                                     │ │
│  │ │ schema design?  │   │  │ Nodes:                              │ │
│  │ │                 │   │  │ - Customer (id, name, segment)      │ │
│  │ │ [User]: What    │   │  │ - Product (id, name, category)      │ │
│  │ │ relationships   │   │  │ - Sale (id, date, amount)           │ │
│  │ │ should I add?   │   │  │                                     │ │
│  │ │                 │   │  │ Relationships:                      │ │
│  │ │ [AI]: Based on  │   │  │ - PURCHASED (Customer → Product)    │ │
│  │ │ your data, I    │   │  │ - CONTAINS (Sale → Product)         │ │
│  │ │ recommend...    │   │  │ - MADE_BY (Sale → Customer)         │ │
│  │ └─────────────────┘   │  │                                     │ │
│  │                       │  │ Justification:                      │ │
│  │                       │  │ This schema captures the sales      │ │
│  │                       │  │ relationship between customers      │ │
│  │                       │  │ and products while maintaining      │ │
│  │                       │  │ transaction details in the Sale     │ │
│  │                       │  │ node.                               │ │
│  └───────────────────────┘  └─────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Purpose**: The KGInsights Generate Schema Screen uses AI to recommend optimal knowledge graph schemas based on input data.

**Key Features**:
- Dataset selection dropdown
- GenAI Bot section positioned on the left for interactive querying
- Visual schema representation showing nodes and relationships
- Detailed node and relationship listings with properties
- Justification for the recommended schema
- Save schema version button

**Functionality**:
- AI-powered schema generation based on dataset analysis
- Interactive discussion with GenAI Bot for schema refinement
- Visual representation of the proposed graph structure
- Detailed property lists for each node and relationship type
- Integration with KG Schema Generator component from the system architecture
- Leverages RAG-based Neo4j schema optimization and Cypher query generation

## 10. KGInsights Manage Schema Screen
```
┌─────────────────────────────────────────────────────────────────────┐
│ Manage Schema                                 👤 User ▼            │
├─────────────────────────────────────────────────────────────────────┤
│ Dashboard | Generate Schema | [Manage Schema] | Insights            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Select Knowledge Graph: [Customer Relations___▼]                    │
│                                                                     │
│  Schema Editor:                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                                                                 ││
│  │  [Interactive visual schema editor with nodes and relationships]││
│  │                                                                 ││
│  │  🟢 Customer                    🟢 Product                      ││
│  │     id: string                    id: string                    ││
│  │     name: string                  name: string                  ││
│  │     segment: string               category: string              ││
│  │     region: string                price: float                  ││
│  │            │                             ▲                      ││
│  │            │                             │                      ││
│  │            │ PURCHASED                   │ CONTAINS             ││
│  │            ▼                             │                      ││
│  │  🟢 Sale                                                        ││
│  │     id: string                                                  ││
│  │     date: datetime                                              ││
│  │     amount: float                                               ││
│  │                                                                 ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐          │
│  │ Save Changes   │ │ Apply Schema   │ │ Cancel         │          │
│  └────────────────┘ └────────────────┘ └────────────────┘          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Purpose**: The KGInsights Manage Schema Screen provides an interactive editor for modifying knowledge graph schemas.

**Key Features**:
- Knowledge graph selection dropdown
- Visual interactive schema editor
- Node and relationship visualization with properties
- Save changes, apply schema, and cancel buttons

**Functionality**:
- Visual editing of graph schemas
- Property management for nodes and relationships
- CRUD operations on schema elements
- Direct schema application to the knowledge graph
- Integration with KG Management component from the system architecture
- Backend support for performance optimization and transaction management

## 11. KGInsights Insights Screen
```
┌─────────────────────────────────────────────────────────────────────┐
│ Insights                                      👤 User ▼            │
├─────────────────────────────────────────────────────────────────────┤
│ Dashboard | Generate Schema | Manage Schema | [Insights]            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Select Knowledge Graph: [Customer Relations___▼]  ┌──────────────┐ │
│                                                   │ Save Report   │ │
│                                                   └──────────────┘ │
│  ┌───────────────────────┐  ┌─────────────────────────────────────┐ │
│  │                       │  │ Insights Dashboard                  │ │
│  │ GenAI Bot             │  │                                     │ │
│  │ ┌─────────────────┐   │  │ ┌─────────────────┐ ┌─────────────┐ │ │
│  │ │ Ask about KG... │   │  │ │ Customer        │ │ Product     │ │ │
│  │ └─────────────────┘   │  │ │ Analysis        │ │ Categories  │ │ │
│  │                       │  │ │                 │ │             │ │ │
│  │ Bot Conversation:     │  │ │ [Data Table]    │ │ [Pie Chart] │ │ │
│  │ ┌─────────────────┐   │  │ │                 │ │             │ │ │
│  │ │ [AI]: How can I │   │  │ └─────────────────┘ └─────────────┘ │ │
│  │ │ help you analyze│   │  │                                     │ │
│  │ │ your knowledge  │   │  │ Domain-related insights:            │ │
│  │ │ graph?          │   │  │                                     │ │
│  │ │                 │   │  │ ┌─────────────────────────────────┐ │ │
│  │ │ [User]: What    │   │  │ │ • 85% of premium customers      │ │ │
│  │ │ insights can    │   │  │ │   purchase across multiple      │ │ │
│  │ │ you provide     │   │  │ │   product categories            │ │ │
│  │ │ about customer  │   │  │ │                                 │ │ │
│  │ │ purchasing      │   │  │ │ • Most valuable products by     │ │ │
│  │ │ patterns?       │   │  │ │   customer segment identified   │ │ │
│  │ │                 │   │  │ │                                 │ │ │
│  │ │ [AI]: Based on  │   │  │ │ • Geographic clusters of        │ │ │
│  │ │ metadata from   │   │  │ │   customer behavior detected    │ │ │
│  │ │ your graph, I   │   │  │ │                                 │ │ │
│  │ │ can see that... │   │  │ └─────────────────────────────────┘ │ │
│  │ └─────────────────┘   │  │                                     │ │
│  │                       │  │                                     │ │
│  └───────────────────────┘  └─────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Purpose**: The KGInsights Insights Screen provides domain-related insights derived from knowledge graph metadata using GenAI capabilities.

**Key Features**:
- Knowledge graph selection dropdown
- GenAI Bot section positioned on the left for interactive querying
- Insights dashboard with data visualizations
- Bulleted list of domain-related insights
- Save report button

**Functionality**:
- AI-powered knowledge graph analysis
- Metadata-based insight generation (without direct graph visualizations)
- Interactive exploration through natural language queries
- Multiple visualization types for different knowledge graph aspects
- Integration with the KG GenAI Chatbot component from the system architecture
- Natural language to Cypher query translation for complex analysis

## Technical Implementation Considerations

These UI mock screens align with the technical specifications outlined in the Smart Data Intelligence architecture:

1. **Frontend**:
   - Built using React with component-based responsive design
   - Modern UI elements with consistent layout patterns
   - GenAI Bot positioned consistently on the left side of applicable screens

2. **Backend Integration**:
   - FastAPI endpoints for all data operations
   - Async processing for long-running operations
   - Swagger documentation for API endpoints

3. **Storage**:
   - Redis for vector embeddings with ANN search
   - MongoDB for raw data in flexible schema
   - MySQL for processed data with normalized schema
   - Neo4j for graph data with specialized algorithms

4. **AI Components**:
   - LLM-powered GenAI Bot for natural language interactions
   - RAG-based knowledge generation
   - Specialized agents for transformations, profiling, and analytics
   - Knowledge graph schema optimization

The UI design prioritizes usability while providing access to the powerful AI capabilities of the underlying system, creating a cohesive experience across both the DataPuur and KGInsights components.
