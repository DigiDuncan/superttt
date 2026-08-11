def flatten(lst):
    flat_list = []
    for element in lst:
        if isinstance(element, list):
            flat_list.extend(flatten(element))
        else:
            flat_list.append(element)
    return flat_list
