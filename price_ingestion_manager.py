# --- price_ingestion_manager.py ---

from inventory_manager import InventoryManager 
from database_models import DB_GroceryItem, DB_PriceRecord, DatabaseManager
from decimal import Decimal
import datetime
import random # For simulating new prices

class PriceIngestionManager:
    """Handles loading external price data and updating the main database."""

    def __init__(self, db_manager: DatabaseManager):
        self.session = db_manager.get_session()
        print("Price Ingestion Manager initialized.")

    def _simulate_daily_price_feed(self):
        """
        Simulates loading a full, external price feed.
        In a real system, this would read JSON/XML files from the external source.
        """
        # Get all items that have definitions in the database
        all_grocery_items = self.session.query(DB_GroceryItem).all()
        
        simulated_feed = []
        stores = ["Shufersal", "Rami Levy", "Mega", "Yeynot Bitan"]
        
        for item in all_grocery_items:
            # Generate 2-4 price entries for the item across different stores
            for _ in range(random.randint(2, 4)):
                # Simple price generation: Base price (10-30) +/- 10%
                base_price = Decimal(str(random.uniform(10.0, 30.0))).quantize(Decimal('0.01'))
                price = base_price * Decimal(str(random.uniform(0.9, 1.1)))
                
                # Randomly determine if it's an offer
                is_offer = random.random() < 0.15 # 15% chance of an offer
                offer_details = "Buy 2 Get 1 Free" if is_offer else None
                
                simulated_feed.append({
                    'name': item.name,
                    'store': random.choice(stores),
                    'price': float(price),
                    'is_offer': is_offer,
                    'offer_details': offer_details
                })
        
        return simulated_feed

    def ingest_latest_feed(self, inventory_manager: InventoryManager):
        """Processes the latest price feed and updates price history and averages."""
        
        print("\n--- INGESTION: Running Price Feed Update ---")
        feed = self._simulate_daily_price_feed()
        
        new_records_count = 0
        
        for record in feed:
            grocery_name = record['name']
            
            # Find the Grocery Item definition
            grocery_item = self.session.query(DB_GroceryItem).filter_by(name=grocery_name).first()
            
            if grocery_item:
                # 1. Save the new raw price record
                new_price_record = DB_PriceRecord(
                    grocery_item_id=grocery_item.id,
                    store_name=record['store'],
                    item_price=Decimal(str(record['price'])),
                    price_date=datetime.datetime.now(),
                    is_offer=record['is_offer'],
                    offer_details=record['offer_details']
                )
                self.session.add(new_price_record)
                new_records_count += 1
                
                # 2. Update the running average in the DB_GroceryItem (using the InventoryManager method)
                # We reuse the InventoryManager method which handles the commit and calculation!
                inventory_manager.process_price_update(
                    grocery_name=grocery_name,
                    store=record['store'],
                    price=record['price'],
                    is_offer=record['is_offer'],
                    offer_details=record['offer_details']
                )
        
        # We committed inside process_price_update, but ensure all DB_PriceRecord insertions are flushed/committed
        self.session.commit()
        
        print(f"--- INGESTION COMPLETE: {new_records_count} price records saved. ---\n")

    def clean_old_records(self, days_to_keep=30):
        """Deletes price records older than a specified number of days to keep the database small."""
        
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
        
        deleted_count = self.session.query(DB_PriceRecord)\
            .filter(DB_PriceRecord.price_date < cutoff_date)\
            .delete(synchronize_session=False)
            
        self.session.commit()
        print(f"Database Maintenance: Deleted {deleted_count} old price records (older than {days_to_keep} days).")