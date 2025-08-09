# Persistence & Data Layer Modernization Plan

Status date: 2025-08-09 (branch: chore/clean_code)

## 1. Objectives

- Decouple scraping / presentation layers from raw SQLite details.
- Replace monolithic `database.manager` with layered approach:
  - `scraper.persistence.sqlite` (low-level DB operations)
  - `scraper.persistence.repositories` (intention-revealing API)
  - Higher layers (catalog loader, scrapers, HTML) depend on repositories or manager during transition.
- Provide backward compatible shim (`database.__init__`) while migrating.
- Enable future: alternative backends, richer tests, clearer domain boundaries.

## 2. Completed Work ✅

| Task | Details | Commit(s) |
|------|---------|-----------|
| Create `scraper/persistence` package | Added `sqlite.py` with migrated `DatabaseManager` | refactor(persistence): swap imports ... |
| Port product/url/price/cache logic | Copied & trimmed from legacy manager | same |
| Port issue logging + lookup | `log_product_issue`, `get_product_by_url` migrated | refactor(persistence): port issue logging ... |
| Remove legacy `database/manager.py` | File deleted; shim retains API | refactor(persistence): port issue logging ... |
| Add repositories layer | Thin wrappers (`record_price`, `unresolved_issues`, etc.) | refactor(persistence): swap imports ... |
| Update imports (main, generate_html) | Now pull `DatabaseManager` from persistence | same |
| Lazy shim to prevent circular import | `database/__getattr__` returns `DatabaseManager` lazily | refactor(persistence): add lazy shim ... |
| Index coverage verification | All key indexes already defined in `CREATE_TABLES_SQL` | existing |

## 3. Current Architecture (Layered)

```text
products.json --> scraper.catalog.loader  --> repositories (preferred) --> persistence.sqlite.DatabaseManager --> SQLite
scraper.py / sites/*.py --------------(still direct)--> persistence.sqlite.DatabaseManager
HTML generation ----------------------(direct)-------> persistence.sqlite.DatabaseManager
```

Transition zone: some modules still call `DatabaseManager` directly; safe but tightly coupled.

## 4. Technical Debt & Gaps

- Repositories not yet adopted by `scraper.py`, `sites/idealo.py`, `sites/*` (still direct DB access & issue logging).
- No automated tests for persistence or repositories.
- Shim access has no deprecation warning (silent usage could persist indefinitely).
- Architecture docs (README, ARCHITECTURE) not updated with new layering diagram.
- Mixed return types: issues returned as list[dict] (could use dataclass later).

## 5. Pending Tasks (Ranked)

1. Add one-time deprecation warning when `database.DatabaseManager` accessed (guides migration).
2. Introduce minimal tests for repositories (price record, issue log, cache behavior).
3. Migrate high-level modules (`scraper.py`, `sites/idealo.py`) to repositories helpers where feasible.
4. Update documentation: ARCHITECTURE.md, PROJECT_STATUS.md to reference persistence layering & repositories.
5. Add convenience repository functions for: `product_by_url`, `log_issue` (already done), `products_needing_scrape`.
6. Replace remaining direct cache calls with repository wrappers (optional now).
7. Plan removal timeline: mark shim for removal after N releases (comment & warning).
8. Optional: define Protocol / ABC for a future multi-backend manager.
9. Optional: dataclass for ProductIssue to standardize shape.

## 6. Test Plan (Upcoming)

Minimal test cases to add first:

- test_record_price_round_trip: ensure row inserted; history reflects entry count increment.
- test_log_issue_and_auto_handle: create product, log 404 issue, run auto handler, assert product removed.
- test_cache_backoff: simulate two failed updates and verify next_retry increases.

## 7. Deprecation Strategy

- Phase A (current): Lazy shim, no warning.
- Phase B: Emit one-time `logging.warning` on first attribute access (planned next step).
- Phase C: Update docs directing imports away from `database`.
- Phase D: Remove shim & raise ImportError (future major version / explicit branch).

## 8. Rollback Plan

If regression surfaces (e.g., import errors), revert commits touching shim or temporarily reintroduce `database/manager.py` (copy from prior commit hash) while diagnosing.

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Silent continued use of shim | Architectural drift | Add warning & doc updates |
| Missing tests allow regression | Data integrity issues | Add minimal repository tests early |
| Future multi-backend adds complexity | Slows iteration | Introduce Protocol only when second backend is scheduled |

## 10. Immediate Next Actions (Executing Now)

1. Add one-time deprecation warning in shim.
2. Add repository wrapper for `get_products_needing_scrape`.
3. Refactor `scraper.py` & `sites/idealo.py` to use repository wrappers where low-risk.
4. Stage & commit.

(Tests & docs will follow in subsequent step unless requested sooner.)

---
Generated & maintained automatically; update as tasks complete.
