"""Test content filtering for job postings, link aggregators, and marketing"""
from src.filter import FilterManager

def test_content_filtering():
    print("=" * 70)
    print("Testing Enhanced Content Filtering")
    print("=" * 70)

    # Create a basic filter for testing
    test_prompt = '("AI" OR "machine learning") AND ("safety")'
    filter_mgr = FilterManager(test_prompt)

    # Test 1: Job Posting Detection
    print("\n1. Testing Job Posting Detection:")
    job_postings = [
        {
            'title': 'Job Opening: AI Safety Researcher',
            'abstract': 'We are hiring a senior researcher to join our team. Apply now!'
        },
        {
            'title': 'Career Opportunity in Machine Learning Safety',
            'abstract': 'Join our team of experts. Submit your resume today.'
        },
        {
            'title': 'Now Hiring: AI Alignment Engineer',
            'abstract': 'Position available for experienced AI safety professional.'
        },
        {
            'title': 'AI Safety Careers at OpenAI',
            'abstract': 'Explore employment opportunities on our careers page.'
        }
    ]

    passed = 0
    for paper in job_postings:
        result = filter_mgr.is_relevant(paper)
        status = "[PASS]" if not result else "[FAIL]"
        print(f"   {status} '{paper['title'][:50]}...' - Filtered: {not result}")
        if not result:
            passed += 1

    print(f"   Job postings filtered: {passed}/{len(job_postings)}")
    if passed == len(job_postings):
        print("   [PASS] All job postings correctly filtered")
    else:
        print("   [FAIL] Some job postings not filtered")

    # Test 2: Link Aggregator Detection
    print("\n2. Testing Link Aggregator Detection:")
    link_aggregators = [
        {
            'title': 'AI Safety Weekly Roundup',
            'abstract': 'Links to recent papers and articles.'
        },
        {
            'title': 'This Week in AI Safety',
            'abstract': ''  # Empty abstract, typical of link lists
        },
        {
            'title': 'AI Safety News Digest - Latest Links',
            'abstract': 'See https://link1.com https://link2.com https://link3.com for more'
        },
        {
            'title': 'Curated Links: Machine Learning Safety',
            'abstract': 'Collection of recent safety research. Visit www.example.com'
        }
    ]

    passed = 0
    for paper in link_aggregators:
        result = filter_mgr.is_relevant(paper)
        status = "[PASS]" if not result else "[FAIL]"
        print(f"   {status} '{paper['title'][:50]}...' - Filtered: {not result}")
        if not result:
            passed += 1

    print(f"   Link aggregators filtered: {passed}/{len(link_aggregators)}")
    if passed >= 3:  # Allow 1 false negative
        print("   [PASS] Most link aggregators correctly filtered")
    else:
        print("   [FAIL] Too many link aggregators not filtered")

    # Test 3: Marketing Content Detection
    print("\n3. Testing Marketing Content Detection:")
    marketing_content = [
        {
            'title': 'Announcing Our New AI Safety Platform',
            'abstract': 'Sign up today for a free trial. Best-in-class solution for your needs.'
        },
        {
            'title': 'Introducing AI Safety Tool - Request a Demo',
            'abstract': 'Contact sales to learn more about our pricing plans.'
        },
        {
            'title': 'Why Choose Our Machine Learning Safety Solution',
            'abstract': 'Industry-leading platform. Subscribe now!'
        },
        {
            'title': 'New AI Safety Service Launches',
            'abstract': 'Buy now and get special offer pricing.'
        }
    ]

    passed = 0
    for paper in marketing_content:
        result = filter_mgr.is_relevant(paper)
        status = "[PASS]" if not result else "[FAIL]"
        print(f"   {status} '{paper['title'][:50]}...' - Filtered: {not result}")
        if not result:
            passed += 1

    print(f"   Marketing content filtered: {passed}/{len(marketing_content)}")
    if passed == len(marketing_content):
        print("   [PASS] All marketing content correctly filtered")
    else:
        print("   [FAIL] Some marketing content not filtered")

    # Test 4: Legitimate Content (Should NOT be filtered)
    print("\n4. Testing Legitimate Research Content (should pass):")
    legitimate_papers = [
        {
            'title': 'Machine Learning Safety: A Survey',
            'abstract': 'This paper surveys recent advances in AI safety research, covering alignment techniques and risk mitigation strategies.'
        },
        {
            'title': 'Novel Approach to AI Safety Through Alignment',
            'abstract': 'We propose a new method for ensuring machine learning safety through alignment with human values during training.'
        },
        {
            'title': 'Evaluating Safety in Large Language Models',
            'abstract': 'This work presents comprehensive safety benchmarks for evaluating AI systems across multiple risk categories.'
        },
        {
            'title': 'AI Safety Through Interpretability',
            'abstract': 'By improving model interpretability, we can better understand and mitigate potential safety issues in machine learning systems.'
        }
    ]

    passed = 0
    for paper in legitimate_papers:
        result = filter_mgr.is_relevant(paper)
        status = "[PASS]" if result else "[FAIL]"
        print(f"   {status} '{paper['title'][:50]}...' - Passed: {result}")
        if result:
            passed += 1

    print(f"   Legitimate papers passed: {passed}/{len(legitimate_papers)}")
    if passed == len(legitimate_papers):
        print("   [PASS] All legitimate content correctly passed")
    else:
        print("   [FAIL] Some legitimate content incorrectly filtered")

    # Test 5: Edge Cases
    print("\n5. Testing Edge Cases:")

    # Case 1: Paper mentioning jobs in research context (should pass)
    edge_case_1 = {
        'title': 'AI Safety Research Creates New Jobs in Tech',
        'abstract': 'This research explores how advancements in AI safety are creating employment opportunities and shaping the job market, analyzing 500 positions.'
    }
    result1 = filter_mgr.is_relevant(edge_case_1)
    print(f"   Research about jobs: {result1} - {'[PASS]' if result1 else '[FAIL]'}")

    # Case 2: Product announcement with substantial research content (should pass)
    edge_case_2 = {
        'title': 'Introducing Constitutional AI: A Research-Driven Approach',
        'abstract': 'We present Constitutional AI, a novel training method based on extensive research into AI alignment. This paper details our experimental methodology, results from 100+ model variants, theoretical foundations, and empirical validation across multiple benchmarks. Our approach demonstrates significant improvements in safety metrics while maintaining performance.'
    }
    result2 = filter_mgr.is_relevant(edge_case_2)
    print(f"   Product with research: {result2} - {'[PASS]' if result2 else '[FAIL]'}")

    # Case 3: Blog post with links but substantial content (borderline)
    edge_case_3 = {
        'title': 'Recent Advances in AI Safety: Analysis and Commentary',
        'abstract': 'This comprehensive analysis examines five recent papers on AI alignment, providing detailed technical commentary on methodology, results, and implications for the field. We discuss convergent approaches and highlight key open problems.'
    }
    result3 = filter_mgr.is_relevant(edge_case_3)
    print(f"   Analytical commentary: {result3} - {'[PASS]' if result3 else '[FAIL]'}")

    # Case 4: Marketing language but research content (should pass if abstract is long enough)
    edge_case_4 = {
        'title': 'Best Practices for AI Safety Implementation',
        'abstract': 'Drawing from 50+ interviews with AI safety researchers and analysis of 200+ deployed systems, this paper identifies industry-leading practices for implementing safety measures in machine learning pipelines. We present a comprehensive framework validated across multiple organizations and domains.'
    }
    result4 = filter_mgr.is_relevant(edge_case_4)
    print(f"   'Best practices' research: {result4} - {'[PASS]' if result4 else '[FAIL]'}")

    # Test 6: Default Exclusions Count
    print("\n6. Testing Default Exclusions Configuration:")
    print(f"   Total default exclusions: {len(filter_mgr.default_exclusions)}")
    print(f"   Job posting terms: {sum(1 for t in filter_mgr.default_exclusions if 'job' in t or 'career' in t or 'hiring' in t)}")
    print(f"   Link aggregator terms: {sum(1 for t in filter_mgr.default_exclusions if 'link' in t or 'roundup' in t)}")
    print(f"   Marketing terms: {sum(1 for t in filter_mgr.default_exclusions if 'buy' in t or 'subscribe' in t or 'demo' in t or 'pricing' in t)}")

    if len(filter_mgr.default_exclusions) >= 20:
        print("   [PASS] Comprehensive default exclusions configured")
    else:
        print("   [WARN] May need more default exclusions")

    # Test 7: Integration with User Exclusions
    print("\n7. Testing Integration with User Exclusions:")
    combined_prompt = '("AI" OR "machine learning") AND ("safety") ANDNOT ("automotive")'
    combined_filter = FilterManager(combined_prompt)

    # Paper with user exclusion term
    auto_paper = {
        'title': 'Machine Learning Safety in Automotive Systems',
        'abstract': 'This paper explores AI safety considerations for self-driving cars.'
    }
    result_auto = combined_filter.is_relevant(auto_paper)
    print(f"   User exclusion (automotive): Filtered={not result_auto} - {'[PASS]' if not result_auto else '[FAIL]'}")

    # Paper with default exclusion term (job posting)
    job_paper = {
        'title': 'AI Safety Researcher - Join Our Team',
        'abstract': 'We are hiring for a position in machine learning safety research.'
    }
    result_job = combined_filter.is_relevant(job_paper)
    print(f"   Default exclusion (job): Filtered={not result_job} - {'[PASS]' if not result_job else '[FAIL]'}")

    # Paper with neither exclusion (should pass)
    clean_paper = {
        'title': 'Machine Learning Safety: New Techniques',
        'abstract': 'We present novel techniques for improving AI safety in language model deployment and training.'
    }
    result_clean = combined_filter.is_relevant(clean_paper)
    print(f"   No exclusions: Passed={result_clean} - {'[PASS]' if result_clean else '[FAIL]'}")

    print("\n" + "=" * 70)
    print("Content Filtering Testing Complete")
    print("=" * 70)
    print("\nNew Filtering Capabilities:")
    print("  + Job postings and career announcements")
    print("  + Link aggregator pages and roundups")
    print("  + Marketing/advertising content")
    print("  + Product-focused pages with minimal research")
    print("  + 25+ default exclusion terms always applied")
    print("  + Preserves legitimate research content")
    print("  + Works alongside user ANDNOT exclusions")
    print("=" * 70)

if __name__ == "__main__":
    test_content_filtering()
