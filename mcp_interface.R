#!/usr/bin/env Rscript
# mcp_interface.R
# Bridge between the MCP Python server and the wikilite R package.
# Usage: echo '<JSON>' | Rscript mcp_interface.R
#
# Protocol:
#   stdin  -> {"tool": "<name>", "args": {...}}
#   stdout -> JSON result (or {"error": true, "message": "..."})

suppressPackageStartupMessages({
  library(wikilite)
  library(jsonlite)
})

# -- Null-coalescing operator --------------------------------------------------
`%||%` <- function(x, y) if (!is.null(x)) x else y

# -- Read stdin ----------------------------------------------------------------
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

# -- Helper: save htmlwidget to self-contained HTML and return as string -------
.widget_to_html <- function(widget, description = "Interactive visualisation") {
  if (!requireNamespace("htmlwidgets", quietly = TRUE)) {
    stop("Package 'htmlwidgets' is required for interactive plot tools.")
  }
  tmp <- tempfile(fileext = ".html")
  on.exit(unlink(tmp), add = TRUE)
  htmlwidgets::saveWidget(widget, tmp, selfcontained = TRUE)
  html <- paste(readLines(tmp, warn = FALSE), collapse = "\n")
  list(html = html, format = "html", description = description)
}

# -- Helper: save ggplot/base plot to base64 PNG ------------------------------
.plot_to_png <- function(expr, width = 900L, height = 500L, res = 96L,
                          description = "Plot") {
  if (!requireNamespace("base64enc", quietly = TRUE)) {
    stop("Package 'base64enc' is required for static plot tools.")
  }
  tmp <- tempfile(fileext = ".png")
  on.exit(unlink(tmp), add = TRUE)
  grDevices::png(tmp, width = width, height = height, res = res)
  force(expr)
  grDevices::dev.off()
  list(
    image_base64 = base64enc::base64encode(tmp),
    format       = "png",
    description  = description
  )
}

