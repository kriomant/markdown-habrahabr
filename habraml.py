#!/usr/bin/python

from __future__ import with_statement
import sys
import re
import cgi
import subprocess
import markdown
import pygments, pygments.formatter, pygments.lexers

# Formats highlighted source into HTML usable on habrahabr,
# i.e. using only plain "<b>", "<i>" and "<font>" tags.
class HabraFormatter(pygments.formatter.Formatter):
	def __init__(self, **options):
		pygments.formatter.Formatter.__init__(self, **options)

		self.styles = {}

		for ttype, style in self.style:
			start, end = [], []
			if style['color']:
				start.append('<font color="#%s">' % style['color'])
				end.append('</font>')
			if style['bold']:
				start.append('<b>')
				end.append('</b>')
			if style['italic']:
				start.append('<i>')
				end.append('</i>')
			if style['underline']:
				start.append('<u>')
				end.append('</u>')

			end.reverse()
			self.styles[ttype] = (''.join(start), ''.join(end))

	def format(self, tokens, out):
		lasttype = None
		pending_end = ''

		for ttype, value in tokens:
			while ttype not in self.styles:
				ttype = ttype.parent

			if ttype == pygments.token.Text:
				value = value.replace('\n', '<br/>').replace(' ', '&nbsp;')

			start, end = self.styles[ttype]

			if ttype != lasttype:
				lasttype = ttype
				out.write(pending_end)
				pending_end = end
				out.write(start)

			out.write(value)

		out.write(pending_end)


class HabracutPreprocessor(markdown.Preprocessor):
	RE_CUT = re.compile(r'-[xX]-+(?:\s+(.+))?')

	def run(self, lines):
		return [self.processLine(line) for line in lines]

	def processLine(self, line):
		m = self.RE_CUT.match(line)
		if m:
			if m.group(1):
				return '<habracut text="%s"/>' % cgi.escape(m.group(1), True)
			else:
				return '<habracut/>'
		else:
			return line

class HeaderPostprocessor(markdown.Postprocessor):
	def run(self, root):
		self.renameHeaders(root.documentElement)

	RENAMES = {'h1': 'h4', 'h2': 'h5', 'h3': 'h6'}

	def renameHeaders(self, node):
		if node.type == 'element':
			if node.nodeName in self.RENAMES:
				node.nodeName = self.RENAMES[node.nodeName]

			for child in node.childNodes:
				self.renameHeaders(child)

class ImagePostprocessor(markdown.Postprocessor):
	def run(self, root):
		self.relocateImages(root.documentElement, root)

	def relocateImages(self, node, doc):
		if node.nodeName == 'img':
			src = node.attribute_values['src']
			if not src.startswith('http://'):
				with open('%s.address' % src) as f:
					thumb_url, page_url = [line.rstrip() for line in f]
				link = doc.createElement('a')
				link.setAttribute('href', page_url)
				node.setAttribute('src', thumb_url)
				node.parent.replaceChild(node, link)
				link.appendChild(node)
		else:
			for child in node.childNodes:
				if child.type == 'element':
					self.relocateImages(child, doc)

class RemoveCodePostprocessor(markdown.Postprocessor):
	def run(self, root):
		self.removeCodeFromPre(root.documentElement)

	def removeCodeFromPre(self, node):
		if node.nodeName == 'pre' \
			and len(node.childNodes) == 1 \
			and node.childNodes[0].type == 'element' \
			and node.childNodes[0].nodeName == 'code':

			code = node.childNodes[0]
			for child in code.childNodes:
				code.removeChild(child)
				node.appendChild(child)
			node.removeChild(code)

		else:
			for child in node.childNodes:
				if child.type == 'element':
					self.removeCodeFromPre(child)

class RawNode:
	def __init__(self, raw_html):
		self.raw_html = raw_html

	def toxml(self): return self.raw_html

	def handleAttributes(self): pass

class HighlightPostprocessor(markdown.Postprocessor):
	def run(self, root):
		self.highlight(root.documentElement)

	RE = re.compile(r'(\\)?@\s*([^\s]+)\s*@')
	RE_INDENT = re.compile(r'^\s+')

	def highlight(self, node):
		if node.nodeName == 'pre':
			text_node = node.childNodes[0]
			text = text_node.value
			m = self.RE.match(text.split('\n')[0])

			if m:
				if not m.group(1):
					lang = m.group(2)
					text = '\n'.join(text.split('\n')[1:])

					lexer = pygments.lexers.get_lexer_by_name(lang)
					formatter = HabraFormatter()
					output = pygments.highlight(text, lexer, formatter)

					node.nodeName = 'blockquote'
					node.replaceChild(text_node, RawNode(output))

				else:
					text_node.value = text[1:]

		else:
			for child in node.childNodes:
				if child.type == 'element':
					self.highlight(child)

class HabrauserPattern(markdown.Pattern):
	def __init__(self):
		markdown.Pattern.__init__(self, r'@([a-zA-Z0-9_]+)')

	def handleMatch(self, m, doc):
		el = doc.createElement('hh')
		el.setAttribute('user', m.group(2))
		return el

class StrikePattern(markdown.SimpleTagPattern):
	def __init__(self):
		markdown.SimpleTagPattern.__init__(self, r'~~([^~]+)~~', 's')

md = markdown.Markdown()
md.preprocessors.append(HabracutPreprocessor())
md.postprocessors.append(HeaderPostprocessor())
md.postprocessors.append(ImagePostprocessor())
md.postprocessors.append(RemoveCodePostprocessor())
md.postprocessors.append(HighlightPostprocessor())
md.inlinePatterns.append(HabrauserPattern())
md.inlinePatterns.append(StrikePattern())

text = sys.stdin.read().decode('utf-8')
html = md.convert(text)
print(html.encode('utf-8'))

