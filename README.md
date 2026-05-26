# X Electronics - Warehouse Management System

A Frappe Framework application that implements a complete warehouse management system for X Electronics with hierarchical warehouse management, FIFO queue valuation, and full test coverage.

Built as a technical assessment for **Navari Limited**.

## Screenshots

### Workspace
![Landing Screen](screenshots/Landing%20Screen.png)

### Item
| List View | Add Item |
|---|---|
| ![Item List](screenshots/Items%20List%20Screen.png) | ![Add Item](screenshots/Add%20Item%20Screen.png) |

### Warehouse
| List View | New Warehouse |
|---|---|
| ![Warehouse List](screenshots/Warehouse%20List%20Screen.png) | ![New Warehouse](screenshots/New%20Warehouse%20Screen.png) |

### Stock Entry
| List View | New Stock Entry |
|---|---|
| ![Stock Entry List](screenshots/Stock%20Entry%20List%20Screen.png) | ![New Stock Entry](screenshots/New%20Stock%20Entry%20Screen.png) |

### Reports
| Stock Balance | Stock Ledger |
|---|---|
| ![Stock Balance](screenshots/Stock%20Balance%20Report%20Screen.png) | ![Stock Ledger](screenshots/Stock%20Ledger%20Report%20Screen.png) |

## DocTypes

| DocType | Description |
|---|---|
| **Item** | Product master with `item_code`, `item_name`, `unit_of_measure`, and an auto-computed `valuation_rate`. |
| **Warehouse** | Nested-Set tree DocType supporting Group (organisational) and Leaf (physical) warehouses. |
| **Stock Entry** | User-facing transaction document — Receipt, Consume, or Transfer — that creates Stock Ledger Entry rows on submit. |
| **Stock Entry Detail** | Child table for Stock Entry line items (item, quantity, rate, warehouses). |
| **Stock Ledger Entry** | Immutable ledger row recording every stock movement with computed `balance_qty`, FIFO `outgoing_rate`, and `valuation_rate`. |

## Key Features

### 1. Hierarchical Warehouse Management

`Warehouse` uses Frappe's Nested-Set tree structure:

- **Group Warehouses** — organisational nodes (e.g., "All Warehouses", "Nairobi Warehouse")
- **Leaf Warehouses** — physical locations where stock is held (e.g., "Nairobi - Main Store")
- **Tree-aware reports** — selecting a group warehouse automatically includes all descendants using `lft`/`rgt` bounds

### 2. FIFO Queue Valuation

Each `Stock Ledger Entry` carries the full FIFO queue state as a JSON snapshot — no full-history replay on every submit:

- **Receipts** append a new `[qty, rate]` batch to the back of the queue
- **Consumes** drain batches from the front; `outgoing_rate` is the weighted average cost of exactly the batches consumed
- **Backdated entries** trigger a chronological repost of all subsequent entries so the queue stays consistent
- **Cancellations** repost subsequent entries then reset `Item.valuation_rate` to the latest surviving entry
- **Concurrent safety** — `SELECT ... FOR UPDATE` row locks prevent two simultaneous submits from reading stale queue state
- `valuation_rate` = cost of stock still in the queue, not a historical blend

**Example:**
| Action | Queue | Balance Qty | Outgoing Rate | Valuation Rate |
|---|---|---|---|---|
| Receive 10 @ 800 | `[(10, 800)]` | 10 | — | 800.00 |
| Receive 5 @ 1,000 | `[(10, 800), (5, 1000)]` | 15 | — | 866.67 |
| Consume 12 | `[(3, 1000)]` | 3 | 833.33 | 1,000.00 |

### 3. Three Transaction Types

| Type | Source Warehouse | Target Warehouse | Effect |
|---|---|---|---|
| **Receipt** | Not applicable | Required | +qty into target |
| **Consume** | Required | Not applicable | -qty from source |
| **Transfer** | Required | Required | -qty from source, +qty into target |

The form dynamically shows/hides warehouse columns based on the selected type.

### 4. Business-Rule Validation

- Quantity must be greater than zero
- Rate cannot be negative
- Source and target warehouse cannot be the same (Transfer)
- Negative stock is prevented — Consume/Transfer rejected when insufficient stock
- Warehouse selection is restricted to leaf warehouses only

### 5. Cancellation Support

