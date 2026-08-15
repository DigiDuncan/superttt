from arcade import Rect


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

def lerp_rect(rect_a: Rect, rect_b: Rect, t: float) -> Rect:
    sub_t = (1 - t)
    return Rect(*(sub_t * a + t * b for a, b in zip(rect_a, rect_b)))

def lerp(a: float, b: float, t: float) -> float:
    sub_t = (1 - t)
    return (sub_t * a + t * b)

def clamp(mi, ma, x):
    return max(mi, min(ma, x))

def ease_rect(rect_a: Rect, rect_b: Rect, start: float, end: float, t: float) -> Rect:
    return(lerp_rect(rect_a, rect_b, clamp(0, 1, ((t - start) / (end - start)))))

def ease(a: float, b: float, start: float, end: float, t: float) -> float:
    return(lerp(a, b, clamp(0, 1, ((t - start) / (end - start)))))
