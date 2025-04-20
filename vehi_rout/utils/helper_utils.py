from datetime import datetime
import pandas as pd
import numpy as np


def get_date_difference(date_str1, date_str2, format1='%Y-%m-%d', format2='%Y-%m-%d'):
    """
    Calculates the difference in days between two dates given as strings,
    allowing for different date formats.

    Args:
        date_str1 (str): The first date string.
        date_str2 (str): The second date string.
        format1 (str): The format of the first date string. Defaults to '%Y-%m-%d'.
        format2 (str): The format of the second date string. Defaults to '%Y-%m-%d'.

    Returns:
        int: The difference in days between the two dates, or None if an error occurs.
    """
    try:
        if isinstance(date_str1, pd.Timestamp): #Added this check
            date1 = date_str1.date()
        else:
            date1 = datetime.strptime(date_str1, format1).date()


        if isinstance(date_str2, pd.Timestamp): #Added this check
            date2 = date_str2.date()
        else:
            date2 = datetime.strptime(date_str2, format2).date()

        difference = date1 - date2
        return difference.days
    except ValueError:
        return None  # Or raise an exception, or return an error string.
    except TypeError: #handle pandas Timestamp
        return None

def get_str_key(df):
    if df['CODE'].dtype in ['float', 'int']:
        df['CODE'] = df['CODE'].astype(int)
        df['CODE'] = df['CODE'].astype(str)
        print('Converting to Object')
    return df

import requests
def get_osrm_data(origin, destination):
    """
    Get the distance and path between two coordinates using OSRM API.
    :param origin: (latitude, longitude)
    :param destination: (latitude, longitude)
    :return: Tuple of (path_coordinates, distance in km, duration in minutes)
    """
    osrm_base_url = "http://router.project-osrm.org/route/v1/car"
    url = f"{osrm_base_url}/{origin[1]},{origin[0]};{destination[1]},{destination[0]}?overview=full&geometries=geojson"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if "routes" in data and len(data["routes"]) > 0:
            path_cords = data["routes"][0]["geometry"]["coordinates"]
            # Convert [longitude, latitude] to [latitude, longitude] for folium
            path_cords = [[coord[1], coord[0]] for coord in path_cords]
            distance = data["routes"][0]["distance"] / 1000
            duration = data["routes"][0]["duration"] / 60
            return path_cords, distance, duration

    return None, np.inf, np.inf

def get_values_not_in_second_list(list1, list2):
    """
    Returns a list of values from list1 that are not present in list2.

    Args:
        list1 (list): The first list.
        list2 (list): The second list.

    Returns:
        list: A list containing values from list1 that are not in list2.
    """
    return [item for item in list1 if item not in list2]



def sigmoid(x):
    return x / (x + np.exp(-x))


def get_penalty_list(demand_dict, base_penalty, total_days, current_date=None):
    """
    Calculate penalties for not visiting nodes based on days remaining and demand.

    Args:
        demand_dict (dict): Dictionary containing demand information
        base_penalty (int): Base penalty value
        total_days (int): Total number of days for planning
        current_date (str, optional): Current date in format 'YYYY-MM-DD'

    Returns:
        list: List of penalties for each node
    """
    # Define base penalty weights for different days remaining
    base_penalty_dict = {
        7: 500,
        6: 500,
        5: 500,
        4: 500,
        3: 500,
        2: 500,
        1: 400
    }

    penalties = []

    # If current_date is not provided, use today's date
    if current_date is None:
        current_date = datetime.now().strftime('%Y-%m-%d')

    # Calculate penalties based on days remaining and demand
    for i, key in enumerate(demand_dict['key']):
        if key == '0':
            # Depot has no penalty
            penalties.append(0)
            continue

        # Get the PO date for this demand
        po_date = demand_dict['po_date'][i]

        # Calculate days remaining
        days_remaining = total_days - (get_date_difference(current_date, po_date) + 1)

        if days_remaining is None or days_remaining < 1 or days_remaining > 7:
            # If days_remaining is invalid, use a default penalty
            penalties.append(base_penalty)
            continue

        # Get the weight for this number of days remaining
        weight = base_penalty_dict.get(days_remaining, 100)

        # Calculate penalty based on days remaining and demand
        demand = demand_dict.get(key, 1)
        penalty = weight * demand
        print(f"Penalty for {key}: {penalty}")

        penalties.append(penalty)

    return penalties