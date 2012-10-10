#!/usr/bin/env python
""" Extraction parsers for structured data embedded into HTML or XML files. The former may include
RDFa or microdata. The syntax and the extraction procedures are based on:

* The RDFa specifications: http://www.w3.org/TR/#tr_RDFa
* The microdata specification: http://www.w3.org/TR/microdata/
* The specification of the microdata to RDF conversion: http://www.w3.org/TR/microdata-rdf/

License: W3C Software License, http://www.w3.org/Consortium/Legal/copyright-software
Author: Ivan Herman

"""
import sys, imp

from rdflib.parser import Parser, StringInputSource, URLInputSource, FileInputSource

def _get_orig_source(source) :
	"""A bit of a hack; the RDFa/microdata parsers need more than what the upper layers of RDFLib provide...
	This method returns the original source references.
	"""
	if isinstance(source, StringInputSource) :
		orig_source = source.getByteStream()
	elif isinstance(source, URLInputSource) :
		orig_source = source.url
	elif isinstance(source, FileInputSource) :
		orig_source = source.file.name
		source.file.close()
	baseURI = source.getPublicId()
	return (baseURI, orig_source)


def _check_error(graph) :
	from .pyRdfa import RDFA_Error, ns_rdf
	for (s,p,o) in graph.triples((None, ns_rdf["type"], RDFA_Error)) :
		for (x,y,msg) in graph.triples((s,None,None)) :
			raise Exception(msg)


# This is the parser interface as it would look when called from the rest of RDFLib
class RDFaParser(Parser) :
	""" 
	Wrapper around the RDFa 1.1 parser. For further details on the RDFa 1.1 processing, see the
	relevant W3C documents at http://www.w3.org/TR/#tr_RDFa. RDFa 1.1 is defined for XHTML, HTML5, SVG and, 
	in general, for any XML language.

	Note that the parser can also handle RDFa 1.0 if the extra parameter is used and/or the input source uses
	RDFa 1.0 specific @version or DTD-s.
	"""
	def parse(self, source, graph,
			  pgraph                 = None,
			  media_type             = "",
			  rdfa_version           = None,
			  embedded_rdf           = False,
			  vocab_expansion        = False, vocab_cache = False) :
		"""
		@param source: one of the input sources that the RDFLib package defined
		@type source: InputSource class instance
		@param graph: target graph for the triples; output graph, in RDFa spec. parlance
		@type graph: RDFLib Graph
		@keyword pgraph: target for error and warning triples; processor graph, in RDFa spec. parlance. If set to None, these triples are ignored
		@type pgraph: RDFLib Graph
		@keyword media_type: explicit setting of the preferred media type (a.k.a. content type) of the the RDFa source. None means the content type of the HTTP result is used, or a guess is made based on the suffix of a file
		@type media_type: string
		@keyword rdfa_version: 1.0 or 1.1. If the value is "", then, by default, 1.1 is used unless the source has explicit signals to use 1.0 (e.g., using a @version attribute, using a DTD set up for 1.0, etc)
		@type rdfa_version: string
		@keyword embedded_rdf: some formats allow embedding RDF in other formats: (X)HTML can contain turtle in a special <script> element, SVG can have RDF/XML embedded in a <metadata> element. This flag controls whether those triples should be interpreted and added to the output graph. Some languages (e.g., SVG) require this, and the flag is ignored.
		@type embedded_rdf: Boolean
		@keyword vocab_expansion: whether the RDFa @vocab attribute should also mean vocabulary expansion (see the RDFa 1.1 spec for further details)
		@type vocab_expansion: Boolean
		@keyword vocab_cache: in case vocab expansion is used, whether the expansion data (i.e., vocabulary) should be cached locally. This requires the ability for the local application to write on the local file system
		@type vocab_chache: Boolean
		"""
		(baseURI, orig_source) = _get_orig_source(source)
		self._process(graph, pgraph, baseURI, orig_source, 
			          media_type      = media_type,
			          rdfa_version    = rdfa_version,
			          embedded_rdf    = embedded_rdf,
			          vocab_expansion = vocab_expansion, vocab_cache = vocab_cache)

	def _process(self, graph, pgraph, baseURI,  orig_source,
			  media_type      = "",
			  rdfa_version    = None,
			  embedded_rdf    = False,
			  vocab_expansion = False, vocab_cache     = False) :
		from .pyRdfa import pyRdfa, Options			
		self.options = Options(output_processor_graph = (pgraph != None),
							   embedded_rdf           = embedded_rdf,
							   vocab_expansion        = vocab_expansion,
							   vocab_cache            = vocab_cache)
		
		if media_type == None : media_type = ""
		processor    = pyRdfa(self.options, 
							  base = baseURI, 
							  media_type = media_type, 
							  rdfa_version = rdfa_version)
		processor.graph_from_source(orig_source, graph=graph, pgraph=pgraph, rdfOutput=False)
		# This may result in an exception if the graph parsing led to an error
		_check_error(graph)

