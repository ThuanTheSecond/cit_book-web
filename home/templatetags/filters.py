from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    return value - arg

@register.filter
def get_item(dictionary, key):
    value = dictionary.get(key)
    return str(value)