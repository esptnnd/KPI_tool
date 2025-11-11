import streamlit as st
import pandas as pd
import os
import zipfile
import tempfile
from lib.KPI import process_kpi_logs
import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Initialize session state to store data across page loads
if 'page' not in st.session_state:
    st.session_state.page = 'upload'
if 'KPI_5G_BEFORE' not in st.session_state:
    st.session_state.KPI_5G_BEFORE = pd.DataFrame()
if 'KPI_5G_AFTER' not in st.session_state:
    st.session_state.KPI_5G_AFTER = pd.DataFrame()
if 'KPI_LTE_BEFORE' not in st.session_state:
    st.session_state.KPI_LTE_BEFORE = pd.DataFrame()
if 'KPI_LTE_AFTER' not in st.session_state:
    st.session_state.KPI_LTE_AFTER = pd.DataFrame()
if 'date_columns' not in st.session_state:
    st.session_state.date_columns = []
if 'date_columns_lte' not in st.session_state:
    st.session_state.date_columns_lte = []
if 'all_counters' not in st.session_state:
    st.session_state.all_counters = []
if 'all_counters_lte' not in st.session_state:
    st.session_state.all_counters_lte = []
if 'all_nodenames' not in st.session_state:
    st.session_state.all_nodenames = []
if 'all_nodenames_lte' not in st.session_state:
    st.session_state.all_nodenames_lte = []
if 'aggregation_mode' not in st.session_state:
    st.session_state.aggregation_mode = 'ALL'

# Helper function to aggregate data
def aggregate_data(data, group_mode, method):
    """
    Aggregate data based on group mode and aggregation method
    group_mode: 'ALL', 'NODENAME', 'OBJECT'
    method: 'AVERAGE', 'MAX', 'MIN', 'SUM'
    """
    if data.empty:
        return data
    
    # Create a copy to avoid modifying original data
    df = data.copy()
    
    # Identify date columns (excluding NODENAME, Object, Counter)
    date_columns = [col for col in df.columns if col not in ['NODENAME', 'Object', 'Counter']]
    
    # Perform aggregation based on group_mode
    if group_mode == 'ALL':
        # Aggregate all data together
        agg_funcs = {
            'AVERAGE': 'mean',
            'MAX': 'max',
            'MIN': 'min',
            'SUM': 'sum'
        }
        
        agg_func = agg_funcs.get(method, 'mean')
        
        # Apply aggregation to date columns only
        result_data = {}
        result_data['NODENAME'] = ['ALL']  # Single row for all aggregated data
        result_data['Object'] = [df['Object'].iloc[0]]  # Use first object
        result_data['Counter'] = [df['Counter'].iloc[0]]  # Use first counter
        
        for col in date_columns:
            values = pd.to_numeric(df[col], errors='coerce')
            if agg_func == 'mean':
                result_data[col] = [values.mean()]
            elif agg_func == 'max':
                result_data[col] = [values.max()]
            elif agg_func == 'min':
                result_data[col] = [values.min()]
            elif agg_func == 'sum':
                result_data[col] = [values.sum()]
        
        return pd.DataFrame(result_data)
    
    elif group_mode == 'NODENAME':
        # Group by NODENAME and aggregate
        agg_funcs = {
            'AVERAGE': 'mean',
            'MAX': 'max', 
            'MIN': 'min',
            'SUM': 'sum'
        }
        
        agg_func = agg_funcs.get(method, 'mean')
        
        # Convert date columns to numeric before aggregation
        for col in date_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Group by NODENAME, Object, and Counter, then aggregate date columns
        group_cols = ['NODENAME', 'Object', 'Counter']
        aggregated = df.groupby(group_cols)[date_columns].agg(agg_func).reset_index()
        return aggregated
    
    elif group_mode == 'OBJECT':
        # Group by Object and aggregate
        agg_funcs = {
            'AVERAGE': 'mean',
            'MAX': 'max',
            'MIN': 'min',
            'SUM': 'sum'
        }
        
        agg_func = agg_funcs.get(method, 'mean')
        
        # Convert date columns to numeric before aggregation
        for col in date_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Group by Object and Counter, then aggregate date columns - keeping NODENAME as well
        group_cols = ['Object', 'Counter']
        aggregated = df.groupby(group_cols)[date_columns].agg(agg_func).reset_index()
        
        # Add a placeholder for NODENAME since we're grouping by Object
        aggregated['NODENAME'] = 'AGGREGATED_BY_OBJECT'
        return aggregated
    
    else:
        # Default to no aggregation
        return data

