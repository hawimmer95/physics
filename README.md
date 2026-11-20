# Physik-Trainer

Interactive study aid for a lower-secondary school physics exam, built with Streamlit.
The app itself is in German, matching the class it was made for.

Topics covered:

- Speed (`v = s/t`, converting between m/s and km/h)
- Uniform and accelerated motion, including s-t and v-t diagrams
- Inertia and mass (unit conversion between kg, dag and g)
- Force and weight on Earth and on the Moon
- Friction (static, sliding and rolling, conceptual only)
- Newton's laws
- Free fall

Each topic starts with an intuitive explanation, followed by interactive sliders and charts,
randomly generated practice problems with step-by-step solutions, and a short quiz.

## Run locally

Requires [uv](https://docs.astral.sh/uv/).

```
uv sync
uv run streamlit run app.py
```

Then open http://localhost:8501.

## Deploy

The app can be hosted for free on [Streamlit Community Cloud](https://share.streamlit.io):
create an app from this repository, branch `main`, main file `app.py`.
Dependencies are installed from `uv.lock`.
