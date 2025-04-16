from vehi_rout.utils.helper_utils import get_date_difference, sigmoid
# def get_penalty_list(demand_dic, base_penalty, total_days, today):
#     # penalty_list = [base_penalty * (total_days - (get_date_difference(today, day) + 1)) for day in demand_dic['po_date']]   
#     penalty_list = []
#     # today = date.today().strftime('%Y-%m-%d')
#     for day in demand_dic['po_date']:
#         remain_days = total_days - (get_date_difference(today, day) + 1)
#         value = sigmoid(remain_days) * base_penalty
#         penalty_list.append(int(value))
#     return penalty_list

def sort_nodes_by_distance(matrix):
    distances = [(node, matrix[0][node]) for node in range(1, len(matrix))]
    return [node for node, _ in sorted(distances, key=lambda x: x[1])]


def get_penalty_list(demand_dic, base_penalty, total_days, today):
    # penalty_list = [base_penalty * (total_days - (get_date_difference(today, day) + 1)) for day in demand_dic['po_date']]
    base_penalty_dict = {7:100,
                         6:1000,
                         5:100,
                         4:100,
                         3:100,
                         2:50,
                         1:40}
    penalty_list = []
    # today = date.today().strftime('%Y-%m-%d')
    for day in demand_dic['po_date']:
        remain_days = total_days - (get_date_difference(today, day) + 1)
        value = base_penalty_dict[remain_days]
        penalty_list.append(int(value))
    return penalty_list