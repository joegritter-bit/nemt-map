import pandas as pd
import matplotlib
matplotlib.use('Agg')  # 🟢 FIX: Forces non-interactive mode for Cron/Linux
import matplotlib.pyplot as plt
import os

PULSE_FILE = 'data/market_pulse.csv'

def generate_pulse_chart():
    if not os.path.exists(PULSE_FILE):
        print("❌ No pulse data found. Let the cron job run for a few hours first!")
        return

    # 1. Load and Clean Data
    df = pd.read_csv(PULSE_FILE)
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
    
    if 'hour' not in df.columns:
        df['hour'] = df['timestamp'].dt.hour

    # 2. Aggregation (Ensuring all 24 hours exist for the X-axis)
    hourly_avg = df.groupby('hour')['count'].mean()
    all_hours = pd.Series(0, index=range(24))
    # We use combine_first to keep our averages and fill gaps with 0
    plot_data = hourly_avg.combine_first(all_hours)

    # 3. Plotting
    plt.style.use('ggplot')
    fig, ax1 = plt.subplots(figsize=(12, 7))

    # --- PRIMARY AXIS: Hourly Bar Chart ---
    plot_data.plot(kind='bar', color='teal', edgecolor='black', alpha=0.7, ax=ax1, label='Avg Volume')
    
    # --- TREND LINE: Safety check for small datasets ---
    df = df.sort_values('timestamp')
    
    # ✅ FIX: Rolling window must be at least 1. 
    # This prevents a crash when you only have 1-4 data points.
    window_size = max(1, len(df)//5)
    df['trend'] = df['count'].rolling(window=window_size, min_periods=1).mean()
    
    # Secondary axis for the trend line
    ax2 = ax1.twinx()
    
    # ✅ FIX: For the trend line to align with bars, we map it to the 24h index
    # We only plot the trend where we actually have data points
    ax2.plot(df['hour'], df['trend'], color='crimson', marker='o', markersize=4, linewidth=2, label='Market Trend', linestyle='--')
    
    # Formatting
    ax1.set_title('NEMT Market Pulse: Hourly Volume & Trend Analysis', fontsize=16, fontweight='bold')
    ax1.set_xlabel('Hour of Day (24h Format)', fontsize=12)
    ax1.set_ylabel('Avg Trips Available (Bars)', fontsize=12, color='teal')
    ax2.set_ylabel('Volume Trend (Line)', fontsize=12, color='crimson')
    
    # Sync the scales so the line doesn't look weirdly higher than the bars
    ax2.set_ylim(ax1.get_ylim()) 
    
    ax1.set_xticks(range(24))
    ax1.set_xticklabels(range(24))
    ax1.grid(axis='y', linestyle='--', alpha=0.5)

    # Legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    # Save the chart
    output_image = "market_pulse_chart.png"
    plt.tight_layout()
    plt.savefig(output_image)
    print(f"✅ Success! Pulse & Trend chart saved as '{output_image}'")

if __name__ == "__main__":
    generate_pulse_chart()