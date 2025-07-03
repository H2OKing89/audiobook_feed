/**
 * Confidence-based matching system ported from Python
 * Implements the same fuzzy matching and confidence scoring logic
 */

const stringSimilarity = require('string-similarity');

class AudiobookMatcher {
    constructor() {
        // Core weights (must sum to 1.0)
        this.coreWeights = {
            title: 0.5,   // Most important
            author: 0.3,  // Very important  
            series: 0.2,  // Important for series books
        };
        
        // Bonus weights (additive, can exceed 1.0)
        this.bonusWeights = {
            publisher: 0.1,      // Publisher match bonus
            narrator: 0.1,       // Narrator match bonus
            volumeRecency: 0.05  // Newer volume bonus
        };
        
        this.thresholds = {
            title: { exact: 1.0, high: 0.85, medium: 0.70 },
            series: { exact: 1.0, high: 0.85, medium: 0.70 },
            author: { exact: 1.0, high: 0.90, medium: 0.75 },
            publisher: { exact: 1.0, high: 0.95, medium: 0.80 }
        };
        
        this.credit = {
            exact: 1.0,    // Full credit for exact matches
            high: 0.9,     // 90% credit for high quality fuzzy matches
            medium: 0.6,   // 60% credit for medium quality matches
            low: 0.0       // No credit for poor matches
        };
    }
    
    /**
     * Normalize string for comparison (equivalent to Python normalize_string)
     */
    normalizeString(str) {
        if (!str) return '';
        return str.toLowerCase()
                  .replace(/[^\w\s]/g, '')  // Remove punctuation
                  .replace(/\s+/g, ' ')     // Multiple spaces to single
                  .trim();
    }
    
    /**
     * Calculate fuzzy ratio between two strings (equivalent to Python fuzzy_ratio)
     */
    fuzzyRatio(s1, s2) {
        if (!s1 || !s2) return 0.0;
        return stringSimilarity.compareTwoStrings(
            this.normalizeString(s1), 
            this.normalizeString(s2)
        );
    }
    
    /**
     * Extract volume number with decimal support (equivalent to Python extract_volume_number)
     */
    extractVolumeNumber(title) {
        if (!title) return null;
        
        const titleLower = title.toLowerCase();
        const volumePatterns = [
            /vol\.?\s*(\d+(?:\.\d+)?)/,           // "Vol. 14", "Vol 14.5"
            /volume\s*(\d+(?:\.\d+)?)/,           // "Volume 14", "Volume 14.5"
            /book\s*(\d+(?:\.\d+)?)/,             // "Book 14", "Book 14.5"
            /(\d+(?:\.\d+)?)\s*\(light novel\)/, // "14 (Light Novel)", "14.5 (Light Novel)"
            /(\d+(?:\.\d+)?)\s*\(ln\)/,          // "14 (LN)", "14.5 (LN)"
            /,\s*vol\.?\s*(\d+(?:\.\d+)?)/,      // ", Vol. 14", ", Vol. 14.5"
            /:\s*volume\s*(\d+(?:\.\d+)?)/,      // ": Volume 14", ": Volume 14.5"
            /\s+(\d+(?:\.\d+)?)$/,               // " 14" or " 14.5" at end of title
        ];
        
        for (const pattern of volumePatterns) {
            const match = titleLower.match(pattern);
            if (match) {
                const volume = parseFloat(match[1]);
                if (!isNaN(volume)) {
                    return volume;
                }
            }
        }
        
        return null;
    }
    
    /**
     * Generate title key for matching (equivalent to Python get_title_volume_key)
     */
    getTitleVolumeKey(title) {
        if (!title) return '';
        
        let titleLower = title.toLowerCase().trim();
        
        // Remove common volume indicators and normalize
        const volumeRemovals = [
            /\s*vol\.?\s*\d+.*$/,           // Remove "Vol. 14" and everything after
            /\s*volume\s*\d+.*$/,           // Remove "Volume 14" and everything after  
            /\s*book\s*\d+.*$/,             // Remove "Book 14" and everything after
            /\s*\d+\s*\(light novel\).*$/,  // Remove "14 (Light Novel)" and after
            /\s*\d+\s*\(ln\).*$/,           // Remove "14 (LN)" and after
            /,\s*vol\.?\s*\d+.*$/,          // Remove ", Vol. 14" and after
            /:\s*volume\s*\d+.*$/,          // Remove ": Volume 14" and after
            /\s+\d+$/,                      // Remove " 14" at end
        ];
        
        let normalized = titleLower;
        for (const pattern of volumeRemovals) {
            normalized = normalized.replace(pattern, '');
        }
        
        // Clean up extra spaces and punctuation
        normalized = normalized.replace(/\s+/g, ' ').trim();
        normalized = normalized.replace(/[^\w\s]/g, '');
        
        return normalized;
    }
    
