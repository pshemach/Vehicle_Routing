import pandas as pd 
from vehi_rout.utils.helper_utils import get_str_key

def load_matrix_df(path):
    return pd.read_csv(path, index_col=0)

def load_df(path):
    return pd.read_csv(path)

def load_daily_demand(file_name):
    try:
        df = pd.read_csv(file_name)
        df = df.dropna(subset=['CODE'])
        df = get_str_key(df)
        if "DEMAND" not in df.columns:
            df['DEMAND'] = 1
        df['DATE'] = pd.to_datetime(df['DATE'])
        return df
    except FileNotFoundError as e:
        print(f"Error loading daily demand file: {e}")

def get_demand_df(today_path=None, wait_path=None):
    today_df = load_daily_demand(today_path) if today_path is not None else None  
    wait_df = load_daily_demand(wait_path) if wait_path is not None else None
        
    # Combine today and wait dataframes
    if today_df is not None and wait_df is not None:
        demand_df = pd.concat([today_df, wait_df], ignore_index=True)
    elif today_df is not None:
        demand_df = today_df
    elif wait_df is not None:
        demand_df = wait_df
        
    if demand_df is not None:
        return demand_df

def get_demand_matrix_df(full_df, demand_df, depot):
    keys = demand_df['CODE'].to_list()
    today_shop_indices = [full_df.index.get_loc(str(code)) for code in keys if str(code) in full_df.index]
    selected_indices = [depot] + today_shop_indices
    return full_df.iloc[selected_indices, selected_indices].copy()

def update_demand_dic(demand_df):
    """
    Updates the demand_dic with data from demand_df where DEMAND > 0, converting DATE to datetime.

    Args:
        demand_dic (dict): The dictionary to update.
        demand_df (pd.DataFrame): The DataFrame containing demand data.

    Returns:
        dict: The updated demand_dic.
    """
    demand_dic = {"key":None, "demand":None, "po_date":None}
    filtered_df = demand_df[demand_df['DEMAND'] > 0]

    demand_dic["key"] = filtered_df['CODE'].values.tolist()
    demand_dic["demand"] = filtered_df['DEMAND'].values.tolist()
    demand_dic["po_date"] = pd.to_datetime(filtered_df['DATE']).tolist() #convert to datetime

    return demand_dic