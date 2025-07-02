# Confidence-Based Matching Integration Guide

## Overview

The AudioStacker project now includes a complete Node.js web backend that implements the same confidence-based matching logic as the Python system. This provides a user-friendly web interface for searching audiobooks with intelligent filtering and confidence scoring.

## Architecture

### Dual Implementation
- **Python Backend**: Original confidence-based matching in `audible.py`, `utils.py`
- **Node.js Backend**: Complete port in `src/web/backend/matching.js`
- **Both systems use identical logic**: Same weights, thresholds, and scoring algorithms

### Key Components

1. **Node.js Matching Engine** (`matching.js`)
   - Direct port of Python confidence logic
   - Fuzzy string matching using `string-similarity`
   - Decimal volume support (Vol. 4.5 ≠ Vol. 4.0)
   - Multi-factor confidence scoring

2. **Enhanced API Endpoints**
   - `POST /api/search` - Search with confidence filtering
   - `POST /api/match` - Apply matching to raw results
   - All endpoints return confidence metadata

3. **Vue.js Frontend Integration**
   - Advanced search controls
   - Confidence score display
   - Real-time filtering options

## Confidence Scoring System

### Core Weights (Must sum to 1.0)
- **Title**: 50% (0.5) - Most important factor
- **Author**: 30% (0.3) - Very important for accuracy  
- **Series**: 20% (0.2) - Important for series books

### Bonus Weights (Additive)
- **Publisher**: 10% (0.1) - Publisher match bonus
- **Narrator**: 10% (0.1) - Narrator match bonus
- **Volume Recency**: 5% (0.05) - Newer volume preference

### Confidence Thresholds
- **≥ 0.7**: High confidence (ready for notification)
- **≥ 0.5**: Medium confidence (good match, may need review)
- **< 0.5**: Low confidence (filtered out by default)

## Web Interface Features

### Advanced Search Options

The web interface includes an expandable "Advanced Search Options" panel with:

1. **Confidence Matching Toggle**
   - Enable/disable confidence-based filtering
   - When disabled, shows all raw search results
   - When enabled, applies confidence thresholds

2. **Confidence Threshold Slider**
   - Adjustable minimum confidence (0.1 to 1.0)
   - Real-time threshold adjustment
   - Shows current setting in tooltip

3. **Quick Presets**
   - **Strict (0.7+)**: Only high-confidence matches
   - **Balanced (0.5+)**: Good balance of quality and quantity
   - **Loose (0.3+)**: More permissive matching

### Results Display

1. **Search Summary**
   - Shows raw vs filtered result counts
   - Displays current confidence settings
   - Visual indicators for matching status

2. **Confidence Indicators**
   - Color-coded confidence score badges
   - Green: High confidence (≥ 0.7)
   - Orange: Needs review (< 0.7 but ≥ threshold)
   - Percentage display of confidence score

3. **Review Flags**
   - Automatic flagging of matches needing manual review
   - Clear visual indicators for uncertain matches
   - Helps users focus on questionable results

## API Usage Examples

### Search with Confidence Matching

```javascript
// Basic confidence search
const response = await fetch('/api/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: "Brandon Sanderson",
    searchType: "author",
    useMatching: true,
    minConfidence: 0.5
  })
});

const results = await response.json();
console.log('Raw results:', results.meta.totalRawResults);
console.log('Filtered results:', results.meta.totalFilteredResults);
```

### Apply Matching to Existing Results

```javascript
// Apply confidence matching to pre-existing results
const matchResponse = await fetch('/api/match', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    results: rawSearchResults,
    wanted: { author: "Brandon Sanderson" },
    minConfidence: 0.5,
    preferredConfidence: 0.7
  })
});

const { allMatches, bestMatch, meta } = await matchResponse.json();
```

## Configuration

### Backend Configuration

The matching system uses the same configuration as the Python system:

```yaml
# config.yaml - Confidence thresholds
confidence:
  minimum: 0.5          # Minimum confidence for processing
  preferred: 0.7        # Preferred confidence for auto-notification
  
# Matching weights (in matching.js)
core_weights:
  title: 0.5
  author: 0.3
  series: 0.2

bonus_weights:
  publisher: 0.1
  narrator: 0.1
  volume_recency: 0.05
```

### Frontend Defaults

```javascript
// Default settings in SearchView.vue
data() {
  return {
    useMatching: true,           // Enable by default
    minConfidence: 0.5,          // Balanced threshold
    selectedConfidencePreset: 'balanced'
  };
}
```

## Volume Matching Features

### Decimal Volume Support
- Correctly distinguishes Vol. 4.5 from Vol. 4.0
- Supports various volume formats: "Vol.", "Volume", "Book", etc.
- Handles light novel numbering: "14 (Light Novel)"

### Volume-Aware Matching
- For series books, compares base titles without volume numbers
- Applies volume recency bonus for newer releases
- Maintains precision with floating-point volume numbers

## Testing the Integration

### Manual Testing Steps

1. **Open Web Interface**: Navigate to `http://localhost:5006`
2. **Enable Advanced Options**: Expand the "Advanced Search Options" panel
3. **Test Confidence Levels**:
   - Try "Strict" preset with a popular author
   - Switch to "Loose" to see more results
   - Adjust slider manually to see real-time filtering

4. **Observe Results**:
   - Check the results summary for raw vs filtered counts
   - Look for confidence score badges on book cards
   - Note any "review needed" flags

### API Testing

```bash
# Test confidence search
curl -X POST http://localhost:5005/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Andy Weir", "searchType": "author", "useMatching": true, "minConfidence": 0.3}'

# Test raw matching service
curl -X POST http://localhost:5005/api/match \
  -H "Content-Type: application/json" \
  -d '{"results": [...], "wanted": {"author": "Test Author"}, "minConfidence": 0.5}'
```

## Benefits

### For Users
- **Improved Search Quality**: Intelligent filtering reduces noise
- **Transparency**: Clear confidence scores help manual review
- **Flexibility**: Adjustable thresholds for different use cases
- **Visual Feedback**: Easy-to-understand confidence indicators

### For Developers
- **Dual Implementation**: Choice between Python and Node.js
- **API Integration**: RESTful endpoints for external tools
- **Maintainability**: Single matching logic ported accurately
- **Extensibility**: Easy to add new matching criteria

## Migration from Python-Only

### Existing Users
- No changes required for Python-only usage
- Web interface provides additional capabilities
- Same configuration files and database format

### New Features Available
- Real-time confidence adjustment
- Visual search result analysis
- Web-based feed management
- Export functionality via web interface

## Future Enhancements

### Planned Features
- **Machine Learning**: Train confidence models on user feedback
- **Custom Weighting**: Per-user confidence weight adjustment
- **Batch Processing**: Apply confidence matching to large datasets
- **Analytics**: Track confidence score effectiveness over time

### Integration Opportunities
- **Notification Filtering**: Use confidence scores for notification prioritization
- **Auto-Review**: Automatically approve high-confidence matches
- **Feed Optimization**: Suggest confidence thresholds based on feed content

---

**Note**: This integration maintains 100% compatibility with the existing Python system while adding powerful web-based capabilities for confidence-based matching and result analysis.