# Function to go to visualization page
def go_to_visualization():
    st.session_state.page = 'chart_analysis_5g'  # Default to 5G chart analysis page

# Main application based on current page
if st.session_state.page == 'upload':
    # App title
    st.title("KPI Comparison Tool - Upload Page")

    # Section for user inputs
    st.header("Input Parameters")

    # Note about folder structure
    st.info("Note: Upload a ZIP file containing 'Before' and 'After' subdirectories with log files.")

    # Upload ZIP file containing Before and After directories
    uploaded_zip = st.file_uploader("Upload ZIP file with 'Before' and 'After' directories:", type=["zip"])

    if uploaded_zip is not None:
        # Define BEFORE_TIME and AFTER_TIME
        before_time = st.text_input("BEFORE_TIME (format: YYYY-MM-DD HH:MM or 'NO_START'):", value="NO_START")
        after_time = st.text_input("AFTER_TIME (format: YYYY-MM-DD HH:MM or 'NO_START'):", value="NO_START")

        # Button to trigger processing
        if st.button("Process KPI Logs and Go to Visualization"):
            with st.spinner("Processing KPI logs..."):
                # Create temporary directory to extract the ZIP file
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Extract the ZIP file to the temporary directory
                    with zipfile.ZipFile(uploaded_zip, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    # Define the Before and After paths
                    folder_before = os.path.join(temp_dir, "Before")
                    folder_after = os.path.join(temp_dir, "After")
                    
                    # Validate that both directories exist in the extracted ZIP
                    before_exists = os.path.isdir(folder_before)
                    after_exists = os.path.isdir(folder_after)
                    
                    if not before_exists:
                        st.error(f"'Before' folder does not exist in the uploaded ZIP file: {folder_before}")
                    elif not after_exists:
                        st.error(f"'After' folder does not exist in the uploaded ZIP file: {folder_after}")
                    else:
                        # Process KPI logs with progress indication
                        progress_bar = st.progress(0)
                        
                        # Process 5G BEFORE data
                        progress_bar.progress(20, text="Processing 5G BEFORE data...")
                        KPI_5G_BEFORE = process_kpi_logs(folder_before, "GREP_KPI_5G", before_time)
                        
                        # Process 5G AFTER data
                        progress_bar.progress(40, text="Processing 5G AFTER data...")
                        KPI_5G_AFTER = process_kpi_logs(folder_after, "GREP_KPI_5G", after_time)
                        
                        # Process LTE BEFORE data
                        progress_bar.progress(60, text="Processing LTE BEFORE data...")
                        KPI_LTE_BEFORE = process_kpi_logs(folder_before, "GREP_KPI_LTE", before_time)
                        
                        # Process LTE AFTER data
                        progress_bar.progress(80, text="Processing LTE AFTER data...")
                        KPI_LTE_AFTER = process_kpi_logs(folder_after, "GREP_KPI_LTE", after_time)
                        
                        # Store 5G data in session state
                        st.session_state.KPI_5G_BEFORE = KPI_5G_BEFORE
                        st.session_state.KPI_5G_AFTER = KPI_5G_AFTER
                        
                        # Store LTE data in session state
                        st.session_state.KPI_LTE_BEFORE = KPI_LTE_BEFORE
                        st.session_state.KPI_LTE_AFTER = KPI_LTE_AFTER
                        
                        # Get 5G date columns
                        date_columns = [col for col in KPI_5G_BEFORE.columns if col not in ['NODENAME', 'Object', 'Counter']]
                        st.session_state.date_columns = date_columns
                        
                        # Get 5G unique counters for charting
                        if not KPI_5G_BEFORE.empty:
                            unique_counters = KPI_5G_BEFORE['Counter'].unique()
                        else:
                            unique_counters = []
                        
                        if not KPI_5G_AFTER.empty:
                            unique_counters_after = KPI_5G_AFTER['Counter'].unique()
                            all_counters = list(set(list(unique_counters) + list(unique_counters_after)))
                        else:
                            all_counters = list(unique_counters)
                        
                        st.session_state.all_counters = all_counters
                        
                        # Get 5G unique nodenames for selection
                        if not KPI_5G_BEFORE.empty:
                            unique_nodenames_before = KPI_5G_BEFORE['NODENAME'].unique()
                        else:
                            unique_nodenames_before = []
                        
                        if not KPI_5G_AFTER.empty:
                            unique_nodenames_after = KPI_5G_AFTER['NODENAME'].unique()
                        else:
                            unique_nodenames_after = []
                        
                        all_nodenames = list(set(list(unique_nodenames_before) + list(unique_nodenames_after)))
                        st.session_state.all_nodenames = all_nodenames
                        
                        # Get LTE date columns
                        date_columns_lte = [col for col in KPI_LTE_BEFORE.columns if col not in ['NODENAME', 'Object', 'Counter']]
                        st.session_state.date_columns_lte = date_columns_lte
                        
                        # Get LTE unique counters for charting
                        if not KPI_LTE_BEFORE.empty:
                            unique_counters_lte = KPI_LTE_BEFORE['Counter'].unique()
                        else:
                            unique_counters_lte = []
                        
                        if not KPI_LTE_AFTER.empty:
                            unique_counters_after_lte = KPI_LTE_AFTER['Counter'].unique()
                            all_counters_lte = list(set(list(unique_counters_lte) + list(unique_counters_after_lte)))
                        else:
                            all_counters_lte = list(unique_counters_lte)
                        
                        st.session_state.all_counters_lte = all_counters_lte
                        
                        # Get LTE unique nodenames for selection
                        if not KPI_LTE_BEFORE.empty:
                            unique_nodenames_before_lte = KPI_LTE_BEFORE['NODENAME'].unique()
                        else:
                            unique_nodenames_before_lte = []
                        
                        if not KPI_LTE_AFTER.empty:
                            unique_nodenames_after_lte = KPI_LTE_AFTER['NODENAME'].unique()
                        else:
                            unique_nodenames_after_lte = []
                        
                        all_nodenames_lte = list(set(list(unique_nodenames_before_lte) + list(unique_nodenames_after_lte)))
                        st.session_state.all_nodenames_lte = all_nodenames_lte
                        
                        # Show the dataframes
                        st.subheader("KPI 5G BEFORE Data")
                        st.dataframe(KPI_5G_BEFORE)
                        
                        st.subheader("KPI 5G AFTER Data")
                        st.dataframe(KPI_5G_AFTER)
                        
                        st.subheader("KPI LTE BEFORE Data")
                        st.dataframe(KPI_LTE_BEFORE)
                        
                        st.subheader("KPI LTE AFTER Data")
                        st.dataframe(KPI_LTE_AFTER)
                        
                        progress_bar.progress(100, text="Processing complete!")
                        
                        # Go to visualization page
                        go_to_visualization()
                        st.rerun()

else:  # Visualization pages
    # Create sidebar for navigation (only shown after upload)
    st.sidebar.title("Navigation")
    page_selection = st.sidebar.radio("Go to", [
        "[KPI 5G] CHART ANALYSIS", 
        "[KPI 5G] TOP 10 HIGH/LOWEST KPI Specific Analysis",
        "[KPI LTE] CHART ANALYSIS", 
        "[KPI LTE] TOP 10 HIGH/LOWEST KPI Specific Analysis"
    ])
    
    if page_selection == "[KPI 5G] CHART ANALYSIS":
        st.session_state.page = "chart_analysis_5g"
    elif page_selection == "[KPI 5G] TOP 10 HIGH/LOWEST KPI Specific Analysis":
        st.session_state.page = "top10_analysis_5g"
    elif page_selection == "[KPI LTE] CHART ANALYSIS":
        st.session_state.page = "chart_analysis_lte"
    elif page_selection == "[KPI LTE] TOP 10 HIGH/LOWEST KPI Specific Analysis":
        st.session_state.page = "top10_analysis_lte"

# Handle the visualization pages
if st.session_state.page == 'chart_analysis_5g':
    st.title("KPI Comparison Tool - [KPI 5G] CHART ANALYSIS")
    
    # Back button to upload page
    if st.button("Back to Upload Page"):
        st.session_state.page = 'upload'
        st.rerun()
    
    # Check if data exists
    if st.session_state.KPI_5G_BEFORE.empty or st.session_state.KPI_5G_AFTER.empty:
        st.error("No data available. Please go back and upload a ZIP file first.")
        st.stop()
    
    # Custom chart visualization inputs
    st.subheader("Custom Chart Configuration")
    
    # Date range selection using slider
    if st.session_state.date_columns:
        # Create a slider for date range selection
        date_range_indices = st.slider(
            "Select date range:", 
            min_value=0, 
            max_value=len(st.session_state.date_columns)-1, 
            value=(0, len(st.session_state.date_columns)-1),
            format="%s",
            key="date_range_slider"
        )
        
        start_idx, end_idx = date_range_indices
        start_date = st.session_state.date_columns[start_idx]
        end_date = st.session_state.date_columns[end_idx]
    else:
        st.error("No date columns available for visualization.")
        st.stop()
    
    # Aggregation Mode control (global)
    st.session_state.aggregation_mode = st.selectbox(
        "Aggregation Mode (applies to all charts):",
        options=["ALL", "NODENAME", "OBJECT"],
        index=["ALL", "NODENAME", "OBJECT"].index(st.session_state.aggregation_mode),
        key="agg_mode_select"
    )
    
    # Add "All" option for NODENAME selection
    all_nodenames_with_all = ["All"] + st.session_state.all_nodenames
    selected_options = st.multiselect("Select NODENAMES to include in charts:", 
                                      options=all_nodenames_with_all, 
                                      default=["All"] if st.session_state.all_nodenames else [],
                                      key="selected_nodenames")
    
    # Handle "All" selection
    if "All" in selected_options:
        selected_nodenames = st.session_state.all_nodenames
    else:
        selected_nodenames = selected_options

    # Get data from session state
    KPI_5G_BEFORE = st.session_state.KPI_5G_BEFORE
    KPI_5G_AFTER = st.session_state.KPI_5G_AFTER

    # Get the date columns for chart visualization
    date_columns = st.session_state.date_columns[start_idx:end_idx+1]

    # Generate charts for each counter with interactivity
    st.info(f"Generating charts for {len(st.session_state.all_counters)} counters...")
    progress_bar = st.progress(0)
    total_counters = len(st.session_state.all_counters)
    
    for idx, counter in enumerate(st.session_state.all_counters):
        # Update progress bar
        progress_percentage = int((idx / total_counters) * 100)
        progress_bar.progress(progress_percentage / 100, text=f"Processing counter {idx + 1} of {total_counters}: {counter}")
        st.subheader(f"Charts for Counter: {counter}")
        
        # Per-chart aggregation method selector
        agg_method = st.selectbox(
            f"Aggregation Method for {counter}:",
            options=["AVERAGE", "MAX", "MIN", "SUM"],
            index=0,  # Default to AVERAGE
            key=f"agg_method_{counter}"
        )

        # Filter data for the specific counter
        if counter in KPI_5G_BEFORE['Counter'].values:
            before_data = KPI_5G_BEFORE[KPI_5G_BEFORE['Counter'] == counter]
            # Filter by selected nodenames
            before_data = before_data[before_data['NODENAME'].isin(selected_nodenames)]
            
            # Apply aggregation based on user selection
            before_data = aggregate_data(before_data, st.session_state.aggregation_mode, agg_method)

            # Create line chart for BEFORE data
            if not before_data.empty:
                # Prepare data for plotting
                before_plot_data = before_data[date_columns].T
                before_plot_data.columns = before_data['NODENAME'].values
                before_plot_data.index.name = 'Datetime'
                before_plot_data = before_plot_data.reset_index()

                # Convert all nodename columns to numeric, handling non-numeric values
                for col in before_data['NODENAME'].values:
                    if col in before_plot_data.columns:
                        before_plot_data[col] = pd.to_numeric(before_plot_data[col], errors='coerce')

                # Create line chart
                chart_title = f"BEFORE - {counter} (Aggregation: {st.session_state.aggregation_mode} / {agg_method})"
                fig_before = px.line(
                    before_plot_data,
                    x='Datetime',
                    y=before_plot_data.columns.tolist()[1:],  # All columns except Datetime
                    title=chart_title,
                    labels={'value': 'Counter Value', 'variable': 'NODENAME'}
                )
                
                # Show the chart
                st.plotly_chart(fig_before, use_container_width=True, key=f"before_chart_{counter}")

        if counter in KPI_5G_AFTER['Counter'].values:
            after_data = KPI_5G_AFTER[KPI_5G_AFTER['Counter'] == counter]
            # Filter by selected nodenames
            after_data = after_data[after_data['NODENAME'].isin(selected_nodenames)]
            
            # Apply aggregation based on user selection
            after_data = aggregate_data(after_data, st.session_state.aggregation_mode, agg_method)

            # Create line chart for AFTER data
            if not after_data.empty:
                # Prepare data for plotting
                after_plot_data = after_data[date_columns].T
                after_plot_data.columns = after_data['NODENAME'].values
                after_plot_data.index.name = 'Datetime'
                after_plot_data = after_plot_data.reset_index()

                # Convert all nodename columns to numeric, handling non-numeric values
                for col in after_data['NODENAME'].values:
                    if col in after_plot_data.columns:
                        after_plot_data[col] = pd.to_numeric(after_plot_data[col], errors='coerce')

                # Create line chart
                chart_title = f"AFTER - {counter} (Aggregation: {st.session_state.aggregation_mode} / {agg_method})"
                fig_after = px.line(
                    after_plot_data,
                    x='Datetime',
                    y=after_plot_data.columns.tolist()[1:],  # All columns except Datetime
                    title=chart_title,
                    labels={'value': 'Counter Value', 'variable': 'NODENAME'}
                )

                # Show the chart
                st.plotly_chart(fig_after, use_container_width=True, key=f"after_chart_{counter}")
    
    # Complete progress bar
    progress_bar.progress(100, text="All charts generated successfully!")

elif st.session_state.page == 'top10_analysis_5g':
    st.title("KPI Comparison Tool - [KPI 5G] TOP 10 HIGH/LOWEST KPI Specific Analysis")
    
    # Back button to upload page
    if st.button("Back to Upload Page"):
        st.session_state.page = 'upload'
        st.rerun()
    
    # Check if data exists
    if st.session_state.KPI_5G_BEFORE.empty or st.session_state.KPI_5G_AFTER.empty:
        st.error("No data available. Please go back and upload a ZIP file first.")
        st.stop()
    
    # Add "All" option for NODENAME selection
    all_nodenames_with_all = ["All"] + st.session_state.all_nodenames
    selected_options = st.multiselect("Select NODENAMES to include in analysis:", 
                                      options=all_nodenames_with_all, 
                                      default=["All"] if st.session_state.all_nodenames else [],
                                      key="top10_selected_nodenames")
    
    # Handle "All" selection
    if "All" in selected_options:
        selected_nodenames = st.session_state.all_nodenames
    else:
        selected_nodenames = selected_options

    # Date range selection using slider for analysis page
    if st.session_state.date_columns:
        # Create a slider for date range selection
        date_range_indices = st.slider(
            "Select date range for analysis:", 
            min_value=0, 
            max_value=len(st.session_state.date_columns)-1, 
            value=(0, len(st.session_state.date_columns)-1),
            format="%s",
            key="top10_date_range_slider"
        )
        
        start_idx, end_idx = date_range_indices
        start_date = st.session_state.date_columns[start_idx]
        end_date = st.session_state.date_columns[end_idx]
    else:
        st.error("No date columns available for visualization.")
        st.stop()

    # Get data from session state
    KPI_5G_BEFORE = st.session_state.KPI_5G_BEFORE
    KPI_5G_AFTER = st.session_state.KPI_5G_AFTER

    # Get the date columns for chart visualization
    date_columns = st.session_state.date_columns[start_idx:end_idx+1]

    # Generate analysis for each counter
    for counter in st.session_state.all_counters:
        st.subheader(f"Analysis for Counter: {counter}")
        
        # Datetime selection for analysis
        selected_datetime = st.selectbox(f"Select datetime to analyze for {counter}:", 
                                         options=date_columns, 
                                         key=f"top10_datetime_select_{counter}")
        
        # Show top/bottom performers for the selected datetime
        if counter in KPI_5G_BEFORE['Counter'].values:
            before_data = KPI_5G_BEFORE[KPI_5G_BEFORE['Counter'] == counter]
            before_data = before_data[before_data['NODENAME'].isin(selected_nodenames)]
            
            if not before_data.empty and selected_datetime in before_data.columns:
                # Get data for the selected datetime
                datetime_data = before_data[['NODENAME', selected_datetime]].copy()
                # Convert the selected datetime column to numeric, handling non-numeric values
                datetime_data[selected_datetime] = pd.to_numeric(datetime_data[selected_datetime], errors='coerce')
                datetime_data = datetime_data.dropna()  # Remove rows with non-numeric values
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Show top 10 lowest performers (sorted ascending)
                    top_lowest = datetime_data.nsmallest(10, selected_datetime)
                    st.write(f"**Top 10 LOWEST performers at {selected_datetime} - BEFORE**")
                    st.dataframe(top_lowest)
                
                with col2:
                    # Show top 10 highest performers (sorted descending)
                    top_highest = datetime_data.nlargest(10, selected_datetime)
                    st.write(f"**Top 10 HIGHEST performers at {selected_datetime} - BEFORE**")
                    st.dataframe(top_highest)
        
        if counter in KPI_5G_AFTER['Counter'].values:
            after_data = KPI_5G_AFTER[KPI_5G_AFTER['Counter'] == counter]
            after_data = after_data[after_data['NODENAME'].isin(selected_nodenames)]
            
            if not after_data.empty and selected_datetime in after_data.columns:
                # Get data for the selected datetime
                datetime_data = after_data[['NODENAME', selected_datetime]].copy()
                # Convert the selected datetime column to numeric, handling non-numeric values
                datetime_data[selected_datetime] = pd.to_numeric(datetime_data[selected_datetime], errors='coerce')
                datetime_data = datetime_data.dropna()  # Remove rows with non-numeric values
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Show top 10 lowest performers (sorted ascending)
                    top_lowest = datetime_data.nsmallest(10, selected_datetime)
                    st.write(f"**Top 10 LOWEST performers at {selected_datetime} - AFTER**")
                    st.dataframe(top_lowest)
                
                with col2:
                    # Show top 10 highest performers (sorted descending)
                    top_highest = datetime_data.nlargest(10, selected_datetime)
                    st.write(f"**Top 10 HIGHEST performers at {selected_datetime} - AFTER**")
                    st.dataframe(top_highest)

elif st.session_state.page == 'chart_analysis_lte':
    st.title("KPI Comparison Tool - [KPI LTE] CHART ANALYSIS")
    
    # Back button to upload page
    if st.button("Back to Upload Page"):
        st.session_state.page = 'upload'
        st.rerun()
    
    # Check if data exists
    if st.session_state.KPI_LTE_BEFORE.empty or st.session_state.KPI_LTE_AFTER.empty:
        st.error("No LTE data available. Please go back and upload a ZIP file first.")
        st.stop()
    
    # Custom chart visualization inputs
    st.subheader("Custom Chart Configuration")
    
    # Date range selection using slider
    if st.session_state.date_columns_lte:
        # Create a slider for date range selection
        date_range_indices = st.slider(
            "Select date range:", 
            min_value=0, 
            max_value=len(st.session_state.date_columns_lte)-1, 
            value=(0, len(st.session_state.date_columns_lte)-1),
            format="%s",
            key="date_range_slider_lte"
        )
        
        start_idx, end_idx = date_range_indices
        start_date = st.session_state.date_columns_lte[start_idx]
        end_date = st.session_state.date_columns_lte[end_idx]
    else:
        st.error("No date columns available for visualization.")
        st.stop()
    
    # Aggregation Mode control (global)
    st.session_state.aggregation_mode = st.selectbox(
        "Aggregation Mode (applies to all charts):",
        options=["ALL", "NODENAME", "OBJECT"],
        index=["ALL", "NODENAME", "OBJECT"].index(st.session_state.aggregation_mode),
        key="agg_mode_select_lte"
    )
    
    # Add "All" option for NODENAME selection
    all_nodenames_with_all = ["All"] + st.session_state.all_nodenames_lte
    selected_options = st.multiselect("Select NODENAMES to include in charts:", 
                                      options=all_nodenames_with_all, 
                                      default=["All"] if st.session_state.all_nodenames_lte else [],
                                      key="selected_nodenames_lte")
    
    # Handle "All" selection
    if "All" in selected_options:
        selected_nodenames = st.session_state.all_nodenames_lte
    else:
        selected_nodenames = selected_options

    # Get data from session state
    KPI_LTE_BEFORE = st.session_state.KPI_LTE_BEFORE
    KPI_LTE_AFTER = st.session_state.KPI_LTE_AFTER

    # Get the date columns for chart visualization
    date_columns = st.session_state.date_columns_lte[start_idx:end_idx+1]

    # Generate charts for each counter with interactivity
    st.info(f"Generating charts for {len(st.session_state.all_counters_lte)} counters...")
    progress_bar = st.progress(0)
    total_counters = len(st.session_state.all_counters_lte)
    
    for idx, counter in enumerate(st.session_state.all_counters_lte):
        # Update progress bar
        progress_percentage = int((idx / total_counters) * 100)
        progress_bar.progress(progress_percentage / 100, text=f"Processing counter {idx + 1} of {total_counters}: {counter}")
        st.subheader(f"Charts for Counter: {counter}")
        
        # Per-chart aggregation method selector
        agg_method = st.selectbox(
            f"Aggregation Method for {counter}:",
            options=["AVERAGE", "MAX", "MIN", "SUM"],
            index=0,  # Default to AVERAGE
            key=f"agg_method_lte_{counter}"
        )

        # Filter data for the specific counter
        if counter in KPI_LTE_BEFORE['Counter'].values:
            before_data = KPI_LTE_BEFORE[KPI_LTE_BEFORE['Counter'] == counter]
            # Filter by selected nodenames
            before_data = before_data[before_data['NODENAME'].isin(selected_nodenames)]
            
            # Apply aggregation based on user selection
            before_data = aggregate_data(before_data, st.session_state.aggregation_mode, agg_method)

            # Create line chart for BEFORE data
            if not before_data.empty:
                # Prepare data for plotting
                before_plot_data = before_data[date_columns].T
                before_plot_data.columns = before_data['NODENAME'].values
                before_plot_data.index.name = 'Datetime'
                before_plot_data = before_plot_data.reset_index()

                # Convert all nodename columns to numeric, handling non-numeric values
                for col in before_data['NODENAME'].values:
                    if col in before_plot_data.columns:
                        before_plot_data[col] = pd.to_numeric(before_plot_data[col], errors='coerce')

                # Create line chart
                chart_title = f"BEFORE - {counter} (Aggregation: {st.session_state.aggregation_mode} / {agg_method})"
                fig_before = px.line(
                    before_plot_data,
                    x='Datetime',
                    y=before_plot_data.columns.tolist()[1:],  # All columns except Datetime
                    title=chart_title,
                    labels={'value': 'Counter Value', 'variable': 'NODENAME'}
                )
                
                # Show the chart
                st.plotly_chart(fig_before, use_container_width=True, key=f"before_chart_lte_{counter}")

        if counter in KPI_LTE_AFTER['Counter'].values:
            after_data = KPI_LTE_AFTER[KPI_LTE_AFTER['Counter'] == counter]
            # Filter by selected nodenames
            after_data = after_data[after_data['NODENAME'].isin(selected_nodenames)]
            
            # Apply aggregation based on user selection
            after_data = aggregate_data(after_data, st.session_state.aggregation_mode, agg_method)

            # Create line chart for AFTER data
            if not after_data.empty:
                # Prepare data for plotting
                after_plot_data = after_data[date_columns].T
                after_plot_data.columns = after_data['NODENAME'].values
                after_plot_data.index.name = 'Datetime'
                after_plot_data = after_plot_data.reset_index()

                # Convert all nodename columns to numeric, handling non-numeric values
                for col in after_data['NODENAME'].values:
                    if col in after_plot_data.columns:
                        after_plot_data[col] = pd.to_numeric(after_plot_data[col], errors='coerce')

                # Create line chart
                chart_title = f"AFTER - {counter} (Aggregation: {st.session_state.aggregation_mode} / {agg_method})"
                fig_after = px.line(
                    after_plot_data,
                    x='Datetime',
                    y=after_plot_data.columns.tolist()[1:],  # All columns except Datetime
                    title=chart_title,
                    labels={'value': 'Counter Value', 'variable': 'NODENAME'}
                )

                # Show the chart
                st.plotly_chart(fig_after, use_container_width=True, key=f"after_chart_lte_{counter}")
    
    # Complete progress bar
    progress_bar.progress(100, text="All charts generated successfully!")

elif st.session_state.page == 'top10_analysis_lte':
    st.title("KPI Comparison Tool - [KPI LTE] TOP 10 HIGH/LOWEST KPI Specific Analysis")
    
    # Back button to upload page
    if st.button("Back to Upload Page"):
        st.session_state.page = 'upload'
        st.rerun()
    
    # Check if data exists
    if st.session_state.KPI_LTE_BEFORE.empty or st.session_state.KPI_LTE_AFTER.empty:
        st.error("No LTE data available. Please go back and upload a ZIP file first.")
        st.stop()
    
    # Add "All" option for NODENAME selection
    all_nodenames_with_all = ["All"] + st.session_state.all_nodenames_lte
    selected_options = st.multiselect("Select NODENAMES to include in analysis:", 
                                      options=all_nodenames_with_all, 
                                      default=["All"] if st.session_state.all_nodenames_lte else [],
                                      key="top10_selected_nodenames_lte")
    
    # Handle "All" selection
    if "All" in selected_options:
        selected_nodenames = st.session_state.all_nodenames_lte
    else:
        selected_nodenames = selected_options

    # Date range selection using slider for analysis page
    if st.session_state.date_columns_lte:
        # Create a slider for date range selection
        date_range_indices = st.slider(
            "Select date range for analysis:", 
            min_value=0, 
            max_value=len(st.session_state.date_columns_lte)-1, 
            value=(0, len(st.session_state.date_columns_lte)-1),
            format="%s",
            key="top10_date_range_slider_lte"
        )
        
        start_idx, end_idx = date_range_indices
        start_date = st.session_state.date_columns_lte[start_idx]
        end_date = st.session_state.date_columns_lte[end_idx]
    else:
        st.error("No date columns available for visualization.")
        st.stop()

    # Get data from session state
    KPI_LTE_BEFORE = st.session_state.KPI_LTE_BEFORE
    KPI_LTE_AFTER = st.session_state.KPI_LTE_AFTER

    # Get the date columns for chart visualization
    date_columns = st.session_state.date_columns_lte[start_idx:end_idx+1]

    # Generate analysis for each counter
    for counter in st.session_state.all_counters_lte:
        st.subheader(f"Analysis for Counter: {counter}")
        
        # Datetime selection for analysis
        selected_datetime = st.selectbox(f"Select datetime to analyze for {counter}:", 
                                         options=date_columns, 
                                         key=f"top10_datetime_select_lte_{counter}")
        
        # Show top/bottom performers for the selected datetime
        if counter in KPI_LTE_BEFORE['Counter'].values:
            before_data = KPI_LTE_BEFORE[KPI_LTE_BEFORE['Counter'] == counter]
            before_data = before_data[before_data['NODENAME'].isin(selected_nodenames)]
            
            if not before_data.empty and selected_datetime in before_data.columns:
                # Get data for the selected datetime
                datetime_data = before_data[['NODENAME', selected_datetime]].copy()
                # Convert the selected datetime column to numeric, handling non-numeric values
                datetime_data[selected_datetime] = pd.to_numeric(datetime_data[selected_datetime], errors='coerce')
                datetime_data = datetime_data.dropna()  # Remove rows with non-numeric values
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Show top 10 lowest performers (sorted ascending)
                    top_lowest = datetime_data.nsmallest(10, selected_datetime)
                    st.write(f"**Top 10 LOWEST performers at {selected_datetime} - BEFORE**")
                    st.dataframe(top_lowest)
                
                with col2:
                    # Show top 10 highest performers (sorted descending)
                    top_highest = datetime_data.nlargest(10, selected_datetime)
                    st.write(f"**Top 10 HIGHEST performers at {selected_datetime} - BEFORE**")
                    st.dataframe(top_highest)
        
        if counter in KPI_LTE_AFTER['Counter'].values:
            after_data = KPI_LTE_AFTER[KPI_LTE_AFTER['Counter'] == counter]
            after_data = after_data[after_data['NODENAME'].isin(selected_nodenames)]
            
            if not after_data.empty and selected_datetime in after_data.columns:
                # Get data for the selected datetime
                datetime_data = after_data[['NODENAME', selected_datetime]].copy()
                # Convert the selected datetime column to numeric, handling non-numeric values
                datetime_data[selected_datetime] = pd.to_numeric(datetime_data[selected_datetime], errors='coerce')
                datetime_data = datetime_data.dropna()  # Remove rows with non-numeric values
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Show top 10 lowest performers (sorted ascending)
                    top_lowest = datetime_data.nsmallest(10, selected_datetime)
                    st.write(f"**Top 10 LOWEST performers at {selected_datetime} - AFTER**")
                    st.dataframe(top_lowest)
                
                with col2:
                    # Show top 10 highest performers (sorted descending)
                    top_highest = datetime_data.nlargest(10, selected_datetime)
                    st.write(f"**Top 10 HIGHEST performers at {selected_datetime} - AFTER**")
                    st.dataframe(top_highest)


# Export to Excel (available on both pages)
output_file = "KPI_Report.xlsx"
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    st.session_state.KPI_5G_BEFORE.to_excel(writer, sheet_name="KPI_5G_BEFORE", index=False)
    st.session_state.KPI_5G_AFTER.to_excel(writer, sheet_name="KPI_5G_AFTER", index=False)
    st.session_state.KPI_LTE_BEFORE.to_excel(writer, sheet_name="KPI_LTE_BEFORE", index=False)
    st.session_state.KPI_LTE_AFTER.to_excel(writer, sheet_name="KPI_LTE_AFTER", index=False)

# Provide download link in sidebar
with st.sidebar:
    st.divider()
    st.write("Download Report:")
    with open(output_file, "rb") as f:
        st.download_button(
            label="Download Excel Report",
            data=f.read(),
            file_name=output_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )