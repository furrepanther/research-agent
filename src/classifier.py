"""
Paper classification module for categorizing research papers.
"""

import re

def classify_paper(title, abstract, author=""):
    """
    Classify a paper into a category based on keywords in title and abstract.
    
    Special handling:
    - Papers by Steven Byrnes go into "Byrnes" folder
    
    Args:
        title: Paper title
        abstract: Paper abstract
        author: Paper author(s)
    
    Returns:
        Category name as string
    """
    # SPECIAL CASE: Steven Byrnes papers go into dedicated folder
    if author and "steven byrnes" in author.lower():
        return "Byrnes"
    
    text = (title + " " + abstract).lower()
    
    # 1. Red Teaming
    if any(k in text for k in ["red team", "jailbreak", "prompt injection", "adversarial", "attack", "exploit", "trojan", "backdoor"]):
        return "Red Teaming"
        
    # 2. Alignment Research
    if any(k in text for k in ["alignment", "constitutional ai", "rlhf", "dpo", "preference optimization", "value learning", "reward modeling"]):
        return "Alignment Research"
        
    # 3. Agentic AI
    if any(k in text for k in ["agent", "multi-agent", "autonomous system", "autonomy", "planning", "tool use"]):
        return "Agentic AI"
        
    # 4. Consciousness / Personhood
    if any(k in text for k in ["consciousness", "personhood", "sentience", "qualia", "subjective experience", "persona ", "personality"]):
        return "Consciousness"
        
    # 5. Futures
    if any(k in text for k in ["future", "forecast", "predict", "trajectory", "scenario", "long-term", "existential", "x-risk"]):
        return "Futures"
        
    # 6. Taxonomy
    if any(k in text for k in ["taxonomy", "survey", "landscape", "review", "framework", "categorization", "overview"]):
        return "Taxonomy Research"
        
    # 7. Default
    return "AI Safety (Unspecified)"
