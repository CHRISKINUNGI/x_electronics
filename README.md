# X Electronics

Warehouse Management System For X Electronics

This application was developed as a technical assessment for **Navari Limited**. It implements a robust inventory tracking system with hierarchical location management, automated financial valuation, and full test coverage.

### DocTypes

| DocType | Description |
|---|---|
| **Item** | Product master — stores `item_code`, `item_name`, `unit_of_measure`, and a running `valuation_rate` updated on each stock movement. |
| **Warehouse** | Nested-Set tree structure supporting Group (organisational node) and Leaf (physical location) warehouses. |
| **Stock Ledger Entry** | Stateless, immutable ledger row — records every stock movement (quantity, rate, warehouse, date) and computes a per-row running `balance_qty` and moving-average `valuation_rate` on submit. |
| **Stock Entry** | User-facing transaction document (Receipt / Consume / Transfer) that creates the corresponding `Stock Ledger Entry` rows on submit. |

### Key Features

**1. Hierarchical Warehouse Management**
`Warehouse` is implemented as a Frappe Nested-Set (tree) DocType:
* **Group Warehouses** — organisational nodes (e.g., "All Warehouses").
* **Leaf Warehouses** — physical locations where transactions occur (e.g., "Nairobi Store").
* **Tree-aware reports** — both reports accept a group warehouse filter and automatically include all descendant warehouses using `lft`/`rgt` bounds.

**2. Stateless Moving Average Valuation**
Valuation is derived entirely from the ledger on each submit — no persistent running total is maintained outside the rows themselves:
* Each `Stock Ledger Entry` computes `valuation_rate` and `balance_qty` via a single aggregate SQL query against already-submitted rows for the same item/warehouse.
* Row-level `FOR UPDATE` locks on the `Item` and the affected SLE rows prevent concurrent valuations from producing inconsistent results.
* The `valuation_rate` on the **Item** master is updated immediately after each commit.

**3. Business-Rule Validation & Security**
Input is validated before any ledger rows are written:
* Quantity must be > 0; rate cannot be negative.
* Required warehouse fields are enforced per entry type.
* Source and target warehouse cannot be identical on a Transfer.
* Consume and Transfer are rejected when available stock is insufficient (no negative stock).

**4. Reports**

| Report | Description |
|---|---|
| **Stock Ledger** | Line-by-line movement log per item/warehouse. Supports `from_date`, `to_date`, and `warehouse` (tree-aware) filters. Shows running `balance_qty` and `valuation_rate` per row. |
| **Stock Balance** | Aggregated balance snapshot. Supports `to_date` and `warehouse` (tree-aware) filters. Shows Balance Qty, Valuation Rate, and Total Stock Value per item+warehouse pair. |

**5. Test Coverage**

All non-report functionality is covered by unit tests. Reports also have data-backed unit tests:

| Test class | What it covers |
|---|---|
| `TestItem` | Item creation and field validation |
| `TestWarehouse` | Tree parent-child relationship |
| `TestStockEntry` | Receipt / Consume / Transfer ledger creation; underflow rejection; invalid quantity rejection |
| `TestStockLedgerEntry` | Moving-average calculation; running balance; negative-stock rejection |
| `TestStockBalanceReport` | Column schema; computed balance qty, valuation rate, and total value |
| `TestStockLedgerReport` | Column schema; correct movement rows returned |

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app [https://github.com/CHRISKINUNGI/x_electronics.git](https://github.com/CHRISKINUNGI/x_electronics.git) --branch main
bench install-app x_electronics
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/x_electronics
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.

### License

MIT