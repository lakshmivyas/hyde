from django import template
from django.conf import settings
from django.utils import safestring
from django.template import Node
from django.utils.text import normalize_newlines
import cStringIO as StringIO
import re
import hashlib

register = template.Library()

@register.tag(name="textile")
def textileParser(parser, token):
    nodelist = parser.parse(('endtextile',))
    parser.delete_first_token()
    return TextileNode(nodelist)

class TextileNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        output = self.nodelist.render(context)
        try:
            import textile
        except ImportError:
            print u"Requires Textile library to use textile tag."
            raise
        return textile.textile(output)

@register.tag(name="markdown2")
def markdown2Parser(parser, token):
    nodelist = parser.parse(('endmarkdown2',))
    parser.delete_first_token()
    return Markdown2Node(nodelist)

class Markdown2Node(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        output = self.nodelist.render(context)
        try:
            import markdown2
        except ImportError:
            print u"Template uses markdown2 tag but markdown2 library not found."
            raise                                                               
            
        md = markdown2.Markdown()
        return md.convert(output)

@register.tag(name="markdown")
def markdownParser(parser, token):
    token_list = token.split_contents()
    extensions = token_list[1:]

    nodelist = parser.parse(('endmarkdown',))
    parser.delete_first_token()
    return MarkdownNode(nodelist, extensions)

class MarkdownNode(template.Node):
    def __init__(self, nodelist, extensions):
        self.nodelist = nodelist
        self.extensions = extensions

    def render(self, context):
        context.push()
        context['in_markdown'] = True
        output = self.nodelist.render(context)
        context.pop()
        extensions = self.extensions
        if hasattr(settings,'MD_EXTENSIONS'):
            extensions = extensions + settings.MD_EXTENSIONS
        extensions_config = {}
        if hasattr(settings,'MD_EXTENSIONS_CONFIG'):
            extensions_config = settings.MD_EXTENSIONS_CONFIG
        try:
            import markdown
        except ImportError:
            print u"Requires Markdown library to use Markdown tag."
            raise            
        md = markdown.Markdown(extensions=extensions,extension_configs=extensions_config)
        return md.convert(output)


@register.tag(name="asciidoc")
def asciidocParser(parser, token):
    nodelist = parser.parse(('endasciidoc',))
    parser.delete_first_token()
    return asciidocNode(nodelist)

class asciidocNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        output = self.nodelist.render(context)
        try:
            from asciidocapi import AsciiDocAPI
        except ImportError:
            print u"Requires AsciiDoc library to use AsciiDoc tag."
            raise
        asciidoc = AsciiDocAPI()
        asciidoc.options('--no-header-footer')
        result = StringIO.StringIO()
        asciidoc.execute(StringIO.StringIO(output.encode('utf-8')), result, 'html4')
        return safestring.mark_safe(result.getvalue())


@register.tag(name="syntax")
def syntaxHighlightParser(parser, token):
    token_list = token.split_contents()
    if len(token_list) > 1:
        lexer = token_list[1]
    else:
        lexer = None

    nodelist = parser.parse(('endsyntax',))
    parser.delete_first_token()
    return SyntaxHighlightNode(nodelist,lexer)

class SyntaxHighlightNode(template.Node):
    def __init__(self, nodelist, lexer):
        self.nodelist = nodelist
        self.lexer = lexer

    def render(self, context):
        try:
            import pygments
            from pygments import lexers
            self.lexers = lexers
            from pygments import formatters
        except ImportError:
            print u"Requires Pygments library to use syntax highlighting tags."
            raise
        
        output = self.nodelist.render(context)
        lexer = self.get_lexer(output)
        pygments_options = dict()
        if hasattr(settings, 'PYGMENTS_OPTIONS'):
            pygments_options = settings.PYGMENTS_OPTIONS
        formatter = formatters.HtmlFormatter(**pygments_options)
        h = pygments.highlight(output, lexer, formatter)
        if context.get('in_markdown', False):
            h = self.preprocess_for_markdown(h)
        return safestring.mark_safe(h)
    
    def preprocess_for_markdown(self, code):
        code = code.replace('\n\n', '\n&nbsp;\n').replace('\n', '<br />')
        return '\n\n<div class="code">%s</div>\n\n' % code
        
    def get_lexer(self, value):
        if self.lexer is None:
            return self.lexers.guess_lexer(value)
        return self.lexers.get_lexer_by_name(self.lexer)


class NewlineLessNode(Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        return re.sub('\s{2,}', ' ', normalize_newlines(self.nodelist.render(context)).replace('\n', ''))

@register.tag(name="newlineless")
def newlineless(parser, token):
    nodelist = parser.parse(('endnewlineless',))
    parser.delete_first_token()
    return NewlineLessNode(nodelist)        

    
@register.filter
def md5_querystring(value, arg=None):
    '''filter that appends a path with an md5 querystring'''
    try:
        f = file(value, 'r')
    except IOError:
        print "Couldn't find path to generate hash querystring for %s" % value
        return value

    m = hashlib.md5(f.read()).hexdigest()
    return "%s?%s" % (value, m)        
