# --- main_app.py (Updated initialization section) ---

from inventory_manager import InventoryManager
from price_ingestion_manager import PriceIngestionManager # Import the new manager
from database_models import UnitType, ItemStatus 

def initialize_demo_data(manager: InventoryManager):
    """Initializes basic definitions, stock, and price data for testing."""
    
    # 1. Grocery Definitions
    manager.add_new_grocery_item("Milk 3%", UnitType.LITERS, 1.0, 1) # Threshold = 1 liter
    manager.add_new_grocery_item("Whole Wheat Bread", UnitType.UNITS, 1.0, 2) # Threshold = 2 units
    manager.add_new_grocery_item("Eggs (L)", UnitType.UNITS, 1.0, 6) # Threshold = 6 eggs
    manager.add_new_grocery_item("Yogurt", UnitType.UNITS, 1.0, 3) # Threshold = 3 units

    # 2. Initial Stock
    manager.add_inventory_stock("Milk 3%", 3.0, "Fridge Door")
    manager.add_inventory_stock("Whole Wheat Bread", 5.0, "Freezer")
    manager.add_inventory_stock("Eggs (L)", 12.0, "Egg Tray")

    # REMOVE initial price_update calls here, as the new Ingestion Manager will handle it.
    
    # 4. Run initial check to populate the persistent shopping list (should be empty initially)
    manager.check_thresholds_and_update_shopping_list()
    print("\n[Demo data initialized. Ready to simulate.]")


def main_cli():
    """The main command-line interface loop for the application."""
    manager = InventoryManager()

        # NEW: Initialize the PriceIngestionManager
    price_manager = PriceIngestionManager(manager.db_manager) 
    
    # NOTE: Run initialize_demo_data ONLY if you want to wipe/reset the data
    # For persistent testing, you might comment this out after the first run.

    # We now call initialize_demo_data AND run an ingestion to set initial prices
    initialize_demo_data(manager) 
    print("Running initial price feed ingestion...")
    price_manager.ingest_latest_feed(manager) # Use the new method for initial prices

    while True:
        print("\n==============================================")
        print("     SMART FRIDGE INVENTORY MANAGER (CLI)     ")
        print("==============================================")
        print("1. View Full Inventory")
        print("2. Simulate CV Scan & Reconcile")
        print("3. View Shopping List & Price Recommendations")
        print("4. Add New Stock/New Item Definition")
        print("5. Force Inventory Threshold Check")
        print("6. RUN Daily Price Feed Ingestion & Cleanup 💰") # NEW OPTION
        print("0. Exit Application")
        
        choice = input("Enter choice (0-6): ")

        try:
            if choice == '1':
                manager.get_all_inventory()
            
            elif choice == '2':
                # --- CV RECONCILIATION SIMULATION ---
                print("\n--- Simulating New Fridge Snapshot (CV Output) ---")
                
                # Snapshot demonstrating the core reconciliation concepts:
                new_snapshot = [
                    # 1. Milk: Moved from 'Fridge Door' to 'Shelf A', and some consumed (now 0.2, below threshold of 1)
                    {'name': 'Milk 3%', 'quantity': 0.2, 'location': 'Shelf A'},
                    
                    # 2. Bread: Moved from 'Freezer' to 'Shelf B', fully consumed (quantity 0.0). Should be added to list.
                    {'name': 'Whole Wheat Bread', 'quantity': 0.0, 'location': 'Shelf B'},
                    
                    # 3. Eggs: Not included in this list (assumed consumed). Should be marked OUT_OF_STOCK.
                    
                    # 4. Yogurt: New stock detected (will use get_or_create_grocery_definition)
                    {'name': 'Yogurt', 'quantity': 4.0, 'location': 'Door Shelf'}
                ]
                
                manager.reconcile_inventory_snapshot(new_snapshot)
                
            elif choice == '3':
                manager.display_shopping_list()
                manager.get_shopping_recommendations()

            elif choice == '4':
                print("\n--- Add/Define Item ---")
                name = input("Grocery Item Name: ")
                
                # Check if item exists, if not, prompt for definition details
                existing_item = manager.session.query(manager.db_manager.Base.metadata.tables['grocery_items']).filter_by(name=name).first()

                if not existing_item:
                    print("This is a NEW Grocery Item definition.")
                    unit = input("Unit Type (KG/LITER/UNIT): ").upper()
                    
                    try:
                        unit_type = UnitType[unit]
                    except KeyError:
                        print("Invalid unit type. Must be KG, LITER, or UNIT.")
                        continue
                        
                    size = float(input("Standard Size Per Unit (e.g., 1.0): "))
                    threshold = int(input("Low Stock Threshold (e.g., 2): "))
                    manager.add_new_grocery_item(name, unit_type, size, threshold)
                else:
                    print(f"'{name}' definition already exists.")
                
                # Always prompt to add current stock
                qty = float(input(f"Current Stock Quantity of {name} to add: "))
                loc = input("Location (e.g., 'Shelf'): ")
                manager.add_inventory_stock(name, qty, loc)

            elif choice == '5':
                 manager.check_thresholds_and_update_shopping_list()

            elif choice == '6':
                price_manager.ingest_latest_feed(manager)
                price_manager.clean_old_records(days_to_keep=7) # Keep 7 days of history for testing
            
            elif choice == '0':
                manager.close()
                print("Exiting application. Goodbye!")
                break
                
            else:
                print("Invalid choice. Please enter a number between 0 and 5.")
        
        except ValueError:
            print("Invalid input. Please ensure quantities and choices are numbers.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main_cli()