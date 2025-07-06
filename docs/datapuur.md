# DataPuur

- [Home](./index.md)
- [Getting Started](./getting-started.md)
- [Djinni Assistant](./djinni-assistant.md)
- Tools
  - [DataPuur](./datapuur.md) (You are here)
  - [KGInsights](./kginsights.md)
- [API Reference](./api-reference.md)

## Table of Contents
- [Introduction](#introduction)
- [Features Overview](#features-overview)
- [Accessing DataPuur](#accessing-datapuur)
- [Data Ingestion](#data-ingestion)
  - [Supported File Formats](#supported-file-formats)
  - [Uploading Files](#uploading-files)
  - [Database Connections](#database-connections)
- [AI Profile](#ai-profile)
  - [Automatic Data Profiling](#automatic-data-profiling)
  - [Data Quality Assessment](#data-quality-assessment)
- [AI Transformation](#ai-transformation)
  - [Data Cleaning](#data-cleaning)
  - [Data Enrichment](#data-enrichment)
  - [Data Normalization](#data-normalization)
- [Data Catalog](#data-catalog)
- [Export Options](#export-options)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Introduction

DataPuur is the comprehensive data management module of the RSW platform, designed to streamline the entire data lifecycle from ingestion to analysis. It provides tools for data acquisition, processing, profiling, transformation, and analytics, enabling users to extract valuable insights from their data.

![DataPuur Dashboard](./images/datapuur-dashboard.png)

## Features Overview

- **Data Ingestion**: Upload files or connect to databases
- **AI Profile**: Automatic data profiling and quality assessment
- **AI Transformation**: Intelligent data cleaning and enrichment
- **Data Catalog**: Centralized repository of available datasets
- **Export Options**: Multiple formats for downstream use
- **Dashboard**: Visual overview of data metrics and status

## Accessing DataPuur

1. **Navigation**:
   - Click on "DataPuur" in the sidebar under Tools
   - Use the dropdown to access specific DataPuur features

2. **Interface Components**:
   - **Dashboard**: Overview of data metrics and status
   - **Ingestion**: File upload and database connection
   - **AI Profile**: Data profiling tools
   - **AI Transformation**: Data transformation tools
   - **Data Catalog**: Dataset browser
   - **Export**: Download options

## Data Ingestion

### Supported File Formats

DataPuur supports multiple file formats for data ingestion:

- **CSV**: Comma-separated values
- **JSON**: JavaScript Object Notation
- **Parquet**: Columnar storage format
- **Database Connections**: Direct database access

### Uploading Files

1. Navigate to DataPuur > Ingestion
2. Click "Upload File" button
3. Select file from your computer
4. Configure ingestion parameters:
   - File format detection
   - Column delimiter (for CSV)
   - Header row options
   - Data type inference
5. Click "Start Ingestion"
6. Monitor ingestion progress

![Data Ingestion Interface](./images/data-ingestion.png)

### Database Connections

DataPuur can connect directly to various database systems:

1. Navigate to DataPuur > Ingestion
2. Click "Connect Database"
3. Select database type:
   - PostgreSQL
   - MySQL
   - SQL Server
   - Oracle
   - MongoDB
4. Enter connection parameters:
   - Host/server
   - Port
   - Database name
   - Username/password
   - SSL options
5. Test connection
6. Select tables/collections to ingest
7. Configure ingestion schedule (one-time or recurring)

## AI Profile

The AI Profile feature uses advanced generative AI to automatically analyze and provide deep insights into your datasets, helping you understand data characteristics, quality issues, and potential use cases.

### Starting a New AI Profiling Session

1. Navigate to DataPuur > AI Profile
2. Click on "Profile Sessions" tab
3. Click "Start New AI Profiling Session"
4. Select a data source from the list of available datasets
5. Click "Start AI Analysis"

![AI Profile New Session](./img/ai-profile-new-session.png)

### Profile List

The Profile List provides an overview of all profiled datasets with key metrics:

1. Navigate to DataPuur > AI Profile
2. Click on "Profile List" tab
3. View profiled datasets with metrics:
   - Dataset name
   - Size (rows and columns)
   - Duplicates (exact and fuzzy)
   - Quality score
   - Creation timestamp
   - Available actions

![AI Profile List](./img/ai-profile-list.png)

### Profile Details

The Profile Details view provides comprehensive insights into your dataset:

1. Navigate to DataPuur > AI Profile
2. Select a dataset from the Profile List
3. View detailed profile information:
   - Dataset overview (rows, columns, age)
   - Quality score with rating (Excellent, Good, etc.)
   - Duplicate analysis (exact and fuzzy duplicates)
   - Column-specific analysis with interactive visualizations
   - Value distributions and patterns
   - Missing values analysis
   - Statistical summaries

![AI Profile Details](./img/ai-profile-details.png)
![AI Profile Results](./images/ai-profile.png)

### Data Quality Assessment

The AI Profile also provides a detailed data quality assessment:

1. **Completeness**: Percentage of non-missing values
2. **Validity**: Conformance to expected formats
3. **Accuracy**: Correctness of values
4. **Consistency**: Internal data coherence
5. **Uniqueness**: Duplicate detection
6. **Timeliness**: Data freshness

Each metric is scored from 0-100, with recommendations for improvement.

### AI-Generated Analysis

The AI Profile provides a comprehensive natural language analysis of your dataset:

1. Navigate to DataPuur > AI Profile > Profile Details
2. Review the AI-generated analysis sections:
   - **Overview of Data Characteristics**: Summary of dataset size, structure, and content
   - **Notable Features or Anomalies**: Identification of unusual patterns or outliers
   - **Data Quality Assessment**: Evaluation of data quality with specific issues
   - **Potential Use Cases**: AI-suggested applications for the dataset
   - **Process & Quality Analysis**: Insights into process performance and quality over time
   - **Productivity & Cost Reporting**: Analysis of efficiency metrics and cost factors
   - **Workforce Insights**: Assessment of workforce patterns and performance
   - **Action Points**: Recommended next steps to improve data quality

![AI Profile Analysis](./img/ai-profile-analysis.png)

### Session History

Access and manage your previous AI profiling sessions:

1. Navigate to DataPuur > AI Profile
2. Click on "Profile Sessions" tab
3. View list of previous profiling sessions with:
   - Dataset name
   - Creation timestamp
   - Session status (Active, Completed)
   - AI-generated summary
   - Options to resume analysis or view details

![AI Profile Session History](./img/ai-profile-sessions.png)

## AI Transformation

The AI Transformation feature uses advanced generative AI to intelligently transform your datasets, automatically applying the most appropriate data cleaning, enrichment, and normalization techniques based on your specific data characteristics and business needs.

### Transform Data

1. Navigate to DataPuur > AI Transformation
2. Click on the "Transform Data" tab
3. Select a dataset from the available list
4. Click the "Transform" button next to your selected dataset
5. The system will begin the AI-powered transformation process

![Transform Data](./img/ai-transformation-transform-data.png)

### Transformation Plans

Transformation Plans allow you to view, manage, and create reusable data transformation workflows:

1. Navigate to DataPuur > AI Transformation
2. Click on the "Transformation Plans" tab
3. View existing transformation plans with details:
   - Plan name
   - Description
   - Status (Completed, In Progress)
   - Creation timestamp
   - Available actions (Edit, Delete)

![Transformation Plans](./img/ai-transformation-plans.png)

### Edit Transformation Plan

The Edit Transformation Plan interface allows you to customize and refine your data transformation workflows:

1. Navigate to DataPuur > AI Transformation > Transformation Plans
2. Click "Edit" next to the plan you want to modify
3. Update plan details:
   - Name
   - Description
4. Modify transformation steps with AI assistance
5. Click "Execute Plan" to apply the updated transformations

![Edit Transformation Plan](./img/ai-transformation-edit.png)

### AI Assistant for Transformations

The AI Assistant helps you create and refine transformation plans through natural language interaction:

1. In the Edit Transformation Plan view, interact with the AI Assistant panel
2. View AI-suggested transformation steps based on your data profile
3. Examples of transformation operations:
   - Remove irrelevant or redundant columns
   - Detect and impute missing values
   - Standardize formats and units
   - Generate derived features
4. Type your own transformation instructions in natural language
5. Click "Update Plan" to incorporate your changes

### Transformation Execution and Results

After executing a transformation plan, you can view detailed results and the transformed dataset:

1. The transformation execution page shows:
   - Step-by-step execution of each transformation operation
   - Detailed script of applied transformations
   - Execution status and results
   - Before/after metrics for data quality
2. Click "View Catalog" to access the transformed dataset in the Data Catalog

![Transformation Execution](./img/ai-transformation-execution.png)

### Common Transformation Operations

The AI Transformation feature can perform various operations automatically:

#### Data Cleaning
- Missing value detection and imputation
- Outlier identification and handling
- Error correction and validation
- Format standardization
- Duplicate removal

#### Data Enrichment
- Feature generation
- Derived metrics calculation
- Temporal feature extraction
- Statistical aggregations
- Data type conversions

#### Data Normalization
- Date/time standardization
- Text case normalization
- Unit conversion
- Numerical scaling (min-max, z-score)
- Categorical encoding

## Data Catalog

The Data Catalog provides a centralized repository of transformed and clean datasets that are ready for analysis and decision-making:

1. Navigate to DataPuur > Data Catalog
2. Browse available datasets
3. View dataset details:
   - Schema information
   - Quality metrics
   - Transformation history
   - Data lineage (tracking data origins and transformations)
   - Usage statistics
   - Data quality certifications
   - Tags and descriptions

![Data Catalog Interface](./images/data-catalog.png)

## Export Options

DataPuur offers multiple export options for processed data:

1. Navigate to DataPuur > Export
2. Select a dataset
3. Export as CSV format
4. Configure export options:
   - Column selection
   - Filtering
   - Sorting
   - Compression
5. Generate export
6. Download or access via API

## Best Practices

### Data Ingestion Best Practices

1. **Prepare your data**:
   - Ensure consistent formatting
   - Validate file integrity
   - Document data sources

2. **Configure appropriately**:
   - Set correct delimiters
   - Specify header rows
   - Define data types when possible

3. **Monitor ingestion**:
   - Check for warnings and errors
   - Verify row counts
   - Validate sample data

### Data Profiling Best Practices

1. **Profile early**:
   - Run AI Profile immediately after ingestion
   - Address quality issues before analysis

2. **Review all metrics**:
   - Check completeness scores
   - Investigate anomalies
   - Understand distributions

3. **Document findings**:
   - Save profile reports
   - Note data limitations
   - Share insights with stakeholders

### Data Transformation Best Practices

1. **Incremental approach**:
   - Apply transformations in logical order
   - Validate after each step
   - Maintain transformation history

2. **Preserve raw data**:
   - Keep original datasets
   - Document transformation steps
   - Enable reproducibility

3. **Test thoroughly**:
   - Verify transformations with samples
   - Check edge cases
   - Validate business rules

## Troubleshooting

### Ingestion Issues

1. **File Upload Failures**:
   - Check file size limits (max 500MB per file)
   - Verify file format and encoding
   - Check for file corruption

2. **Database Connection Problems**:
   - Verify connection parameters
   - Check network connectivity
   - Confirm database permissions

3. **Parsing Errors**:
   - Check for delimiter mismatches
   - Verify character encoding
   - Look for malformed records

### Profiling Issues

1. **Slow Profile Generation**:
   - Large datasets may take time
   - Check system resources
   - Consider sampling for initial profiles

2. **Incomplete Profiles**:
   - Check for timeout errors
   - Verify data access permissions
   - Look for unsupported data types

### Transformation Issues

1. **Failed Transformations**:
   - Check error messages
   - Verify data compatibility
   - Review transformation rules

2. **Unexpected Results**:
   - Compare before/after samples
   - Check transformation parameters
   - Verify business logic

---

*Next: [KGInsights](./kginsights.md)*

*Last updated: July 6, 2025*
