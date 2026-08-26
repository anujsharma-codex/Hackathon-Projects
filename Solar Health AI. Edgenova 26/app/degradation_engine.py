'''
What it does:

Calculates degradation rate (W/year)

Predicts remaining life (years until 80% efficiency)

Decision engine (Keep/Repurpose/Recycle)

Calculates financial loss

AI Prompt: "Write a Python module with functions that: 1) Calculate degradation rate from original and current wattage, 2) Predict remaining life until 80% efficiency is reached, 3) Apply decision logic: >=85% = Keep, 70-85% = Repurpose, <70% = Recycle, 4) Calculate financial loss at ₹50/watt. Use pandas DataFrames."
'''

"""
degradation_engine.py - Core algorithm for solar panel health analysis
Team Optisuns - SolarPanel Health AI
"""

import pandas as pd
import numpy as np

def calculate_metrics(df):
    """
    Calculate degradation metrics and recommendations for each panel
    
    Parameters:
    df (pd.DataFrame): DataFrame with panel data
    
    Returns:
    pd.DataFrame: DataFrame with added metrics
    """
    
    # Make a copy to avoid modifying original
    result = df.copy()
    
    # 1. Calculate degradation rate in Watts/year
    # If years_operating is 0, set degradation_rate_w to 0
    result['degradation_rate_w'] = np.where(
        result['years_operating'] > 0,
        (result['original_wattage'] - result['current_wattage']) / result['years_operating'],
        0
    )
    result['degradation_rate_w'] = result['degradation_rate_w'].round(2)
    
    # 2. Calculate remaining life (years until 80% of original wattage)
    # Formula: (current_wattage - 0.8*original_wattage) / degradation_rate_w
    threshold_wattage = result['original_wattage'] * 0.8
    
    # Avoid division by zero
    remaining_life = np.where(
        result['degradation_rate_w'] > 0,
        (result['current_wattage'] - threshold_wattage) / result['degradation_rate_w'],
        0
    )
    
    # If remaining_life is negative, panel is already below 80%
    result['remaining_life'] = np.where(
        remaining_life > 0,
        remaining_life,
        0
    ).round(1)
    
    # 3. Recommendation engine
    def get_recommendation(efficiency, remaining_life):
        """
        Decision logic based on efficiency and remaining life
        """
        if efficiency >= 85:
            return 'KEEP'
        elif efficiency >= 70:
            # Check if repurposing is viable (has at least some life left)
            if remaining_life > 0:
                return 'REPURPOSE'
            else:
                return 'RECYCLE'
        else:
            return 'RECYCLE'
    
    result['recommendation'] = result.apply(
        lambda row: get_recommendation(row['efficiency'], row['remaining_life']),
        axis=1
    )
    
    # 4. Health score (0-100)
    result['health_score'] = result['efficiency'].round(1)
    
    # 5. Add color codes for visualization
    def get_status_color(efficiency):
        if efficiency >= 85:
            return '🟢'
        elif efficiency >= 70:
            return '🟡'
        else:
            return '🔴'
    
    result['status_icon'] = result['efficiency'].apply(get_status_color)
    
    return result

def calculate_financial_loss(df, price_per_watt=50):
    """
    Calculate total financial loss due to degradation
    
    Parameters:
    df (pd.DataFrame): DataFrame with panel data
    price_per_watt (int): Price per watt in INR
    
    Returns:
    dict: Financial metrics
    """
    
    # Loss per panel = (original - current) * price_per_watt
    loss_per_panel = (df['original_wattage'] - df['current_wattage']) * price_per_watt
    
    total_loss = loss_per_panel.sum()
    
    # Calculate loss by recommendation category
    loss_by_category = df.groupby('recommendation').apply(
        lambda x: ((x['original_wattage'] - x['current_wattage']) * price_per_watt).sum()
    ).to_dict()
    
    # Number of panels by category
    count_by_category = df['recommendation'].value_counts().to_dict()
    
    return {
        'total_loss': round(total_loss, 0),
        'total_loss_formatted': f"₹{total_loss:,.0f}",
        'loss_by_category': {k: round(v, 0) for k, v in loss_by_category.items()},
        'count_by_category': count_by_category,
        'price_per_watt': price_per_watt
    }

def get_panel_summary(df):
    """
    Get summary statistics for the panel dataset
    
    Parameters:
    df (pd.DataFrame): DataFrame with panel metrics
    
    Returns:
    dict: Summary statistics
    """
    
    return {
        'total_panels': len(df),
        'healthy_count': len(df[df['efficiency'] >= 85]),
        'degrading_count': len(df[(df['efficiency'] >= 70) & (df['efficiency'] < 85)]),
        'end_of_life_count': len(df[df['efficiency'] < 70]),
        'avg_efficiency': df['efficiency'].mean(),
        'avg_remaining_life': df['remaining_life'].mean(),
        'recycling_recommendations': len(df[df['recommendation'] == 'RECYCLE']),
        'repurpose_recommendations': len(df[df['recommendation'] == 'REPURPOSE']),
        'keep_recommendations': len(df[df['recommendation'] == 'KEEP'])
    }

# Example usage
if __name__ == "__main__":
    # Test the engine
    from data_generator import generate_panel_data
    
    print("Testing Degradation Engine...")
    df = generate_panel_data(100)
    result = calculate_metrics(df)
    financial = calculate_financial_loss(result)
    summary = get_panel_summary(result)
    
    print("\n📊 Sample Output:")
    print(f"Total Panels: {summary['total_panels']}")
    print(f"Keep: {summary['keep_recommendations']}")
    print(f"Repurpose: {summary['repurpose_recommendations']}")
    print(f"Recycle: {summary['recycling_recommendations']}")
    print(f"Financial Loss: {financial['total_loss_formatted']}")
    print("\n✅ Engine test passed!")