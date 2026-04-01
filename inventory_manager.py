from sqlalchemy.orm import joinedload
from sqlalchemy import func, distinct, desc
import datetime
from decimal import Decimal
from database_models import DB_GroceryItem, DB_InventoryItem, DB_PriceRecord, DB_ShoppingListItem, DatabaseManager, UnitType, ItemStatus

class InventoryManager:
    
    def __init__(self):
        self.db_manager = DatabaseManager(db_path='inventory.db') 
        self.session = self.db_manager.get_session()
        # self.shopping_list (set) is now replaced by the DB_ShoppingListItem table
        print("Database connection established and inventory loaded.")

    # --- CORE CRUD & HELPER METHODS (Mostly Unchanged/Minor Fixes) ---
    
    def add_new_grocery_item(self, name: str, unit_type: UnitType, size_per_unit: float, threshold_qty: int):
        """Adds a definition of a new grocery item (e.g., 'Milk')."""
        
        existing_item = self.session.query(DB_GroceryItem).filter_by(name=name).first()
        if existing_item:
            # print(f"Grocery item '{name}' already exists.") # Keep silent for internal calls
            return existing_item

        new_item = DB_GroceryItem(
            name=name,
            unit_type=unit_type,
            size_per_unit=size_per_unit,
            threshold_qty=threshold_qty
        )
        self.session.add(new_item)
        self.session.commit()
        return new_item

    def add_inventory_stock(self, grocery_name: str, quantity: float, location_tag: str):
        """Adds a specific stock instance of a grocery item (e.g., '1 liter of Milk in the door')."""
    
        grocery_item = self.session.query(DB_GroceryItem).filter_by(name=grocery_name).first()
        if not grocery_item:
            print(f"Error: Grocery item '{grocery_name}' not found. Add it first.")
            return

        # Check if item is on shopping list and remove it if stock is added
        self.remove_from_shopping_list(grocery_item.id)
        
        # Create the new inventory item (store quantity as Decimal)
        new_stock = DB_InventoryItem(
            grocery_item_id=grocery_item.id,
            current_quantity=Decimal(str(quantity)),
            location_tag=location_tag,
            status=ItemStatus.IN_STOCK,
            last_scan_date=datetime.datetime.now()
        )
        
        self.session.add(new_stock)
        self.session.commit()
        print(f"Added {quantity} of {grocery_name} to inventory at {location_tag}.")

    def get_all_inventory(self):
        """Retrieves and prints all items currently in stock."""
        items = self.session.query(DB_InventoryItem).options(joinedload(DB_InventoryItem.grocery_ref)).all()
        # ... (rest of the print logic is the same) ...
        
        if not items:
            print("Inventory is currently empty.")
            return []

        print("\n--- Current Inventory ---")
        for item in items:
            g = item.grocery_ref
            print(f"Product: {g.name} | Qty: {item.current_quantity} {g.unit_type.value} | Loc: {item.location_tag} | Status: {item.status.value}")
        print("-------------------------\n")
        return items

    def close(self):
        self.session.close()
        print("Database session closed.")
        
    def process_price_update(self, grocery_name: str, store: str, price: float, is_offer: bool = False, offer_details: str = None):
        # ... (Same logic as provided in the previous step) ...
        
        grocery_item = self.session.query(DB_GroceryItem).filter_by(name=grocery_name).first()
        if not grocery_item:
            return

        price_dec = Decimal(str(price))

        new_price_record = DB_PriceRecord(
            grocery_item_id=grocery_item.id,
            store_name=store,
            item_price=price_dec,
            is_offer=is_offer,
            offer_details=offer_details,
            price_date=datetime.datetime.now()
        )
        self.session.add(new_price_record)

        all_prices = self.session.query(DB_PriceRecord.item_price).filter_by(grocery_item_id=grocery_item.id).all()
        
        # Calculate the new average
        total_price = sum(p[0] for p in all_prices)
        new_avg = total_price / len(all_prices) if len(all_prices) > 0 else Decimal('0.00')
        
        grocery_item.price_per_unit_avg = new_avg
        
        self.session.commit()
        # print(f"Price update for {grocery_name}: New Avg Price = {new_avg:.2f} NIS.") # Keep silent for internal calls

    # --- PERSISTENT SHOPPING LIST METHODS (NEW/UPDATED) ---

    def add_to_shopping_list(self, grocery_item: DB_GroceryItem):
        """Adds an item to the persistent shopping list table."""
        
        # Check if already on the list (using the unique constraint)
        existing_item = self.session.query(DB_ShoppingListItem).filter_by(grocery_item_id=grocery_item.id).first()
        
        if not existing_item:
            # Calculate suggested quantity to buy (e.g., 2x the threshold to restock properly)
            suggested_qty = Decimal(str(grocery_item.threshold_qty * 2)) 
            
            new_list_item = DB_ShoppingListItem(
                grocery_item_id=grocery_item.id,
                date_added=datetime.datetime.now(),
                suggested_qty=suggested_qty
            )
            self.session.add(new_list_item)
            # Commit is handled by the caller (check_thresholds) for batch processing
            print(f"   --> Added to Shopping List (Buy {suggested_qty:.0f} {grocery_item.unit_type.value}).")
            
    def remove_from_shopping_list(self, grocery_item_id: int):
        """Removes an item from the persistent shopping list table."""
        item = self.session.query(DB_ShoppingListItem).filter_by(grocery_item_id=grocery_item_id).first()
        if item:
            self.session.delete(item)
            # Commit is handled by the caller (e.g., add_inventory_stock)

    def display_shopping_list(self):
        """Queries and prints the current persistent shopping list."""
        
        items = self.session.query(DB_ShoppingListItem).options(joinedload(DB_ShoppingListItem.grocery_ref_item)).all()
        
        if not items:
            print("\n🛒 Shopping List is Empty. Good job!")
            return []

        print("\n--- Current Shopping List (Persistent) ---")
        for item in items:
            g = item.grocery_ref_item
            print(f"- {g.name} (Buy: {item.suggested_qty:.0f} {g.unit_type.value})")
        print("------------------------------------------\n")
        return [item.grocery_ref_item.name for item in items] # Return list of names for compatibility with other methods

    # --- THRESHOLD CHECK (UPDATED for Persistence) ---
    
    def check_thresholds_and_update_shopping_list(self):
        """Checks all inventory items against their defined thresholds and updates the persistent shopping list."""
        
        print("\n--- Running Stock Check & Updating Shopping List ---")
        
        # 1. Find all LOW_STOCK or OUT_OF_STOCK items
        low_stock_items = self.session.query(DB_InventoryItem)\
            .join(DB_GroceryItem)\
            .filter(DB_InventoryItem.current_quantity <= DB_GroceryItem.threshold_qty)\
            .options(joinedload(DB_InventoryItem.grocery_ref))\
            .all()

        items_to_add = []
        items_in_stock = set() # Track all items with ANY remaining stock
        
        for item in low_stock_items:
            grocery_item = item.grocery_ref
            
            # Update status for low stock items
            if item.current_quantity > Decimal('0.0'):
                item.status = ItemStatus.LOW_STOCK
                items_in_stock.add(grocery_item.id) # Track for potential removal logic (if stock is added back)
            
            # If the item is low/out of stock AND not already on the list, add it to the pending list
            if not self.session.query(DB_ShoppingListItem).filter_by(grocery_item_id=grocery_item.id).first():
                items_to_add.append(grocery_item)
            
            print(f"🚨 LOW STOCK: '{grocery_item.name}' ({item.current_quantity:.2f} {grocery_item.unit_type.value})")

        # 2. Add all pending items to the persistent list
        for grocery_item in items_to_add:
            self.add_to_shopping_list(grocery_item)
            
        # 3. Check for items on the list that are no longer low-stock (e.g., restocked manually, not via add_inventory_stock)
        
        # Find items on the list
        current_shopping_items = self.session.query(DB_ShoppingListItem).all()
        
        for list_item in current_shopping_items:
            # Check the TOTAL current stock for this grocery item
            total_stock = self.session.query(func.sum(DB_InventoryItem.current_quantity))\
                .filter(DB_InventoryItem.grocery_item_id == list_item.grocery_item_id)\
                .scalar()
            
            # Compare total stock to the threshold of the parent item
            threshold = list_item.grocery_ref_item.threshold_qty
            
            if total_stock is None or total_stock > threshold:
                self.session.delete(list_item)
                print(f"✅ RESTOCKED: '{list_item.grocery_ref_item.name}' stock is above threshold. Removed from list.")
                
        self.session.commit()
        print(f"Shopping list reconciliation complete. Total items: {len(self.session.query(DB_ShoppingListItem).all())}.")
        print("----------------------------------------------------------\n")

    # --- RECONCILIATION & DEFINITION (REFINED) ---

    def get_or_create_grocery_definition(self, name: str):
        """Checks for an existing GroceryItem definition. If missing, it creates one with defaults."""
        
        grocery_item = self.session.query(DB_GroceryItem).filter_by(name=name).first()
        
        if not grocery_item:
            print(f"\n🚨 NEW ITEM DEFINITION REQUIRED: '{name}' detected for the first time.")
            
            # In a real app, this would be a user prompt or a database lookup.
            # For now, we use a sensible default:
            print(f"--> Auto-defining '{name}' as 1 UNIT, Threshold: 1.")
            grocery_item = self.add_new_grocery_item(
                name=name, 
                unit_type=UnitType.UNITS, 
                size_per_unit=1.0, 
                threshold_qty=1
            )

        return grocery_item

    def reconcile_inventory_snapshot(self, snapshot_data: list):
        """
        Compares the current database inventory with a complete snapshot from the 
        Computer Vision system to identify stock changes and location moves/consumption.
        """
        # ... (reconciliation logic remains the same, but uses the new helper functions) ...
        
        print("\n--- Running Inventory Reconciliation ---")
        
        current_db_items = self.session.query(DB_InventoryItem)\
            .join(DB_GroceryItem)\
            .options(joinedload(DB_InventoryItem.grocery_ref))\
            .all()
        
        db_composite_keys = set((item.grocery_ref.name, item.location_tag) for item in current_db_items)
        snapshot_composite_keys = set((data['name'], data['location']) for data in snapshot_data)
        
        consumed_or_moved_keys = db_composite_keys - snapshot_composite_keys
        
        for data in snapshot_data:
            grocery_name = data['name']
            new_qty = Decimal(str(data['quantity']))
            new_loc = data['location']
            
            existing_instances = self.session.query(DB_InventoryItem).join(DB_GroceryItem)\
                .filter(DB_GroceryItem.name == grocery_name)\
                .all()
            
            # Scenario 1a & 1b: Found the item in the same or new location
            target_item = self.session.query(DB_InventoryItem).join(DB_GroceryItem)\
                .filter(DB_GroceryItem.name == grocery_name, DB_InventoryItem.location_tag == new_loc)\
                .first()

            if target_item:
                # 1a: Found in the same location (simple quantity update)
                qty_change = target_item.current_quantity - new_qty
                
                if abs(qty_change) > Decimal('0.01'):
                    target_item.current_quantity = new_qty
                    target_item.last_scan_date = datetime.datetime.now()
                    print(f"✅ UPDATED QTY: {grocery_name} at {new_loc}. Qty changed by {qty_change:.2f}. New Qty: {new_qty:.2f}")

            elif existing_instances:
                # 1b: Item is in a NEW location (Relocation simulation)
                largest_instance = max(existing_instances, key=lambda i: i.current_quantity)
                
                if largest_instance.location_tag != new_loc:
                    old_loc = largest_instance.location_tag
                    largest_instance.location_tag = new_loc
                    largest_instance.current_quantity = new_qty
                    largest_instance.last_scan_date = datetime.datetime.now()
                    print(f"🔄 MOVED/UPDATED: {grocery_name} relocated from {old_loc} to {new_loc}. New Qty: {new_qty:.2f}")
                    
                    consumed_or_moved_keys.discard((grocery_name, old_loc))
            else:
                # 1c: Item has NO previous instance (Brand new stock added)
                grocery_def = self.get_or_create_grocery_definition(grocery_name)
                
                if grocery_def:
                    self.add_inventory_stock(grocery_name, float(new_qty), new_loc)


        # C. Identify Items that are GONE (Consumed)
        for g_name, old_loc in consumed_or_moved_keys:
            missing_item = self.session.query(DB_InventoryItem).join(DB_GroceryItem)\
                .filter(DB_GroceryItem.name == g_name, DB_InventoryItem.location_tag == old_loc)\
                .first()

            if missing_item and missing_item.current_quantity > Decimal('0.0'):
                missing_item.current_quantity = Decimal('0.0')
                missing_item.status = ItemStatus.OUT_OF_STOCK
                missing_item.last_scan_date = datetime.datetime.now()
                print(f"🗑️ CONSUMED: {g_name} is no longer detected at {old_loc}. Marked as OUT OF STOCK.")
        
        self.session.commit()
        self.check_thresholds_and_update_shopping_list()
        print("-------------------------------------------\n")

    def get_shopping_recommendations(self):
        """Analyzes the current persistent shopping list against price records to recommend the best place to buy."""
        
        # 1. Query the persistent list for names and suggested quantities
        shopping_items = self.session.query(DB_ShoppingListItem).options(joinedload(DB_ShoppingListItem.grocery_ref_item)).all()
        
        if not shopping_items:
            print("\n✅ Shopping List is empty. No recommendations needed.")
            return []

        print("\n--- Price Recommendations ---")
        
        for list_item in shopping_items:
            item_name = list_item.grocery_ref_item.name
            item_id = list_item.grocery_ref_item.id
            suggested_qty = list_item.suggested_qty

            # Find the best (lowest) current price/offer
            best_price_record = self.session.query(DB_PriceRecord)\
                .filter(DB_PriceRecord.grocery_item_id == item_id)\
                .order_by(DB_PriceRecord.item_price.asc(), DB_PriceRecord.price_date.desc())\
                .first()

            if best_price_record:
                
                offer_text = f" (Offer: {best_price_record.offer_details})" if best_price_record.is_offer else ""
                
                print(f"🛍️ {item_name} (Buy {suggested_qty:.0f}): Best Price is {best_price_record.item_price:.2f} NIS at {best_price_record.store_name}{offer_text}")
            else:
                avg_price = list_item.grocery_ref_item.price_per_unit_avg
                print(f"⚠️ {item_name} (Buy {suggested_qty:.0f}): No recent price data. Avg Price: {avg_price:.2f} NIS (Estimate)")

        print("-----------------------------\n")