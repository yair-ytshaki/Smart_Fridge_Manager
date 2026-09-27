# --- price_ingestion_manager.py ---

from inventory_manager import InventoryManager 
from database_models import DB_GroceryItem, DB_PriceRecord, DatabaseManager, UnitType
from decimal import Decimal
import datetime
from datetime import datetime, timedelta
import random # For simulating new prices
from supermarket_parser import SupermarketDataParser
from typing import Tuple
import os
from sqlalchemy import func
from mongo_manager import MongoManager

class PriceIngestionManager:
    """Handles loading external price data and updating the main database."""

    def __init__(self, db_manager: DatabaseManager = None):
        # Fallback to creating a DatabaseManager instance if none is passed
        self.db = db_manager or DatabaseManager(db_path="inventory.db")
        self.parser = SupermarketDataParser()
        self.mongo = MongoManager()
        print("Price Ingestion Manager initialized.")

    def _determine_unit_type(self, unit_qty_str: str) -> UnitType:
        """Helper to map supermarket unit indicators to database UnitType."""
        if not unit_qty_str:
            return UnitType.UNITS
        unit_lower = str(unit_qty_str).lower()
        if "ק\"ג" in unit_lower or "kg" in unit_lower:
            return UnitType.KILOGRAMS
        if "ליטר" in unit_lower or "liter" in unit_lower:
            return UnitType.LITERS
        return UnitType.UNITS

    def ingest_latest_price_file(self, chain_name="Wolt"):
        session = self.db.get_session()
        try:
            # 1. Parse raw XML data
            parsed_items = self.parser.parse_latest_output(chain_folder=chain_name)
            
            # 2. Tier 1: Archive raw payload in MongoDB Atlas
            print(f"☁️ Streaming {len(parsed_items)} raw records to MongoDB Atlas...")
            raw_collection = self.mongo.get_raw_collection("raw_supermarket_feeds")
            payload_document = {
                "chain_name": chain_name,
                "ingested_at": datetime.now(),
                "record_count": len(parsed_items),
                "items": parsed_items
            }
            raw_collection.insert_one(payload_document)
            print(" Raw payload archived in MongoDB Atlas.")

            # 3. Tier 2: Update local SQLite master inventory and price records
            print("📥 Updating local SQLite database...")
            inserted_records = 0

            for item in parsed_items:
                name = item.get("ItemName") or item.get("ItemDescription")
                raw_price = item.get("ItemPrice")
                store_id = str(item.get("StoreID") or "Unknown")

                if not name or raw_price is None:
                    continue

                try:
                    price_val = Decimal(str(raw_price))
                except Exception:
                    continue

                # Fetch or create the master Grocery Item definition
                grocery_item = session.query(DB_GroceryItem).filter_by(name=str(name)).first()
                if not grocery_item:
                    unit_type = self._determine_unit_type(item.get("UnitOfMeasure"))
                    grocery_item = DB_GroceryItem(
                        name=str(name),
                        unit_type=unit_type,
                        size_per_unit=Decimal("1.000"),
                        threshold_qty=1,
                        price_per_unit_avg=price_val,
                        last_purchase_date=datetime.now()
                    )
                    session.add(grocery_item)
                    session.flush()

                # Add store-specific Price Record
                price_record = DB_PriceRecord(
                    grocery_item_id=grocery_item.id,
                    store_name=f"{chain_name}_{store_id}",
                    item_price=price_val,
                    price_date=datetime.now(),
                    is_offer=False
                )
                session.add(price_record)
                inserted_records += 1

            session.commit()
            print(f" Ingestion complete: {inserted_records} SQLite rows saved!")

        except Exception as e:
            session.rollback()
            print(f" Ingestion failed: {e}")
            raise
        finally:
            session.close()

    # def _simulate_daily_price_feed(self):
    #     """
    #     Simulates a full external price feed for every grocery item
    #     currently stored in the database.
    #     """
    #     simulated_feed = []
    #     stores = ["Shufersal", "Rami Levy", "Mega", "Yeynot Bitan"]

    #     session = self.db.get_session()
    #     try:
    #         all_grocery_items = session.query(DB_GroceryItem).all()

    #         for item in all_grocery_items:
    #             # Generate 2-4 price entries for each item.
    #             for _ in range(random.randint(2, 4)):
    #                 base_price = Decimal(
    #                     str(random.uniform(10.0, 30.0))
    #                 ).quantize(Decimal("0.01"))

    #                 price = base_price * Decimal(
    #                     str(random.uniform(0.9, 1.1))
    #                 )

    #                 is_offer = random.random() < 0.15
    #                 offer_details = "Buy 2 Get 1 Free" if is_offer else None

    #                 simulated_feed.append({
    #                     "name": item.name,
    #                     "store": random.choice(stores),
    #                     "price": float(price),
    #                     "is_offer": is_offer,
    #                     "offer_details": offer_details,
    #                 })

    #     finally:
    #         session.close()

    #     return simulated_feed

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

    # def clean_old_records(self, days_to_keep=30):
    #     """Deletes price records older than a specified number of days to keep the database small."""
        
    #     cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
        
    #     deleted_count = self.session.query(DB_PriceRecord)\
    #         .filter(DB_PriceRecord.price_date < cutoff_date)\
    #         .delete(synchronize_session=False)
            
    #     self.session.commit()
    #     print(f"Database Maintenance: Deleted {deleted_count} old price records (older than {days_to_keep} days).")

    def clean_old_records(self, retention_days: int = 14):
        """Deletes price records older than retention_days to prevent database bloat."""
        session = self.db.get_session()
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        try:
            deleted_count = session.query(DB_PriceRecord).filter(
                DB_PriceRecord.price_date < cutoff_date
            ).delete()
            session.commit()
            print(f"🧹 Cleaned up {deleted_count} price records older than {retention_days} days.")
        except Exception as e:
            session.rollback()
            print(f"❌ Prune failed: {e}")
        finally:
            session.close()

def run_volume_assessment(db_manager: DatabaseManager, dump_file_path: str):
    session = db_manager.get_session()
    try:
        # File footprint metrics
        file_size_mb = os.path.getsize(dump_file_path) / (1024 * 1024)
        
        # Database volume metrics
        total_groceries = session.query(func.count(DB_GroceryItem.id)).scalar()
        total_price_records = session.query(func.count(DB_PriceRecord.id)).scalar()
        
        print("\n📊 === Stage A Step 1: Volume Assessment Report ===")
        print(f"📦 Raw Feed File Size:        {file_size_mb:.2f} MB")
        print(f"🏷️ Unique Master Items:       {total_groceries:,}")
        print(f"💰 Branch Price Records:      {total_price_records:,}")
        print(f"📈 Projected Weekly Volume:   ~{(total_price_records * 7):,} rows (for 1 daily file)")
        print("===================================================\n")
    finally:
        session.close()

if __name__ == "__main__":
    manager = PriceIngestionManager()
    manager.ingest_latest_price_file(chain_name="Wolt")
    
    db_mgr = DatabaseManager(db_path="inventory.db")
    # Point to the dump file you just ingested
    parser = SupermarketDataParser()
    latest_file = parser.get_latest_dump_file(chain_folder="Wolt")
    # run_volume_assessment(db_mgr, latest_file)
    ## Run the cleanup (set retention_days as needed, default 14)
    # manager.clean_old_records(retention_days=14)