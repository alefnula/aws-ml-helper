__author__ = 'Viktor Kerkez <alefnula@gmail.com>'
__date__ = '21 March 2018'
__copyright__ = 'Copyright (c)  2018 Viktor Kerkez'


def name_from_tags(tags):
    """Extract name from tags"""
    tags = tags or []
    names = [tag['Value'] for tag in tags if tag['Key'] == 'Name']
    if len(names) == 1:
        return names[0]
    return ''
