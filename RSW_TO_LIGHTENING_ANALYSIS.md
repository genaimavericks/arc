# RSW to Lightening Brand Rename Analysis

## Executive Summary

This document provides a comprehensive analysis of all references to "RSW" in the codebase that need to be renamed to "Lightening". The analysis covers:

1. **Repository References**: GitHub repository URLs that need to be updated
2. **Brand/Product Name References**: UI text, documentation, and code comments
3. **Technical References**: Database names, file paths, configuration values
4. **Documentation Files**: README files, setup guides, and technical documentation

---

## 1. Repository References

### Current Repository
- **Old**: `https://github.com/RSWdjinni/rsw.git`
- **New**: `https://github.com/genaimavericks/arc`

### Files Requiring Repository URL Updates

#### README.md (6 occurrences)
- Line 87: `git clone https://github.com/RSWdjinni/rsw.git`
- Line 88: `cd rsw`
- Line 113: `git clone https://github.com/RSWdjinni/rsw.git`
- Line 114: `cd rsw`
- Line 149: `git clone https://github.com/RSWdjinni/rsw.git`
- Line 150: `cd rsw`
- Line 182: `git clone git@github.com:RSWdjinni/rsw.git`
- Line 183: `cd rsw`
- Line 192: `git clone https://USERNAME:TOKEN@github.com/RSWdjinni/rsw.git`
- Line 193: `cd rsw`
- Line 212: `gh repo clone RSWdjinni/rsw`
- Line 213: `cd rsw`

**Action Required**: Replace all repository URLs with `https://github.com/genaimavericks/arc` and update directory references from `rsw` to `arc`.

---

## 2. Brand/Product Name References

### 2.1 Main Documentation Files

#### README.md
- Line 1: Title "# Smart Data Intelligence (SDI)" - **Keep as is** (SDI is the product name)
- Line 333: "The RSW project includes..." → Change to "The Lightening project includes..."
- Line 351: "Package everything into a single archive (`rsw-deployment.tar.gz`)" → Change to `lightening-deployment.tar.gz`
- Line 366: `scp rsw-deployment.tar.gz` → Change to `lightening-deployment.tar.gz`
- Line 370: `put rsw-deployment.tar.gz` → Change to `lightening-deployment.tar.gz`
- Line 376-378: `/opt/rsw` → Change to `/opt/lightening`
- Line 400: `/etc/systemd/system/rsw.service` → Change to `lightening.service`
- Line 406: "Description=RSW Application" → Change to "Lightening Application"
- Line 411-412: `/opt/rsw/package` → Change to `/opt/lightening/package`
- Line 417: "SyslogIdentifier=rsw" → Change to "lightening"
- Line 426: "sudo systemctl enable rsw" → Change to "lightening"
- Line 433: "sudo systemctl status rsw" → Change to "lightening"
- Line 436: "sudo journalctl -u rsw -f" → Change to "lightening"
- Line 487: "sudo journalctl -u rsw -f" → Change to "lightening"
- Line 497: "sudo chown -R your_user:your_user /opt/rsw" → Change to `/opt/lightening`
- Line 498: "chmod -R 755 /opt/rsw" → Change to `/opt/lightening`
- Line 535: "RSW Team" → Change to "Lightening Team"

#### PACKAGE_README.md
- Line 1: "# RSW Deployment Package" → Change to "# Lightening Deployment Package"
- Line 3: "This package contains a deployable version of the RSW application." → Change to "Lightening"
- Line 9: `rsw-deployment.tar.gz` → Change to `lightening-deployment.tar.gz`

#### Smart_Data_Intelligence_HLD.md
- **No RSW references found** - This file uses "SDI" (Smart Data Intelligence) throughout

#### SDI_UI_Mock_Screens.md
- **No RSW references found** - Uses "SDI", "DataPuur", and "KGInsights"

### 2.2 Test Database Documentation

#### test_db_ingestion/README_DB_SETUP.md
- Line 1: "# PostgreSQL Setup for RSW DataPuur Testing" → Change to "Lightening DataPuur Testing"
- Line 3: "...in the RSW DataPuur module..." → Change to "Lightening DataPuur module"
- Line 21: "- RSW platform installed and running" → Change to "Lightening platform"
- Line 51: `/Users/dhani/GitHub/dpk/rsw/populate_sample_data.sql` → Change path to `arc`
- Line 82: `cd C:\path\to\rsw\directory` → Change to `arc`
- Line 173: "1. **Open the RSW DataPuur Ingestion interface**" → Change to "Lightening DataPuur"

