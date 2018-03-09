import os

from jinja2 import Environment, FileSystemLoader  # , select_autoescape

SCRIPT_DIR = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

env = Environment(
    loader=FileSystemLoader(os.path.join(SCRIPT_DIR, 'templates')),
    # autoescape=select_autoescape(['html', 'xml'])
)


def render(relPath, context=None, request=None):
    """Render template at relPath with the given context (parameters)
    
    @param relPath: relative path to template to render (relative to templates dir)
    @type relPath: str
    @param context: dictionary with template parameters
    @type context: dict
    @param request: Twisted HTTP request object (optional)
    @type request: twisted.web.http.Request"""
    from management_portal.auth import checkCapabilities, getCurrentUser
    if context is None:
        context = {}
    else:
        # Create a copy of the context before adding our own stuff, since we 
        # don't own the dictionary and it may be serialized to to JSON at some point
        context = context.copy()

    if request:
        context['path'] = request.path
        context['user'] = getCurrentUser(request)
        context['hasCap'] = lambda c: checkCapabilities(request, [c])
    else:
        context['hasCap'] = lambda c: False

    tpl = env.get_template(relPath)
    return tpl.render(**context).encode('utf-8')
