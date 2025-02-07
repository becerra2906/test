import streamlit as st
import pandas as pd

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
    
    # Ensure the required column exists and convert order_date to datetime.
    if 'order_date' not in df.columns:
        st.error("The CSV file must include an 'order_date' column.")
        return pd.DataFrame()
        
    try:
        df['order_date'] = pd.to_datetime(df['order_date'])
    except Exception as e:
        st.error(f"Error converting 'order_date' to datetime: {e}")
        return pd.DataFrame()

    # Create a 'day' column (using only the date part).
    df['day'] = df['order_date'].dt.date

    daily_thresholds = []  # List to collect the computed daily thresholds.

    # Group data by SKU.
    for sku, sku_df in df.groupby('sku'):
        # For each SKU, process day by day.
        for day, day_df in sku_df.groupby('day'):
            day_df = day_df.sort_values('order_date')
            cumulative = 0
            threshold_for_day = None

            # Process orders in the day sequentially.
            for _, row in day_df.iterrows():
                # Check if the order is fully served.
                # (An order stops the accumulation if either:
                # 1. found_quantity != ordered_quantity, or
                # 2. state equals "removed" (case-insensitive))
                if (row['found_quantity'] != row['ordered_quantity']) or (str(row.get('state', '')).lower() == 'removed'):
                    threshold_for_day = cumulative
                    break
                else:
                    cumulative += row['found_quantity']

            # If no order failed the check during the day, use the total accumulated.
            if threshold_for_day is None:
                threshold_for_day = cumulative

            daily_thresholds.append({
                'sku': sku,
                'day': day,
                'threshold': threshold_for_day
            })

    daily_df = pd.DataFrame(daily_thresholds)
    if daily_df.empty:
        st.error("No threshold data could be computed from the CSV file.")
        return daily_df

    # Group the daily thresholds by week.
    # Convert 'day' back to datetime and then get the week period.
    daily_df['week'] = pd.to_datetime(daily_df['day']).dt.to_period('W').astype(str)

    # For each SKU and each week, compute the average daily threshold.
    weekly = daily_df.groupby(['sku', 'week'])['threshold'].mean().reset_index()

    # Pivot the table so that each week is a column.
    pivot_df = weekly.pivot(index='sku', columns='week', values='threshold').reset_index()

    # Compute an overall average threshold for each SKU (across all weeks).
    week_columns = pivot_df.columns.drop('sku')
    pivot_df['Average'] = pivot_df[week_columns].mean(axis=1)

    # Sort the table descendingly by the average threshold.
    pivot_df = pivot_df.sort_values('Average', ascending=False)

    return pivot_df

def main():
    st.title("Inventory Threshold Calculator")
    st.write(
        """
        **Problem Statement:**  
        Supermarkets often face lost sales due to unnoticed low inventory in their aisles.
        This tool helps by analyzing sales data to compute the inventory threshold for each SKU.
        <br><br>
        **How It Works:**  
        1. Upload a CSV file containing your sales data.  
        2. For each SKU, the tool goes through daily orders, summing the found quantity
           for orders that were completely served until a failure (i.e. when the found quantity 
           does not match the ordered quantity or the product state is "removed") is encountered.
        3. Daily thresholds are then averaged by week to smooth out daily variances.
        4. The final table lists each SKU along with its weekly thresholds and an overall 
           average threshold (used to determine if a product may be at risk of stockout).
        """
        , unsafe_allow_html=True
    )

    # File uploader widget.
    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Error reading CSV file: {e}")
            return

        # Show a spinner while processing.
        with st.spinner("Processing data..."):
            result_df = process_csv(df)

        if not result_df.empty:
            st.success("Processing complete!")
            st.subheader("Weekly Inventory Thresholds per SKU")
            st.dataframe(result_df)

            # Prepare the CSV download.
            csv_buffer = result_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Results as CSV",
                data=csv_buffer,
                file_name="inventory_thresholds.csv",
                mime="text/csv"
            )

if __name__ == '__main__':
    main()
