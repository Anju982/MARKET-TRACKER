import pandas as pd
import plotly.graph_objects as go
from typing import List

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate common technical indicators: SMA, EMA, RSI, Bollinger Bands.
    Expects 'df' to have a 'price' column.
    """
    if df.empty or 'price' not in df.columns:
        return df

    # SMA
    df['SMA_20'] = df['price'].rolling(window=20).mean()
    df['SMA_50'] = df['price'].rolling(window=50).mean()

    # EMA
    df['EMA_20'] = df['price'].ewm(span=20, adjust=False).mean()

    # RSI (14)
    delta = df['price'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    # Handle division by zero or NaN
    df['RSI_14'] = df['RSI_14'].fillna(50) 

    # Bollinger Bands (20, 2)
    df['BB_Mid'] = df['price'].rolling(window=20).mean()
    df['BB_Std'] = df['price'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Mid'] + (df['BB_Std'] * 2)
    df['BB_Lower'] = df['BB_Mid'] - (df['BB_Std'] * 2)

    return df

def add_indicators_to_fig(fig: go.Figure, df: pd.DataFrame, selected_indicators: List[str]):
    """
    Adds traces for selected technical indicators to an existing Plotly figure.
    """
    if df.empty:
        return

    # Secondary Y-axis for RSI if needed, but for now let's plot overlays on the main price chart
    # Note: RSI is 0-100, while prices vary. We might need a subplot for RSI.
    
    # Simple Overlays
    if "SMA 20" in selected_indicators:
        fig.add_trace(go.Scatter(x=df['date'], y=df['SMA_20'], name="SMA 20", line=dict(color='#ff9f43', width=1.5)))
    
    if "SMA 50" in selected_indicators:
        fig.add_trace(go.Scatter(x=df['date'], y=df['SMA_50'], name="SMA 50", line=dict(color='#ee5253', width=1.5)))

    if "EMA 20" in selected_indicators:
        fig.add_trace(go.Scatter(x=df['date'], y=df['EMA_20'], name="EMA 20", line=dict(color='#5f27cd', width=1.5, dash='dash')))

    if "Bollinger Bands" in selected_indicators:
        fig.add_trace(go.Scatter(x=df['date'], y=df['BB_Upper'], name="BB Upper", line=dict(color='rgba(173, 216, 230, 0.4)', width=1)))
        fig.add_trace(go.Scatter(x=df['date'], y=df['BB_Lower'], name="BB Lower", line=dict(color='rgba(173, 216, 230, 0.4)', width=1), fill='tonexty', fillcolor='rgba(173, 216, 230, 0.1)'))

    # RSI usually needs its own subplot or a separate plot area. 
    # For now, let's keep it simple. If RSI is selected, we might want to return it as a separate info if we can't subplot easily here without refactoring the whole fig creation.
    # Actually, let's just add it as a trace for now, though scales will be off. 
    # A better way is to handle subplots in the caller or here.
