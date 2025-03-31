#!/usr/bin/env python
"""
Permission Migration Script for RSW

This script migrates existing roles from the old granular permission structure
(data:*, ingestion:*, schema:*) to the new hierarchical DataPuur permission structure
(datapuur:read, datapuur:write, datapuur:manage).

Run this script after updating the codebase to the new permission model.
"""

import os
import sys
import json
from datetime import datetime

# Add the parent directory to the path so we can import the app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.db_config import get_db, SessionLocal
from api.models import Role
from api.auth import initialize_default_roles

# Permission mapping from old to new
PERMISSION_MAPPING = {
    # Basic read permissions
    "data:read": "datapuur:read",
    
    # Write permissions
    "data:write": "datapuur:write",
    "data:upload": "datapuur:write",
    "schema:write": "datapuur:write",
    "ingestion:create": "datapuur:write",
    "ingestion:update": "datapuur:write",
    
    # Management permissions
    "data:delete": "datapuur:manage",
    "ingestion:delete": "datapuur:manage",
    
    # Read-only permissions that map to basic read
    "schema:read": "datapuur:read",
    "ingestion:read": "datapuur:read",
}

def migrate_role_permissions():
    """Migrate all roles from old permission structure to new one."""
    db = next(get_db())
    roles = db.query(Role).all()
    
    print(f"Found {len(roles)} roles to process")
    
    for role in roles:
        try:
            # Skip if role has no description
            if not role.description:
                print(f"Role {role.name} (ID: {role.id}) has no description, skipping")
                continue
                
            # Try to parse the description as JSON
            try:
                description_data = json.loads(role.description)
            except json.JSONDecodeError:
                print(f"Role {role.name} (ID: {role.id}) has invalid JSON description, skipping")
                continue
                
            if "permissions" not in description_data:
                print(f"Role {role.name} (ID: {role.id}) has no permissions in description, skipping")
                continue
                
            old_permissions = description_data["permissions"]
            new_permissions = set()
            
            # Map old permissions to new permissions
            for perm in old_permissions:
                if perm in PERMISSION_MAPPING:
                    new_permissions.add(PERMISSION_MAPPING[perm])
                elif perm.startswith(("datapuur:", "kginsights:", "database:", "user:", "role:")):
                    # These are already in the new format, keep them
                    new_permissions.add(perm)
            
            # Convert to list and sort
            new_permissions = sorted(list(new_permissions))
            
            # Update the role if permissions changed
            if set(old_permissions) != set(new_permissions):
                description_data["permissions"] = new_permissions
                role.description = json.dumps(description_data)
                role.updated_at = datetime.utcnow()
                print(f"Updated role {role.name} (ID: {role.id})")
                print(f"  Old: {old_permissions}")
                print(f"  New: {new_permissions}")
            else:
                print(f"No changes needed for role {role.name} (ID: {role.id})")
                
        except Exception as e:
            print(f"Error processing role {role.name} (ID: {role.id}): {str(e)}")
    
    # Commit all changes
    try:
        db.commit()
        print("Successfully committed all role permission updates")
    except Exception as e:
        db.rollback()
        print(f"Error committing updates: {str(e)}")
        
    # Re-initialize default roles to ensure they have the correct permissions
    initialize_default_roles(db)

if __name__ == "__main__":
    print("Starting permission migration...")
    migrate_role_permissions()
    print("Permission migration complete!")
