# ☀️ SolarPanel Health AI

## Data-Driven Solar Panel Lifecycle Management

**Team Optisuns**

---

## 🎯 What is SolarPanel Health AI?

SolarPanel Health AI is a decision engine that tracks individual solar panel health and recommends:

- ✅ **KEEP** - Panel is performing well (≥85% efficiency)
- 🔄 **REPURPOSE** - Panel can be used for secondary applications (70-85% efficiency)
- ♻️ **RECYCLE** - Panel has reached end-of-life (<70% efficiency)

### Why This Matters

- 78 million tons of solar e-waste expected by 2050
- 90% of functional panels are prematurely discarded
- ₹2-3 Crore lost per farm annually
- No system for individual panel health tracking

---

## 🚀 Quick Start

### 1. Clone or Download
```bash
git clone https://github.com/yourusername/solarpanel-health-ai.git
cd solarpanel-health-ai

--------------------------------------------------------------------------------------
app.py initial content


Purpose: The main Streamlit dashboard

What it does:

Displays metrics (total panels, healthy, degrading, end-of-life)

Shows distribution charts (bar chart, pie chart)

Panel detail view with QR code

Recommendation summary table

Financial impact display

AI Prompt: "Write a Streamlit app for a solar panel health monitoring dashboard. It should: 
1) Allow CSV upload or use demo data, 
2) Show metrics in columns (total, healthy, degrading, end-of-life, financial loss), 
3) Display a histogram and pie chart of panel health, 
4) Allow searching individual panels and show details with QR code, 
5) Show recommendations summary table. Use plotly for charts."

app.py - Streamlit Dashboard for SolarPanel Health AI
Team Optisuns - SolarPanel Health AI

---------------------------------
To Run the application
---------------------------------
# On Mac/Linux
./run.sh

# On Windows
python app/data_generator.py
streamlit run app/app.py
---------------------------------

Design note: this dashboard is styled as a "fleet control room" for a solar
farm operator — dark instrument-panel surfaces, an amber energy accent, and
monospace numerals for anything that reads like a live readout. The theme
tokens live in .streamlit/config.toml (native widgets) and in the CSS block
below (layout/typography). Change TOKENS below to re-theme everything.
"""