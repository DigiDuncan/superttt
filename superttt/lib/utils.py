def flatten(lst):
    """https://www.reddit.com/r/learnpython/comments/1lo5f6y/how_to_efficiently_flatten_a_nested_list_of/n0kiivo/"""
    flat_list = []
    for element in lst:
        if isinstance(element, list):
            flat_list.extend(flatten(element))
        else:
            flat_list.append(element)
    return flat_list

def format_time(seconds: float, decimal_places = 1) -> str:
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    seconds, fractional = divmod(seconds, 1)
    fractional *= (10 ** decimal_places)
    fractional = int(fractional)

    s = f"{int(minutes):02}:{int(seconds):02}"
    if hours:
        s = f"{int(hours)}:" + s
    if decimal_places:
        s += f".{fractional}"
    return s
