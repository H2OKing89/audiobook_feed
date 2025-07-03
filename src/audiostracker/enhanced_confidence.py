"""
Enhanced confidence scoring for AudioStacker matching
"""

from typing import Dict, List, Tuple, Optional
from decimal import Decimal
import re
from difflib import SequenceMatcher

from .author_matching import match_authors
from .series_analysis import SeriesVolumeAnalyzer

# Import the new title and series matching
try:
    from .title_series_matching import titles_match, series_match, extract_volume_number
    TITLE_SERIES_MATCHING_AVAILABLE = True
except ImportError:
    TITLE_SERIES_MATCHING_AVAILABLE = False

class EnhancedConfidenceScorer:
    """Enhanced confidence scoring with multiple factors"""
    
    def __init__(self):
        self.weights = {
            'author_match': 0.35,      # Author matching is very important
            'series_match': 0.25,      # Series matching is important
            'title_match': 0.15,       # Title similarity
            'volume_consistency': 0.12, # Volume number consistency (increased weight)
            'publisher_match': 0.04,   # Publisher consistency (slightly reduced)
            'narrator_match': 0.05,    # Narrator consistency
            'release_date_logic': 0.04 # Release date makes sense (slightly reduced)
        }
        
        # Create a series analyzer instance
        self.series_analyzer = SeriesVolumeAnalyzer()
        
        # Thresholds for different confidence levels
        self.thresholds = {
            'high': 0.85,    # Very confident match
            'medium': 0.65,  # Reasonably confident match
            'low': 0.45      # Possible match but needs review
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
        
        # Series matching - use new enhanced series matching if available
        if wanted.get('series') and result.get('series'):
            # Handle cases where series might be a list or dict
            result_series = result['series']
            wanted_series = wanted['series']
            
            # Extract series name from different formats
            if isinstance(result_series, list) and result_series:
                result_series = result_series[0].get('title', '') if isinstance(result_series[0], dict) else str(result_series[0])
            elif isinstance(result_series, dict) and 'title' in result_series:
                result_series = result_series['title']
            elif not isinstance(result_series, str):
                result_series = str(result_series) if result_series is not None else ""
            
            if isinstance(wanted_series, list) and wanted_series:
                wanted_series = wanted_series[0].get('title', '') if isinstance(wanted_series[0], dict) else str(wanted_series[0])
            elif isinstance(wanted_series, dict) and 'title' in wanted_series:
                wanted_series = wanted_series['title']
            elif not isinstance(wanted_series, str):
                wanted_series = str(wanted_series) if wanted_series is not None else ""
            
            # Use enhanced series matching if available
            if TITLE_SERIES_MATCHING_AVAILABLE:
                series_matches, series_sim = series_match(str(result_series), str(wanted_series))
            else:
                # Fallback to old logic
                normalized_result_series = self.series_analyzer.normalize_series_name(str(result_series))
                normalized_wanted_series = self.series_analyzer.normalize_series_name(str(wanted_series))
                
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
                            str(result_series).lower(),
                            str(wanted_series).lower()
                        ).ratio()
            
            scores['series_match'] = series_sim
        else:
            scores['series_match'] = 0.5  # Neutral if no series specified
        
        # Title matching - use enhanced title matching if available
        if wanted.get('title') and result.get('title'):
            if TITLE_SERIES_MATCHING_AVAILABLE:
                # Use the new enhanced title matching
                result_series = result.get('series', '')
                wanted_series = wanted.get('series', '')
                
                # Extract series strings from complex formats
                if isinstance(result_series, list) and result_series:
                    result_series = result_series[0].get('title', '') if isinstance(result_series[0], dict) else str(result_series[0])
                elif isinstance(result_series, dict) and 'title' in result_series:
                    result_series = result_series['title']
                else:
                    result_series = str(result_series) if result_series else ''
                    
                if isinstance(wanted_series, list) and wanted_series:
                    wanted_series = wanted_series[0].get('title', '') if isinstance(wanted_series[0], dict) else str(wanted_series[0])
                elif isinstance(wanted_series, dict) and 'title' in wanted_series:
                    wanted_series = wanted_series['title']
                else:
                    wanted_series = str(wanted_series) if wanted_series else ''
                
                title_matches, title_sim = titles_match(
                    result.get('title', ''), 
                    wanted.get('title', ''),
                    threshold=0.8,
                    series1=result_series,
                    series2=wanted_series
                )
            else:
                # Fallback to old title matching logic
                # Extract title without series name for better comparison
                result_title = result.get('title', '').lower()
                wanted_title = wanted.get('title', '').lower()
                
                # Remove series name from titles if possible for cleaner comparison
                if result.get('series'):
                    # Handle series as either string or list
                    result_series = result.get('series', '')
                    if isinstance(result_series, list):
                        for series in result_series:
                            if isinstance(series, dict) and 'title' in series:
                                series_title = series['title'].lower()
                                result_title = result_title.replace(series_title, '').strip()
                    elif isinstance(result_series, str):
                        result_title = result_title.replace(result_series.lower(), '').strip()
                        
                if wanted.get('series'):
                    # Handle series as either string or list
                    wanted_series = wanted.get('series', '')
                    if isinstance(wanted_series, list):
                        for series in wanted_series:
                            if isinstance(series, dict) and 'title' in series:
                                series_title = series['title'].lower()
                                wanted_title = wanted_title.replace(series_title, '').strip()
                    elif isinstance(wanted_series, str):
                        wanted_title = wanted_title.replace(wanted_series.lower(), '').strip()
                    
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
        
        # Volume consistency - use enhanced volume extraction if available
        if TITLE_SERIES_MATCHING_AVAILABLE:
            result_vol = extract_volume_number(result.get('title', ''))
            wanted_vol = extract_volume_number(wanted.get('title', '')) if wanted.get('title') else None
        else:
            # Fallback to old volume extraction
            result_vol = self.series_analyzer.extract_volume_number(result.get('title', ''))
            wanted_vol = self.series_analyzer.extract_volume_number(wanted.get('title', '')) if wanted.get('title') else None
        
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
                elif abs(float(result_vol) - float(wanted_vol)) < 1.1:
                    # Fairly close volume numbers might be acceptable (e.g., 1 vs 2)
                    # This handles off-by-one errors in volume numbering between publishers/regions
                    scores['volume_consistency'] = 0.5
                # Handle the case where one is "0" (prequel/prologue) and the other is "1" (first volume)
                elif (float(result_vol) == 0 and float(wanted_vol) == 1) or (float(result_vol) == 1 and float(wanted_vol) == 0):
                    scores['volume_consistency'] = 0.4  # Give some credit, but still low
                else:
                    scores['volume_consistency'] = 0.0
        # Handle case where we don't have volume numbers
        elif not result_vol and not wanted_vol:
            # If neither has volume info, give full score - they're likely the same
            scores['volume_consistency'] = 1.0
        elif not wanted_vol:
            # If wanted doesn't specify volume but result has one, it's potentially ok
            scores['volume_consistency'] = 0.8  # Somewhat neutral but positive
        elif not result_vol:
            # If we wanted a specific volume but result doesn't specify, that's not great
            scores['volume_consistency'] = 0.5  # Lower neutral score
        else:
            scores['volume_consistency'] = 0.7  # General neutral score
        
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
        if confidence < self.thresholds['low']:
            return True, f"Low overall confidence score: {confidence:.2f}"
        
        # Critical factor checks
        
        # Author match is critical - if it's bad, definitely needs review
        if score_breakdown.get('author_match', 0) < 0.7:
            return True, f"Poor author match: {score_breakdown['author_match']:.2f}"
        
        # Series match is also important when a series is specified
        if score_breakdown.get('series_match', 1) < 0.6 and score_breakdown.get('series_match', 1) != 0.5:
            # 0.5 is the neutral value when no series was specified
            return True, f"Poor series match: {score_breakdown['series_match']:.2f}"
        
        # Volume mismatch - critical for series
        if score_breakdown.get('volume_consistency', 1) < 0.3:
            return True, f"Volume number mismatch: {score_breakdown['volume_consistency']:.2f}"
            
        # Mixed signals (good in some areas, poor in others)
        critical_factors = ['author_match', 'series_match', 'volume_consistency']
        critical_scores = [score_breakdown.get(factor, 0) for factor in critical_factors]
        
        # If critical factors are good but overall confidence is mediocre
        if min(critical_scores) > 0.7 and confidence < self.thresholds['medium']:
            return True, "Inconsistent confidence signals (critical factors good, overall mediocre)"
            
        # If we have a mix of very good and very poor signals
        high_scores = sum(1 for score in score_breakdown.values() if score > 0.9)
        low_scores = sum(1 for score in score_breakdown.values() if score < 0.4)
        
        if high_scores >= 2 and low_scores >= 2:
            return True, "Mixed confidence signals (both very high and very low factor scores)"
            
        # If overall confidence is good but any critical factor is just mediocre
        if confidence > self.thresholds['medium'] and any(0.5 <= score <= 0.75 for score in critical_scores):
            return True, "Possible false positive (good overall score but mediocre critical factors)"
        
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
