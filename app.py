import streamlit as st
import pandas as pd
import time

def process_csv(data):
    # Convert the uploaded data into a DataFrame
    df = pd.DataFrame(data)
    
    # Ensure the data has the required columns
    required_columns = ['OrderID', 'SKU', 'Date', 'OrderedQty', 'FoundQty', 'Status']
    if not all(col in df.columns for col in required_columns):
        raise ValueError("CSV is missing required columns")

    # Convert Date column to datetime
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Create a Month column for grouping
    df['Month'] = df['Date'].dt.to_period('M')
    
    # Calculate threshold for each SKU and month
    thresholds = []
    for sku in df['SKU'].unique():
        sku_data = df[df['SKU'] == sku]
        
        for month in sku_data['Month'].unique():
            month_data = sku_data[sku_data['Month'] == month]
            found_qty = month_data['FoundQty'].sum()
            ordered_qty = month_data['OrderedQty'].sum()
            
            # Calculate threshold based on order fulfillment
            if found_qty <= ordered_qty:
                threshold = found_qty
            else:
                threshold = ordered_qty
            
            thresholds.append({
                'SKU': sku,
                'Month': month,
                'Threshold': threshold
            })
    
    # Create a DataFrame from the thresholds
    thresholds_df = pd.DataFrame(thresholds)
    
    # Calculate average threshold per SKU
    avg_thresholds = thresholds_df.groupby('SKU')['Threshold'].mean().reset_index()
    avg_thresholds.columns = ['SKU', 'Average Threshold']
    
    # Merge with thresholds_df to get monthly data
    result_df = pd.merge(thresholds_df, avg_thresholds, on='SKU')
    
    # Sort by average threshold descending
    result_df = result_df.sort_values('Average Threshold', ascending=False)
    
    return result_df

def main():
    st.title("Inventory Threshold Calculator")
    
    # File upload section
    uploaded_file = st.file_uploader("Upload your CSV file", type=['csv'])
    if uploaded_file is not None:
        st.info("Processing the file...")
        
        # Show loading spinner
        with st.spinner("Processing..."):
            try:
                # Read the CSV file
                data = pd.read_csv(uploaded_file)
                
                # Process the data
                result_df = process_csv(data)
                
                # Display the results
                st.subheader("Processing Results")
                st.dataframe(result_df)
                
                # Create a download button
                st.markdown("### Download Results")
                csv = result_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name='inventory_thresholds.csv',
                    mime='text/csv'
                )
                
                st.success("Processing completed successfully!")
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