    /**
     * Calculate confidence score (equivalent to Python confidence function)
     */
    calculateConfidence(result, wanted) {
        let score = 0.0;
        const logParts = [];
        
        // Extract volume information early for volume-aware matching
        const resultVolume = this.extractVolumeNumber(result.title);
        const wantedVolume = this.extractVolumeNumber(wanted.title || '');
        
        // Title matching - use volume-aware normalization for series books
        const normTitleResult = this.normalizeString(result.title);
        const normTitleWanted = this.normalizeString(wanted.title || '');
        
        // For series books, compare base titles without volume numbers
        const resultSeries = result.series || '';
        const wantedSeries = wanted.series || '';
        
        if (resultSeries && wantedSeries && 
            this.normalizeString(resultSeries) === this.normalizeString(wantedSeries)) {
            // Same series - use volume-aware title matching
            const resultBaseTitle = this.getTitleVolumeKey(result.title);
            const wantedBaseTitle = this.getTitleVolumeKey(wanted.title || '');
            
            if (resultBaseTitle === wantedBaseTitle) {
                // Same base title (series match) - give high score
                score += this.coreWeights.title * this.credit.exact;
                logParts.push(`Series title match: '${resultBaseTitle}' == '${wantedBaseTitle}'`);
                
                // Volume recency bonus - prefer higher volume numbers
                if (resultVolume && wantedVolume) {
                    if (resultVolume > wantedVolume) {
                        score += this.bonusWeights.volumeRecency;
                        logParts.push(`Volume recency bonus: ${resultVolume} > ${wantedVolume}`);
                    } else if (resultVolume === wantedVolume) {
                        logParts.push(`Same volume: ${resultVolume}`);
                    } else {
                        logParts.push(`Older volume: ${resultVolume} < ${wantedVolume}`);
                    }
                } else if (resultVolume) {
                    // Has volume info when wanted doesn't - small bonus
                    score += this.bonusWeights.volumeRecency * 0.5;
                    logParts.push(`Has volume info: ${resultVolume}`);
                }
            } else {
                // Different base titles in same series
                const titleRatio = this.fuzzyRatio(result.title, wanted.title || '');
                if (titleRatio >= this.thresholds.title.high) {
                    score += this.coreWeights.title * this.credit.high;
                    logParts.push(`Fuzzy series title match: '${resultBaseTitle}' ~ '${wantedBaseTitle}' (${titleRatio.toFixed(2)})`);
                } else if (titleRatio >= this.thresholds.title.medium) {
                    score += this.coreWeights.title * this.credit.medium;
                    logParts.push(`Partial series title match: '${resultBaseTitle}' ~ '${wantedBaseTitle}' (${titleRatio.toFixed(2)})`);
                }
            }
        } else {
            // Regular title matching for non-series or different series
            const titleRatio = this.fuzzyRatio(result.title, wanted.title || '');
            
            if (normTitleResult && normTitleWanted) {
                if (normTitleResult === normTitleWanted) {
                    score += this.coreWeights.title * this.credit.exact;
                } else if (titleRatio >= this.thresholds.title.high) {
                    score += this.coreWeights.title * this.credit.high;
                    logParts.push(`Fuzzy title match: '${normTitleResult}' ~ '${normTitleWanted}' (${titleRatio.toFixed(2)})`);
                } else if (titleRatio >= this.thresholds.title.medium) {
                    score += this.coreWeights.title * this.credit.medium;
                    logParts.push(`Partial title match: '${normTitleResult}' ~ '${normTitleWanted}' (${titleRatio.toFixed(2)})`);
                } else {
                    logParts.push(`Title mismatch: '${normTitleResult}' vs '${normTitleWanted}' (${titleRatio.toFixed(2)})`);
                }
            }
        }
        
        // Author matching
        const normAuthorResult = this.normalizeString(result.author);
        const normAuthorWanted = this.normalizeString(wanted.author || '');
        const authorRatio = this.fuzzyRatio(result.author, wanted.author || '');
        
        if (normAuthorResult && normAuthorWanted) {
            if (normAuthorResult === normAuthorWanted) {
                score += this.coreWeights.author * this.credit.exact;
            } else if (authorRatio >= this.thresholds.author.high) {
                score += this.coreWeights.author * this.credit.high;
                logParts.push(`Fuzzy author match: '${normAuthorResult}' ~ '${normAuthorWanted}' (${authorRatio.toFixed(2)})`);
            } else if (authorRatio >= this.thresholds.author.medium) {
                score += this.coreWeights.author * this.credit.medium;
                logParts.push(`Partial author match: '${normAuthorResult}' ~ '${normAuthorWanted}' (${authorRatio.toFixed(2)})`);
            } else {
                logParts.push(`Author mismatch: '${normAuthorResult}' vs '${normAuthorWanted}' (${authorRatio.toFixed(2)})`);
            }
        }
        
        // Series matching
        const normSeriesResult = this.normalizeString(result.series);
        const normSeriesWanted = this.normalizeString(wanted.series || '');
        const seriesRatio = this.fuzzyRatio(result.series, wanted.series || '');
        
        if (normSeriesResult && normSeriesWanted) {
            if (normSeriesResult === normSeriesWanted) {
                score += this.coreWeights.series * this.credit.exact;
            } else if (seriesRatio >= this.thresholds.series.high) {
                score += this.coreWeights.series * this.credit.high;
                logParts.push(`Fuzzy series match: '${normSeriesResult}' ~ '${normSeriesWanted}' (${seriesRatio.toFixed(2)})`);
            } else if (seriesRatio >= this.thresholds.series.medium) {
                score += this.coreWeights.series * this.credit.medium;
                logParts.push(`Partial series match: '${normSeriesResult}' ~ '${normSeriesWanted}' (${seriesRatio.toFixed(2)})`);
            } else {
                logParts.push(`Series mismatch: '${normSeriesResult}' vs '${normSeriesWanted}' (${seriesRatio.toFixed(2)})`);
            }
        }
        
        // Publisher bonus
        if (result.publisher && wanted.publisher) {
            const publisherRatio = this.fuzzyRatio(result.publisher, wanted.publisher);
            if (publisherRatio >= this.thresholds.publisher.high) {
                score += this.bonusWeights.publisher;
                logParts.push(`Publisher bonus: ${publisherRatio.toFixed(2)}`);
            }
        }
        
        // Narrator bonus
        if (result.narrator && wanted.narrator) {
            const narratorRatio = this.fuzzyRatio(result.narrator, wanted.narrator);
            if (narratorRatio >= 0.9) { // High threshold for narrator matching
                score += this.bonusWeights.narrator;
                logParts.push(`Narrator bonus: ${narratorRatio.toFixed(2)}`);
            }
        }
        
        if (logParts.length > 0) {
            console.debug(`Confidence calculation: ${logParts.join(', ')}`);
        }
        
        return score;
    }
    
