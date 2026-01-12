import os
import pandas as pd
from src.utils import logger

class ExportManager:
    def __init__(self, config):
        self.config = config
        self.export_dir = config.get("export_dir", "exports")
        self.filename = config.get("export_filename", "research_log.xlsx")
        self.full_path = os.path.join(self.export_dir, self.filename)
        self._ensure_dir()

    def _ensure_dir(self):
        os.makedirs(self.export_dir, exist_ok=True)

    def export_papers(self, papers):
        """
        papers: list of dicts (unsynced papers)
        """
        if not papers:
            return []

        # Convert to DataFrame
        new_df = pd.DataFrame(papers)
        
        # Select and Reorder columns for cleaner output
        cols = ["id", "title", "published_date", "authors", "abstract", "source_url", "pdf_path", "downloaded_date"]
        # Ensure all cols exist
        for c in cols:
            if c not in new_df.columns:
                new_df[c] = ""
        new_df = new_df[cols]

        try:
            if os.path.exists(self.full_path):
                # Load existing
                existing_df = pd.read_excel(self.full_path)
                
                # Filter duplicates just in case basic DB check failed or file was modified manually
                # We use 'id' as unique key
                combined = pd.concat([existing_df, new_df])
                combined = combined.drop_duplicates(subset=['id'], keep='first') # Keep existing
                
                # Check what was actually added (ids in new_df that are now in combined)
                # Actually proper logic:
                # 1. We only want to append unique new items.
                # 2. But we passed in 'papers' which DB says are not exported.
                # 3. So we just append them. But reading existing helps prevent double write if DB desyncs.
                
                # Let's trust input but filter against existing file IDs
                existing_ids = set(existing_df['id'].astype(str))
                to_append = new_df[~new_df['id'].astype(str).isin(existing_ids)]
                
                if to_append.empty:
                    logger.info("No new unique papers to export to Excel.")
                    return [p['id'] for p in papers] # Mark them as synced so we don't try again? Or maybe not?
                    # If they are in Excel but not marked in DB, we should mark them in DB.
                
                # Append
                with pd.ExcelWriter(self.full_path, mode='a', if_sheet_exists='overlay', engine='openpyxl') as writer:
                    # Actually pd.ExcelWriter 'overlay' with openpyxl can be tricky for just appending rows.
                    # Safest is read all, concat, write all. For reasonable sizes (<100k rows) this is fine.
                    final_df = pd.concat([existing_df, to_append], ignore_index=True)
                    final_df.to_excel(writer, index=False)
                    
                exported_ids = to_append['id'].tolist()
                # Also include IDs that were already in Excel (so we update DB state)
                already_in_excel = new_df[new_df['id'].astype(str).isin(existing_ids)]['id'].tolist()
                return exported_ids + already_in_excel

            else:
                # Create new
                new_df.to_excel(self.full_path, index=False)
                logger.info(f"Created new Excel file at {self.full_path}")
                return new_df['id'].tolist()
                
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            return []
