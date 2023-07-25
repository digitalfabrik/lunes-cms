"""
This is a collection of admin filter tags and filters
"""
from collections import defaultdict
import logging

from django import template

logger = logging.getLogger(__name__)
register = template.Library()


@register.simple_tag
def group_discipline_filter_choices(choices):
    """
    Group the discipline options by their parent discipline

    :param choices: The flat choices
    :type choices: list [ dict ]

    :return: The grouped choices
    :rtype: dict
    """
    options = []
    optgroups = defaultdict(list)
    delimiter = " \u2794 "
    for choice in choices:
        if delimiter not in choice["display"]:
            options.append(choice)
        else:
            parent, child = choice["display"].split(delimiter)
            choice["display"] = child
            optgroups[parent].append(choice)
    return {
        "options": options,
        "optgroups": dict(optgroups),
    }
