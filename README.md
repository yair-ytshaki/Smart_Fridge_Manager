# Smart_Fridge_Manager
An intelligent system designed to bridge the gap between computer vision and smart consumerism. It automates the tedious task of tracking household groceries, predicts consumption patterns, and ensures you always get the best price for your next restock.
## Under Construction

### Core Features
Computer Vision Reconciliation: Instead of manual updates, the system processes a "snapshot" of the fridge. It intelligently detects if an item was consumed or simply moved to a different shelf.

Persistent SQLite Database: All data—from grocery definitions to historical stock levels—is stored in a robust SQL database, ensuring no data is lost between sessions.

Automated Price Ingestion: The system simulates the ingestion of official Israeli supermarket price feeds (based on the OpenIsraeliSupermarkets project). It tracks price history and identifies trends.

Smart Shopping List: When stock falls below a custom-defined threshold, the item is automatically added to a persistent shopping list.

Price Optimization: The manager analyzes the shopping list against the latest price records to recommend exactly where to buy each item for the "lucrative" (cheapest) price.

Consumption Analytics: The system calculates how many days it takes to finish a specific product (e.g., "One milk carton every 3.2 days"), allowing for better planning.

### Technical Architecture
Language: Python.

ORM/Database: SQLAlchemy with SQLite for reliable data persistence.

Logic Layers:

InventoryManager: Handles the "brain" of the fridge and stock logic.

PriceIngestionManager: Manages external data feeds and price history.

DatabaseModels: Defines the complex relationships between products, stock, and prices.
