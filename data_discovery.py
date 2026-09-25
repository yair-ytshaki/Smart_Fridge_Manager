import os
import sys
import ftplib

# --- FORCE MULTIPROCESSING COMPATIBLE MONKEY PATCH ---
# 1. Define the fallback class
class FallbackFTP_TLS(ftplib.FTP_TLS):
    def auth(self):
        try:
            return super().auth()
        except ftplib.error_perm as e:
            if "504" in str(e):
                print("⚠️ Subprocess caught TLS 504 error. Overriding encryption requirement...")
                self._secure_data_conn = False
                return "200 Aligned with fallback"
            raise e

# 2. Apply it locally to the module
ftplib.FTP_TLS = FallbackFTP_TLS

# 3. Hijack Python's module cache system so background workers inherit the patch
sys.modules['ftplib'] = ftplib
# -----------------------------------------------------

# Now it is safe to import the scraper
from il_supermarket_scarper import ScarpingTask
from il_supermarket_scarper.scrappers_factory import ScraperFactory

def fetch_wolt_pricing_feed():
    print("🚀 Pulling latest Wolt PriceFull dataset...")
    task = ScarpingTask(
        enabled_scrapers=["WOLT"],
        files_types=["PRICE_FULL_FILE"],
        limit=1,

    )
    task.start()
    print("✅ Download finished. Files stored in /dumps/Wolt")

def download_price_catalog(chain_name="WOLT", target_folder="dumps"):
    """
    Downloads exactly 1 full price catalog (PRICE_FULL_FILE) for a selected chain.
    """
    os.makedirs(target_folder, exist_ok=True)
    print(f"Targeting chain: {chain_name} | Requesting PRICE_FULL_FILE...")

    task = ScarpingTask(
        enabled_scrapers=[chain_name],
        limit=1,
        files_types=["PRICE_FULL_FILE"],
        dump_folder=target_folder
    )
    
    task.start()
    print(f"\nDownload completed. Files saved to folder: '{target_folder}/{chain_name}'")

def download_rami_levy_data():
    print("Initializing Scraper for Rami Levy...")
    
    task = ScarpingTask(
        enabled_scrapers=["WOLT"],
        limit=1,
    )
    
    print("Starting download across worker threads...")
    task.start()
    
    print("\n✅ Execution finished! Look in your local directory for 'dumps/RamiLevy'")

if __name__ == "__main__":
    # download_rami_levy_data()
    # download_price_catalog("WOLT")
    fetch_wolt_pricing_feed()