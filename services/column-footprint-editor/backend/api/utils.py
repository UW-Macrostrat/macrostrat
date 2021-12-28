def merge(left, right):
    """ takes two arrays and merges by comparison """

    result = []
    left_i = 0
    right_i = 0
    # go one at a time comparing
    while left_i < len(left) and right_i < len(right):
        if left[left_i] > right[right_i]:
            # add right to result
            result.append(right[right_i])
            right_i += 1
        else:
            result.append(left[left_i])
            left_i += 1
    result = result + left[left_i:] + right[right_i:]
    return result

def merge_sort(array):
    if len(array) == 1:
        return array
    
    leng = len(array)
    half_rough = leng // 2
    left = array[:half_rough]
    right = array[half_rough:]
    
    return merge(merge_sort(left), merge_sort(right))

def clean_change_set(change_set):
    """ use pointers """
    for_deletion = []
    for i in range(len(change_set)):
        current_line = change_set[i]
        if current_line['action'] == "draw.create":
            for j in range(i, len(change_set)):
                line = change_set[j]
                if line['feature']['id'] == current_line['feature']['id']:
                    if line['action'] == "change_coordinates":
                        current_line['feature']["geometry"] = line['feature']['geometry']
                        for_deletion.append(j)
                    elif line['action'] == "draw.delete":
                        for_deletion.append(i)
                        for_deletion.append(j)
                        break
    if len(for_deletion):                
        sorted_deletions = merge_sort(for_deletion)
        for index in sorted_deletions[::-1]:
            del change_set[index]
    
    return change_set