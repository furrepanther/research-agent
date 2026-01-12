import re
import logging

logger = logging.getLogger(__name__)

class FilterManager:
    def __init__(self, prompt_text):
        self.required_groups = [] # List of lists (AND of ORs)
        self.excluded_terms = []
        self._parse_prompt(prompt_text)

    def _parse_prompt(self, text):
        text = text.replace('\n', ' ').strip()
        
        # Split inclusions and exclusions
        parts = text.split('ANDNOT')
        include_section = parts[0].strip()
        exclude_section = parts[1].strip() if len(parts) > 1 else ""
        
        # Parse Exclusions: Treat as a single OR group (any match = fail)
        self.excluded_terms = re.findall(r'"([^"]*)"', exclude_section)
        
        # Parse Inclusions: ("A") AND ("B" OR "C")
        # Regex to find (...) blocks. 
        # Note: This assumes the prompt format is strictly ("...") AND ("...")
        group_matches = re.findall(r'\(([^)]+)\)', include_section)
        
        if not group_matches and include_section:
            # Simple string fallback: treated as a single OR group of all words or just the whole string?
            # Standard: Treat the whole inclusion section as one OR group if it doesn't have parens
            self.required_groups.append([include_section.strip('"')])
        else:
            for group_str in group_matches:
                # Split by OR
                terms = group_str.split(' OR ')
                # Clean quotes
                terms = [t.strip().strip('"') for t in terms]
                self.required_groups.append(terms)
            
        logger.info(f"Filter Configured.")
        logger.info(f"  Required Groups: {len(self.required_groups)}")
        logger.info(f"  Excluded Terms: {len(self.excluded_terms)}")

    def is_relevant(self, paper_meta):
        # Combine title and abstract for searching
        title = paper_meta.get('title', '')
        abstract = paper_meta.get('abstract', '')
        if not title: return False
        
        content = (title + ' ' + abstract).lower()
        
        # 1. Check Exclusions
        for term in self.excluded_terms:
            if term.lower() in content:
                # logger.debug(f"Filtered: '{title[:30]}...' contains excluded '{term}'")
                return False
                
        # 2. Check Inclusions (AND of ORs)
        for group in self.required_groups:
            # Must match at least one term in this group
            match_found = False
            for term in group:
                if term.lower() in content:
                    match_found = True
                    break
            
            if not match_found:
                # logger.debug(f"Filtered: '{title[:30]}...' missing term from group {group}")
                return False
                
        return True
