def flatten(lst):
    """https://www.reddit.com/r/learnpython/comments/1lo5f6y/how_to_efficiently_flatten_a_nested_list_of/n0kiivo/"""
    flat_list = []
    for element in lst:
        if isinstance(element, list):
            flat_list.extend(flatten(element))
        else:
            flat_list.append(element)
    return flat_list