class RDFa10Parser(Parser) :
	"""
	This is just a convenience class to wrap around the RDFa 1.0 parser.
	"""
	def parse(self, source, graph, pgraph = None, media_type = "") :
		"""
		@param source: one of the input sources that the RDFLib package defined
		@type source: InputSource class instance
		@param graph: target graph for the triples; output graph, in RDFa spec. parlance
		@type graph: RDFLib Graph
		@keyword pgraph: target for error and warning triples; processor graph, in RDFa spec. parlance. If set to None, these triples are ignored
		@type pgraph: RDFLib Graph
		@keyword media_type: explicit setting of the preferred media type (a.k.a. content type) of the the RDFa source. None means the content type of the HTTP result is used, or a guess is made based on the suffix of a file
		@type media_type: string
		@keyword rdfOutput: whether Exceptions should be catched and added, as triples, to the processor graph, or whether they should be raised.
		@type rdfOutput: Boolean
		"""
		RDFaParser().parse(source, graph, pgraph = pgraph, media_type = media_type, rdfa_version = "1.0")

class MicrodataParser(Parser) :
	"""
	Wrapper around an HTML5 microdata, extracted and converted into RDF. For the specification of microdata,
	see the relevant section of the HTML5 spec: http://www.w3.org/TR/microdata/; for the algorithm used
	to extract microdata into RDF, see http://www.w3.org/TR/microdata-rdf/.
	"""
	def parse(self, source, graph, vocab_expansion = False, vocab_cache = False) :
		"""
		@param source: one of the input sources that the RDFLib package defined
		@type source: InputSource class instance
		@param graph: target graph for the triples; output graph, in RDFa spec. parlance
		@type graph: RDFLib Graph
		@keyword vocab_expansion: whether the RDFa @vocab attribute should also mean vocabulary expansion (see the RDFa 1.1 spec for further details)
		@type vocab_expansion: Boolean
		@keyword vocab_cache: in case vocab expansion is used, whether the expansion data (i.e., vocabulary) should be cached locally. This requires the ability for the local application to write on the local file system
		@type vocab_chache: Boolean
		@keyword rdfOutput: whether Exceptions should be catched and added, as triples, to the processor graph, or whether they should be raised.
		@type rdfOutput: Boolean
		"""
		(baseURI, orig_source) = _get_orig_source(source)
		self._process(graph, baseURI, orig_source, 
			          vocab_expansion = vocab_expansion,
			          vocab_cache     = vocab_cache)

	def _process(self, graph, baseURI, orig_source, vocab_expansion = False, vocab_cache  = False) :
		from .pyMicrodata import pyMicrodata
		processor    = pyMicrodata(base = baseURI, vocab_expansion = vocab_expansion, vocab_cache = vocab_cache)
		processor.graph_from_source(orig_source, graph=graph, rdfOutput = False)

class StructuredDataParser(Parser) :
	"""
	Convenience parser to extract both RDFa (including embedded Turtle) and microdata from an HTML file.
	It is simply a wrapper around the specific parsers.
	"""
	def parse(self, source, graph,
			  pgraph                 = None,
			  rdfa_version           = "",
			  vocab_expansion        = False,
			  vocab_cache            = False) :
		"""
		@param source: one of the input sources that the RDFLib package defined
		@type source: InputSource class instance
		@param graph: target graph for the triples; output graph, in RDFa spec. parlance
		@keyword rdfa_version: 1.0 or 1.1. If the value is "", then, by default, 1.1 is used unless the source has explicit signals to use 1.0 (e.g., using a @version attribute, using a DTD set up for 1.0, etc)
		@type rdfa_version: string
		@type graph: RDFLib Graph
		@keyword pgraph: target for error and warning triples; processor graph, in RDFa spec. parlance. If set to None, these triples are ignored
		@type pgraph: RDFLib Graph
		@keyword vocab_expansion: whether the RDFa @vocab attribute should also mean vocabulary expansion (see the RDFa 1.1 spec for further details)
		@type vocab_expansion: Boolean
		@keyword vocab_cache: in case vocab expansion is used, whether the expansion data (i.e., vocabulary) should be cached locally. This requires the ability for the local application to write on the local file system
		@type vocab_chache: Boolean
		@keyword rdfOutput: whether Exceptions should be catched and added, as triples, to the processor graph, or whether they should be raised.
		@type rdfOutput: Boolean
		"""
		(baseURI, orig_source) = _get_orig_source(source)
		RDFaParser()._process(graph, pgraph, baseURI, orig_source, 
			          media_type      = 'text/html',
			          rdfa_version    = rdfa_version,
			          vocab_expansion = vocab_expansion,
			          vocab_cache     = vocab_cache)
		MicrodataParser()._process(graph, baseURI, orig_source,
			          vocab_expansion = vocab_expansion,
			          vocab_cache     = vocab_cache)
		from .hturtle import HTurtleParser
		HTurtleParser()._process(graph, baseURI, orig_source, media_type = 'text/html')

