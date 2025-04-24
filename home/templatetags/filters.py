from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Returns string value from dictionary
    Used for text content
    """
    value = dictionary.get(key)
    return str(value)

@register.filter
def subtract(value, arg):
    return value - arg
