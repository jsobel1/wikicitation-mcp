# WikiCitationHistoRy MCP Server

Serveur MCP qui expose le package R
[WikiCitationHistoRy](https://github.com/jsobel1/WikiCitationHistoRy)
comme outils utilisables depuis **Claude Code**, **Claude Desktop** et
**claude.ai**.

---

## Prérequis

| Outil | Version minimale |
|---|---|
| Python | 3.10 |
| R | 4.0 |
| uv | dernière version |
| WikiCitationHistoRy | installé dans R |

```bash
# Installer uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Vérifier que le package R est installé
Rscript -e "library(WikiCitationHistoRy); cat('OK\n')"

# Si non installé :
Rscript -e "devtools::install_github('jsobel1/WikiCitationHistoRy')"

# Pour les visualisations, installer aussi base64enc :
Rscript -e "install.packages('base64enc')"
```

---

## Installation

```bash
# Cloner / copier le dossier wikicitation-mcp
cd wikicitation-mcp

# Installer les dépendances Python
uv sync

# Tester le bridge R directement
echo '{"tool":"get_doi_count","args":{"text":"see 10.1038/nature12373"}}' \
  | Rscript mcp_interface.R
# → {"count":1}
```

---

## Connexion à Claude Code

```bash
# Depuis le dossier wikicitation-mcp/ :
claude mcp add wikicitation -- uv run python server.py

# Vérifier
claude mcp list
# wikicitation    stdio    uv run python server.py

# Tester l'inspecteur visuel
uv run fastmcp dev server.py
# → ouvre http://localhost:5173
```

---

## Connexion à Claude Desktop

Editez `~/.claude/claude_desktop_config.json`
(Windows : `%APPDATA%\Claude\claude_desktop_config.json`) :

```json
{
  "mcpServers": {
    "wikicitation": {
      "command": "uv",
      "args": ["run", "python", "/CHEMIN/VERS/wikicitation-mcp/server.py"],
      "env": {
        "R_HOME": "/usr/lib/R"
      }
    }
  }
}
```

Redémarrez Claude Desktop. Le serveur `wikicitation` apparaît dans
la barre d'outils.

> **Trouver votre R_HOME :**
> ```bash
> Rscript -e "R.home()"
> ```

---

## Connexion à claude.ai (mode HTTP)

```bash
# Lancer le serveur HTTP
uv run fastmcp run server.py --transport streamable-http --port 8000

# Dans claude.ai → Settings → Connections → Add MCP server
# URL : http://localhost:8000/mcp
```

Pour un accès distant, utilisez un tunnel :
```bash
# Avec ngrok
ngrok http 8000
# URL publique : https://xxx.ngrok.io/mcp
```

---

## Outils disponibles (30 outils)

### Groupe 1 — Historique Wikipedia
| Outil | Description |
|---|---|
| `get_article_history` | Historique complet d'un article (sans wikitext) |
| `get_article_recent` | Révision la plus récente + wikitext |
| `get_article_initial` | Première révision (création) + wikitext |
| `get_article_info` | Métadonnées courantes (pageid, titre, taille) |
| `get_category_pages` | Liste des pages d'une catégorie |
| `get_category_history` | Historique de plusieurs articles |
| `get_category_recent` | Révision récente de plusieurs articles |
| `get_category_creation` | Révision de création de plusieurs articles |
| `get_subcat_table` | Sous-catégories directes d'une catégorie |
| `get_subcat_with_depth` | Sous-catégories récursives jusqu'à une profondeur |

### Groupe 2 — Extraction et comptage
| Outil | Description |
|---|---|
| `get_doi_count` | Nombre de DOIs dans un texte |
| `get_ref_count` | Nombre de balises `<ref>` |
| `get_url_count` | Nombre d'URLs |
| `get_isbn_count` | Nombre d'ISBNs |
| `get_hyperlink_count` | Nombre de liens `[[...]]` |
| `get_any_count` | Comptage par expression régulière personnalisée |
| `extract_citations` | Extraction des templates CS1 |
| `extract_wikihypelinks` | Extraction des hyperliens Wikipedia |
| `replace_wikihypelinks` | Nettoyage du wikitext (supprime la syntaxe `[[]]`) |
| `extract_with_regex` | Extraction par regexp sur un article |
| `extract_all_regex` | Application de tous les regexps intégrés |
| `parse_citations` | Parsing structuré de toutes les citations CS1 |
| `get_citation_types` | Comptage par type de citation |
| `get_source_type_counts` | Comptage direct depuis un texte |
| `get_sci_score` | SciScore et SciScore2 d'un article |
| `get_top_cited_papers` | Top 40 DOIs les plus cités dans un article |

### Groupe 3 — Annotation
| Outil | Description |
|---|---|
| `annotate_dois_europmc` | Annotation via EuropePMC |
| `annotate_dois_crossref` | Annotation via CrossRef |
| `annotate_dois_altmetric` | Scores Altmetric |
| `annotate_dois_bibtex` | Export BibTeX via CrossRef |
| `annotate_isbn_google` | Métadonnées livre via Google Books |
| `annotate_isbn_openlib` | Métadonnées livre via Open Library |
| `annotate_isbns_altmetric` | Scores Altmetric pour ISBNs |

### Groupe 4 — Visualisations
| Outil | Description | Retour |
|---|---|---|
| `plot_article_creation` | Timeline de création d'articles | PNG base64 |
| `plot_static_timeline` | Timeline statique labellisée | PNG base64 |
| `plot_citation_distribution` | Distribution des types de citation | PNG base64 |
| `plot_page_edits` | Historique hebdomadaire des éditions | PNG base64 |

---

## Exemples d'utilisation dans Claude

Une fois connecté, tu peux dire à Claude :

```
"Donne-moi l'historique de l'article Zeitgeber depuis 2020"

"Compte les DOIs dans ce wikitext : [colle le texte]"

"Calcule le SciScore de l'article 'Sleep deprivation'"

"Annote ces DOIs avec EuropePMC : 10.1038/nature12373, 10.1016/j.cell.2020.01.001"

"Génère une timeline de création pour les articles :
 Zeitgeber, Advanced sleep phase disorder, Sleep deprivation"

"Extrait toutes les citations de l'article 'Circadian clock' et
 dis-moi combien sont des articles de journal vs des sites web"
```

---

## Lancer les tests

```bash
# Tests unitaires (sans réseau, sans R)
uv run pytest tests/ -m "not integration" -v

# Tests d'intégration (nécessitent R + WikiCitationHistoRy + internet)
uv run pytest tests/ -m integration -v

# Tous les tests
uv run pytest tests/ -v
```

---

## Dépannage

**`Rscript introuvable`**
```bash
# macOS avec Homebrew
export PATH="/opt/homebrew/bin:$PATH"
# Linux
export PATH="/usr/bin:$PATH"
```

**`WikiCitationHistoRy introuvable dans R`**
```r
install.packages("devtools")
devtools::install_github("jsobel1/WikiCitationHistoRy")
```

**Timeout sur les gros historiques**
Augmentez `DEFAULT_TIMEOUT` dans `r_bridge.py` (défaut : 120s).

**Le serveur ne s'affiche pas dans Claude Code**
```bash
claude mcp list          # vérifier l'enregistrement
claude mcp remove wikicitation
claude mcp add wikicitation -- uv run python server.py
```
