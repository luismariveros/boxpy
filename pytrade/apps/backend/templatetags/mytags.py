from django import template

register = template.Library()

@register.assignment_tag
def get_bootstrap_msg(tags):
    return 'danger' if tags == 'error' else tags


@register.filter
def truncatebackward(value, limit=80):
    """
    Truncates a string after a given number of chars keeping whole words.

    Usage:
        {{ string|truncatesmart }}
        {{ string|truncatesmart:50 }}
    """

    try:
        limit = int(limit)
    # invalid literal for int()
    except ValueError:
        # Fail silently.
        return value

    # Make sure it's unicode
    value = unicode(value)

    # Return the string itself if length is smaller or equal to the limit
    if len(value) <= limit:
        return value

    # Cut the string
    value = value[len(value)-limit:]

    # Break into words and remove the last
    #words = value.split(' ')[:-1]

    # Join the words and return
    #return ' '.join(words) + '...'
    return '...' + value