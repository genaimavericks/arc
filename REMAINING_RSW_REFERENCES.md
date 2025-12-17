# Remaining RSW References - Additional Updates Needed

## Summary

After the initial rename, the following files still contain RSW references that need manual review and updates:

---

## Files Successfully Updated (Additional Round)

### Configuration Files
1. ✅ `.github/workflows/playwright-tests.yml` - Updated database names
2. ✅ `.gitignore` - Updated deployment package names and venv directory
3. ✅ `api/env.example` - Updated header, DB_NAME, and DB_USER
4. ✅ `app/layout.tsx` - Updated metadata (Team RSW → Team Lightening)
5. ✅ `public/config.js` - Updated __RSW_CONFIG__ → __LIGHTENING_CONFIG__
6. ✅ `lib/config.ts` - Updated config variable and comments

---

## Files Requiring Manual Review

### Build Scripts (Need Extensive Updates)
These files contain multiple RSW references and should be reviewed carefully:

1. **backup_and_copy.sh**
   - Line: `# In backup mode, SOURCE_PATH should be the source RSW installation`
   - Line: `BACKUP_DIR="${DEST_PATH}/rsw_backup_${TIMESTAMP}"`
   - Line: `echo "===== RSW Backup and Copy Script ====="`
   - Line: `echo "===== RSW Restore Script ====="`

2. **build-frontend.sh**
   - Line: `// Runtime configuration for RSW application`
   - Line: `window.__RSW_CONFIG__ = {`

3. **build-package.sh** (Multiple references)
   - Header: `# RSW Application Packager`
   - Line: `echo "=== RSW Application Packager ==="`
   - Line: `DB_NAME=rsw`
   - Line: `// Runtime configuration for RSW application`
   - Line: `window.__RSW_CONFIG__ = {`
   - Line: `echo "RSW application is ready to start!"`
   - Line: `export DB_NAME=${DB_NAME:-rsw}`
   - Line: `echo "Starting RSW application..."`
   - Line: `tar -czf rsw-deployment.tar.gz package/`
   - Line: `echo "Deployment archive: rsw-deployment.tar.gz"`

### Documentation Files (docs/ directory)
All files in the `docs/` directory need updates:

1. **docs/api-reference.md**
   - Multiple instances of `your-rsw-instance.com` in API examples
   - "The RSW platform provides..."
   - "The RSW API uses URL versioning"

2. **docs/datapuur.md**
   - "DataPuur is the comprehensive data management module of the RSW platform"

3. **docs/djinni-assistant.md**
   - "Djinni Assistant is an AI-powered conversational interface integrated into the RSW platform"

4. **docs/getting-started.md**
   - Title: "# Getting Started with RSW"
   - "Welcome to the RSW Smart Data Intelligence (SDI) platform!"
   - Repository URL: `git clone https://github.com/your-organization/rsw.git`
   - Directory: `cd rsw`
   - Database URL: `# DATABASE_URL=postgresql://user:password@localhost/rsw`
   - "RSW uses a hierarchical permission system"
   - "The RSW platform is organized into..."
   - Support email: `support@rsw-platform.com`

5. **docs/index.md**
   - Title: "# RSW Platform Documentation"
   - "Welcome to the RSW Smart Data Intelligence (SDI) platform"
   - "## About RSW Platform"
   - "RSW is a comprehensive Smart Data Intelligence (SDI) platform"
   - "RSW uses advanced generative AI to:"
   - "RSW dramatically reduces the technical barriers"
   - "RSW's GenAI capabilities deliver"
   - Support email: `support@rsw.com`
   - Repository: `https://github.com/your-organization/rsw`

6. **docs/kginsights.md**
   - "KGInsights (K-Graff) is the knowledge graph management module of the RSW platform"

### HTML Documentation Files (html_docs/ directory)
All HTML files mirror the markdown docs and need similar updates:

1. **html_docs/api-reference.html**
2. **html_docs/datapuur.html**
3. **html_docs/djinni-assistant.html**
4. **html_docs/getting-started.html**
5. **html_docs/index.html**
6. **html_docs/kginsights.html**
7. **html_docs/template.html**
8. **html_docs/convert_md_to_html.py** - Contains old file paths

### Library Files
1. **lib/auth/fetch.ts**
   - Comment: `* Fetch with authentication for RSW API requests`

### Playwright Configuration
1. **playwright.config.ts**
   - Comment: `* Playwright configuration for RSW project`

### Data Files (Can be ignored - these are sample data)
1. **api/samples/TelecomChurn.csv** - Contains customer ID "7064-FRRSW" (sample data)
2. **api/static_dashboards/TelecomChurn.csv** - Same sample data

### Gen AI Layer Documentation
1. **api/gen_ai_layer/README.md**
   - Title: "# Gen AI Layer for RSW Platform"
   - "This package provides AI capabilities to the RSW platform"
   - "## Integration with RSW Components"
   - "The Gen AI Layer is designed to integrate seamlessly with other RSW components"

---

## Recommended Actions

### High Priority
1. Update all build scripts (backup_and_copy.sh, build-frontend.sh, build-package.sh)
2. Update api/gen_ai_layer/README.md
3. Update lib/auth/fetch.ts comment
4. Update playwright.config.ts comment

### Medium Priority
5. Update all documentation in docs/ directory
6. Update all HTML documentation in html_docs/ directory

### Low Priority
7. Sample data files can be left as-is (they contain customer IDs, not brand references)

---

## Bulk Update Recommendations

For documentation files, consider using a script or bulk find-replace with these patterns:

1. `RSW platform` → `Lightening platform`
2. `RSW Smart Data Intelligence` → `Lightening Smart Data Intelligence`
3. `RSW is` → `Lightening is`
4. `RSW uses` → `Lightening uses`
5. `RSW's` → `Lightening's`
6. `RSW Application` → `Lightening Application`
7. `your-rsw-instance.com` → `your-lightening-instance.com`
8. `support@rsw.com` → `support@lightening.com`
9. `support@rsw-platform.com` → `support@lightening-platform.com`
10. `https://github.com/your-organization/rsw` → `https://github.com/genaimavericks/arc`
11. `cd rsw` → `cd arc`
12. `rsw-deployment.tar.gz` → `lightening-deployment.tar.gz`
13. `rsw_backup` → `lightening_backup`
14. `DB_NAME=rsw` → `DB_NAME=lightening`
15. `__RSW_CONFIG__` → `__LIGHTENING_CONFIG__`

---

**Note**: The analysis documents (RSW_TO_LIGHTENING_ANALYSIS.md and RENAME_COMPLETED.md) should be kept as-is since they document the rename process itself.