    /**
     * Find all good matches above confidence threshold (equivalent to Python find_all_good_matches)
     */
    findAllGoodMatches(results, wanted, minConfidence = 0.5, preferredConfidence = 0.7) {
        if (!results || results.length === 0) {
            return [];
        }
        
        // Score all results
        const scoredResults = [];
        for (const result of results) {
            const score = this.calculateConfidence(result, wanted);
            if (score >= minConfidence) {  // Only include results that meet minimum threshold
                const resultCopy = { ...result };  // Create a copy to avoid modifying original
                resultCopy.confidenceScore = score;
                resultCopy.needsReview = score < preferredConfidence;
                
                if (score >= preferredConfidence) {
                    console.info(`High confidence match (${score.toFixed(2)}): ${result.title}`);
                } else {
                    console.warn(`Low confidence match (${score.toFixed(2)}) - needs review: ${result.title}`);
                }
                
                scoredResults.push([score, resultCopy]);
            }
        }
        
        // Sort by confidence score (highest first)
        scoredResults.sort((a, b) => b[0] - a[0]);
        
        // Extract just the results (without the scores)
        const goodMatches = scoredResults.map(([score, result]) => result);
        
        if (goodMatches.length === 0) {
            console.info(`No matches above minimum confidence (${minConfidence}).`);
        }
        
        return goodMatches;
    }
    
    /**
     * Find best single match with review flagging (equivalent to Python find_best_match_with_review)
     */
    findBestMatchWithReview(results, wanted, minConfidence = 0.5, preferredConfidence = 0.7) {
        const allMatches = this.findAllGoodMatches(results, wanted, minConfidence, preferredConfidence);
        return allMatches.length > 0 ? allMatches[0] : null;
    }
}

module.exports = AudiobookMatcher;