# -- Dispatch -----------------------------------------------------------------
result <- tryCatch({

  switch(tool,

    # =========================================================================
    # GROUP 1 -- Wikipedia history & metadata
    # =========================================================================

    "get_article_history" = {
      date_an <- args$date_limit %||% "2024-01-01T00:00:00Z"
      df <- get_article_full_history_table(args$article_name, date_an = date_an)
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

    "get_tables_all" = {
      # Returns initial + most-recent + full history + info in one call
      res <- get_tables_initial_most_recent_full_info(
        args$article_name,
        date_an = args$date_limit %||% "2024-01-01T00:00:00Z"
      )
      # Strip wikitext from all data frames to keep response manageable
      lapply(res, function(x) {
        if (is.data.frame(x)) x[, setdiff(names(x), "*"), drop = FALSE]
        else x
      })
    },

    "get_category_pages" = {
      as.character(get_pagename_in_cat(args$category))
    },

    "get_pages_in_cat_table" = {
      get_pages_in_cat_table(args$category)
    },

    "get_subcat_table" = {
      get_subcat_table(args$catname, replecement = args$replecement %||% "_")
    },

    "get_subcat_multiple" = {
      # article_list is a character vector of category names
      get_subcat_multiple(args$catname_list)
    },

    "get_subcat_with_depth" = {
      get_subcat_with_depth(
        args$catname,
        depth       = as.integer(args$depth %||% 1L),
        replecement = args$replecement %||% "_"
      )
    },

    "get_page_in_cat_multiple" = {
      get_page_in_cat_multiple(args$catname_list)
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

    # =========================================================================
    # GROUP 2 -- Citation counting, extraction & quality metrics
    # =========================================================================

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

    "parse_cite_type" = {
      # Parse a single CS1 template string into a tidy data frame
      list(result = as.list(parse_cite_type(args$text)))
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
      do.call(rbind, lapply(names(result), function(nm) {
        d <- result[[nm]]
        if (!is.null(d) && nrow(d) > 0L) { d$pattern_name <- nm; d }
      }))
    },

    "parse_citations" = {
      date_an <- args$date_limit %||% "2024-01-01T00:00:00Z"
      df      <- get_article_most_recent_table(args$article_name, date_an = date_an)
      get_parsed_citations(df)
    },

    "parse_all_citations" = {
      # Full structured parse of all CS1 templates into a long tidy table
      date_an <- args$date_limit %||% "2024-01-01T00:00:00Z"
      df      <- get_article_most_recent_table(args$article_name, date_an = date_an)
      parse_article_ALL_citations(df)
    },

    "get_citation_types" = {
      date_an <- args$date_limit %||% "2024-01-01T00:00:00Z"
      df      <- get_article_most_recent_table(args$article_name, date_an = date_an)
      get_citation_type(df)
    },

    "get_source_type_counts" = {
      get_source_type_counts(args$text)
    },

    "get_sci_score" = {
      date_an <- args$date_limit %||% "2024-01-01T00:00:00Z"
      df      <- get_article_most_recent_table(args$article_name, date_an = date_an)
      list(
        sci_score  = get_sci_score(df$`*`),
        sci_score2 = get_sci_score2(df$`*`),
        article    = args$article_name
      )
    },

    "get_top_cited_papers" = {
      date_an <- args$date_limit %||% "2024-01-01T00:00:00Z"
      df      <- get_article_most_recent_table(args$article_name, date_an = date_an)
      doi_df  <- get_regex_citations_in_wiki_table(df, pkg.env$doi_regexp)
      get_top_cited_wiki_papers(doi_df)
    },

    "get_revert_counts" = {
      get_revert_counts(
        start = args$start %||% "2024-01-01",
        end   = args$end   %||% "2024-12-31"
      )
    },

    # =========================================================================
    # GROUP 3 -- DOI & ISBN annotation
    # =========================================================================

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

    # =========================================================================
    # GROUP 4 -- Static visualisations (base64 PNG)
    # =========================================================================

    "plot_article_creation" = {
      df <- get_category_articles_creation(args$article_list)
      .plot_to_png(
        plot_article_creation_per_year(
          df,
          name_title = args$title %||% "Article creation over time",
          Cumsum     = as.logical(args$cumsum %||% TRUE)
        ),
        width = 900L, height = 500L,
        description = paste("Article creation timeline for",
                            length(args$article_list), "articles")
      )
    },

    "plot_static_timeline" = {
      df <- get_category_articles_creation(args$article_list)
      .plot_to_png(
        plot_static_timeline(df),
        width = 1200L, height = 400L,
        description = "Static article creation timeline"
      )
    },

    "plot_citation_distribution" = {
      df  <- get_category_articles_most_recent(args$article_list)
      ct  <- get_citation_type(df)
      .plot_to_png(
        plot_distribution_source_type(ct),
        width = 800L, height = 500L,
        description = "Citation source type distribution"
      )
    },

    "plot_top_source" = {
      date_an     <- args$date_limit %||% "2024-01-01T00:00:00Z"
      df          <- get_article_most_recent_table(args$article_name, date_an = date_an)
      cite_parsed <- get_parsed_citations(df)
      source_type <- args$source_type %||% "publisher"
      .plot_to_png(
        plot_top_source(cite_parsed, source_type),
        width = 800L, height = 600L,
        description = paste("Top 20", source_type, "for", args$article_name)
      )
    },

    "plot_page_views" = {
      .plot_to_png(
        page_view_plot(
          args$article_name,
          start = args$start %||% "2020010100",
          end   = args$end   %||% "2024010100"
        ),
        width = 900L, height = 400L,
        description = paste("Daily page views for", args$article_name)
      )
    },

    "plot_page_edits" = {
      .plot_to_png(
        page_edit_plot(
          args$article_name,
          start = args$start %||% "2020010100",
          end   = args$end   %||% "2024010100"
        ),
        width = 900L, height = 400L,
        description = paste("Weekly edit history for", args$article_name)
      )
    },

    # =========================================================================
    # GROUP 5 -- Interactive visualisations (self-contained HTML)
    # =========================================================================

    "plot_interactive_timeline" = {
      widget <- plot_interactive_timeline(
        articles = as.character(args$article_list),
        date_an  = args$date_limit %||% "2024-01-01T00:00:00Z",
        color_by = args$color_by %||% "sciscore"
      )
      .widget_to_html(widget, paste(
        "Interactive timeline for", length(args$article_list), "articles"
      ))
    },

    "plot_publication_network" = {
      widget <- plot_article_publication_network(
        articles       = as.character(args$article_list),
        date_an        = args$date_limit %||% "2024-01-01T00:00:00Z",
        top_n_dois     = as.integer(args$top_n_dois %||% 50L),
        min_wiki_count = as.integer(args$min_wiki_count %||% 2L),
        annotate       = as.logical(args$annotate %||% FALSE)
      )
      .widget_to_html(widget, paste(
        "Article-publication network for", length(args$article_list), "articles"
      ))
    },

    "plot_cocitation_network" = {
      widget <- plot_article_cocitation_network(
        articles        = as.character(args$article_list),
        date_an         = args$date_limit %||% "2024-01-01T00:00:00Z",
        min_shared_dois = as.integer(args$min_shared_dois %||% 1L)
      )
      if (is.null(widget)) {
        list(html = NULL, message = "No article pairs share enough DOIs.")
      } else {
        .widget_to_html(widget, paste(
          "Co-citation network for", length(args$article_list), "articles"
        ))
      }
    },

    "plot_wikilink_network" = {
      widget <- plot_article_wikilink_network(
        articles      = as.character(args$article_list),
        date_an       = args$date_limit %||% "2024-01-01T00:00:00Z",
        only_internal = as.logical(args$only_internal %||% TRUE),
        top_n_links   = as.integer(args$top_n_links %||% 80L)
      )
      if (is.null(widget)) {
        list(html = NULL, message = "No qualifying wikilinks found.")
      } else {
        .widget_to_html(widget, paste(
          "Wikilink network for", length(args$article_list), "articles"
        ))
      }
    },

    # -- Unknown tool ----------------------------------------------------------
    stop(paste0(
      "Unknown tool: '", tool, "'. ",
      "Check the list of available tools in server.py."
    ))
  )

}, error = function(e) {
  list(error = TRUE, message = conditionMessage(e))
})

# -- Serialise and write to stdout --------------------------------------------
cat(jsonlite::toJSON(
  result,
  auto_unbox = TRUE,
  na         = "null",
  null       = "null",
  dataframe  = "rows"
))
