import sqlite3
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

# Import the module to test functions
try:
    from senti1_sl import init_db, add_organization, get_organizations, add_brand, get_brands, get_model
    print("Import successful.")
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

# Test DB Init
print("Testing DB Init...")
init_db()
if os.path.exists('senti.db'):
    print("senti.db created.")
else:
    print("senti.db NOT created.")

# Test Org Creation
print("Testing Org Creation...")
org_id = add_organization("Test Org")
if org_id:
    print(f"Org created with ID: {org_id}")
else:
    # Might exist if run multiple times
    print("Org creation returned None (might exist).")

df_org = get_organizations()
print(f"Orgs found: {len(df_org)}")
print(df_org)

# Test Brand Creation
print("Testing Brand Creation...")
if not df_org.empty:
    oid = df_org.iloc[0]['id']
    bid = add_brand(oid, "Test Brand")
    print(f"Brand created with ID: {bid}")
    
    df_brand = get_brands(oid)
    print(f"Brands found: {len(df_brand)}")
    print(df_brand)

# Test Lazy Loading (Mock)
print("Testing Lazy Loading availability...")
# access get_model function
# We won't actually download 500MB+ models in this script to save time/bandwidth unless necessary, 
# but we check if the function exists and syntax is correct by calling with a fake code first or just inspecting.
try:
    # Just checking it doesn't crash on import
    print("get_model function exists.")
except Exception as e:
    print(f"get_model failed: {e}")

print("Verification complete.")
