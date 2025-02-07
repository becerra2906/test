import pandas as pd
import streamlit as st
from datetime import datetime

# Function to calculate threshold for each item
def calculate_threshold(df):
    # Filter orders where the found amount is equal to the ordered amount
    valid_orders = df[(df['unidades_encontradas'] == df['unidades_pedidas']) & (df['estado_item'] == 'ADDED')]

    # Group by item and calculate the maximum found amount
    thresholds = valid_orders.groupby('nombre_item')['unidades_encontradas'].max().reset_index()

    # Rename the column
    thresholds = thresholds.rename(columns={'unidades_encontradas': 'threshold'})

    return thresholds

# Function to calculate monthly thresholds
def calculate_monthly_thresholds(df):
    # Convert the creation date to datetime
    df['creacion_job'] = pd.to_datetime(df['creacion_job'])

    # Extract the month and year
    df['month'] = df['creacion_job'].dt.month
    df['year'] = df['creacion_job'].dt.year

    # Group by item, month, and year, and calculate the threshold
    monthly_thresholds = df.groupby(['nombre_item', 'onth', 'year']).apply(lambda x: calculate_threshold(x)).reset_index()

    # Pivot the table to get monthly thresholds
    monthly_thresholds = monthly_thresholds.pivot(index='nombre_item', columns='month', values='threshold')

    # Calculate the average threshold
    monthly_thresholds['average_threshold'] = monthly_thresholds.mean(axis=1)

    # Sort by average threshold in descending order
    monthly_thresholds = monthly_thresholds.sort_values(by='average_threshold', ascending=False)

    return monthly_thresholds

# Streamlit app
def main():
    st.title("Inventory Threshold Calculator")

    # Upload CSV file
    uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])

    if uploaded_file is not None:
        # Read the CSV file
        df = pd.read_csv(uploaded_file)

        # Show a loader while processing the data
        with st.spinner("Processing data..."):
            monthly_thresholds = calculate_monthly_thresholds(df)

        # Display the results
        st.write(monthly_thresholds)

        # Add a button to download the CSV file
        @st.cache
        def convert_df(df):
            return df.to_csv().encode('utf-8')

        csv = convert_df(monthly_thresholds)

        st.download_button(
            label="Download CSV",
            data=csv,
            file_name='monthly_thresholds.csv',
            mime='text/csv',
        )

if __name__ == "__main__":
    main()
