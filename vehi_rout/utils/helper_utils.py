from datetime import datetime
import pandas as pd

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

def get_penalty_list(demand_dic, base_penalty, total_days):
    # penalty_list = [base_penalty * (total_days - (get_date_difference(today, day) + 1)) for day in demand_dic['po_date']]   
    penalty_list = []
    # today = date.today().strftime('%Y-%m-%d')
    today = '2025-02-28'
    for day in demand_dic['po_date']:
        remain_days = total_days - (get_date_difference(today, day) + 1)
        penalty_list.append(remain_days * base_penalty)
    return penalty_list

def sort_nodes_by_distance(matrix):
    distances = [(node, matrix[0][node]) for node in range(1, len(matrix))]
    return [node for node, _ in sorted(distances, key=lambda x: x[1])]