Stock Entries can be cancelled, which automatically cancels all linked Stock Ledger Entries. Each SLE stores a `voucher_no` reference back to the originating Stock Entry for traceability.

### 6. Reports

| Report | Description |
|---|---|
| **Stock Balance** | Aggregated balance snapshot per item/warehouse. Filters: `to_date`, `item`, `warehouse` (tree-aware). Shows Balance Qty, Valuation Rate, and Total Value with a totals row. |
| **Stock Ledger** | Line-by-line movement log. Filters: `from_date`, `to_date`, `item`, `warehouse` (tree-aware). Shows `Outgoing Rate` on consume rows as proof of FIFO costing. Positive quantities shown in green, negative in red. |

Both reports use shared utilities from `utils.py` — `build_stock_conditions()` for common SQL filter logic and `get_warehouse_filter()` for tree-aware warehouse expansion.

### 7. Smart UX

- **Dynamic form** — Stock Entry shows only relevant warehouse columns per entry type
- **Auto-fetch rate** — selecting an item auto-populates the basic rate from the item's current valuation
- **Calculated fields** — amount (qty x rate), total quantity, and total amount computed automatically
- **Color-coded list view** — Receipt (green), Consume (red), Transfer (blue)
- **Report buttons** — Item and Warehouse forms have buttons to jump to filtered reports
- **Workspace** — central landing page with shortcuts, cards, and sidebar navigation
- **Drill-down** — clicking a row in Stock Balance navigates to the Stock Ledger filtered for that item/warehouse

## Test Coverage

All non-report functionality is covered by unit tests. Reports also have data-backed tests.

```
$ bench --site mysite.localhost run-tests --app x_electronics

 ✔ test_item_creation
 ✔ test_warehouse_tree
 ✔ test_receipt_creates_ledger_entry
 ✔ test_consume_creates_negative_ledger_entry
 ✔ test_transfer_creates_two_ledger_entries
 ✔ test_consume_without_available_stock_is_blocked
 ✔ test_non_positive_quantity_is_blocked
 ✔ test_cancel_reverses_ledger_entries
 ✔ test_full_receipt_consume_transfer_flow
 ✔ test_fifo_valuation_and_balance
 ✔ test_fifo_cross_batch_consume
 ✔ test_backdated_entry_recalculates_subsequent
 ✔ test_cancel_recalculates_subsequent
 ✔ test_direct_negative_stock_submission_is_blocked
 ✔ test_report_returns_movement_rows
 ✔ test_date_range_filter
 ✔ test_report_calculation
 ✔ test_warehouse_hierarchy_filter

Ran 18 tests in 1.0s — OK
```

| Test Class | What It Covers |
|---|---|
| `TestItem` | Item creation and field validation |
| `TestWarehouse` | Tree parent-child relationship |
| `TestStockEntry` | Receipt / Consume / Transfer ledger creation; cancellation reversal; underflow rejection; invalid quantity rejection; end-to-end flow |
| `TestStockLedgerEntry` | FIFO single-batch and cross-batch valuation; backdated entry repost; cancellation repost; negative-stock rejection |
| `TestStockBalanceReport` | Computed balance qty, valuation rate, total value; warehouse hierarchy filter |
| `TestStockLedgerReport` | Movement rows returned; date range filter |

## Project Structure

```
x_electronics/
├── x_electronics/
│   ├── doctype/
│   │   ├── item/                    # Product master
│   │   ├── warehouse/               # Tree DocType (NestedSet)
│   │   ├── stock_entry/             # Transaction document
│   │   ├── stock_entry_detail/      # Child table
│   │   └── stock_ledger_entry/      # Immutable ledger
│   ├── report/
│   │   ├── stock_balance/           # Aggregated balance report
│   │   └── stock_ledger/            # Movement history report
│   ├── workspace/
│   │   └── x_electronics/           # App workspace
│   └── utils.py                     # Shared utilities
├── hooks.py
└── modules.txt
```

## Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/CHRISKINUNGI/x_electronics.git --branch main
bench --site your-site.localhost install-app x_electronics
bench --site your-site.localhost migrate
```

## Development

This app uses `pre-commit` for code formatting and linting:

```bash
cd apps/x_electronics
pre-commit install
```

Tools configured: **ruff**, **eslint**, **prettier**, **pyupgrade**

## License

MIT
