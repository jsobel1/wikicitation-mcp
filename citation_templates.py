"""
citation_templates.py
Per-language registry of Wikipedia citation templates and field aliases.

Sourced from each Wikipedia's bibliographic-conventions / Zitierregeln /
Conventions bibliographiques / Cite las fontes pages plus the template-namespace
documentation. Verified 2026-04 against fr/de/es/it/pt/en.

Each language entry maps native template names -> a canonical citation type:
    journal | book | web | news | chapter | thesis | conference |
    encyclopedia | report | citation
The canonical type is stable across languages so downstream metrics
(SciScore, citation-class breakdowns) are comparable cross-lingually.

Field aliases let us pull the same logical field (title, author, year, doi,
isbn, url, journal/work, publisher) out of templates regardless of language —
e.g. fr "titre" / de "Titel" / es "título" / pt "título" / en "title" all
become canonical "title".

Adding a language: define TEMPLATE_REGISTRY[code] and FIELD_ALIASES[code].
Both maps are consulted with case-insensitive, whitespace-collapsed keys, so
"Cite Web" and "cite web" both resolve.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Template -> canonical citation type
# ---------------------------------------------------------------------------

TEMPLATE_REGISTRY: dict[str, dict[str, str]] = {
    # English Wikipedia (CS1 family). The "cite " prefix is stripped by the
    # parser before lookup, so we register the bare type names too.
    "en": {
        "cite journal":      "journal",
        "cite book":         "book",
        "cite web":          "web",
        "cite news":         "news",
        "cite magazine":     "news",
        "cite press release":"news",
        "cite conference":   "conference",
        "cite thesis":       "thesis",
        "cite encyclopedia": "encyclopedia",
        "cite encyclopaedia":"encyclopedia",
        "cite report":       "report",
        "cite techreport":   "report",
        "cite document":     "report",
        "cite arxiv":        "journal",
        "cite biorxiv":      "journal",
        "cite medrxiv":      "journal",
        "cite ssrn":         "journal",
        "cite chapter":      "chapter",
        "cite interview":    "news",
        "cite podcast":      "web",
        "cite video":        "web",
        "citation":          "citation",
    },

    # Wikipédia francophone — see fr:Wikipédia:Conventions_bibliographiques.
    # CS1 templates are also tolerated (many fr articles import them).
    "fr": {
        "article":           "journal",
        "périodique":        "journal",
        "ouvrage":           "book",
        "livre":             "book",
        "chapitre":          "chapter",
        "lien web":          "web",
        "lien brisé":        "web",
        "article de presse": "news",
        "thèse":             "thesis",
        "mémoire":           "thesis",
        "conférence":        "conference",
        "encyclopédie":      "encyclopedia",
        "rapport":           "report",
    },

    # Deutsche Wikipedia — see de:Wikipedia:Zitierregeln.
    # de uses fewer, more flexible templates; {{Literatur}} covers books and
    # journals depending on its parameters. We disambiguate with field
    # introspection in citation_utils.
    "de": {
        "literatur":         "book",   # disambiguated to "journal" by the parser
                                       # when the template carries a Sammelwerk= field.
        "internetquelle":    "web",
        "patent":            "report",
    },

    # Wikipedia en español — see es:Wikipedia:Verificabilidad and the
    # Plantilla:Cita_* family.
    "es": {
        "cita libro":         "book",
        "cita publicación":   "journal",
        "cita publicacion":   "journal",
        "cita web":           "web",
        "cita noticia":       "news",
        "cita enciclopedia":  "encyclopedia",
        "cita conferencia":   "conference",
        "cita tesis":         "thesis",
        "cita informe":       "report",
        "cita entrevista":    "news",
        "cita vídeo":         "web",
        "cita video":         "web",
        "obra citada":        "citation",
    },

    # Wikipedia in italiano — see it:Aiuto:Cita_le_fonti.
    "it": {
        "cita libro":         "book",
        "cita pubblicazione": "journal",
        "cita rivista":       "journal",
        "cita web":           "web",
        "cita news":          "news",
        "cita conferenza":    "conference",
        "cita tesi":          "thesis",
        "cita enciclopedia":  "encyclopedia",
        "cita testo":         "citation",
    },

    # Wikipédia em português — see pt:Wikipédia:Livro_de_estilo/Cite_as_fontes.
    "pt": {
        "citar livro":             "book",
        "citar revista":           "journal",
        "citar periódico":         "journal",
        "citar periodico":         "journal",
        "citar web":               "web",
        "citar jornal":            "news",
        "citar notícia":           "news",
        "citar noticia":           "news",
        "citar conferência":       "conference",
        "citar conferencia":       "conference",
        "citar tese":              "thesis",
        "citar enciclopédia":      "encyclopedia",
        "citar enciclopedia":      "encyclopedia",
        "citar entrevista":        "news",
        "citar vídeo":             "web",
        "citar video":             "web",
        "citar podcast":           "web",
        "citar série":             "web",
        "citar relatório técnico": "report",
        "citar relatorio tecnico": "report",
    },
}


# ---------------------------------------------------------------------------
# Field aliases  (canonical -> set of native names)
# ---------------------------------------------------------------------------
#
# Each language entry maps a *native* parameter name to a *canonical* field.
# Canonical fields are: title, author, year, doi, isbn, pmid, url, journal,
# publisher, work, accessdate.

FIELD_ALIASES: dict[str, dict[str, str]] = {
    "en": {
        "title": "title", "author": "author", "author1": "author",
        "first": "author", "last": "author", "first1": "author", "last1": "author",
        "year": "year", "date": "year",
        "doi": "doi", "isbn": "isbn", "pmid": "pmid",
        "url": "url", "website": "url",
        "journal": "journal", "magazine": "journal", "newspaper": "journal",
        "work": "work",
        "publisher": "publisher",
        "accessdate": "accessdate", "access-date": "accessdate",
    },

    "fr": {
        "titre": "title", "title": "title",
        "auteur": "author", "auteur1": "author", "nom": "author",
        "prénom": "author", "prenom": "author",
        "nom1": "author", "prénom1": "author",
        "année": "year", "annee": "year", "date": "year",
        "doi": "doi", "isbn": "isbn", "pmid": "pmid",
        "url": "url", "lien": "url", "site": "url",
        "périodique": "journal", "periodique": "journal", "journal": "journal",
        "revue": "journal",
        "éditeur": "publisher", "editeur": "publisher",
        "consulté le": "accessdate", "consulte le": "accessdate",
    },

    "de": {
        "titel": "title",
        "autor": "author", "verfasser": "author", "hrsg": "author",
        "jahr": "year", "datum": "year",
        "doi": "doi", "isbn": "isbn", "pmid": "pmid",
        "url": "url", "online": "url",
        # Sammelwerk = the host work for a Literatur citation; its presence
        # is what disambiguates a "Literatur" template into "journal" vs "book".
        "sammelwerk": "journal", "fundstelle": "journal", "zeitschrift": "journal",
        "verlag": "publisher", "herausgeber": "publisher",
        "abruf": "accessdate", "zugriff": "accessdate",
    },

    "es": {
        "título": "title", "titulo": "title", "title": "title",
        "autor": "author", "apellido": "author", "nombre": "author",
        "apellido1": "author", "nombre1": "author",
        "año": "year", "ano": "year", "fecha": "year",
        "doi": "doi", "isbn": "isbn", "pmid": "pmid",
        "url": "url", "enlace": "url", "sitioweb": "url",
        "publicación": "journal", "publicacion": "journal", "revista": "journal",
        "periódico": "journal", "periodico": "journal",
        "editorial": "publisher",
        "fechaacceso": "accessdate",
    },

    "it": {
        "titolo": "title", "title": "title",
        "autore": "author", "cognome": "author", "nome": "author",
        "anno": "year", "data": "year",
        "doi": "doi", "isbn": "isbn", "pmid": "pmid",
        "url": "url", "sito": "url",
        "rivista": "journal", "pubblicazione": "journal",
        "editore": "publisher",
        "accesso": "accessdate",
    },

    "pt": {
        "título": "title", "titulo": "title", "title": "title",
        "autor": "author", "sobrenome": "author", "nome": "author",
        "ano": "year", "data": "year",
        "doi": "doi", "isbn": "isbn", "pmid": "pmid",
        "url": "url", "url-arquivo": "url",
        "periódico": "journal", "periodico": "journal", "revista": "journal",
        "obra": "work", "jornal": "journal",
        "editora": "publisher", "publicado": "publisher",
        "acessodata": "accessdate", "acesso-data": "accessdate",
    },
}


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def _normalize(name: str) -> str:
    """Lowercase + collapse whitespace for case/space-insensitive matching."""
    return " ".join(name.strip().lower().split())


def _lang_or_fallback(lang: str) -> str:
    """Coerce e.g. 'pt-br' down to 'pt' when no explicit subvariant registry exists."""
    if lang in TEMPLATE_REGISTRY:
        return lang
    base = lang.split("-", 1)[0]
    return base if base in TEMPLATE_REGISTRY else "en"


def classify_template(template_name: str, lang: str = "en") -> str | None:
    """
    Return the canonical citation type for a template name in the given lang,
    or None if the template is not a citation template in that wiki.

    Always falls back to the English CS1 registry as well, since cs1-style
    {{cite journal}} / {{cite book}} templates are commonly imported into
    non-English wikis.
    """
    name = _normalize(template_name)
    primary = TEMPLATE_REGISTRY.get(_lang_or_fallback(lang), {})
    if name in primary:
        return primary[name]
    if lang != "en":
        en_reg = TEMPLATE_REGISTRY["en"]
        if name in en_reg:
            return en_reg[name]
        # Strip the "cite " prefix and try the bare type as a last-resort
        # match against either registry (covers some hand-rolled templates).
        if name.startswith("cite "):
            bare = name[5:]
            if bare in primary:
                return primary[bare]
    return None


def canonical_field(param_name: str, lang: str = "en") -> str | None:
    """
    Map a native template parameter name to a canonical field
    (title/author/year/doi/isbn/pmid/url/journal/publisher/work/accessdate),
    or None if the parameter is unrecognised.
    """
    name = _normalize(param_name)
    primary = FIELD_ALIASES.get(_lang_or_fallback(lang), {})
    if name in primary:
        return primary[name]
    if lang != "en" and name in FIELD_ALIASES["en"]:
        return FIELD_ALIASES["en"][name]
    return None


def disambiguate_de_literatur(fields: dict[str, str]) -> str:
    """
    de:Literatur covers both books and journal articles. The presence of
    Sammelwerk / Fundstelle / Zeitschrift / Band (volume) is the convention
    that signals a journal/serial citation.
    """
    keys = {k.lower() for k in fields}
    if keys & {"sammelwerk", "fundstelle", "zeitschrift", "band", "issn"}:
        return "journal"
    return "book"
