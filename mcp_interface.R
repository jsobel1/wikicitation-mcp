#!/usr/bin/env Rscript
# mcp_interface.R
# Bridge entre le serveur MCP Python et le package WikiCitationHistoRy.
# Usage : echo '<JSON>' | Rscript mcp_interface.R
#
# Protocole :
#   stdin  → {"tool": "<nom>", "args": {...}}
#   stdout → JSON du résultat (ou {"error": true, "message": "..."})

suppressPackageStartupMessages({
  library(WikiCitationHistoRy)
  library(jsonlite)
})

# ── Opérateur null-coalescing ─────────────────────────────────────────────────
`%||%` <- function(x, y) if (!is.null(x)) x else y

# ── Lecture stdin ─────────────────────────────────────────────────────────────
input_raw <- readLines("stdin", n = 1L, warn = FALSE)

if (length(input_raw) == 0L || nchar(trimws(input_raw)) == 0L) {
  cat(jsonlite::toJSON(
    list(error = TRUE, message = "Empty input on stdin"),
    auto_unbox = TRUE
  ))
  quit(status = 1L)
}

input <- tryCatch(
  jsonlite::fromJSON(input_raw, simplifyVector = TRUE),
  error = function(e) {
    cat(jsonlite::toJSON(
      list(error = TRUE, message = paste("JSON parse error:", conditionMessage(e))),
      auto_unbox = TRUE
    ))
    quit(status = 1L)
  }
)

tool <- input$tool
args <- input$args %||% list()

