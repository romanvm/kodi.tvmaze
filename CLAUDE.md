# CLAUDE.md

Kodi TV show metadata scraper (`metadata.tvmaze`) backed by the TVmaze API (https://www.tvmaze.com/api).
Published to the official Kodi `repo-scrapers` repository (current target branch: `omega`).

## Layout

The repo root is tooling only; the add-on itself lives in `metadata.tvmaze/` (that directory is what gets zipped
and submitted).

- `metadata.tvmaze/addon.xml` — manifest: version, dependencies, `<news>` changelog.
- `metadata.tvmaze/main.py` — entry point: initializes logging, calls `router(sys.argv[2][1:])` inside
  `catch_exception`.
- `metadata.tvmaze/libs/`
  - `actions.py` — Kodi scraper actions and `router()`. `HANDLE = int(sys.argv[1])` is read at import time.
  - `data_service.py` — business logic: search/year filtering, NFO parsing, show-ID resolution from
    episodeguide/URLs/external IDs, episode map building, artwork, episode order setting.
  - `tvmaze_api.py` — thin HTTP layer over the TVmaze API (uses `simple_requests`). HTTP errors are logged and
    turned into `None`/`[]`, never raised to callers.
  - `info_tag_property_setters.py` — declarative mapping of TVmaze JSON → `xbmc.InfoTagVideo` setters.
  - `cache_service.py` — two caches: show info as JSON files in `special://temp/scrapers/metadata.tvmaze/`
    (TTL governed by `cachepersistence` in `addon.xml`), and the episodes map in a Home window (10000) property
    with a 10-minute TTL (`MemoryCache`, holds only one show at a time).
  - `kodi_utils.py` — `ADDON`, `ADDON_ID`, `ADDON_VERSION`, `KODI_VERSION` (Decimal), `Settings` singleton,
    Kodi logging handler.
  - `exception_logger.py` — `catch_exception` context manager that dumps frames/locals to the Kodi log.
- `metadata.tvmaze/resources/settings.xml` + `resources/language/resource.language.en_gb/strings.po` — settings
  and their labels (string IDs `32000+`).

## Scraper flow

Kodi invokes `main.py` with `sys.argv = [plugin_url, handle, '?action=...&pathSettings=...']`.
`router()` dispatches on `action`:

| action              | handler                | result                                                          |
|---------------------|------------------------|-----------------------------------------------------------------|
| `find`              | `find_show`            | directory items, `url` = TVmaze show ID                          |
| `NfoUrl`            | `parse_nfo_file`       | one directory item with unique IDs (and episodeguide for shows) |
| `getdetails`        | `get_details`          | `setResolvedUrl` with full show info + artwork                  |
| `getepisodelist`    | `get_episode_list`     | directory items, `url` = quoted urlencoded show/episode IDs      |
| `getepisodedetails` | `get_episode_details`  | `setResolvedUrl` with full episode info                         |
| `getartwork`        | `get_artwork`          | legacy; apparently unused in Kodi 21+                            |

Key details:
- `episodeguide` is a JSON string of unique IDs (`{"tvmaze": "...", "tvdb": "...", "imdb": "..."}`). Legacy
  formats (plain numeric ID, or a URL) are still accepted with a warning.
- Per-source settings come in `pathSettings` and override add-on settings via `Settings().initialize()`.
  Always read settings through `Settings().get_value_*()`, never `ADDON.getSetting*` directly.
- Episode map keys are `f'{id}_{season}_{number}'` because alternate orders can repeat the same episode ID.
  Specials without a number are renumbered into season 0 by airdate.
- Episode order setting index → TVmaze alternate-list key via `EPISODE_ORDER_MAP`; falls back to the default
  list when no matching alternate list exists.
- `thetvdb` (TVmaze/URL naming) vs `tvdb` (Kodi uniqueid naming) — conversions happen in several places; keep
  them consistent.

## Adding/changing metadata fields

Add a tuple `(info_tag_method_name, SetterClass, tvmaze_json_key_or_None)` to the relevant list in
`info_tag_property_setters.py` (`BASIC_`/`FULL_` × `SHOW_`/`EPISODE_`). Use `SimpleInfoTagPropertySetter` when
the value maps 1:1; otherwise subclass it and override `should_set()` / `get_method_args()`.

Kodi API compatibility: the add-on targets Kodi 21 (Omega) and must keep working there. Gate newer APIs either
with `KODI_VERSION >= 22` (see `OriginalLanguageSetter`, `SeasonInfoSetter`) or with `hasattr`/`getattr`
feature checks (see `CastSetter`, `set_show_artwork`). Kodi Python API reference stubs: `Kodistubs`
(installed in `.venv`; source also at `/home/roman/Projects/Kodistubs`).

## Development

- Python: must stay compatible with Python 3.8 (the local `.venv` is 3.8). Use `typing.Optional/Dict/List`,
  not `X | None` or `list[...]`. Walrus operator is fine.
- No tests and no way to run the add-on outside Kodi; `xbmc*` modules only exist inside Kodi. Verify changes by
  linting and reasoning; real testing is done by the maintainer in Kodi.
- Dependencies (`requirements.txt`): `Kodistubs`, `ruff`, `simple-requests` (the add-on's only runtime dep,
  provided in Kodi by `script.module.simple-requests`; import as `import simple_requests as requests`).
- Commands (Makefile, use the `.venv`):
  - `make lint` — `ruff check`
  - `make format` — `ruff format`
  - `make ruff` — autofix + format
  Run `make ruff` (or at least `make lint`) after every code change.
- CI (`.github/workflows/check-addon.yml`): ruff + `kodi-addon-checker --branch omega` on every push/PR.
  Pushing a tag (not ending in `-beta`) triggers `publish-addon.yml`, which submits to `repo-scrapers`.

## Code style

- Ruff config in `ruff.toml`: line length 100, single quotes (double for docstrings/multiline), isort with
  case-insensitive plain alphabetical ordering, flake8-logging rules.
- Logging via the stdlib `logging` root logger (`logging.debug(...)` etc.) with `%s`-style lazy args, not
  f-strings. Do not call `xbmc.log` directly outside `kodi_utils`/`exception_logger`.
- Every source file starts with the GPL-3.0 license header; new files use the current year.
- Type hints on function signatures; `InfoType = Dict[str, Any]` for TVmaze JSON dicts.
- Any user-visible string goes into `strings.po` with a new `32xxx` ID.

## Releases

1. Bump `version` in `metadata.tvmaze/addon.xml` and replace the `<news>` section with the new changes.
2. Tag and push (existing tags look like `1.4.0-4`; any tag except `*-beta` triggers publishing).
Never commit, tag or push without explicit confirmation from the maintainer.
