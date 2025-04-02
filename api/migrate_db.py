from sqlalchemy.orm import Session
from api.models import Role, User
from api.db_config import SessionLocal, engine, get_db
import json
from api.auth import AVAILABLE_PERMISSIONS

def migrate_database():
    """
    Perform database migrations. This is a placeholder function that can be expanded
    with actual migration logic as needed.
    """
    print("Running database migrations...")
    # This would typically contain SQLAlchemy migrations or other database setup
    # For now, we'll just ensure the roles are set up correctly
    with SessionLocal() as db:
        setup_default_role_permissions(db)
    print("Database migrations complete")

def setup_default_role_permissions(db: Session):
    """
    Ensure all roles have properly formatted permissions in the description field.
    This migrates old roles to the new format if needed.
    """
    roles = db.query(Role).all()
    
    for role in roles:
        try:
            # Try to parse existing description as JSON
            if role.description and role.description.startswith('{'):
                description_data = json.loads(role.description)
                # If already in JSON format with permissions, continue
                if "permissions" in description_data:
                    print(f"Role {role.name} already has proper JSON format")
                    continue
            
            # If we get here, role description is not in JSON format or doesn't have permissions
            # Create a new JSON format with any existing permissions and description
            
            # Start with empty permissions
            permissions = []
            
            # If this is a system role, assign default permissions
            if role.name == "admin":
                # Admin has all permissions
                permissions = AVAILABLE_PERMISSIONS
            elif role.name == "superhero":
                # Give superhero role access to everything except admin tasks
                permissions = [p for p in AVAILABLE_PERMISSIONS if not p.startswith(("role:"))]
            
            # Store current description as text if it exists and isn't already JSON
            original_description = ""
            if role.description and not role.description.startswith('{'):
                original_description = role.description
            
            # Create new JSON description
            new_description = json.dumps({
                "text": original_description,
                "permissions": permissions
            })
            
            # Update the role
            role.description = new_description
            db.commit()
            
            print(f"Updated role {role.name} with proper JSON format and permissions: {permissions}")
        
        except Exception as e:
            print(f"Error updating role {role.name}: {str(e)}")
            db.rollback()

if __name__ == "__main__":
    # Run this script directly to migrate all roles
    db = next(get_db())
    setup_default_role_permissions(db)
    print("Migration complete")