---

## 3. Technical References

### 3.1 Database Names

#### Test Database Files
**Files**: 
- `test_db_ingestion/test_schema_extract.py` (Line 184)
- `test_db_ingestion/test_ingestion.py` (Line 34)
- `test_db_ingestion/test_db_connection.py` (Lines 9, 60)
- `test_db_ingestion/sample_data_postgres.sql` (Lines 2, 5, 171)
- `test_db_ingestion/README_DB_SETUP.md` (Lines 42, 51, 73, 85, 91, 101, 104, 179)

**Current**: `rsw_test`, `rsw_user`, `rsw_password`
**Recommendation**: Change to `lightening_test`, `lightening_user`, `lightening_password`

#### Production Database
**File**: `api/db_config.py` (Line 59)
```python
DB_NAME = os.getenv("DB_NAME", "rsw")
```
**Recommendation**: Change default to `"lightening"`

### 3.2 SSL/Certificate Paths

#### README.md
- Lines 264, 267, 270, 273-274, 284: `/etc/ssl/rsw/` → Change to `/etc/ssl/lightening/`

### 3.3 Process Management

#### Shell Scripts

**stop.sh**
- Line 4: `echo "Stopping RSW processes..."` → Change to "Lightening"
- Line 12: `pkill -f "node .*/rsw/node_modules/.bin/next"` → Change to `arc`
- Line 31: "# Stop any uvicorn/fastapi processes related to RSW" → Change to "Lightening"
- Line 49: `RSW_PIDS=$(ps aux | grep -E "[p]ython.*rsw|[u]vicorn.*rsw|[n]ode.*next" | awk '{print $2}')` → Change to `lightening`
- Lines 50-53: Variable name `RSW_PIDS` → Change to `LIGHTENING_PIDS`
- Line 56: `echo "All RSW processes stopped."` → Change to "Lightening"

**stop_ubuntu.sh**
- Line 4: `echo "Stopping RSW processes..."` → Change to "Lightening"
- Line 12: `pkill -f "node .*/rsw/node_modules/.bin/next"` → Change to `arc`
- Line 14: `echo "All RSW processes stopped."` → Change to "Lightening"

**stop.bat**
- Line 2: `echo Stopping RSW processes...` → Change to "Lightening"
- Line 22: `echo All RSW processes stopped.` → Change to "Lightening"

**README.md**
- Line 322: `pm2 start "./start.sh" --name rsw` → Change to `--name lightening`

### 3.4 Python API Code

#### File Path Comments
**Files with old path references**:
- `api/utils/llm_provider.py` (Line 1): `/Users/asgiri218/gam-project/rsw/api/utils/llm_provider.py`
- `api/kgdatainsights/agent/csv_to_cypher_generator.py` (Lines 1, 188-189)

**Action**: Update file path comments to reflect new repository structure

#### Module Docstrings
**Files**:
- `api/profiler/router.py` (Line 2): "Data Profiler Router for the RSW platform."
- `api/logging_config.py` (Line 2): "Custom logging configuration for the RSW API."
- `api/gen_ai_layer/__init__.py` (Line 2): "Gen AI Layer for RSW platform."
- `api/factory_astro.py` (Line 2): "Factory Astro API Module for RSW"
- `api/churn_astro/__init__.py` (Line 2): "Churn Astro module for RSW"
- `api/churn_astro/router.py` (Line 2): "Churn Astro Router Module for RSW"
- `api/churn_astro/compat.py` (Line 2): "Compatibility layer for churn_astro to work with RSW dependencies"
- `api/astro_data/compat.py` (Line 2): "Compatibility layer for astro_data to work with RSW dependencies"

**Action**: Change "RSW" to "Lightening" in all docstrings

### 3.5 SQL Sample Data

#### test_db_ingestion/sample_data_postgres.sql
- Line 1: `-- Create sample database for RSW testing` → Change to "Lightening testing"
- Line 2: `CREATE DATABASE rsw_test;` → Change to `lightening_test;`
- Line 5: `\c rsw_test;` → Change to `lightening_test;`
- Line 170: `CREATE USER rsw_user WITH PASSWORD 'rsw_password';` → Change to `lightening_user` and `lightening_password`
- Line 171: `GRANT ALL PRIVILEGES ON DATABASE rsw_test TO rsw_user;` → Update accordingly
- Lines 172-173: Update user references in GRANT statements

