
import arxiv
import logging

def test_query():
    client = arxiv.Client()
    
    # Original query template from prompt
    raw_query = '(("AI" OR "Artificial Intelligence") AND ("LLM" OR "Language Model")) AND ("Agentic" OR "AI Safety" OR "AI Alignment") ANDNOT ("medicine" OR "medical")'
    
    # Variant 1: Original
    print(f"Testing Original: {raw_query}")
    try:
        search1 = arxiv.Search(query=raw_query, max_results=10)
        results1 = list(client.results(search1))
        print(f"Results Count (ANDNOT): {len(results1)}")
    except Exception as e:
        print(f"Error Original: {e}")

    # Variant 2: Fixed AND NOT
    fixed_query = raw_query.replace("ANDNOT", "AND NOT")
    print(f"\nTesting Fixed: {fixed_query}")
    try:
        search2 = arxiv.Search(query=fixed_query, max_results=10)
        results2 = list(client.results(search2))
        print(f"Results Count (AND NOT): {len(results2)}")
    except Exception as e:
        print(f"Error Fixed: {e}")

if __name__ == "__main__":
    test_query()
