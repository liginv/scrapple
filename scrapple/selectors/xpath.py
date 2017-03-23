"""
scrapple.selectors.xpath
~~~~~~~~~~~~~~~~~~~~~~~~

"""

from __future__ import print_function

try:
	from urlparse import urljoin
except ImportError:
	from urllib.parse import urljoin

from lxml.etree import XPathError
from scrapple.selectors.selector import Selector
from scrapple.utils.text import make_ascii


class XpathSelector(Selector):
	"""
	The ``XpathSelector`` object defines XPath expressions.

	"""
	
	def __init__(self, url):
		"""
		The ``Selector`` class acts as the super class for this class.

		"""
		super(XpathSelector, self).__init__(url)


	def extract_content(self, *args, **kwargs):
		"""
		Method for performing the content extraction for the given XPath expression.

		The XPath selector expression can be used to extract content \
		from the element tree corresponding to the fetched web page.

		If the selector is "url", the URL of the current web page is returned.
		Otherwise, the selector expression is used to extract content. The particular \
		attribute to be extracted ("text", "href", etc.) is specified in the method \
		arguments, and this is used to extract the required content. If the content \
		extracted is a link (from an attr value of "href" or "src"), the URL is parsed \
		to convert the relative path into an absolute path.

		If the selector does not fetch any content, the default value is returned. \
		If no default value is specified, an exception is raised.

		:param selector: The XPath expression
		:param attr: The attribute to be extracted from the selected tag
		:param default: The default value to be used if the selector does not return any data
		:return: The extracted content

		"""
		try:
			selector, attr, default, connector = [kwargs.get(x, '') for x in ['selector', 'attr', 'default', 'connector']]
			if selector == "url":
				return self.url
			if attr == "text":
				tag = self.tree.xpath(selector)[0]
				content = connector.join([make_ascii(x).strip() for x in tag.itertext()])
				content = content.replace("\n", " ").strip()
			else:
				content = self.tree.xpath(selector)[0].get(attr)
				if attr in ["href", "src"]:
					content = urljoin(self.url, content)
			return content
		except IndexError:
			if default is not "":
				return default
			raise Exception("There is no content for the selector " + selector)
		except XPathError:
			raise Exception("Invalid XPath selector " + selector)


	def extract_links(self, *args, **kwargs):
		"""
		Method for performing the link extraction for the crawler.

		The selector passed as the argument is a selector to point to the anchor tags \
		that the crawler should pass through. A list of links is obtained, and the links \
		are iterated through. The relative paths are converted into absolute paths and \
		a ``XpathSelector`` object is created with the URL of the next page as the argument \
		and this created object is yielded. 

		The extract_links method basically generates ``XpathSelector`` objects for all of \
		the links to be crawled through.

		:param selector: The selector for the anchor tags to be crawled through
		:return: A ``XpathSelector`` object for every page to be crawled through 
		
		"""
		try:
			selector = kwargs.get('selector', '')
			links = self.tree.xpath(selector)
			for link in links:
				next_url = urljoin(self.url, link.get('href'))
				yield XpathSelector(next_url)
		except XPathError:
			raise Exception("Invalid XPath selector " + selector)


	def extract_rows(self, *args, **kwargs):
		"""
		Row data extraction for extract_tabular
		"""
		result_list = []
		result = kwargs.get('result', {})

		try:
			values = self.tree.xpath(kwargs.get('selector', ''))
			if len(kwargs.get('table_headers', [])) >= len(values):
				from itertools import izip_longest
				pairs = izip_longest(kwargs.get('table_headers', []), values, fillvalue=kwargs.get('default', ''))
			else:
				from itertools import izip
				pairs = izip(kwargs.get('table_headers', []), values)
			for head, val in pairs:
				if kwargs.get('verbosity', 0) > 1:
					print("\nExtracting", head, "attribute", sep=' ', end='')
				if kwargs.get('attr', 'text') == "text":
					try:
						content = kwargs.get('connector', '').join([make_ascii(x).strip() for x in val.itertext()])
					except Exception:
						content = kwargs.get('default', '')
					content = content.replace("\n", " ").strip()
				else:
					content = val.get(kwargs.get('attr', 'text'))
					if kwargs.get('attr', 'text') in ["href", "src"]:
						content = urljoin(self.url, content)
				result[head] = content
			result_list.append(result)
		except XPathError:
			raise Exception("Invalid XPath selector " + kwargs.get('selector', ''))
		except TypeError:
			raise Exception("Selector expression string to be provided. Got " + kwargs.get('selector', ''))

		return result_list


	def extract_columns(self, *args, **kwargs):
		"""
		Column data extraction for extract_tabular
		"""
		result_list = []
		result = kwargs.get('result', {})

		try:
			if type(kwargs.get('selector', '')) in [str, unicode]:
				selectors = [kwargs.get('selector', '')]
			elif type(kwargs.get('selector', '')) == list:
				selectors = kwargs.get('selector', '')
			else:
				raise Exception("Use a list of selector expressions for the various columns")
			from itertools import izip, count
			pairs = izip(kwargs.get('table_headers', []), selectors)
			columns = {}
			for head, selector in pairs:
				columns[head] = self.tree.xpath(selector)
			try:
				for i in count(start=0):
					r = result.copy()
					for head in columns.keys():
						if kwargs.get('verbosity', 0) > 1:
							print("\nExtracting", head, "attribute", sep=' ', end='')
						col = columns[head][i]
						if kwargs.get('attr', 'text') == "text":
							try:
								content = kwargs.get('connector', '').join([make_ascii(x).strip() for x in col.itertext()])
							except Exception:
								content = kwargs.get('default', '')
							content = content.replace("\n", " ").strip()
						else:
							content = col.get(kwargs.get('attr', 'text'))
							if kwargs.get('attr', 'text') in ["href", "src"]:
								content = urljoin(self.url, content)
						r[head] = content
					result_list.append(r)
			except IndexError:
				pass
		except XPathError:
			raise Exception("Invalid XPath selector " + selector)
		except TypeError:
			raise Exception("Selector expression string to be provided. Got " + selector)

		return result_list


	def extract_tabular(self, *args, **kwargs):
		"""
		Method for performing the extraction of tabular data.

		:param result: A dictionary containing the extracted data so far
		:param table_type: Can be "rows" or "columns". This determines the type of table to be extracted. \
		A row extraction is when there is a single row to be extracted and mapped to a set of headers. \
		A column extraction is when a set of rows have to be extracted, giving a list of header-value mappings.
		:param header: The headers to be used for the table. This can be a list of headers, or a selector that gives the list of headers
		:param prefix: A prefix to be added to each header
		:param suffix: A suffix to be added to each header
		:param selector: For row extraction, this is a selector that gives the row to be extracted. \
		For column extraction, this is a list of selectors for each column.
		:param attr: The attribute to be extracted from the selected tag
		:param default: The default value to be used if the selector does not return any data
		:param verbosity: The verbosity set as the argument for scrapple run
		:return: A 2-tuple containing the list of all the column headers extracted and the list of \
		dictionaries which contain (header, content) pairs
		"""
		result = kwargs.get('result', {})
		if type(kwargs.get('header', [])) in [str, unicode]:
			try:
				header_list = self.tree.xpath(kwargs.get('header', []))
				table_headers = [kwargs.get('prefix', '') + h.text + kwargs.get('suffix', '') for h in header_list]
			except XPathError:
				raise Exception("Invalid XPath selector " + kwargs.get('header', []))
		else:
			table_headers = [kwargs.get('prefix', '') + h + kwargs.get('suffix', '') for h in kwargs.get('header', [])]
		if kwargs.get('table_type', 'rows') not in ["rows", "columns"]:
			raise Exception("Specify 'rows' or 'columns' in table_type")
		kwargs.update({'table_headers': table_headers})
		if kwargs.get('table_type', 'rows') == "rows":
			result_list = self.extract_rows(**kwargs)
		else:
			result_list = self.extract_columns(**kwargs)
		return table_headers, result_list