---

## 4. Frontend/UI References

### 4.1 API Endpoints

**Note**: The codebase uses `/api/datapuur/` endpoints extensively. These should remain as "datapuur" since that's a component name, not the brand name.

**Files with DataPuur API calls** (No changes needed):
- `lib/ingestion-context.tsx`
- `lib/api.ts`

### 4.2 Package Configuration

**package.json**
- Line 2: `"name": "my-v0-project"` → Consider changing to `"lightening-sdi"` or similar

---

## 5. Summary of Changes Required

### High Priority (User-Facing)

1. **README.md**: Update all brand references, repository URLs, installation paths
2. **PACKAGE_README.md**: Update brand name and package references
3. **test_db_ingestion/README_DB_SETUP.md**: Update brand references

### Medium Priority (Configuration & Scripts)

4. **Shell scripts** (stop.sh, stop_ubuntu.sh, stop.bat): Update process names and echo messages
5. **Database configuration** (api/db_config.py): Update default database name
6. **Test database files**: Update database names, users, and passwords
7. **SSL certificate paths**: Update from `/etc/ssl/rsw/` to `/etc/ssl/lightening/`

### Low Priority (Code Comments & Docstrings)

8. **Python file headers**: Update old file path comments
9. **Module docstrings**: Update platform name references
10. **SQL comments**: Update testing references

---

## 6. Recommended Approach

### Phase 1: Repository & Documentation
1. Update all GitHub repository URLs
2. Update README.md and PACKAGE_README.md
3. Update test database documentation

### Phase 2: Configuration & Scripts
1. Update shell scripts
2. Update database configuration
3. Update SSL certificate paths
4. Update systemd service files

### Phase 3: Code & Comments
1. Update Python docstrings
2. Update file path comments
3. Update SQL sample data

### Phase 4: Testing
1. Test installation procedures with new paths
2. Verify database connections with new names
3. Test deployment scripts
4. Verify systemd service configuration

---

## 7. Files Requiring Changes

### Documentation (8 files)
1. `README.md`
2. `PACKAGE_README.md`
3. `test_db_ingestion/README_DB_SETUP.md`

### Scripts (3 files)
4. `stop.sh`
5. `stop_ubuntu.sh`
6. `stop.bat`

### Python Files (11 files)
7. `api/db_config.py`
8. `api/utils/llm_provider.py`
9. `api/profiler/router.py`
10. `api/logging_config.py`
11. `api/kgdatainsights/agent/csv_to_cypher_generator.py`
12. `api/gen_ai_layer/__init__.py`
13. `api/factory_astro.py`
14. `api/churn_astro/__init__.py`
15. `api/churn_astro/router.py`
16. `api/churn_astro/compat.py`
17. `api/astro_data/compat.py`

### Test Files (4 files)
18. `test_db_ingestion/test_schema_extract.py`
19. `test_db_ingestion/test_ingestion.py`
20. `test_db_ingestion/test_db_connection.py`
21. `test_db_ingestion/sample_data_postgres.sql`

### Configuration (1 file)
22. `package.json` (optional)

---

## 8. Important Notes

### What NOT to Change

1. **"SDI" (Smart Data Intelligence)**: This is the product name and should remain unchanged
2. **"DataPuur"**: This is a component name, not the brand name
3. **"KGInsights"**: This is a component name, not the brand name
4. **API endpoint paths** containing "datapuur": These are technical paths, not brand references

### Search & Replace Caution

Do NOT do a global search-and-replace. Each instance needs to be evaluated:
- File paths in comments may need updating
- Database names should be consistent
- Process names in scripts need updating
- But component names (DataPuur, KGInsights) should remain

---

## 9. Next Steps

1. Review this analysis document
2. Confirm the new brand name "Lightening" is correct
3. Confirm the repository URL `https://github.com/genaimavericks/arc`
4. Decide on database naming convention (lightening_test vs arc_test)
5. Create a backup before making changes
6. Execute changes in phases as outlined above
7. Test thoroughly after each phase

---

**Document Version**: 1.0  
**Date**: 2025-12-17  
**Prepared for**: Brand rename from RSW to Lightening
