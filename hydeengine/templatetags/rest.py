from django import template
from django.conf import settings
from django.utils import safestring

try:
    import docutils
except ImportError:
    docutils = None

try:
    import pygments
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters.html import _get_ttype_class
except ImportError:
    pygments = None

register = template.Library()

@register.tag(name='restructuredtext')
def restructuredtextParser(parser, token):
    nodelist = parser.parse(('endrestructuredtext',))
    parser.delete_first_token()
    return RestructuredTextNode(nodelist)

class RestructuredTextNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        output = self.nodelist.render(context)
        try:
            from docutils.core import publish_parts
        except ImportError:
            print u"Requires docutils library to use restructuredtext tag."
            raise

        overrides = getattr(settings, 'RST_SETTINGS_OVERRIDES', {})
        overrides['_disable_config'] = True
        overrides['raw_enabled'] = False
        overrides['file_insertion_enabled'] = False
        # TODO: 'warning_stream'

        parts = publish_parts(source=output, writer_name='html4css1',
                settings_overrides=overrides)
        return safestring.mark_safe(parts['fragment'])

class DocutilsInterface(object):
    """Parse `code` string and yield "classified" tokens.
    
    Arguments
    
      code     -- string of source code to parse
      language -- formal language the code is written in.
    
    Merge subsequent tokens of the same token-type. 
    
    Yields the tokens as ``(ttype_class, value)`` tuples, 
    where ttype_class is taken from pygments.token.STANDARD_TYPES and 
    corresponds to the class argument used in pygments html output.
    """

    def __init__(self, code, language):
        self.code = code
        self.language = language
        
    def lex(self):
        # Get lexer for language (use text as fallback)
        try:
            lexer = get_lexer_by_name(self.language)
        except ValueError:
            lexer = get_lexer_by_name('text')
        return pygments.lex(self.code, lexer)
            
    def join(self, tokens):
        """Join subsequent tokens of same token-type."""
        tokens = iter(tokens)
        (lasttype, lastval) = tokens.next()
        for ttype, value in tokens:
            if ttype is lasttype:
                lastval += value
            else:
                yield(lasttype, lastval)
                (lasttype, lastval) = (ttype, value)
        yield(lasttype, lastval)

    def __iter__(self):
        """Parse code string and yield "clasified" tokens."""
        try:
            tokens = self.lex()
        except IOError:
            print u"Pygments lexer not found; using fallback"
            yield ('', self.code)
            return

        for ttype, value in self.join(tokens):
            yield (_get_ttype_class(ttype), value)

def code_block_directive(name, arguments, options, content, lineno,
                         content_offset, block_text, state, state_machine):
    """Directive that parses and classifies the conents of a code_block."""
    language = arguments[0]

    # Create a literal block element and set the class argument.
    code_block = docutils.nodes.literal_block(classes=['code-block', language])

    # Parse the content with pygments and add to our code_block element.
    for cls, value in DocutilsInterface(u'\n'.join(content), language):
        code_block += docutils.nodes.inline(value, value, classes=[cls])

    return [code_block]

# Register the code_block directive.
if pygments is not None and docutils is not None:
    from docutils.parsers.rst import directives
    code_block_directive.arguments = (1, 0, 1)
    code_block_directive.content = 1
    directives.register_directive('code-block', code_block_directive)
