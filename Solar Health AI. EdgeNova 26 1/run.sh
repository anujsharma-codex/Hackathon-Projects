#!/bin/bash
# run.sh - Quick start script for SolarPanel Health AI
# Team Optisuns

echo "☀️ SolarPanel Health AI - Team Optisuns"
echo "========================================"
echo ""

# Check if data directory exists
if [ ! -d "data" ]; then
    echo "📁 Creating data directory..."
    mkdir data
fi

# Check if data exists
if [ ! -f "data/solar_farm_data.csv" ]; then
    echo "📊 Generating sample data..."
    python app/data_generator.py
else
    echo "✅ Data already exists at data/solar_farm_data.csv"
fi

echo ""
echo "🚀 Starting Streamlit application..."
echo "🌐 Opening dashboard in your browser..."
echo ""

# Launch the app
streamlit run app/app.py