# Streamlit App (Performance / Analytics)

Simple Streamlit application for interactive performance/analytics exploration.

## Prerequisites
- Python 3.9+ (recommended)
- pip (or pipx / uv)
- (macOS only, for watchdog native build) Xcode Command Line Tools

## Install
```bash
# (optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install streamlit watchdog
```

If watchdog fails to build on macOS:
```bash
xcode-select --install
pip install watchdog
```

## Quick Test
```bash
streamlit hello
```

## Run This Project
```bash
streamlit run /Users/pierolivierletourneau/Documents/GitHub/MASTER/ANALYTIQUE/performance/streamlit/Hello.py
# Pass arguments to your script after a -- separator, e.g.:
streamlit run path/to/app.py -- --config config.yml
```

After launch:
- Local URL: http://localhost:8501
- Network URL (auto-shown): use for devices on same LAN

## Recommended Script Structure (example)
```python
import streamlit as st

@st.cache_data
def load_data():
    ...

def main():
    st.title("Performance Dashboard")
    tab1, tab2 = st.tabs(["Overview", "Details"])
    with tab1:
        ...
    with tab2:
        ...
if __name__ == "__main__":
    main()
```

## Performance Tips
- Use st.cache_data for pure data loads
- Use st.cache_resource for models / DB connections
- Avoid large dataframe re-renders (prefer filtering client-side via st.dataframe)
- Batch API calls; avoid inside loops
- Use smaller image assets / lazy load where possible

## Hot Reload Optimization
Installing watchdog gives faster, more reliable file change detection:
```bash
pip install watchdog
```

## Project Structure (suggested)
```
performance/
  streamlit_test.py
  data/
  components/
  utils/
  requirements.txt
  README.md
```

## Dependency Freezing
```bash
pip freeze > requirements.txt
```

## Troubleshooting
- App not updating: ensure no long blocking loops; consider st.spinner + threads
- Stale data: clear cache (menu) or use st.cache_data(ttl=...)
- Port busy: run with --server.port 8502

## Next Steps
- Add authentication (e.g. streamlit-authenticator)
- Containerize (Docker) for deployment
- Integrate with a database (PostgreSQL, DuckDB, etc.)

## Reference
Docs: https://docs.streamlit.io/
Component Gallery: https://streamlit.io/components