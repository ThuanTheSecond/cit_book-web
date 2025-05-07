from django import template

register = template.Library()

@register.filter
def get_number(dictionary, key):
    if not dictionary:
        return 0
    try:
        return dictionary.get(str(key), 0)  # Convert key to string
    except (AttributeError, TypeError):
        return 0

@register.filter  
def get_raw_number(dictionary, key):
    return dictionary.get(key, 0)

@register.filter
def subtract(value, arg):
    return value - arg

