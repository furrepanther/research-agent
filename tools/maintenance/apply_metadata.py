
import sqlite3
import json
import os
import sys

# Add project root to path
sys.path.append("f:/Github/research-agent")

from src.utils import generate_stable_hash, normalize_url, get_config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_metadata_findings(findings_path):
    db_path = "R:/My Drive/03 Research Papers/metadata.db"
    
    if not os.path.exists(findings_path):
        print(f"Findings file {findings_path} not found.")
        return

    with open(findings_path, "r") as f:
        findings = json.load(f)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"Applying metadata from {findings_path} to records...")
    
    updates = 0
    # Normalize findings into a list of dicts
    items = []
    if isinstance(findings, dict):
        for k, v in findings.items():
            if isinstance(v, str):
                items.append({'id': int(k), 'source_url': v})
            else:
                items.append(v)
    else:
        items = findings

    for item in items:
        internal_id = item.get('id')
        source_url = item.get('source_url')
        
        # If item doesn't have source_url but has arxiv/doi (from divine_metadata.py)
        if not source_url:
            arxiv_id = item.get('arxiv')
            doi = item.get('doi')
            if arxiv_id:
                source_url = f"https://arxiv.org/abs/{arxiv_id}"
            elif doi:
                source_url = f"https://doi.org/{doi}"
        
        if internal_id and source_url:
            # Generate new hashes
            p_hash = generate_stable_hash(normalize_url(source_url))
            
            try:
                cursor.execute("""
                    UPDATE papers SET 
                        source_url = ?, 
                        paper_hash = ? 
                    WHERE id = ?
                """, (source_url, p_hash, internal_id))
                updates += 1
            except sqlite3.IntegrityError as e:
                # Collision! find the master record
                cursor.execute("SELECT id, title, source, source_url FROM papers WHERE paper_hash = ?", (p_hash,))
                master = cursor.fetchone()
                if master:
                    master_id = master[0]
                    logger.info(f"  - Collision: Paper {internal_id} matches URL of ID {master_id}. Merging...")
                    
                    # Get current record data
                    cursor.execute("SELECT source, source_url FROM papers WHERE id = ?", (internal_id,))
                    current = cursor.fetchone()
                    
                    # Merge sources and URLs
                    new_sources = list(set([s.strip() for s in master[2].split(',')] + [s.strip() for s in current[0].split(',')]))
                    new_urls = list(set([u.strip() for u in master[3].split(',')] + [u.strip() for u in current[1].split(',')]))
                    
                    cursor.execute("UPDATE papers SET source = ?, source_url = ? WHERE id = ?", 
                                   (", ".join(new_sources), ", ".join(new_urls), master_id))
                    
                    # Delete the duplicate
                    cursor.execute("DELETE FROM papers WHERE id = ?", (internal_id,))
                    print(f"  Merged {internal_id} into {master_id} (URL Collision)")
            
    conn.commit()
    conn.close()
    print(f"Successfully processed records. {updates} updated.")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "metadata_findings.json"
    apply_metadata_findings(path)
