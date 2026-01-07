# CLAUDE.md - AI Assistant Guide for Race Control HQ

## Project Overview

**Race Control HQ** is a Streamlit-based web application that provides real-time weather forecasting and racing strategy recommendations for motorsport events. The application serves two primary use cases:

1. **Circuit Racing**: Fixed-location weather monitoring with tire strategy recommendations
2. **Rally Stages**: Route-based weather analysis using GPX track files

**Repository**: gg1007/op
**Main File**: `op.py`
**Framework**: Streamlit
**Language**: Python 3.x
**API Provider**: Open-Meteo (weather data)

---

## Codebase Structure

```
/home/user/op/
├── op.py              # Main application file (216 lines)
├── requirements.txt   # Python dependencies
├── .git/             # Git repository
└── .cache/           # Runtime cache directory (created by requests-cache)
```

### Single-File Architecture

This is a **monolithic Streamlit application** contained entirely in `op.py`. All functionality is organized into three main sections:

1. **Configuration** (lines 11-12): Streamlit page setup
2. **Data Functions** (lines 14-115): API calls, data processing, and logic
3. **UI Layer** (lines 117-216): Streamlit interface and user interactions

---

## Key Features & Functionality

### 1. Circuit/Fixed Location Mode (lines 124-169)

**Purpose**: Monitor weather at racing circuits with 3-hour forecasts

**Key Components**:
- Pre-configured circuits (Zandvoort, Spa-Francorchamps, Nürburgring, Assen, Zolder, Monaco)
- Custom location input via lat/lon coordinates
- 15-minute interval forecasts
- Tire strategy recommendations (SLICKS, INTERS, WETS)

**Data Flow**:
```
User selects circuit → get_weather_data(lat, lon, "circuit")
→ Returns DataFrame with 3-hour forecast
→ get_strategy() applies tire logic
→ Display table + metrics + chart
```

### 2. Rally Stage Mode (lines 171-216)

**Purpose**: Analyze weather conditions along a rally route

**Key Components**:
- GPX file upload and parsing
- Waypoint extraction (every 4km by default)
- Weather sampling at each waypoint
- Wet/dry risk assessment per section

**Data Flow**:
```
User uploads GPX → parse_gpx_route() extracts waypoints
→ Loop through waypoints calling get_weather_data(lat, lon, "rally")
→ Aggregate risk status (WET/DRY)
→ Display advice (Slicks/Wets/Crossover)
```

---

## Critical Functions Reference

### `get_weather_data(lat, lon, mode="circuit")`
**Location**: lines 16-71
**Purpose**: Fetch weather forecast from Open-Meteo API

**Parameters**:
- `lat` (float): Latitude coordinate
- `lon` (float): Longitude coordinate
- `mode` (str): "circuit" or "rally"

**Returns**:
- Circuit mode: Pandas DataFrame with columns `[time, temp, precip, wind, cloud, dir]`
- Rally mode: Dictionary `{precip_max, temp, wind, risk}`

**Caching**: `@st.cache_data(ttl=120)` - 2 minute cache per location

**API Details**:
- Endpoint: `https://api.open-meteo.com/v1/forecast`
- Parameters: `minutely_15` resolution, 1 forecast day, best_match model
- Variables: temperature_2m, precipitation, wind_speed_10m, cloud_cover, wind_direction

**Important Notes**:
- Circuit mode filters to 3-hour window from current time
- Rally mode filters to 1-hour window and returns summary statistics
- Uses retry logic (5 retries, 0.2s backoff) for API reliability
- Cache stored in `.cache/` directory

### `parse_gpx_route(uploaded_file, step_km=4)`
**Location**: lines 73-95
**Purpose**: Extract waypoints from GPX track file

**Parameters**:
- `uploaded_file`: Streamlit UploadedFile object (GPX format)
- `step_km` (int): Distance interval between waypoints (default: 4km)

**Returns**: List of dictionaries `[{name, lat, lon}, ...]`

**Logic**:
1. Parses all tracks and segments in GPX file
2. Calculates geodesic distance between consecutive points
3. Selects points at ~4km intervals
4. Always includes START and FINISH waypoints
5. Names waypoints as "START", "KM X", "FINISH"

**Important**: Uses `geopy.distance.geodesic()` for accurate distance calculation

### `get_strategy(row)`
**Location**: lines 97-115
**Purpose**: Convert weather data row into tire strategy recommendation

**Tire Decision Logic**:
```python
precipitation == 0      → SLICKS (green)
0 < precipitation < 0.5 → INTERS (orange)
precipitation >= 0.5    → WETS (red)
```

**Input**: Pandas Series with `[time, precip, temp, wind]`
**Output**: Pandas Series with `[Time, Rain, Temp, Wind, TIRE CALL]`

