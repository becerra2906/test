import streamlit as st
import pandas as pd
import io

# -------------------------------
# Sample CSV Data (as a multi-line string)
# -------------------------------
SAMPLE_CSV = """order_date,sku,ordered_quantity,found_quantity,state
2023-01-01 08:00:00,SKU1,10,10,active
2023-01-01 09:00:00,SKU1,5,5,active
2023-01-01 10:00:00,SKU1,3,2,active
2023-01-08 08:00:00,SKU1,10,10,active
2023-01-08 09:00:00,SKU1,5,4,active
2023-01-15 08:00:00,SKU1,10,10,active
2023-01-15 09:00:00,SKU1,5,5,active
2023-02-01 08:00:00,SKU1,10,10,active
2023-02-01 09:00:00,SKU1,5,5,removed
2023-01-02 08:00:00,SKU2,7,7,active
2023-01-02 09:00:00,SKU2,8,8,active
2023-01-02 10:00:00,SKU2,4,3,active
2023-01-09 08:00:00,SKU2,7,7,active
2023-01-09 09:00:00,SKU2,8,8,active
2023-01-09 10:00:00,SKU2,4,4,active
2023-02-03 08:00:00,SKU2,7,7,active
2023-02-03 09:00:00,SKU2,8,8,active
2023-02-03 10:00:00,SKU2,4,4,active
2023-01-03 08:00:00,SKU3,5,5,active
2023-01-03 09:00:00,SKU3,3,3,active
2023-01-03 10:00:00,SKU3,6,6,active
2023-01-10 08:00:00,SKU3,5,5,active
2023-01-10 09:00:00,SKU3,3,3,active
2023-01-10 10:00:00,SKU3,6,6,active
"""

# -------------------------------
# Function to Process the CSV Data
# -------------------------------
def process_csv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process the input DataFrame to compute the inventory threshold per SKU.
    
    For each SKU on each day:
      - Orders are sorted by time.
      - The threshold is computed by summing the found_quantity for orders
        where found_quantity equals ordered_quantity (and state is not 'removed').
      - The summing stops at the first order where found_quantity != ordered_quantity
        or state is 'removed'.
    
    Daily thresholds are then grouped into weekly thresholds (averaging the days
    within each week). Finally, a pivoted table is produced where each row is a SKU,
    each column (except the first) represents a week (in "YYYY-WW" format), and the last
    column is the average threshold (across all weeks).
    """
    # Verify that the 'order_date' column exists and convert it to datetime.
    if 'order_date' not in df.columns:
        st.error("The CSV file must include an 'order_date' column.")
        return pd.DataFrame()
    try:
        df['order_date'] = pd.to_datetime(df['order_date'])
    except Exception as e:
        st.error(f"Error converting 'order_date' to datetime: {e}")
        return pd.DataFrame()
    
    # Create a 'day' column (date only, without time).
    df['day'] = df['order_date'].dt.date

    # List to store the computed daily thresholds.
    daily_thresholds = []
    
    # Group the data by SKU.
    for sku, sku_df in df.groupby('sku'):
        # For each SKU, process orders day by day.
        for day, day_df in sku_df.groupby('day'):
            day_df = day_df.sort_values('order_date')
            cumulative = 0
            threshold_for_day = None
            for _, row in day_df.iterrows():
                # Check if the order is fully served:
                # - found_quantity must equal ordered_quantity, and
                # - state should not be "removed"
                if (row['found_quantity'] != row['ordered_quantity']) or (str(row.get('state', '')).lower() == 'removed'):
                    threshold_for_day = cumulative
                    break
                else:
                    cumulative += row['found_quantity']
            # If no failure event occurred, use the total accumulated value.
            if threshold_for_day is None:
                threshold_for_day = cumulative
            daily_thresholds.append({'sku': sku, 'day': day, 'threshold': threshold_for_day})
    
    daily_df = pd.DataFrame(daily_thresholds)
    if daily_df.empty:
        st.error("No threshold data could be computed from the CSV file.")
        return daily_df
    
    # Convert the day column back to datetime to determine the week.
    daily_df['week'] = pd.to_datetime(daily_df['day']).dt.to_period('W').astype(str)
    
    # For each SKU and week, compute the average daily threshold.
    weekly = daily_df.groupby(['sku', 'week'])['threshold'].mean().reset_index()
    
    # Pivot the table so that each week becomes a column.
    pivot_df = weekly.pivot(index='sku', columns='week', values='threshold').reset_index()
    
    # Compute the overall average threshold across all weeks.
    week_columns = pivot_df.columns.drop('sku')
    pivot_df['Average'] = pivot_df[week_columns].mean(axis=1)
    
    # Sort the table descendingly by the average threshold.
    pivot_df = pivot_df.sort_values('Average', ascending=False)
    
    return pivot_df

# -------------------------------
# Main Application
# -------------------------------
def main():
    st.title("Inventory Threshold Calculator")
    st.write(
        """
        **test**
        """
        , unsafe_allow_html=True
    )
    
    # -------------------------------
    # File Upload Section
    # -------------------------------
    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Error reading CSV file: {e}")
            return
    else:
        st.info("No CSV file uploaded. You can use the sample data provided below.")
        # Provide a button to download the sample CSV file.
        st.download_button(
            "Download Sample CSV",
            data=SAMPLE_CSV,
            file_name="sample_inventory_data.csv",
            mime="text/csv"
        )
        # Provide a button to load the sample CSV data.
        if st.button("Use Sample Data"):
            df = pd.read_csv(io.StringIO(SAMPLE_CSV))
        else:
            return

    # -------------------------------
    # Process the Data & Display Results
    # -------------------------------
    with st.spinner("Processing data..."):
        result_df = process_csv(df)
    
    if not result_df.empty:
        st.success("Processing complete!")
        st.subheader("Weekly Inventory Thresholds per SKU")
        st.dataframe(result_df)
        
        # Button to download the result as CSV.
        csv_buffer = result_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download Results as CSV",
            data=csv_buffer,
            file_name="inventory_thresholds.csv",
            mime="text/csv"
        )

if __name__ == '__main__':
    main()
