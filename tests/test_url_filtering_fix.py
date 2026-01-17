"""
Test to verify that research papers with URLs are NOT incorrectly filtered as link aggregators.

This addresses the issue where legitimate research papers containing references, citations,
or dataset links were being incorrectly classified as "link aggregators" and filtered out.
"""

from src.filter import FilterManager

def test_research_papers_with_urls():
    print("=" * 70)
    print("Testing: Research Papers with URLs Should NOT Be Filtered")
    print("=" * 70)

    # Create filter for AI safety research
    test_prompt = '("AI" OR "machine learning") AND ("safety" OR "alignment")'
    filter_mgr = FilterManager(test_prompt)

    # Test Case 1: Research paper with dataset URL
    print("\n1. Research paper with dataset URL:")
    paper1 = {
        'title': 'Evaluating AI Safety Through Comprehensive Benchmarks',
        'abstract': '''We propose a new benchmark for evaluating AI safety in large language models.
        Our methodology involves testing 50 models across 10 safety dimensions including truthfulness,
        harmful content generation, and alignment with human values. We conducted 10,000 experiments
        and our dataset is available at https://github.com/research/safety-benchmark. Results show
        that current models exhibit varying levels of safety depending on the evaluation criteria.
        We demonstrate significant performance differences and propose improvements based on our findings.'''
    }
    result1 = filter_mgr.is_relevant(paper1)
    print(f"   Title: '{paper1['title']}'")
    print(f"   Abstract length: {len(paper1['abstract'].split())} words")
    print(f"   URLs found: 1")
    print(f"   Result: {'PASSED [+]' if result1 else 'FILTERED [-]'}")
    print(f"   [{'PASS' if result1 else 'FAIL'}] - Should pass (legitimate research)")

    # Test Case 2: Research paper with multiple reference URLs
    print("\n2. Research paper with multiple reference URLs:")
    paper2 = {
        'title': 'Machine Learning Safety: A Comprehensive Survey',
        'abstract': '''This survey examines recent advances in machine learning safety research.
        We review over 200 papers published between 2020-2024, analyzing methodologies, datasets,
        and evaluation approaches. Key areas covered include alignment techniques, robustness testing,
        adversarial attacks, and interpretability methods. Our analysis reveals that most approaches
        focus on specific safety dimensions. We identify gaps in current research and propose future
        directions. Code examples available at https://github.com/safety-survey and supplementary
        materials at https://safety-research.org/supplement. This work builds on prior surveys
        (see www.arxiv.org/abs/2301.12345) and contributes a unified framework for understanding
        the landscape of AI safety research.'''
    }
    result2 = filter_mgr.is_relevant(paper2)
    print(f"   Title: '{paper2['title']}'")
    print(f"   Abstract length: {len(paper2['abstract'].split())} words")
    print(f"   URLs found: 3")
    print(f"   Result: {'PASSED [+]' if result2 else 'FILTERED [-]'}")
    print(f"   [{'PASS' if result2 else 'FAIL'}] - Should pass (research with references)")

    # Test Case 3: Research paper with arXiv links
    print("\n3. Research paper with arXiv and DOI links:")
    paper3 = {
        'title': 'Neural Network Alignment Through Iterative Refinement',
        'abstract': '''We propose a novel approach to AI alignment using iterative refinement techniques.
        Our method demonstrates improved safety metrics across multiple benchmarks. The model architecture
        is based on transformer networks with specialized attention mechanisms. We trained on 50B tokens
        and evaluated performance on 15 safety datasets. Results show 23% improvement over baseline methods.
        Our approach extends the work in https://arxiv.org/abs/2203.12345 and incorporates techniques
        from https://doi.org/10.1234/safety.2024 while addressing limitations identified in previous
        studies. The experimental methodology, full results, and ablation studies are detailed in sections
        3-5. We provide theoretical justification and empirical validation of our approach.'''
    }
    result3 = filter_mgr.is_relevant(paper3)
    print(f"   Title: '{paper3['title']}'")
    print(f"   Abstract length: {len(paper3['abstract'].split())} words")
    print(f"   URLs found: 2")
    print(f"   Result: {'PASSED [+]' if result3 else 'FILTERED [-]'}")
    print(f"   [{'PASS' if result3 else 'FAIL'}] - Should pass (academic references)")

    # Test Case 4: Actual link aggregator (should be filtered)
    print("\n4. Actual link aggregator page (should be filtered):")
    paper4 = {
        'title': 'AI Safety Weekly Roundup',
        'abstract': '''Links: https://paper1.com https://paper2.com https://paper3.com
        https://paper4.com https://paper5.com https://paper6.com https://paper7.com
        https://paper8.com https://paper9.com https://paper10.com'''
    }
    result4 = filter_mgr.is_relevant(paper4)
    print(f"   Title: '{paper4['title']}'")
    print(f"   Abstract length: {len(paper4['abstract'].split())} words")
    print(f"   URLs found: 10")
    print(f"   Result: {'PASSED [+]' if result4 else 'FILTERED [-]'}")
    print(f"   [{'PASS' if not result4 else 'FAIL'}] - Should be filtered (link aggregator)")

    # Test Case 5: Short content with many URLs (link aggregator)
    print("\n5. Short content with high URL density (link aggregator):")
    paper5 = {
        'title': 'This Week in AI Safety',
        'abstract': 'See https://a.com https://b.com https://c.com https://d.com https://e.com for safety papers.'
    }
    result5 = filter_mgr.is_relevant(paper5)
    print(f"   Title: '{paper5['title']}'")
    print(f"   Abstract length: {len(paper5['abstract'].split())} words")
    print(f"   URLs found: 5")
    print(f"   Result: {'PASSED [+]' if result5 else 'FILTERED [-]'}")
    print(f"   [{'PASS' if not result5 else 'FAIL'}] - Should be filtered (high URL density)")

    # Test Case 6: Long research paper with many URLs in references
    print("\n6. Long research paper with many URLs in references section:")
    paper6 = {
        'title': 'Comprehensive Analysis of Alignment Techniques in Large Language Models',
        'abstract': '''This paper presents a comprehensive analysis of alignment techniques for large
        language models. We systematically evaluate 15 different alignment methods including RLHF,
        constitutional AI, debate, and amplification. Our experimental framework tests each method
        across 20 safety benchmarks measuring truthfulness, harmlessness, and helpfulness. The study
        involved training 100+ model variants and conducting 50,000+ evaluations. Key findings include:
        (1) RLHF shows strong performance on helpfulness but weaker on edge cases, (2) constitutional
        methods improve robustness to adversarial prompts, (3) hybrid approaches combining multiple
        techniques achieve best overall safety scores. We analyze failure modes, propose improvements,
        and discuss scalability challenges. Related work includes https://arxiv.org/abs/2204.05862
        on RLHF, https://arxiv.org/abs/2212.08073 on constitutional AI, https://arxiv.org/abs/2201.11903
        on debate, and https://anthropic.com/alignment for overview. Dataset at https://github.com/alignment-eval
        and code at https://github.com/alignment-methods. Additional analysis available at
        www.alignment-research.org/comprehensive-study.'''
    }
    result6 = filter_mgr.is_relevant(paper6)
    print(f"   Title: '{paper6['title']}'")
    print(f"   Abstract length: {len(paper6['abstract'].split())} words")
    print(f"   URLs found: 7")
    print(f"   Result: {'PASSED [+]' if result6 else 'FILTERED [-]'}")
    print(f"   [{'PASS' if result6 else 'FAIL'}] - Should pass (substantial research content)")

    # Test Case 7: List-style aggregator with bullet points
    print("\n7. List-style aggregator with formatting:")
    paper7 = {
        'title': 'Latest AI Safety Papers - Curated Links',
        'abstract': '''
- Paper 1: https://example.com/paper1
- Paper 2: https://example.com/paper2
- Paper 3: https://example.com/paper3
- Paper 4: https://example.com/paper4
- Paper 5: https://example.com/paper5
- Paper 6: https://example.com/paper6
        '''
    }
    result7 = filter_mgr.is_relevant(paper7)
    print(f"   Title: '{paper7['title']}'")
    print(f"   Abstract length: {len(paper7['abstract'].split())} words")
    print(f"   URLs found: 6")
    print(f"   Result: {'PASSED [+]' if result7 else 'FILTERED [-]'}")
    print(f"   [{'PASS' if not result7 else 'FAIL'}] - Should be filtered (list format)")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    legitimate_papers_passed = sum([result1, result2, result3, result6])
    link_aggregators_filtered = sum([not result4, not result5, not result7])

    print(f"Legitimate papers with URLs: {legitimate_papers_passed}/4 passed")
    print(f"Link aggregators: {link_aggregators_filtered}/3 filtered")

    total_score = legitimate_papers_passed + link_aggregators_filtered
    print(f"\nTotal Score: {total_score}/7")

    if total_score == 7:
        print("\n[+] ALL TESTS PASSED - Filtering correctly distinguishes research from aggregators")
    elif total_score >= 5:
        print("\n⚠ MOSTLY PASSING - Some edge cases need refinement")
    else:
        print("\n[-] TESTS FAILED - Filtering needs improvement")

    print("\nKey Improvements:")
    print("  • Research papers with URLs in references are NOT filtered")
    print("  • Short content with high URL density IS filtered")
    print("  • Research indicators (method, experiment, results) protect legitimate papers")
    print("  • List-style formatting detected for aggregators")
    print("  • Minimum word count threshold prevents false positives")

    print("=" * 70)

    return total_score == 7

if __name__ == "__main__":
    success = test_research_papers_with_urls()
    exit(0 if success else 1)
