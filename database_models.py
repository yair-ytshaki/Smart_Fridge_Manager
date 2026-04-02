"""SQLAlchemy is an ORM (Object Relational Mapper). It acts as a middleman between your Python code and the database.
Instead of writing raw SQL strings like "SELECT * FROM users", you can just work with Python classes and objects.""" 

from sqlalchemy import create_engine, Column, Integer, String, Numeric, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
from decimal import Decimal
import enum

# --- 1. Base Setup ---
Base = declarative_base()

# --- 2. Enums for Database Mapping ---
class UnitType(enum.Enum):
    KILOGRAMS = "kg"
    LITERS = "liter"
    UNITS = "unit"

class ItemStatus(enum.Enum):
    IN_STOCK = "In Stock"
    LOW_STOCK = "Low Stock"
    OUT_OF_STOCK = "Out Of Stock"
    EXPIRED = "Expired"

# --- 3. Database Table Definitions ---

class DB_GroceryItem(Base):
    """Maps to the 'grocery_items' table. Defines the product itself."""
    __tablename__ = 'grocery_items'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    unit_type = Column(Enum(UnitType), nullable=False) 
    size_per_unit = Column(Numeric(precision=10, scale=3), nullable=False)
    threshold_qty = Column(Integer, default=1)
    price_per_unit_avg = Column(Numeric(precision=10, scale=2), default=Decimal('0.00')) 
    last_purchase_date = Column(DateTime, default=datetime.now)
    # NEW COLUMN: Expiration Date
    expiration_date = Column(DateTime, nullable=True) # Date the item expires

    # Relationships
    inventory_items = relationship("DB_InventoryItem", back_populates="grocery_ref")
    price_records = relationship("DB_PriceRecord", back_populates="grocery_ref")
    # New: Relationship to the Shopping List Item that refers to this Grocery Item
    shopping_list_item = relationship("DB_ShoppingListItem", back_populates="grocery_ref_item", uselist=False)

    def __repr__(self):
        return f"<GroceryItem(name='{self.name}', unit='{self.unit_type.value}')>"

class DB_InventoryItem(Base):
    """Maps to the 'inventory_items' table. Defines specific stock in the fridge."""
    __tablename__ = 'inventory_items'
    id = Column(Integer, primary_key=True)
    grocery_item_id = Column(Integer, ForeignKey('grocery_items.id')) 
    current_quantity = Column(Numeric(precision=10, scale=3), default=Decimal('0.00'))
    location_tag = Column(String)
    status = Column(Enum(ItemStatus), default=ItemStatus.IN_STOCK)
    last_scan_date = Column(DateTime, default=datetime.now)

    # Relationship
    grocery_ref = relationship("DB_GroceryItem", back_populates="inventory_items")
    
    def __repr__(self):
        return f"<InventoryItem(name='{self.grocery_ref.name}', qty={self.current_quantity})>"


class DB_PriceRecord(Base):
    """Maps to the 'price_records' table. Stores historical/current price and offer details."""
    __tablename__ = 'price_records'
    id = Column(Integer, primary_key=True)
    grocery_item_id = Column(Integer, ForeignKey('grocery_items.id'), nullable=False) 
    store_name = Column(String, nullable=False)
    item_price = Column(Numeric(precision=10, scale=2), nullable=False)
    price_date = Column(DateTime, default=datetime.now)
    is_offer = Column(Boolean, default=False)
    offer_details = Column(String, nullable=True)

    # Relationship
    grocery_ref = relationship("DB_GroceryItem", back_populates="price_records")
    
    def __repr__(self):
        return f"<PriceRecord(store='{self.store_name}', price={self.item_price})>"

class DB_ShoppingListItem(Base):
    """Maps to the 'shopping_list' table. Tracks items identified as LOW_STOCK."""
    __tablename__ = 'shopping_list'
    id = Column(Integer, primary_key=True)
    # unique=True prevents the same item from being added multiple times
    grocery_item_id = Column(Integer, ForeignKey('grocery_items.id'), unique=True, nullable=False) 
    date_added = Column(DateTime, default=datetime.now)
    suggested_qty = Column(Numeric(precision=10, scale=3), default=Decimal('1.00')) 

    # Relationship
    grocery_ref_item = relationship("DB_GroceryItem", back_populates="shopping_list_item")
    
    def __repr__(self):
        return f"<ShoppingListItem(name='{self.grocery_ref_item.name}', qty={self.suggested_qty})>"


# --- 4. Database Engine and Session Management ---

class DatabaseManager:
    # ... (remains the same) ...
    def __init__(self, db_path='inventory.db'):
        self.engine = create_engine(f'sqlite:///{db_path}')
        # Create tables if they don't exist (this creates the new tables too)
        Base.metadata.create_all(self.engine) 
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def get_session(self):
        return self.session