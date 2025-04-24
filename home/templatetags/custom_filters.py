from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if not dictionary:
        return 0
    try:
        return dictionary.get(str(key), 0)  # Convert key to string
    except (AttributeError, TypeError):
        return 0
