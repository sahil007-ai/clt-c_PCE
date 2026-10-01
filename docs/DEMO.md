# Demo guide

Create a virtual environment, install dependencies, then run the dashboard:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The sidebar can compare normal planning with a charger failure, late return,
price spike, and blocked missing-battery-data scenario. Every selected proposal
shows the independent check result and data provenance.

For a terminal-only walkthrough:

```bash
python -m scripts.demo
python -m evaluation.run --seed 42 --scenarios 50
pytest
```

The evaluation command writes a timestamped local result under
`evaluation/results/`; these result files are intentionally not versioned.
