"""
Enhanced confidence scoring for AudioStacker matching
"""

from typing import Dict, List, Tuple, Optional
from decimal import Decimal
import re
from difflib import SequenceMatcher

from .author_matching import match_authors
from .series_analysis import normalize_series_name, extract_volume_number

class EnhancedConfidenceScorer:
    """Enhanced confidence scoring with multiple factors"""
    
    def __init__(self):
        self.weights = {
            'author_match': 0.35,      # Author matching is very important
            'series_match': 0.25,      # Series matching is important
            'title_match': 0.15,       # Title similarity
            'volume_consistency': 0.10, # Volume number consistency
            'publisher_match': 0.05,   # Publisher consistency
            'narrator_match': 0.05,    # Narrator consistency
            'release_date_logic': 0.05 # Release date makes sense
        }
    
    def calculate_enhanced_confidence(self, result: Dict, wanted: Dict) -> Tuple[float, Dict]:
        """
        Calculate enhanced confidence score with detailed breakdown
        
        Returns:
            Tuple of (confidence_score, score_breakdown)
        """
        scores = {}
        
        # Author matching (most important)
        author_match, author_score = match_authors(
            result.get('author', ''), 
            wanted.get('author', '')
        )
        scores['author_match'] = author_score
        
        # Series matching - improved to handle more variants
        if wanted.get('series') and result.get('series'):
            normalized_result_series = normalize_series_name(result['series'])
            normalized_wanted_series = normalize_series_name(wanted['series'])
            
            if normalized_result_series == normalized_wanted_series:
                series_sim = 1.0
            else:
                # Also check partial matches for longer series names
                if len(normalized_result_series) > 10 and len(normalized_wanted_series) > 10:
                    # Check if one is a substring of the other
                    if (normalized_result_series in normalized_wanted_series or 
                        normalized_wanted_series in normalized_result_series):
                        series_sim = 0.9  # Good confidence for partial matches of long names
                    else:
                        series_sim = SequenceMatcher(
                            None,
                            normalized_result_series,
                            normalized_wanted_series
                        ).ratio()
                else:
                    series_sim = SequenceMatcher(
                        None,
                        normalized_result_series,
                        normalized_wanted_series
                    ).ratio()
            
            scores['series_match'] = series_sim
        else:
            scores['series_match'] = 0.5  # Neutral if no series specified
        
        # Title matching - improved to handle special cases
        if wanted.get('title') and result.get('title'):
            # Extract title without series name for better comparison
            result_title = result.get('title', '').lower()
            wanted_title = wanted.get('title', '').lower()
            
            # Remove series name from titles if possible for cleaner comparison
            if result.get('series'):
                result_title = result_title.replace(result.get('series', '').lower(), '').strip()
            if wanted.get('series'):
                wanted_title = wanted_title.replace(wanted.get('series', '').lower(), '').strip()
                
            # Clean up remaining punctuation
            result_title = re.sub(r'[,:\-_()]', ' ', result_title)
            wanted_title = re.sub(r'[,:\-_()]', ' ', wanted_title)
            
            # Remove common words that don't add meaning
            common_words = ['vol', 'volume', 'book', 'part', 'light', 'novel', 'ln']
            for word in common_words:
                result_title = re.sub(r'\b' + word + r'\b', '', result_title)
                wanted_title = re.sub(r'\b' + word + r'\b', '', wanted_title)
                
            # Clean up whitespace
            result_title = re.sub(r'\s+', ' ', result_title).strip()
            wanted_title = re.sub(r'\s+', ' ', wanted_title).strip()
            
            # Calculate similarity
            title_sim = SequenceMatcher(None, result_title, wanted_title).ratio()
            scores['title_match'] = title_sim
        else:
            scores['title_match'] = 0.7  # Neutral if no title filter
        
        # Volume consistency - improved with special case handling
        result_vol = extract_volume_number(result.get('title', ''))
        wanted_vol = extract_volume_number(wanted.get('title', '')) if wanted.get('title') else None
        
        if result_vol and wanted_vol:
            if result_vol == wanted_vol:
                scores['volume_consistency'] = 1.0
            else:
                # Allow some flexibility for special volume numbers
                if result_vol >= 9000 and wanted_vol >= 9000:  # Both are "final" volumes
                    scores['volume_consistency'] = 0.9
                elif abs(float(result_vol) - float(wanted_vol)) < 0.6:
                    # Close volume numbers might be acceptable (e.g., 1.5 vs 2)
                    scores['volume_consistency'] = 0.7
                else:
                    scores['volume_consistency'] = 0.0
        else:
            scores['volume_consistency'] = 0.8  # Neutral score
        
        # Publisher matching
        if wanted.get('publisher') and result.get('publisher'):
            pub_sim = SequenceMatcher(
                None,
                result['publisher'].lower(),
                wanted['publisher'].lower()
            ).ratio()
            scores['publisher_match'] = pub_sim
        else:
            scores['publisher_match'] = 0.7  # Neutral
        
        # Narrator matching
        if wanted.get('narrator') and result.get('narrator'):
            narrator_sim = self._compare_narrators(
                result['narrator'], 
                wanted['narrator']
            )
            scores['narrator_match'] = narrator_sim
        else:
            scores['narrator_match'] = 0.7  # Neutral
        
        # Release date logic (future books should score higher)
        from datetime import datetime
        try:
            release_date = datetime.strptime(result.get('release_date', ''), '%Y-%m-%d').date()
            today = datetime.now().date()
            
            if release_date > today:
                scores['release_date_logic'] = 1.0  # Future release is good
            elif release_date == today:
                scores['release_date_logic'] = 0.9  # Today is okay
            else:
                scores['release_date_logic'] = 0.3  # Past release is less desirable
        except (ValueError, TypeError):
            scores['release_date_logic'] = 0.5  # Unknown date
        
        # Calculate weighted average
        total_score = sum(
            scores[factor] * self.weights[factor] 
            for factor in self.weights
        )
        
        # Add bonus for exact matches
        if scores['author_match'] >= 0.95 and scores['series_match'] >= 0.95:
            total_score = min(1.0, total_score + 0.05)
            
        # Add bonus for recent and upcoming releases (most wanted)
        if scores['release_date_logic'] >= 0.9 and total_score >= 0.65:
            total_score = min(1.0, total_score + 0.05)
        
        return total_score, scores
    
    def _compare_narrators(self, result_narrator: str, wanted_narrator: str) -> float:
        """Compare narrator strings (which might contain multiple narrators)"""
        if not result_narrator or not wanted_narrator:
            return 0.7
        
        # Handle multiple narrators
        result_narrators = [n.strip() for n in re.split(r'[,&]', result_narrator)]
        wanted_narrators = [n.strip() for n in re.split(r'[,&]', wanted_narrator)]
        
        # Find best match among all combinations
        best_score = 0.0
        for r_narrator in result_narrators:
            for w_narrator in wanted_narrators:
                score = SequenceMatcher(None, r_narrator.lower(), w_narrator.lower()).ratio()
                best_score = max(best_score, score)
        
        return best_score
    
    def should_review(self, confidence: float, score_breakdown: Dict) -> Tuple[bool, str]:
        """
        Determine if a match should be flagged for manual review
        
        Returns:
            Tuple of (needs_review, reason)
        """
        # Low overall confidence
        if confidence < 0.6:
            return True, f"Low confidence score: {confidence:.2f}"
        
        # Poor author match (this is critical)
        if score_breakdown.get('author_match', 0) < 0.7:
            return True, f"Poor author match: {score_breakdown['author_match']:.2f}"
        
        # Poor series match when series is specified
        if score_breakdown.get('series_match', 1) < 0.6:
            return True, f"Poor series match: {score_breakdown['series_match']:.2f}"
        
        # Mixed signals (good in some areas, poor in others)
        high_scores = sum(1 for score in score_breakdown.values() if score > 0.8)
        low_scores = sum(1 for score in score_breakdown.values() if score < 0.4)
        
        if high_scores >= 2 and low_scores >= 2:
            return True, "Mixed confidence signals"
        
        return False, "Confidence acceptable"


# Global instance
confidence_scorer = EnhancedConfidenceScorer()

def calculate_confidence(result: Dict, wanted: Dict) -> Tuple[float, Dict, bool]:
    """
    Calculate enhanced confidence with review recommendation
    
    Returns:
        Tuple of (confidence, breakdown, needs_review)
    """
    confidence, breakdown = confidence_scorer.calculate_enhanced_confidence(result, wanted)
    needs_review, reason = confidence_scorer.should_review(confidence, breakdown)
    
    return confidence, breakdown, needs_review
