import re
import logging

logger = logging.getLogger(__name__)

class FilterManager:
    # Default exclusions always applied (job postings, etc.)
    DEFAULT_EXCLUSIONS = [
        # Job postings and career pages
        'job opening', 'job opportunity', 'career opportunity', 'now hiring',
        'join our team', 'we are hiring', 'apply now', 'position available',
        'careers at', 'job posting', 'employment opportunity', 'vacancy',
        'job application', 'submit resume', 'submit cv',

        # Link aggregator phrases
        'weekly roundup', 'daily roundup', 'news roundup', 'link roundup',
        'this week in', 'latest links', 'curated links', 'recommended reading',

        # Marketing/advertising language
        'buy now', 'subscribe now', 'sign up today', 'free trial',
        'limited time offer', 'special offer', 'pricing plans',
        'request a demo', 'schedule a demo', 'contact sales',
        'product features', 'why choose us', 'our solutions',

        # Industry-specific exclusions (not relevant to AI safety/alignment research)
        'automotive', 'self-driving car', 'autonomous vehicle',
        'medical imaging', 'medical diagnosis', 'clinical trial', 'surgical', 'patient care',
        'cancer detection', 'tumor', 'radiology', 'pathology',
        'agriculture', 'crop', 'farming', 'livestock',
        'financial trading', 'stock market', 'portfolio management',
        'supply chain', 'logistics', 'warehouse',
        'wireless network', '5G network', 'telecommunications',
        'video game', 'game AI', 'game playing',
        'recommendation system', 'movie recommendation', 'product recommendation',
        'weather forecast', 'climate model'
    ]

    def __init__(self, prompt_text):
        self.required_groups = [] # List of lists (AND of ORs)
        self.excluded_terms = []
        self.default_exclusions = self.DEFAULT_EXCLUSIONS.copy()

        # Validate before parsing
        validation_errors = self._validate_prompt(prompt_text)
        if validation_errors:
            error_msg = "Prompt validation failed:\n" + "\n".join(f"  - {e}" for e in validation_errors)
            logger.error(error_msg)
            raise ValueError(error_msg)

        self._parse_prompt(prompt_text)

    def _validate_prompt(self, text):
        """Validate prompt syntax and return list of errors"""
        errors = []

        if not text or not text.strip():
            errors.append("Prompt is empty")
            return errors

        # Check for balanced parentheses
        open_count = text.count('(')
        close_count = text.count(')')
        if open_count != close_count:
            errors.append(f"Unbalanced parentheses: {open_count} '(' but {close_count} ')'")

        # Check for balanced quotes
        quote_count = text.count('"')
        if quote_count % 2 != 0:
            errors.append(f"Unbalanced quotes: found {quote_count} quotes (must be even)")

        # Check for empty groups
        empty_groups = re.findall(r'\(\s*\)', text)
        if empty_groups:
            errors.append(f"Found {len(empty_groups)} empty group(s): ()")

        # Check for unsupported operators
        unsupported = ['XOR', 'NAND', 'NOR']
        for op in unsupported:
            if op in text.upper():
                errors.append(f"Unsupported operator: {op} (use AND, OR, ANDNOT only)")

        # Check for at least one inclusion term
        if 'ANDNOT' in text:
            include_section = text.split('ANDNOT')[0]
        else:
            include_section = text

        quoted_terms = re.findall(r'"([^"]*)"', include_section)
        if not quoted_terms or all(not t.strip() for t in quoted_terms):
            errors.append("No valid search terms found in quotes (use quotes around terms)")

        # Warn about ANDNOT without inclusions
        if text.strip().startswith('ANDNOT'):
            errors.append("Query starts with ANDNOT (must have inclusion terms first)")

        return errors

    def _parse_prompt(self, text):
        """
        Parse the structured prompt into required groups and exclusions.
        Handles the format: (("A" OR "B") AND ("C" OR "D")) AND ("E" OR "F") ANDNOT ("G")
        """
        text = text.replace('\n', ' ').strip()
        
        # 1. Extract Exclusions (everything after ANDNOT)
        parts = text.split('ANDNOT')
        include_section = parts[0].strip()
        exclude_section = parts[1].strip() if len(parts) > 1 else ""
        
        # User Exclusions: Extract quoted terms
        self.excluded_terms = re.findall(r'"([^"]*)"', exclude_section)
        
        # 2. Extract Inclusion Groups
        # The user's query is basically a series of ( ... OR ... ) blocks joined by AND.
        # We want to find each (...) block and treat its contents as an OR group.
        
        # Logic: Find all groups of terms separated by ' OR ' inside parentheses.
        # We use a non-regex approach to avoid being tripped up by nested parens.
        
        # First, find all terms inside quotes in the include section
        # and then group them based on proximity or the splitting structure.
        
        # REFINED STRATEGY: 
        # The user's prompt is: ((G1) AND (G2)) AND (G3)
        # We can split the include section by ' AND ' to get the major blocks.
        # Then for each block, find the terms inside quotes.
        
        # Normalize and remove the top-level outer parens if they exist
        while include_section.startswith('(') and include_section.endswith(')'):
            # Only remove if they are truly wrapping the whole thing
            # (Check if the open paren matches the final close paren)
            depth = 0
            is_wrapped = True
            for i, char in enumerate(include_section[:-1]):
                if char == '(': depth += 1
                elif char == ')': depth -= 1
                if depth == 0:
                    is_wrapped = False
                    break
            if is_wrapped:
                include_section = include_section[1:-1].strip()
            else:
                break

        # Helper to recursively extract groups joined by AND
        def extract_groups(section):
            section = section.strip()
            # Remove outer parens if they fully wrap the section
            while section.startswith('(') and section.endswith(')'):
                depth = 0
                is_wrapped = True
                for i, char in enumerate(section[:-1]):
                    if char == '(': depth += 1
                    elif char == ')': depth -= 1
                    if depth == 0:
                        is_wrapped = False
                        break
                if is_wrapped:
                    section = section[1:-1].strip()
                else:
                    break
            
            # Look for top-level ANDs in this section
            blocks = []
            current = ""
            depth = 0
            idx = 0
            found_and = False
            while idx < len(section):
                char = section[idx]
                if char == '(': depth += 1
                elif char == ')': depth -= 1
                
                if depth == 0 and section[idx:idx+5] == ' AND ':
                    blocks.append(current.strip())
                    current = ""
                    idx += 5
                    found_and = True
                    continue
                current += char
                idx += 1
            blocks.append(current.strip())
            
            if found_and:
                # Recursively process each sub-block
                for b in blocks:
                    extract_groups(b)
            else:
                # No more ANDs? This is an OR group. Extract all quoted terms.
                terms = re.findall(r'"([^"]*)"', section)
                if terms:
                    self.required_groups.append(terms)

        # Start recursion
        extract_groups(include_section)
            
        logger.info(f"Filter Configured.")
        logger.info(f"  Required Groups: {len(self.required_groups)}")
        for i, group in enumerate(self.required_groups):
            logger.debug(f"    Group {i+1}: {group}")
        logger.info(f"  User Exclusions: {len(self.excluded_terms)}")
        logger.info(f"  Default Exclusions: {len(self.default_exclusions)}")

    def _is_link_aggregator(self, title, abstract):
        """
        Detect if content is primarily a link aggregator page.

        Link aggregators have:
        - Short content with many URLs (high URL density in short text)
        - List-style formatting with minimal narrative
        - Aggregator keywords in title
        - Lack of research indicators

        Research papers may contain URLs but have:
        - Substantial text content (abstracts are typically 150+ words)
        - Research-oriented language and structure
        - URLs primarily in references, not as the main content
        """
        content = (title + ' ' + abstract).lower()
        title_lower = title.lower()

        # Strong indicator: aggregator keywords in title
        aggregator_keywords = [
            'roundup', 'weekly links', 'daily links', 'latest news',
            'this week', 'news digest', 'link collection', 'reading list'
        ]

        if any(keyword in title_lower for keyword in aggregator_keywords):
            # Additional check: short or missing abstract confirms it's a link list
            if not abstract or len(abstract.strip()) < 100:
                return True

        # Analyze URL density only for SHORT content
        # Long research papers can have many URLs in references without being aggregators
        if abstract:
            url_patterns = len(re.findall(r'https?://|www\.|\[.*?\]\(.*?\)', abstract))
            word_count = len(abstract.split())

            # Research papers typically have abstracts of 150+ words
            # Only flag as aggregator if BOTH conditions are true:
            # 1. Short content (< 300 words) - too short for a research abstract
            # 2. High URL density (> 40% of content is URLs)
            if word_count < 300 and url_patterns > 0:
                url_density = url_patterns / word_count

                # Very high URL density in short text = link aggregator
                if url_density > 0.4:
                    logger.debug(f"Link aggregator detected: {url_patterns} URLs in {word_count} words (density: {url_density:.2%})")
                    return True

            # Additional check: If there are MANY URLs (10+) in relatively short text (< 500 words),
            # it's likely an aggregator even if density is lower
            if word_count < 500 and url_patterns >= 10:
                # Check for list-style formatting indicators
                list_indicators = abstract.count('\n-') + abstract.count('\n*') + abstract.count('\n1.')
                if list_indicators >= 5:  # Multiple list items suggests aggregator format
                    logger.debug(f"Link aggregator detected: {url_patterns} URLs with list formatting")
                    return True

            # Check for research content indicators (these suggest NOT an aggregator)
            research_indicators = [
                'method', 'experiment', 'result', 'conclusion', 'analysis',
                'dataset', 'model', 'algorithm', 'evaluation', 'approach',
                'propose', 'demonstrate', 'show that', 'find that', 'performance',
                'accuracy', 'training', 'tested', 'measured', 'compared'
            ]

            research_indicator_count = sum(1 for indicator in research_indicators if indicator in content)

            # If we have multiple research indicators and reasonable length, it's NOT an aggregator
            # even if it has some URLs
            if research_indicator_count >= 3 and word_count >= 150:
                return False

        return False

    def _is_marketing_content(self, title, abstract):
        """
        Detect if content is primarily marketing/advertising.
        Heuristics:
        - Multiple marketing phrases present
        - Call-to-action language
        - Product-focused rather than research-focused
        """
        content = (title + ' ' + abstract).lower()

        # Marketing indicators
        marketing_phrases = [
            'free trial', 'buy now', 'sign up', 'subscribe',
            'request demo', 'contact sales', 'pricing', 'plans',
            'why choose', 'our solution', 'best-in-class',
            'industry-leading', 'cutting-edge solution'
        ]

        # Count marketing phrase occurrences
        marketing_count = sum(1 for phrase in marketing_phrases if phrase in content)

        # If 2+ marketing phrases, likely advertising
        if marketing_count >= 2:
            return True

        # Check title for product announcement patterns
        product_keywords = ['announcing', 'introducing', 'launches', 'unveils']
        solution_keywords = ['solution', 'platform', 'service', 'tool']

        title_lower = title.lower()
        if any(pk in title_lower for pk in product_keywords) and any(sk in title_lower for sk in solution_keywords):
            # Product announcement, but check if it has research content
            if len(abstract.split()) < 150:  # Short abstract = likely just marketing
                return True

        return False

    def _check_term_proximity(self, content, groups, max_distance=3000):
        """
        Check if terms from different groups appear near each other in the text.

        For papers to be relevant, terms from group 1 (e.g., "AI", "LLM") should
        be within max_distance characters of terms from group 2 (e.g., "safety", "alignment").

        This prevents matching papers where "LLM" appears at the top and "alignment"
        appears at the bottom talking about completely different things (e.g., car alignment).

        Args:
            content: The full text to search (lowercase)
            groups: List of term groups (AND of ORs)
            max_distance: Maximum character distance between terms from different groups

        Returns:
            True if terms are in proximity, False otherwise
        """
        if len(groups) < 2:
            # If only one group, no proximity check needed
            return True

        # Find all positions of terms from each group
        group_positions = []
        for group in groups:
            positions = []
            for term in group:
                term_lower = term.lower()
                start = 0
                while True:
                    pos = content.find(term_lower, start)
                    if pos == -1:
                        break
                    positions.append(pos)
                    start = pos + 1
            if positions:
                group_positions.append(sorted(positions))
            else:
                # No term from this group found
                return False

        if len(group_positions) < 2:
            # Need at least 2 groups to check proximity
            return False

        # Check if any term from group 1 is near any term from group 2 (and group 3, etc.)
        # We check pairwise proximity between consecutive groups
        for i in range(len(group_positions) - 1):
            group1_pos = group_positions[i]
            group2_pos = group_positions[i + 1]

            # Check if any position from group1 is within max_distance of any position from group2
            proximity_found = False
            for pos1 in group1_pos:
                for pos2 in group2_pos:
                    if abs(pos1 - pos2) <= max_distance:
                        proximity_found = True
                        break
                if proximity_found:
                    break

            if not proximity_found:
                return False

        return True

    def is_relevant(self, paper_meta):
        """
        Determine if a paper is relevant based on:
        1. Default exclusions (job postings, link aggregators, marketing)
        2. User-defined exclusions (ANDNOT terms)
        3. Content analysis (link aggregator detection, marketing detection)
        4. User-defined inclusions (AND/OR terms)
        5. Proximity check (terms from different groups must be near each other)
        """
        # Combine title and abstract for searching
        title = paper_meta.get('title', '')
        abstract = paper_meta.get('abstract', '')
        if not title: return False

        content = (title + ' ' + abstract).lower()

        # 1. Check Default Exclusions (job postings, etc.)
        for term in self.default_exclusions:
            if term.lower() in content:
                logger.debug(f"Filtered (default): '{title[:40]}...' contains '{term}'")
                return False

        # 2. Check Link Aggregator
        if self._is_link_aggregator(title, abstract):
            logger.debug(f"Filtered (link aggregator): '{title[:40]}...'")
            return False

        # 3. Check Marketing Content
        if self._is_marketing_content(title, abstract):
            logger.debug(f"Filtered (marketing): '{title[:40]}...'")
            return False

        # 4. Check User Exclusions (from ANDNOT)
        for term in self.excluded_terms:
            if term.lower() in content:
                logger.debug(f"Filtered (user): '{title[:40]}...' contains excluded '{term}'")
                return False

        # 5. Check Inclusions (AND of ORs)
        for group in self.required_groups:
            # Must match at least one term in this group
            match_found = False
            for term in group:
                if term.lower() in content:
                    match_found = True
                    break

            if not match_found:
                logger.debug(f"Filtered (inclusion): '{title[:40]}...' missing term from group {group}")
                return False

        # 6. Check Proximity (terms from different groups should be near each other)
        # Relaxed distance to allow more papers through (increased from 3000 to 10000)
        if not self._check_term_proximity(content, self.required_groups, max_distance=10000):
            logger.debug(f"Filtered (proximity): '{title[:40]}...' terms too far apart")
            return False

        return True
