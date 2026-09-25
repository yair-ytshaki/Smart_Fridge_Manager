import os
import glob
import gzip
import xml.etree.ElementTree as ET

class SupermarketDataParser:
    def __init__(self, dumps_dir="dumps"):
        self.dumps_dir = dumps_dir

    def get_latest_dump_file(self, chain_folder="Wolt", file_pattern="*"):
        """Locates the newest scraped XML or XML.GZ file inside the dumps directory."""
        search_path = os.path.join(self.dumps_dir, chain_folder, "**", file_pattern)
        found_files = [
            f for f in glob.glob(search_path, recursive=True)
            if os.path.isfile(f) and not f.endswith(".json")
        ]
        
        if not found_files:
            # Fallback across the entire dumps folder
            found_files = [
                f for f in glob.glob(os.path.join(self.dumps_dir, "**", file_pattern), recursive=True)
                if os.path.isfile(f) and not f.endswith(".json")
            ]

        if not found_files:
            raise FileNotFoundError(f"No dump files found matching pattern '{file_pattern}' in '{self.dumps_dir}'.")

        return max(found_files, key=os.path.getmtime)

    def parse_latest_output(self, chain_folder="Wolt") -> list:
        """Finds the newest price file and extracts Item records directly."""
        target_file = self.get_latest_dump_file(chain_folder=chain_folder)
        print(f"📖 Reading XML data directly from: {target_file}")

        open_fn = gzip.open if target_file.endswith(".gz") else open
        items = []

        with open_fn(target_file, "rb") as f:
            tree = ET.parse(f)
            root = tree.getroot()

            # Global chain & store context if available in root header
            chain_id = root.findtext(".//ChainId") or root.findtext(".//ChainID") or ""
            store_id = root.findtext(".//StoreId") or root.findtext(".//StoreID") or "001"

            # Parse all <Item> or <Product> tags across the tree
            for item_elem in root.iter("Item"):
                name = item_elem.findtext("ItemName") or item_elem.findtext("ItemDescription")
                price = item_elem.findtext("ItemPrice")
                code = item_elem.findtext("ItemCode")
                unit = item_elem.findtext("UnitOfMeasure") or item_elem.findtext("UnitQty")
                item_store = item_elem.findtext("StoreID") or store_id

                if name and price:
                    items.append({
                        "ItemName": name.strip(),
                        "ItemPrice": price.strip(),
                        "ItemCode": code.strip() if code else None,
                        "UnitOfMeasure": unit.strip() if unit else None,
                        "StoreID": item_store.strip()
                    })

        print(f" Extracted {len(items)} items from XML.")
        return items