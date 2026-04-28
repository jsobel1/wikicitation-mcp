# mcp_interface.R
# Called by r_bridge.py via Rscript. Reads a JSON payload from stdin,
# dispatches to the appropriate wikilite function, and writes JSON to stdout.

suppressPackageStartupMessages({
  library(wikilite)
  library(jsonlite)
})

`%||%` <- function(x, y) if (is.null(x)) y else x

con       <- file("stdin", open = "r")
input_raw <- readLines(con, warn = FALSE)
close(con)
payload   <- jsonlite::fromJSON(paste(input_raw, collapse = ""))
tool      <- payload$tool
args      <- payload$args

# Detect whether the installed wikilite supports the `lang` parameter.
.hist_formals  <- names(formals(wikilite::get_article_full_history_table))
.has_lang_hist <- "lang" %in% .hist_formals

.recent_formals  <- names(formals(wikilite::get_article_most_recent_table))
.has_lang_recent <- "lang" %in% .recent_formals

# Helper: fetch most-recent wikitext, compatible with old/new wikilite.
.fetch_wikitext <- function(article_name, date_an, lang) {
  extra <- if (.has_lang_recent) list(lang = lang) else list()
  art <- do.call(
    wikilite::get_article_most_recent_table,
    c(list(article_name = article_name, date_an = date_an), extra)
  )
  art$`*`[1L]
}

result <- tryCatch({
  switch(tool,

    # ── Article history ────────────────────────────────────────────────────────
    "get_article_most_recent" = {
      date_an <- args$date_an %||% args$date_limit %||% NULL
      lang    <- args$lang %||% "en"
      extra   <- if (.has_lang_recent) list(lang = lang) else list()
      do.call(wikilite::get_article_most_recent_table,
              c(list(article_name = args$article_name, date_an = date_an), extra))
    },

    "get_article_history" = {
      date_an <- args$date_an %||% args$date_limit %||% NULL
      lang    <- args$lang %||% "en"
      extra   <- if (.has_lang_hist) list(lang = lang) else list()
      do.call(wikilite::get_article_full_history_table,
              c(list(article_name = args$article_name, date_an = date_an), extra))
    },

    "get_article_info" = {
      date_an <- args$date_an %||% args$date_limit %||% NULL
      tbl     <- wikilite::get_article_info_table(args$article_name,
                                                   date_an = date_an)
      as.list(tbl)
    },

    # ── Citation counts ────────────────────────────────────────────────────────
    "get_doi_count"  = list(count = wikilite::get_doi_count(args$text)),
    "get_ref_count"  = list(count = wikilite::get_refCount(args$text)),
    "get_url_count"  = list(count = wikilite::get_urlCount(args$text)),
    "get_isbn_count" = {
      m <- stringr::str_match_all(args$text, wikilite::pkg.env$isbn_regexp)[[1L]]
      list(count = if (is.matrix(m)) nrow(m) else 0L)
    },
    "get_any_count"  = list(count = wikilite::get_anyCount(args$text, args$regexp)),

    # ── Quality scores ─────────────────────────────────────────────────────────
    "get_sci_score" = {
      wikitext <- if (!is.null(args$text)) {
        args$text
      } else {
        date_an <- args$date_an %||% args$date_limit %||% NULL
        .fetch_wikitext(args$article_name, date_an, args$lang %||% "en")
      }
      list(sci_score  = wikilite::get_sci_score(wikitext),
           sci_score2 = wikilite::get_sci_score2(wikitext))
    },

    "get_sci_score2" = list(sci_score2 = wikilite::get_sci_score2(args$text)),

    # ── Citation extraction & parsing ──────────────────────────────────────────
    "extract_citations" = wikilite::extract_citations(args$text),

    "replace_wikihypelinks" = {
      list(cleaned_text = wikilite::replace_wikihypelinks(args$text))
    },

    "parse_all_citations" = {
      date_an  <- args$date_an %||% args$date_limit %||% NULL
      wikitext <- .fetch_wikitext(args$article_name, date_an,
                                  args$lang %||% "en")
      wikilite::parse_article_ALL_citations(wikitext)
    },

    # ── Annotation ─────────────────────────────────────────────────────────────
    "annotate_dois"          = wikilite::annotate_doi_list_europmc(args$doi_list),
    "annotate_dois_crossref" = wikilite::annotate_doi_list_cross_ref(
      args$doi_list,
      batch_size = as.integer(args$batch_size %||% 50L)
    ),

    # ── Edit trends ────────────────────────────────────────────────────────────
    "get_revert_counts" = wikilite::get_revert_counts(
      args$start,
      args$end,
      rev_eds = args$rev_eds %||% TRUE
    ),

    # ── Citation type counts ───────────────────────────────────────────────────
    "get_citation_type_counts" = {
      date_an  <- args$date_an %||% args$date_limit %||% NULL
      lang     <- args$lang %||% "en"
      wikitext <- .fetch_wikitext(args$article_name, date_an, lang)
      extracted <- wikilite::extract_citations(wikitext)
      if (length(extracted) == 0L) return(list())
      raw_types      <- sapply(extracted, wikilite::parse_cite_type, USE.NAMES = FALSE)
      display_cats   <- sapply(raw_types, wikilite::classify_cite_type, USE.NAMES = FALSE)
      tbl            <- as.data.frame(table(category = display_cats), stringsAsFactors = FALSE)
      colnames(tbl)  <- c("category", "count")
      tbl[order(-tbl$count), ]
    },

    # ── Category helpers ───────────────────────────────────────────────────────
    "get_category_pages" = {
      as.list(wikilite::get_pagename_in_cat(args$category))
    },

    "get_subcat_table" = wikilite::get_subcat_table(args$catname),

    # ── Top cited papers ───────────────────────────────────────────────────────
    "get_top_cited" = {
      date_an <- args$date_an %||% args$date_limit %||% NULL
      lang    <- args$lang %||% "en"
      extra   <- if (.has_lang_recent) list(lang = lang) else list()
      recent  <- do.call(wikilite::get_article_most_recent_table,
                         c(list(article_name = args$article_name,
                                date_an = date_an), extra))
      doi_df <- wikilite::get_regex_citations_in_wiki_table(
        recent, wikilite::pkg.env$doi_regexp
      )
      wikilite::get_top_cited_wiki_papers(doi_df)
    },

    # ── Longitudinal probing ───────────────────────────────────────────────────
    "probe_article" = {
      lang  <- args$lang %||% "en"
      extra <- if ("lang" %in% names(formals(wikilite::probe_article_over_time)))
                 list(lang = lang) else list()
      do.call(wikilite::probe_article_over_time,
              c(list(article_name   = args$article_name,
                     dates_to_probe = args$dates_to_probe,
                     metrics        = args$metrics %||%
                       c("sci_score", "doi_count", "ref_count", "size")),
                extra))
    },

    stop(paste("Unknown tool:", tool))
  )
}, error = function(e) {
  list(error = TRUE, message = conditionMessage(e))
})

cat(jsonlite::toJSON(result, auto_unbox = TRUE, null = "null"))
