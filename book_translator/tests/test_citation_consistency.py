#!/usr/bin/env python3
"""
Citation Consistency Tests
Tests to ensure modernized citations maintain consistency and fidelity to originals.
"""

import re
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

class CitationTester:
    def __init__(self, citation_file_path):
        self.citation_file_path = Path(citation_file_path)
        self.citations = self._parse_citations()
        self.test_results = []
        
    def _parse_citations(self):
        """Parse the citation file and extract original/modernized pairs."""
        citations = []
        
        with open(self.citation_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all citation blocks
        citation_pattern = r'## \[(\^?\d+)\]\s*\n\n\*\*Original:\*\* (.*?)\n\n\*\*Modernized:\*\* (.*?)(?=\n\n---|$)'
        matches = re.findall(citation_pattern, content, re.DOTALL)
        
        for citation_id, original, modernized in matches:
            citations.append({
                'id': citation_id,
                'original': original.strip(),
                'modernized': modernized.strip()
            })
                
        return citations
    
    def _add_result(self, test_name, citation_id, passed, message=""):
        """Add a test result."""
        self.test_results.append({
            'test': test_name,
            'citation': citation_id,
            'passed': passed,
            'message': message
        })
    
    def test_vgl_preservation(self):
        """Test: If 'Vgl.' is in original, it should be in modernized."""
        for citation in self.citations:
            original_has_vgl = 'Vgl.' in citation['original']
            modernized_has_vgl = 'Vgl.' in citation['modernized']
            
            if original_has_vgl:
                passed = modernized_has_vgl
                message = "" if passed else f"Original has 'Vgl.' but modernized doesn't"
            else:
                # If original doesn't have Vgl., modernized shouldn't either (unless it's a contextual addition)
                passed = True  # Allow modernized to add Vgl. for consistency
                message = ""
            
            self._add_result('vgl_preservation', citation['id'], passed, message)
    
    def test_german_und_usage(self):
        """Test: Should use German 'und' not English 'and'."""
        for citation in self.citations:
            # Check for English 'and' in contexts where German 'und' should be used
            # But allow 'and' in English titles
            modernized = citation['modernized']
            
            # Look for 'and' that's not in an English title (between quotes or italics)
            # Simple heuristic: 'and' surrounded by German words/punctuation
            problematic_and = re.search(r'\s+and\s+(?![^"]*"[^"]*$)(?![^*]*\*[^*]*$)', modernized)
            
            passed = not problematic_and
            message = f"Found English 'and' outside title context: {problematic_and.group() if problematic_and else ''}"
            
            self._add_result('german_und_usage', citation['id'], passed, message)
    
    def test_no_cross_references(self):
        """Test: Modernized should not contain 'l. c.', 'ebenda', etc."""
        cross_ref_patterns = ['l. c.', 'l.c.', 'ebenda', 'ebda']
        
        for citation in self.citations:
            found_cross_refs = []
            for pattern in cross_ref_patterns:
                if pattern in citation['modernized']:
                    found_cross_refs.append(pattern)
            
            passed = len(found_cross_refs) == 0
            message = f"Found cross-references: {', '.join(found_cross_refs)}" if found_cross_refs else ""
            
            self._add_result('no_cross_references', citation['id'], passed, message)
    
    def test_page_format_consistency(self):
        """Test: Page formatting should be consistent (pp. XYZff, p. XYZ)."""
        for citation in self.citations:
            modernized = citation['modernized']
            
            # Check page format patterns
            issues = []
            
            # Should be 'pp. NUMBERff' not 'pp. NUMBER ff' or 'pp. NUMBERff.'
            bad_pp_ff = re.search(r'pp\. \d+ ff\.?|pp\.\d+ff\.', modernized)
            if bad_pp_ff:
                issues.append(f"Bad pp.ff format: {bad_pp_ff.group()}")
            
            # Should be 'p. NUMBER' not 'p.NUMBER' or 'p NUMBER'
            bad_p = re.search(r'p\.\d+|p \d+', modernized)
            if bad_p:
                issues.append(f"Bad p. format: {bad_p.group()}")
            
            # Check for inconsistent ff/f usage
            ff_patterns = re.findall(r'pp?\. \d+[^.,\s]*', modernized)
            for pattern in ff_patterns:
                if re.search(r'\d+ ff\.', pattern):  # Space before ff with period
                    issues.append(f"Inconsistent ff format: {pattern}")
            
            passed = len(issues) == 0
            message = "; ".join(issues)
            
            self._add_result('page_format_consistency', citation['id'], passed, message)
    
    def test_page_preservation(self):
        """Test: If original has page reference, modernized should too."""
        for citation in self.citations:
            original = citation['original']
            modernized = citation['modernized']
            
            # Extract page references from original
            original_pages = re.findall(r'p\. ?\d+[^.,\s]*', original)
            
            if original_pages:
                # Check if page references exist in modernized
                modernized_pages = re.findall(r'pp?\. ?\d+[^.,\s]*', modernized)
                
                passed = len(modernized_pages) > 0
                message = f"Original has pages {original_pages} but modernized missing page refs" if not passed else ""
            else:
                passed = True
                message = ""
            
            self._add_result('page_preservation', citation['id'], passed, message)
    
    def test_volume_notation_consistency(self):
        """Test: Should use 'Vol.' consistent with originals, not 'Volume'."""
        for citation in self.citations:
            modernized = citation['modernized']
            
            # Check for inconsistent usage - should use 'Vol.' not 'Volume' 
            has_english_volume = 'Volume' in modernized
            passed = not has_english_volume
            message = "Uses English 'Volume' instead of 'Vol.'" if has_english_volume else ""
            
            self._add_result('volume_notation_consistency', citation['id'], passed, message)
    
    def test_publisher_format(self):
        """Test: Publisher format should be 'City: Publisher, Year'."""
        for citation in self.citations:
            modernized = citation['modernized']
            
            # Look for publisher patterns
            publisher_patterns = re.findall(r'[A-ZÄÖÜ][a-zäöüß]+:\s*[A-Z][^,]+,\s*\d{4}', modernized)
            
            # Also check for incorrect formats
            bad_formats = []
            
            # Check for missing colon after city (but not if colon is present)
            bad_city = re.search(r'[A-ZÄÖÜ][a-zäöüß]+\s+[A-Z][a-zäöüß]+\s+Verlag,?\s*\d{4}', modernized)
            if bad_city:
                # Check if there's a colon before this pattern
                start_pos = bad_city.start()
                if start_pos > 0 and modernized[start_pos-2:start_pos] != ': ':
                    bad_formats.append(f"Missing colon after city: {bad_city.group()}")
            
            passed = len(bad_formats) == 0
            message = "; ".join(bad_formats)
            
            self._add_result('publisher_format', citation['id'], passed, message)
    
    def test_contextual_phrases_preserved(self):
        """Test: Contextual phrases should be preserved."""
        contextual_phrases = [
            'Für Belege', 'hierzu ausführlicher', 'besonders', 
            'Über diesen Begriff', 'Dieses Buch war Bruno Goetz bekannt'
        ]
        
        for citation in self.citations:
            original = citation['original']
            modernized = citation['modernized']
            
            issues = []
            
            # Check for each contextual phrase
            for phrase in contextual_phrases:
                # Handle variations (e.g., "hiezu" vs "hierzu")
                phrase_variants = {
                    'hierzu ausführlicher': ['hiezu ausführlicher', 'hierzu ausführlicher'],
                    'besonders': ['besonders'],
                    'Für Belege': ['Für Belege'],
                    'Über diesen Begriff': ['Uber diesen Begriff', 'Über diesen Begriff'],
                    'Dieses Buch war Bruno Goetz bekannt': ['Dieses Buch war Bruno Goetz bekannt']
                }
                
                # Check if any variant exists in original
                original_has_phrase = False
                for variant in phrase_variants.get(phrase, [phrase]):
                    if variant in original:
                        original_has_phrase = True
                        break
                
                if original_has_phrase:
                    # Check if modernized has the phrase (preferably standardized)
                    if phrase not in modernized:
                        issues.append(f"Missing contextual phrase: {phrase}")
            
            passed = len(issues) == 0
            message = "; ".join(issues)
            
            self._add_result('contextual_phrases_preserved', citation['id'], passed, message)
    
    def run_all_tests(self):
        """Run all tests and return results."""
        print("Running Citation Consistency Tests...")
        print(f"Found {len(self.citations)} citations to test\n")
        
        # Run all tests
        self.test_vgl_preservation()
        self.test_german_und_usage()
        self.test_no_cross_references()
        self.test_page_format_consistency()
        self.test_page_preservation()
        self.test_volume_notation_consistency()
        self.test_publisher_format()
        self.test_contextual_phrases_preserved()
        
        # Summarize results
        self._print_results()
        
        return self.test_results
    
    def _print_results(self):
        """Print test results summary."""
        # Group results by test
        test_groups = {}
        for result in self.test_results:
            test_name = result['test']
            if test_name not in test_groups:
                test_groups[test_name] = {'passed': 0, 'failed': 0, 'failures': []}
            
            if result['passed']:
                test_groups[test_name]['passed'] += 1
            else:
                test_groups[test_name]['failed'] += 1
                test_groups[test_name]['failures'].append({
                    'citation': result['citation'],
                    'message': result['message']
                })
        
        # Print summary
        print("=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        
        total_passed = 0
        total_failed = 0
        
        for test_name, results in test_groups.items():
            passed = results['passed']
            failed = results['failed']
            total_passed += passed
            total_failed += failed
            
            status = "✅ PASS" if failed == 0 else f"❌ FAIL ({failed} failures)"
            print(f"{test_name:<30} {status:<20} ({passed} passed, {failed} failed)")
            
            # Print failure details
            if failed > 0:
                for failure in results['failures']:
                    print(f"  └─ [^{failure['citation']}]: {failure['message']}")
        
        print("-" * 60)
        print(f"TOTAL: {total_passed} passed, {total_failed} failed")
        
        if total_failed == 0:
            print("🎉 ALL TESTS PASSED!")
        else:
            print(f"⚠️  {total_failed} issues found that need attention")


def main():
    # Path to the modernized citations file
    citation_file = Path(__file__).parent.parent.parent / "test-book-pdfs" / "archive" / "Das Reich ohne Raum -- Bruno Goetz-modernized_citations.md"
    
    if not citation_file.exists():
        print(f"Citation file not found: {citation_file}")
        return 1
    
    # Run tests
    tester = CitationTester(citation_file)
    results = tester.run_all_tests()
    
    # Return exit code based on results
    failed_tests = sum(1 for r in results if not r['passed'])
    return 1 if failed_tests > 0 else 0


if __name__ == "__main__":
    exit(main())