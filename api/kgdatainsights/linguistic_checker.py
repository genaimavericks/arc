"""
Linguistic checker module for KG Insights
Uses LanguageTool to check grammar and provide suggestions
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class LinguisticChecker:
    """Handles linguistic checking and suggestions using LanguageTool"""
    
    def __init__(self):
        """Initialize the linguistic checker"""
        self.language_tool = None
        try:
            import language_tool_python
            logger.info("Initializing LanguageTool...")
            self.language_tool = language_tool_python.LanguageTool('en-US')
            logger.info("LanguageTool initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing LanguageTool: {e}")
            logger.warning("Falling back to simple pattern matching for linguistic checks.")
            
    def check_text(self, text: str, cursor_position: int = 0) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Check text for linguistic errors
        
        Args:
            text: The text to check
            cursor_position: Current cursor position in the text
            
        Returns:
            Tuple of (list of errors, quality analysis)
        """
        logger.info(f"Checking text: '{text}', cursor position: {cursor_position}")
        
        if not text or not text.strip():
            logger.info("Empty text received, returning empty results")
            return [], {"quality_score": 100, "error_count": 0}
            
        if not self.language_tool:
            logger.info("LanguageTool not available, using fallback checker")
            # Fallback to simple pattern matching if LanguageTool is not available
            return self._fallback_check(text, cursor_position)
            
        try:
            logger.info("Using LanguageTool to check text")
            # Get errors from LanguageTool
            matches = self.language_tool.check(text)
            logger.info(f"LanguageTool found {len(matches)} matches")
            
            # Convert to our format
            errors = []
            for match in matches:
                logger.info(f"Processing match: {match}")
                if not match.replacements:
                    logger.info("  - No replacements available, skipping")
                    continue
                    
                error = {
                    "category": match.ruleIssueType.lower() if hasattr(match, 'ruleIssueType') else "grammar",
                    "message": match.message,
                    "position": match.offset,
                    "length": match.errorLength,
                    "matched_text": text[match.offset:match.offset + match.errorLength],
                    "suggestion": match.replacements[0],
                    "rule_id": match.ruleId if hasattr(match, 'ruleId') else ""
                }
                logger.info(f"  - Created error object: {error}")
                errors.append(error)
                
            # Generate overall quality analysis
            quality_analysis = {
                "quality_score": max(100 - len(errors) * 5, 0),  # Deduct 5 points per error
                "error_count": len(errors),
                "error_categories": self._count_categories(errors),
                "improvement_suggestions": self._get_improvement_suggestions(errors)
            }
            
            logger.info(f"Returning {len(errors)} errors and quality analysis")
            # Force empty fallback errors if no LanguageTool errors were found
            if not errors:
                logger.info("No errors found with LanguageTool, checking with fallback patterns")
                fallback_errors, _ = self._fallback_check(text, cursor_position)
                if fallback_errors:
                    logger.info(f"Fallback check found {len(fallback_errors)} errors")
                    errors = fallback_errors
                    quality_analysis["error_count"] = len(errors)
                    quality_analysis["error_categories"] = self._count_categories(errors)
                    quality_analysis["improvement_suggestions"] = self._get_improvement_suggestions(errors)
                
            return errors, quality_analysis
            
        except Exception as e:
            logger.error(f"Error checking text with LanguageTool: {e}")
            return [], {"quality_score": 100, "error_count": 0}
    
    def _count_categories(self, errors: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count errors by category"""
        categories = {}
        for error in errors:
            category = error.get("category", "other")
            categories[category] = categories.get(category, 0) + 1
        return categories
    
    def _get_improvement_suggestions(self, errors: List[Dict[str, Any]]) -> List[str]:
        """Generate general improvement suggestions based on errors"""
        suggestions = []
        
        # Grammar suggestions
        if any(e.get("category") == "grammar" for e in errors):
            suggestions.append("Review grammar structure")
            
        # Spelling suggestions
        if any(e.get("category") == "misspelling" for e in errors):
            suggestions.append("Check spelling")
            
        # Style suggestions
        if any(e.get("category") == "style" for e in errors):
            suggestions.append("Consider more concise phrasing")
            
        # Punctuation suggestions
        if any(e.get("rule_id", "").startswith("PUNCTUATION") for e in errors):
            suggestions.append("Review punctuation")
            
        return suggestions or ["No specific suggestions"]
    
    def _fallback_check(self, text: str, cursor_position: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Simple fallback checker when LanguageTool is not available"""
        logger.info("Using fallback checker for linguistic errors")
        errors = []
        patterns = [
            (r"\bless\s+(\w+s)\b", "fewer $1", "Use 'fewer' with countable nouns"),
            (r"\bamount of (\w+s)\b", "number of $1", "Use 'number of' with countable nouns"),
            (r"\bit's\s+(\w+)s\b", "its $1s", "Use 'its' (possessive) not 'it's' (contraction)"),
            (r"\beffect on\b", "affect on", "Use 'affect' (verb) not 'effect' (noun)"),
            (r"\btheir is\b", "there is", "Use 'there' not 'their'"),
            (r"\byour right\b", "you're right", "Use 'you're' (contraction) not 'your' (possessive)"),
            (r"\bcould of\b", "could have", "Use 'could have' not 'could of'"),
            (r"\bshould of\b", "should have", "Use 'should have' not 'should of'"),
            (r"\bwould of\b", "would have", "Use 'would have' not 'would of'"),
            # Add more simple error patterns for testing
            (r"\bthere are (\w+) items\b", "there are $1 items", "Testing pattern match"),
            (r"\bteh\b", "the", "Common typo"),
            (r"\ba lots of\b", "a lot of", "Incorrect plural"),
            (r"\bis there any\s+(\w+s)\b", "are there any $1", "Use plural verb with plural nouns"),
            (r"\byou was\b", "you were", "Incorrect verb conjugation"),
            (r"\bhe have\b", "he has", "Incorrect verb conjugation"),
            (r"\bshe have\b", "she has", "Incorrect verb conjugation")
        ]
        
        import re
        for pattern, replacement, message in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                errors.append({
                    "category": "grammar",
                    "message": message,
                    "position": match.start(),
                    "length": match.end() - match.start(),
                    "matched_text": match.group(0),
                    "suggestion": re.sub(pattern, replacement, match.group(0), flags=re.IGNORECASE),
                    "rule_id": "FALLBACK_RULE"
                })
        
        quality_analysis = {
            "quality_score": max(100 - len(errors) * 5, 0),
            "error_count": len(errors),
            "error_categories": {"grammar": len(errors)} if errors else {},
            "improvement_suggestions": ["Review grammar structure"] if errors else ["No specific suggestions"]
        }
        
        return errors, quality_analysis

# Create a singleton instance
linguistic_checker = LinguisticChecker()
