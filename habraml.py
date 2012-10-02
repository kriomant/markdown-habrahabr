#!/usr/bin/python

from __future__ import with_statement
import sys
import re
import cgi
import markdown

class HabracutPreprocessor(markdown.preprocessors.Preprocessor):
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

class HeaderPostprocessor(markdown.treeprocessors.Treeprocessor):
	def run(self, root):
		self.renameHeaders(root)

	RENAMES = {'h1': 'h2', 'h2': 'h3', 'h3': 'h4', 'h4': 'h5', 'h5': 'h6'}

	def renameHeaders(self, node):
		if node.tag in self.RENAMES:
			node.tag = self.RENAMES[node.tag]

		for child in node:
				self.renameHeaders(child)

class SubstituteTreeprocessor(markdown.treeprocessors.Treeprocessor):
	def run(self, root):
		return self.process_recursively(root)

	def process_recursively(self, node):
		child_was_replaced = False
		new_children = []
		for child in node:
			new_child = self.process(child)
			if new_child is not None:
				child_was_replaced = True
				new_children.append(new_child)
			else:
				new_child = self.process_recursively(child)
				if new_child is not None:
					child_was_replaced = True
					new_children.append(new_child)
				else:
					new_children.append(child)

		if child_was_replaced:
			new_node = markdown.etree.Element(node.tag)
			new_node.attrib = node.attrib
			new_node.extend(new_children)
			return new_node

	def process(self, node):
		raise NotImplemented()

class ImagePostprocessor(SubstituteTreeprocessor):
	def process(self, node):
		if node.tag == 'img':
			src = node.attrib['src']
			if not src.startswith('http://'):
				with open('%s.address' % src) as f:
					thumb_url, page_url = [line.rstrip() for line in f]
				
				link = markdown.etree.Element('a')
				link.attrib['href'] = page_url

				img = markdown.etree.Element('img')
				img.attrib['src'] = thumb_url

				link.append(img)
				return link

class CodeBlockProcessor(SubstituteTreeprocessor):
	RE = re.compile(r'(?<!\\)@\s*([^\s]+)\s*@')
	RE_INDENT = re.compile(r'^\s+')

	def process(self, node):
		if node.tag == 'pre' and len(node) == 1 and node[0].tag == 'code':
			text = node[0].text
			lang = "plain"

			m = self.RE.match(text.split('\n')[0])

			elem = markdown.etree.Element('source')

			if m:
				lang = m.group(1)
				text = '\n'.join(text.split('\n')[1:])

			elem.attrib['lang'] = lang
			elem.text = text
			return elem

class HabrauserPattern(markdown.inlinepatterns.Pattern):
	def __init__(self):
		markdown.inlinepatterns.Pattern.__init__(self, r'@([a-zA-Z0-9_]+)')

	def handleMatch(self, m):
		el = markdown.etree.Element('hh')
		el.attrib['user'] = m.group(2)
		return el

class StrikePattern(markdown.inlinepatterns.SimpleTagPattern):
	def __init__(self):
		markdown.inlinepatterns.SimpleTagPattern.__init__(self, r'(?<!\\)(~~)([^~]+)\2', 's')

md = markdown.Markdown()
md.preprocessors['habr-cut'] = HabracutPreprocessor()
md.treeprocessors['habr-headers'] = HeaderPostprocessor()
md.treeprocessors['habr-image'] = ImagePostprocessor()
md.treeprocessors['habr-highlight'] = CodeBlockProcessor()
md.inlinePatterns['habr-user'] = HabrauserPattern()
md.inlinePatterns['habr-strike'] = StrikePattern()

text = sys.stdin.read().decode('utf-8')
html = md.convert(text)
print(html.encode('utf-8'))

