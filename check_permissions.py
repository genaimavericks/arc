# Quick script to check permissions in the database
from api.models import Role, get_db, User
import json

def main():
    db = next(get_db())
    print("\n=== CHECKING DATABASE ROLES AND PERMISSIONS ===\n")
    
    # Check all roles in the database
    roles = db.query(Role).all()
    print(f"Found {len(roles)} roles in the database")
    
    for role in roles:
        print(f"\nRole: {role.name} (ID: {role.id})")
        print(f"Description: {role.description}")
        print(f"Is system role: {role.is_system_role}")
        
        # Get permissions
        try:
            if role.permissions:
                try:
                    permissions = json.loads(role.permissions)
                    print(f"Permissions (from permissions field): {permissions}")
                except json.JSONDecodeError:
                    print(f"Error parsing permissions JSON: {role.permissions}")
            else:
                print("No permissions set in permissions field")
                
            # Try to get permissions using get_permissions method
            perms = role.get_permissions()
            print(f"Permissions (from get_permissions method): {perms}")
            
            # Check if kginsights:read is in permissions
            has_kg_read = "kginsights:read" in perms
            print(f"Has kginsights:read permission: {has_kg_read}")
            
        except Exception as e:
            print(f"Error getting permissions: {str(e)}")
    
    # Also check for superuser/superhero users
    users = db.query(User).filter(User.role.like("%super%")).all()
    print(f"\nFound {len(users)} users with 'super' in role name")
    for user in users:
        print(f"User: {user.username}, Role: {user.role}")

if __name__ == "__main__":
    main()