---

## Dependencies Explained

| Package | Purpose | Usage in Code |
|---------|---------|---------------|
| `streamlit` | Web UI framework | All `st.*` calls - page layout, widgets, metrics |
| `openmeteo-requests` | Open-Meteo API client | `openmeteo_requests.Client()` for weather data |
| `requests-cache` | HTTP caching | Reduces API calls via `CachedSession('.cache')` |
| `retry-requests` | Retry logic | `retry()` wrapper with 5 retries, 0.2s backoff |
| `pandas` | Data manipulation | DataFrame operations, date range handling |
| `pydantic` | Data validation | Dependency of openmeteo-requests |
| `gpxpy` | GPX file parsing | Parse rally route files (`gpxpy.parse()`) |
| `geopy` | Geographic calculations | `geodesic()` for accurate distance between waypoints |

---

## Development Workflows

### Local Development Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd op

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run application
streamlit run op.py

# 4. Access at http://localhost:8501
```

### Making Changes

**Before modifying code**:
1. Read `op.py` completely to understand current implementation
2. Identify which section to modify (config, data functions, or UI)
3. Consider cache implications (TTL=120s for weather data)
4. Test both circuit and rally modes if changing shared functions

**Testing Checklist**:
- [ ] Circuit mode with preset locations works
- [ ] Circuit mode with custom lat/lon works
- [ ] Rally mode accepts GPX files
- [ ] Weather data loads without errors
- [ ] Tire strategy logic is correct
- [ ] UI displays properly in wide layout

### Git Workflow

**Branch Naming Convention**: All branches must follow pattern `claude/*-<SESSION_ID>`

**Development Branch**: Currently on `claude/add-claude-documentation-JWIXl`

**Commit Process**:
```bash
git add <files>
git commit -m "Clear description of changes"
git push -u origin claude/<branch-name>
```

**Push Requirements**:
- Always use `-u` flag: `git push -u origin <branch-name>`
- Branch must start with `claude/` prefix
- Branch must end with matching session ID
- Retry up to 4 times with exponential backoff (2s, 4s, 8s, 16s) on network failures

---

## Code Conventions & Patterns

### Streamlit Patterns

1. **Page Configuration**: Always at top (line 12)
   ```python
   st.set_page_config(page_title="...", page_icon="...", layout="wide")
   ```

2. **Caching**: Use `@st.cache_data(ttl=120)` for API calls
   - TTL=120 seconds (2 minutes)
   - Prevents excessive API calls
   - Cache key includes function arguments

3. **Layout Structure**:
   - Sidebar for inputs (`st.sidebar.*`)
   - Main area for results
   - Columns for metrics (`st.columns()`)
   - Wide layout mode for tables

### Data Processing Patterns

1. **Time Handling**: Always use UTC timezone
   ```python
   pd.Timestamp.now(tz='UTC')
   pd.to_datetime(..., unit="s", utc=True)
   ```

2. **Error Handling**: Try-except with None fallback
   ```python
   try:
       # API call or processing
   except Exception as e:
       return None
   ```

3. **Conditional Returns**: Different output based on mode parameter
   - Circuit mode → Full DataFrame
   - Rally mode → Summary dictionary

### UI/UX Patterns

1. **Metrics Display**: 3-column layout for current conditions
2. **Color Coding**:
   - Green: Dry/safe conditions
   - Orange: Intermediate conditions
   - Red: Wet/dangerous conditions
3. **Progress Bars**: For multi-waypoint processing in rally mode
4. **Emoji Usage**: Racing-themed icons (🏎️, 🏁, 📍)

---

## Common Development Tasks

### Adding a New Circuit

**Location**: Line 128-136 (circuits dictionary)

```python
circuits = {
    # ... existing circuits ...
    "New Circuit 🏁": (latitude, longitude),
}
```

### Modifying Tire Strategy Logic

**Location**: Line 97-115 (`get_strategy` function)

**Current thresholds**:
- SLICKS: `precip == 0`
- INTERS: `0 < precip < 0.5`
- WETS: `precip >= 0.5`

**To modify**: Adjust the conditional logic and color assignments

### Changing Forecast Duration

**Circuit Mode**: Line 56
```python
hours = 3  # Change this value
```

**Rally Mode**: Line 56
```python
hours = 1  # Change this value
```

### Adjusting Rally Waypoint Interval

**Location**: Line 73 (`parse_gpx_route` function signature)

```python
def parse_gpx_route(uploaded_file, step_km=4):  # Change default here
```

Or expose as UI parameter in rally mode section

### Modifying API Parameters

**Location**: Lines 22-30 (Open-Meteo API params)

**Available variables**: See [Open-Meteo API Docs](https://open-meteo.com/en/docs)

**Current setup**:
- Resolution: `minutely_15` (15-minute intervals)
- Forecast days: 1
- Model: `best_match`
- Variables: temperature_2m, precipitation, wind_speed_10m, cloud_cover, wind_direction

---

## API Integration Details

### Open-Meteo Weather API

**Endpoint**: `https://api.open-meteo.com/v1/forecast`
**Rate Limits**: None for non-commercial use (as of 2025)
**Authentication**: Not required

**Request Structure**:
```python
params = {
    "latitude": float,
    "longitude": float,
    "minutely_15": [list of variables],
    "forecast_days": int,
    "models": str
}
```

**Response Handling**:
- Returns binary protocol buffers (handled by openmeteo-requests)
- Data accessed via `response.Minutely15().Variables(index)`
- Times in Unix timestamp format (converted to pandas datetime)

**Caching Strategy**:
- File-based cache in `.cache/` directory
- 120-second TTL (2 minutes)
- Automatic retry with 5 attempts
- Exponential backoff (0.2s factor)

---

## Important Notes for AI Assistants

### Before Making Changes

1. **Always read `op.py` first** - It's the only source file
2. **Understand mode differences** - Circuit vs Rally have different data flows
3. **Check cache implications** - Weather data cached for 2 minutes
4. **Test both modes** - Changes to shared functions affect both modes

### Code Modification Guidelines

1. **Preserve caching decorators** - Removing `@st.cache_data` will cause excessive API calls
2. **Maintain UTC timezone consistency** - Mixing timezones causes forecast errors
3. **Keep mode parameter logic** - Functions behave differently for "circuit" vs "rally"
4. **Don't break GPX parsing** - Rally mode depends on exact return format
5. **Preserve coordinate formats** - Always use (latitude, longitude) tuple order

### Common Pitfalls

1. **Cache not clearing**: Streamlit cache persists between runs
   - Solution: Use `st.cache_data.clear()` or restart app

2. **Timezone mismatches**: Mixing naive and timezone-aware datetimes
   - Solution: Always use `tz='UTC'` in datetime operations

3. **GPX parsing failures**: Not all GPX files have same structure
   - Current code assumes tracks → segments → points
   - May need error handling for route-only or waypoint-only GPX files

4. **API response changes**: Open-Meteo may change variable indices
   - Variables accessed by index: `Variables(0)` = temperature, etc.
   - Breaking if API reorders response variables

### Performance Considerations

1. **Rally mode performance**: Calls API once per waypoint
   - Long routes (>20 waypoints) may take 10+ seconds
   - Progress bar provides user feedback
   - Consider batch API requests for optimization

2. **Cache effectiveness**: Same location within 2 minutes = cached
   - Switching circuits frequently = new API calls
   - Rally routes with unique waypoints = always new calls

3. **DataFrame operations**: Lightweight for current data volumes
   - 3 hours × 4 intervals/hour = ~12 rows max per circuit
   - Rally routes typically <50 waypoints

---

## Testing Guidelines

### Manual Testing Checklist

**Circuit Mode**:
1. Select preset circuit → Verify coordinates display
2. Click "Scan Atmosfeer" → Verify weather data loads
3. Check metrics display current conditions
4. Verify forecast table shows time progression
5. Check tire strategy logic matches precipitation
6. Verify line chart renders precipitation trend
7. Test custom coordinates with valid lat/lon

**Rally Mode**:
1. Upload valid GPX file → Verify parsing success
2. Check progress bar animates through waypoints
3. Verify START and FINISH waypoints present
4. Check intermediate waypoints at ~4km intervals
5. Verify status colors (WET=red, DRY=green)
6. Check advice logic (all dry → Slicks, mixed → Crossover, all wet → Wets)

**Error Scenarios**:
1. Invalid coordinates → Should return None, display no data
2. Corrupted GPX file → Should fail gracefully
3. API timeout → Retry logic should handle (5 attempts)
4. No internet connection → Cache may provide stale data

### Integration Testing

```python
# Test weather API integration
def test_weather_api():
    df = get_weather_data(52.387, 4.540, mode="circuit")
    assert df is not None
    assert 'time' in df.columns
    assert len(df) > 0

# Test GPX parsing
def test_gpx_parsing():
    with open('test_route.gpx', 'r') as f:
        waypoints = parse_gpx_route(f)
    assert len(waypoints) >= 2  # At least START and FINISH
    assert waypoints[0]['name'] == 'START'
    assert waypoints[-1]['name'] == 'FINISH'

# Test strategy logic
def test_tire_strategy():
    test_data = pd.DataFrame({
        'time': [pd.Timestamp.now()],
        'precip': [0.0],
        'temp': [20.0],
        'wind': [10.0]
    })
    result = test_data.apply(get_strategy, axis=1)
    assert result.iloc[0]['TIRE CALL'] == 'SLICKS'
```

---

## Deployment Considerations

### Streamlit Cloud Deployment

**Requirements**:
- `requirements.txt` present ✓
- Python 3.7+ compatible ✓
- No external database dependencies ✓
- No API keys required ✓

**Configuration**:
```toml
# .streamlit/config.toml (optional)
[theme]
primaryColor = "#F63366"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"

[server]
maxUploadSize = 10  # MB, for GPX files
```

**Environment Variables**: None required (no API keys)

### Local Production Deployment

```bash
# Using streamlit directly
streamlit run op.py --server.port 8501 --server.address 0.0.0.0

# Using Docker (example Dockerfile)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY op.py .
EXPOSE 8501
CMD ["streamlit", "run", "op.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

---

## Future Enhancement Ideas

### Potential Features
1. **Historical weather data**: Compare forecasts to actual conditions
2. **Multiple circuit comparison**: Side-by-side weather for different locations
3. **Weather alerts**: Push notifications for sudden changes
4. **Radar imagery**: Visual precipitation maps
5. **Track temperature**: Surface temperature for tire warm-up calculations
6. **Wind direction visualization**: Show wind relative to track layout
7. **Session scheduling**: Optimal timing for practice/qualifying/race
8. **Data export**: CSV/JSON export of forecasts
9. **Multi-language support**: Dutch/English/French interfaces
10. **Mobile optimization**: Responsive design for pit lane tablets

### Architectural Improvements
1. **Modularization**: Split into separate files (api.py, ui.py, logic.py)
2. **Configuration file**: External config for circuits and thresholds
3. **Database integration**: Store historical forecasts and actual conditions
4. **Testing suite**: Automated tests with pytest
5. **CI/CD pipeline**: Automated deployment on push
6. **Logging system**: Track API calls and errors
7. **User authentication**: Save favorite circuits and routes
8. **API rate limiting**: Respect Open-Meteo fair use policies

---

## Troubleshooting

### Common Issues

**Problem**: Weather data not loading
**Solution**: Check internet connection, verify API endpoint status, clear cache

**Problem**: GPX file upload fails
**Solution**: Ensure file is valid GPX format, check file size (<10MB), verify tracks/segments exist

**Problem**: Incorrect tire recommendations
**Solution**: Review precipitation thresholds in `get_strategy()`, check units (mm vs cm)

**Problem**: Rally mode stuck on progress bar
**Solution**: Long routes take time, check console for API errors, verify waypoint coordinates

**Problem**: Time zone showing wrong hours
**Solution**: Verify UTC handling, check local timezone interpretation in browser

### Debug Mode

Add this to enable Streamlit debug mode:

```bash
streamlit run op.py --logger.level=debug
```

Or add to code:
```python
import streamlit as st
st.write(st.session_state)  # View session state
st.write(df)  # Debug DataFrames
```

---

## Contact & Resources

**Open-Meteo API**: https://open-meteo.com/en/docs
**Streamlit Docs**: https://docs.streamlit.io
**GPX Format**: https://www.topografix.com/gpx.asp
**Geopy Documentation**: https://geopy.readthedocs.io

---

## Document Metadata

**Last Updated**: 2026-01-07
**Document Version**: 1.0
**Code Version**: op.py (216 lines, as of commit d89f67f)
**Maintainer**: AI Assistant Documentation

---

## Quick Reference Card

```
FILE STRUCTURE
├── op.py (main application)
├── requirements.txt (dependencies)
└── .cache/ (runtime cache)

KEY FUNCTIONS
├── get_weather_data(lat, lon, mode) → DataFrame or dict
├── parse_gpx_route(file, step_km) → List[dict]
└── get_strategy(row) → Series (tire recommendation)

MODES
├── Circuit: 3-hour forecast, tire strategy table
└── Rally: GPX upload, per-waypoint risk assessment

API
├── Provider: Open-Meteo
├── Cache: 120 seconds TTL
└── Retry: 5 attempts, 0.2s backoff

TIRE LOGIC
├── 0.0mm = SLICKS (green)
├── 0.0-0.5mm = INTERS (orange)
└── >0.5mm = WETS (red)

GIT WORKFLOW
├── Branch: claude/*-<SESSION_ID>
├── Push: git push -u origin <branch>
└── Retry: 4 attempts (2s, 4s, 8s, 16s)
```

---

*This document is designed for AI assistants (like Claude) to understand and work with the Race Control HQ codebase effectively. It should be updated whenever significant changes are made to the code structure or functionality.*
