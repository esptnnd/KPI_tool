import os
import pandas as pd
import glob
import re
import numpy as np





    
# Function to process KPI log files
def process_kpi_logs(folder, pattern, start_defined):
    all_data = []
    datetime_headers = set()
    
    # Read all log files in the directory
    log_files = sorted(glob.glob(os.path.join(folder, "*.log")), key=os.path.getsize)
    for log_file in log_files:
        nodename = os.path.splitext(os.path.basename(log_file))[0]
        temp_data = []
        temp_datetime_headers = set()
        
        with open(log_file, "r") as file:
            lines = file.readlines()
            
            for line in lines:
                if line.startswith(pattern):
                    parts = line.strip().rstrip(";").split("; ")
                    
                    if "Object" in parts and "Counter" in parts:
                        temp_datetime_headers.update(parts[3:])
                    else:
                        temp_data.append(parts[1:])
        
        #######
        if temp_data:
            datetime_headers.update(temp_datetime_headers)
            temp_datetime_headers = sorted(temp_datetime_headers)
            

            columns = ["NODENAME", "Object", "Counter"] + temp_datetime_headers
            formatted_data = []
            
            for row in temp_data:
                row_dict = {"NODENAME": nodename, "Object": row[0], "Counter": row[1]}
                for dt in temp_datetime_headers:
                    row_dict[dt] = "N/A"
                for i, dt in enumerate(row[2:]):
                    if i < len(temp_datetime_headers):
                        row_dict[temp_datetime_headers[i]] = dt
                formatted_data.append(row_dict)


            # Identify datetime columns based on format "YYYY-MM-DD HH:MM"
            datetime_mapping = {}
            temp_df = pd.DataFrame(formatted_data, columns=columns)
            for col in temp_df.columns:
                try:
                    datetime_format = "%Y-%m-%d %H:%M"
                    dt = pd.to_datetime(col, format=datetime_format, errors='raise')
                    datetime_mapping[col] = dt.strftime(datetime_format)  # Store as string
                except ValueError:
                    pass  # Ignore non-datetime columns        
            
            temp_df.columns = [datetime_mapping[col] if col in datetime_mapping else col for col in temp_df.columns]
            all_data.append(temp_df)
        
        
        
        
    max_rop = 68
    if start_defined == "NO_START":
        datetime_candidates = sorted(datetime_headers)
    else:
        # Convert string column names to datetime for filtering using collected headers
        datetime_candidates = sorted([
            col for col in datetime_headers
            if pd.to_datetime(col, format='%Y-%m-%d %H:%M', errors='coerce') >= pd.Timestamp(start_defined)
        ])
    datetime_headers = datetime_candidates[:max_rop]
        
    final_columns = ["NODENAME", "Object", "Counter"] + datetime_headers
    # If no data was collected, return an empty DataFrame with the expected columns
    if not all_data:
        df = pd.DataFrame(columns=final_columns)
        return df
    df = pd.concat(all_data, ignore_index=True).reindex(columns=final_columns)
    df.fillna("N/A", inplace=True)
    return df


# Merge BEFORE and AFTER datasets for comparison
def create_main_merge_df(before_df, after_df):
    columns_to_keep = {"NODENAME", "Object", "Counter"}
    # Rename columns for before_df
    before_df = before_df.rename(
        columns={col: f"{col}_BEFORE" for col in before_df.columns if col not in columns_to_keep}
    )
    
    # Rename columns for after_df
    after_df = after_df.rename(
        columns={col: f"{col}_AFTER" for col in after_df.columns if col not in columns_to_keep}
    ) 
    
    merged_df = before_df.merge(after_df, on=["NODENAME", "Object", "Counter"], suffixes=("_BEFORE", "_AFTER"), how="outer")
    
    # Get unique Counter values
    counter_values = merged_df["Counter"].unique()
    # If there are no counters, return None as requested
    if len(counter_values) == 0:
        return None
    main_merge_df = None
    
    for counter in counter_values:
        temp_df = merged_df[merged_df["Counter"] == counter].drop(columns=["Counter"]).copy()        
        
        if main_merge_df is None:  
            main_merge_df = temp_df
            
        else:
            formatted_suffix = f"_{counter}"
            main_merge_df = main_merge_df.merge(temp_df, on=["NODENAME", "Object"], how="outer", suffixes=("", formatted_suffix))


    # Safe-guard: if no merged data by counters, return None
    if main_merge_df is None:
        return None
    first_counter_value = counter_values[0]  # Get the first unique value
    formatted_suffix = f"_{first_counter_value}"  # Ensures the format _latest
    # Rename columns dynamically using regex
    main_merge_df.rename(columns={
        col: re.sub(r"_BEFORE$", f"_BEFORE{formatted_suffix}", col)
             if re.search(r"_BEFORE$", col) else
             re.sub(r"_AFTER$", f"_AFTER{formatted_suffix}", col)
             if re.search(r"_AFTER$", col) else col
        for col in main_merge_df.columns
    }, inplace=True)    
    return main_merge_df


###### Save to Excel
#####output_file = "KPI_Report.xlsx"
#####with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
#####    KPI_5G_BEFORE.to_excel(writer, sheet_name="KPI_5G_BEFORE", index=False)
#####    KPI_5G_AFTER.to_excel(writer, sheet_name="KPI_5G_AFTER", index=False)
#####    KPI_LTE_BEFORE.to_excel(writer, sheet_name="KPI_LTE_BEFORE", index=False)
#####    KPI_LTE_AFTER.to_excel(writer, sheet_name="KPI_LTE_AFTER", index=False)
#####    compare_5G.to_excel(writer, sheet_name="Compare_5G", index=False)
#####    compare_LTE.to_excel(writer, sheet_name="Compare_LTE", index=False)
#####
#####print(f"Processing complete. Output saved to {output_file}")	
import pandas as pd
import re
import random

def split_column_name(col_name):
    match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})_(BEFORE|AFTER)_(.+)", col_name)
    if match:
        return match.groups()
    return col_name, "", ""

def transform_headers(df):
    original_headers = df.columns.tolist()
    first_row, second_row, third_row = [], [], []
    
    for col in original_headers:
        if col == "NODENAME":
            first_row.append("NODENAME")
            second_row.append("NODENAME")
            third_row.append("NODENAME")
        else:
            date_time, before_after, kpi_name = split_column_name(col)
            first_row.append(date_time)
            second_row.append(before_after)
            third_row.append(kpi_name)            
    
    return [third_row, second_row, first_row]