# ── Dispatch ──────────────────────────────────────────────────────────────────
result <- tryCatch({

  switch(tool,

    # ── Groupe 1 : Historique Wikipedia ──────────────────────────────────────

    "get_article_history" = {
      date_an <- args$date_limit %||% "2024-01-01T00:00:00Z"
      df <- get_article_full_history_table(args$article_name, date_an = date_an)
      # Exclure le wikitext brut (colonne "*") — trop volumineux pour MCP
      df[, setdiff(names(df), "*"), drop = FALSE]
    },

    "get_article_recent" = {
      date_an <- args$date_limit %||% "2024-01-01T00:00:00Z"
      df <- get_article_most_recent_table(args$article_name, date_an = date_an)
      list(
        metadata = df[, setdiff(names(df), "*"), drop = FALSE],
        wikitext = as.character(df$`*` %||% "")
      )
    },

    "get_article_initial" = {
      df <- get_article_initial_table(args$article_name)
      list(
        metadata = df[, setdiff(names(df), "*"), drop = FALSE],
        wikitext = as.character(df$`*` %||% "")
      )
    },

    "get_article_info" = {
      as.list(get_article_info_table(args$article_name))
    },

    "get_category_pages" = {
      as.character(get_pagename_in_cat(args$category))
    },

    "get_category_history" = {
      df <- get_category_articles_history(args$article_list)
      df[, setdiff(names(df), "*"), drop = FALSE]
    },

    "get_category_recent" = {
      df <- get_category_articles_most_recent(args$article_list)
      list(
        metadata = df[, setdiff(names(df), "*"), drop = FALSE],
        wikitext = as.list(as.character(df$`*` %||% ""))
      )
    },

    "get_category_creation" = {
      df <- get_category_articles_creation(args$article_list)
      df[, setdiff(names(df), "*"), drop = FALSE]
    },

    "get_subcat_table" = {
      get_subcat_table(args$catname, replecement = args$replecement %||% "_")
    },

    "get_subcat_with_depth" = {
      get_subcat_with_depth(
        args$catname,
        depth       = as.integer(args$depth %||% 1L),
        replecement = args$replecement %||% "_"
      )
    },

    # ── Groupe 2 : Comptage et extraction ─────────────────────────────────────

    "get_doi_count" = {
      list(count = get_doi_count(args$text))
    },

    "get_ref_count" = {
      list(count = get_refCount(args$text))
    },

    "get_url_count" = {
      list(count = get_urlCount(args$text))
    },

    "get_isbn_count" = {
      list(count = get_ISBN_count(args$text))
    },

    "get_hyperlink_count" = {
      list(count = get_hyperlinkCount(args$text))
    },

    "get_any_count" = {
      list(count = get_anyCount(args$text, args$regexp))
    },

    "extract_citations" = {
      as.list(extract_citations(args$text))
    },

    "extract_wikihypelinks" = {
      as.list(extract_wikihypelinks(args$text))
    },

    "replace_wikihypelinks" = {
      list(cleaned_text = replace_wikihypelinks(args$text))
    },

    "extract_regex" = {
      date_an <- args$date_limit %||% "2024-01-01T00:00:00Z"
      df      <- get_article_most_recent_table(args$article_name, date_an = date_an)
      get_regex_citations_in_wiki_table(df, args$regexp)
    },

    "extract_all_regex" = {
      date_an <- args$date_limit %||% "2024-01-01T00:00:00Z"
      df      <- get_article_most_recent_table(args$article_name, date_an = date_an)
      result  <- extract_citations_regexp(df)
      # Convertir la liste en data frame combiné avec une colonne pattern_name
      do.call(rbind, lapply(names(result), function(nm) {
        d <- result[[nm]]
        if (nrow(d) > 0L) {
          d$pattern_name <- nm
          d
        }
      }))
    },

    "parse_citations" = {
      date_an <- args$date_limit %||% "2024-01-01T00:00:00Z"
      df      <- get_article_most_recent_table(args$article_name, date_an = date_an)
      get_paresd_citations(df)
    },

    "get_citation_types" = {
      date_an <- args$date_limit %||% "2024-01-01T00:00:00Z"
      df      <- get_article_most_recent_table(args$article_name, date_an = date_an)
      get_citation_type(df)
    },

    "get_source_type_counts" = {
      Get_source_type_counts(args$text)
    },

    "get_sci_score" = {
      date_an <- args$date_limit %||% "2024-01-01T00:00:00Z"
      df      <- get_article_most_recent_table(args$article_name, date_an = date_an)
      list(
        sci_score  = Get_sci_score(df$`*`),
        sci_score2 = Get_sci_score2(df$`*`),
        article    = args$article_name
      )
    },

    "get_top_cited_papers" = {
      date_an <- args$date_limit %||% "2024-01-01T00:00:00Z"
      df      <- get_article_most_recent_table(args$article_name, date_an = date_an)
      doi_df  <- get_regex_citations_in_wiki_table(df, pkg.env$doi_regexp)
      get_top_cited_wiki_papers(doi_df)
    },

    # ── Groupe 3 : Annotation DOIs / ISBN ─────────────────────────────────────

    "annotate_doi_europmc" = {
      annotate_doi_list_europmc(as.character(args$doi_list))
    },

    "annotate_doi_crossref" = {
      annotate_doi_list_cross_ref(as.character(args$doi_list))
    },

    "annotate_doi_altmetric" = {
      annotate_doi_list_altmetrics(list(as.character(args$doi_list)))
    },

    "annotate_doi_bibtex" = {
      bibs <- annotate_doi_to_bibtex_cross_ref(as.character(args$doi_list))
      list(bibtex_entries = as.list(bibs))
    },

    "annotate_isbn_google" = {
      annotate_isbn_google(args$isbn)
    },

    "annotate_isbn_openlib" = {
      annotate_isbn_openlib(args$isbn)
    },

    "annotate_isbn_altmetric" = {
      annotate_isbn_list_altmetrics(list(as.character(args$isbn_list)))
    },

    # ── Groupe 4 : Visualisations (PNG en base64) ─────────────────────────────

    "plot_article_creation" = {
      if (!requireNamespace("base64enc", quietly = TRUE)) {
        stop("Package 'base64enc' is required for plot tools. Install with: install.packages('base64enc')")
      }
      df  <- get_category_articles_creation(args$article_list)
      tmp <- tempfile(fileext = ".png")
      on.exit(unlink(tmp))
      grDevices::png(tmp, width = 900L, height = 500L, res = 96L)
      plot_article_creation_per_year(
        df,
        name_title = args$title %||% "Article creation over time",
        Cumsum     = as.logical(args$cumsum %||% TRUE)
      )
      grDevices::dev.off()
      list(
        image_base64 = base64enc::base64encode(tmp),
        format       = "png",
        description  = paste("Article creation timeline for",
                             length(args$article_list), "articles")
      )
    },

    "plot_static_timeline" = {
      if (!requireNamespace("base64enc", quietly = TRUE)) {
        stop("Package 'base64enc' is required for plot tools.")
      }
      df  <- get_category_articles_creation(args$article_list)
      tmp <- tempfile(fileext = ".png")
      on.exit(unlink(tmp))
      grDevices::png(tmp, width = 1200L, height = 400L, res = 96L)
      plot_static_timeline(df)
      grDevices::dev.off()
      list(
        image_base64 = base64enc::base64encode(tmp),
        format       = "png",
        description  = "Static article creation timeline"
      )
    },

    "plot_citation_distribution" = {
      if (!requireNamespace("base64enc", quietly = TRUE)) {
        stop("Package 'base64enc' is required for plot tools.")
      }
      date_an <- args$date_limit %||% "2024-01-01T00:00:00Z"
      df      <- get_category_articles_most_recent(args$article_list)
      ct      <- get_citation_type(df)
      tmp     <- tempfile(fileext = ".png")
      on.exit(unlink(tmp))
      grDevices::png(tmp, width = 800L, height = 500L, res = 96L)
      plot_distribution_source_type(ct)
      grDevices::dev.off()
      list(
        image_base64 = base64enc::base64encode(tmp),
        format       = "png",
        description  = "Citation source type distribution"
      )
    },

    "plot_page_edits" = {
      if (!requireNamespace("base64enc", quietly = TRUE)) {
        stop("Package 'base64enc' is required for plot tools.")
      }
      tmp <- tempfile(fileext = ".png")
      on.exit(unlink(tmp))
      grDevices::png(tmp, width = 900L, height = 400L, res = 96L)
      page_edit_plot(
        args$article_name,
        start = args$start %||% "2020010100",
        end   = args$end   %||% "2024010100"
      )
      grDevices::dev.off()
      list(
        image_base64 = base64enc::base64encode(tmp),
        format       = "png",
        description  = paste("Weekly edit history for", args$article_name)
      )
    },

    # ── Outil non reconnu ─────────────────────────────────────────────────────
    stop(paste0(
      "Unknown tool: '", tool, "'. ",
      "Check the list of available tools in server.py."
    ))
  )

}, error = function(e) {
  list(error = TRUE, message = conditionMessage(e))
})

# ── Sérialisation et sortie ───────────────────────────────────────────────────
cat(jsonlite::toJSON(
  result,
  auto_unbox = TRUE,
  na         = "null",
  null       = "null",
  dataframe  = "rows"
))
