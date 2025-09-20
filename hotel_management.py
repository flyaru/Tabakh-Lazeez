"""Command-line hotel management tool for Tabakh Lazeez."""

from __future__ import annotations

import datetime as dt
import sqlite3
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence

import click

DB_PATH = Path("hotel.db")
DATE_FORMAT = "%Y-%m-%d"


@click.group(help="Tabakh Lazeez hotel management toolkit")
def cli() -> None:
    """Base command group."""


def echo(message: str, color: Optional[str] = None) -> None:
    click.secho(message, fg=color)


def handle_db_errors(func: Callable) -> Callable:
    """Decorator to surface initialization guidance for missing tables."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.OperationalError as exc:
            if "no such table" in str(exc).lower():
                echo(
                    "Database schema not found. Run `python hotel_management.py init-db` first.",
                    color="red",
                )
                return None
            raise

    wrapper.__click_params__ = getattr(func, "__click_params__", [])  # type: ignore[attr-defined]
    wrapper.__click_attrs__ = getattr(func, "__click_attrs__", {})  # type: ignore[attr-defined]
    return wrapper


def render_table(headers: Sequence[str], rows: Iterable[Sequence[str]], title: Optional[str] = None) -> None:
    rows_list = [tuple(str(value) for value in row) for row in rows]
    if not rows_list:
        echo("No data to display.", color="yellow")
        return

    widths = [len(header) for header in headers]
    for row in rows_list:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def format_row(values: Sequence[str]) -> str:
        return " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(values))

    if title:
        echo(title)
        echo("-" * len(title))

    echo(format_row(headers))
    echo("-" * (sum(widths) + 3 * (len(headers) - 1)))
    for row in rows_list:
        echo(format_row(row))


@contextmanager
def get_connection(db_path: Path = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS guests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_number TEXT UNIQUE NOT NULL,
        room_type TEXT NOT NULL,
        rate REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'available'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guest_id INTEGER NOT NULL,
        room_id INTEGER NOT NULL,
        check_in TEXT NOT NULL,
        check_out TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'upcoming',
        nights INTEGER NOT NULL,
        room_total REAL NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (guest_id) REFERENCES guests(id),
        FOREIGN KEY (room_id) REFERENCES rooms(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        price REAL NOT NULL,
        category TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        service_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        total_price REAL NOT NULL,
        notes TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (booking_id) REFERENCES bookings(id),
        FOREIGN KEY (service_id) REFERENCES services(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL UNIQUE,
        issue_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'unpaid',
        total_amount REAL NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (booking_id) REFERENCES bookings(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        FOREIGN KEY (invoice_id) REFERENCES invoices(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        payment_date TEXT NOT NULL,
        amount REAL NOT NULL,
        method TEXT NOT NULL,
        notes TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (invoice_id) REFERENCES invoices(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT,
        expense_date TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
)


@cli.command("init-db")
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    default=DB_PATH,
    show_default=True,
    help="Path to the SQLite database",
)
def init_db(db_path: Path) -> None:
    """Create the SQLite database with the required schema."""

    with get_connection(db_path) as conn:
        for statement in SCHEMA_STATEMENTS:
            conn.execute(statement)
        conn.commit()
    echo(f"Database initialised at {db_path}", color="green")


def parse_date(value: str, field: str) -> str:
    try:
        return dt.datetime.strptime(value, DATE_FORMAT).date().isoformat()
    except ValueError as exc:
        raise click.BadParameter(f"{field} must be in YYYY-MM-DD format") from exc


@cli.command("add-guest")
@handle_db_errors
@click.option("--name", prompt=True, required=True, help="Guest full name")
@click.option("--phone", default=None, help="Guest phone number")
@click.option("--email", default=None, help="Guest email")
def add_guest(name: str, phone: Optional[str], email: Optional[str]) -> None:
    """Add a new guest profile."""

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO guests(name, phone, email) VALUES (?, ?, ?)",
            (name, phone, email),
        )
        conn.commit()
    echo(f"Guest '{name}' added successfully.", color="green")


@cli.command("list-guests")
@handle_db_errors
def list_guests() -> None:
    """Display all guests."""

    with get_connection() as conn:
        rows = conn.execute("SELECT id, name, phone, email, created_at FROM guests ORDER BY id").fetchall()

    if not rows:
        echo("No guests found.", color="yellow")
        return

    render_table(
        ("ID", "Name", "Phone", "Email", "Created"),
        (
            (
                row["id"],
                row["name"],
                row["phone"] or "-",
                row["email"] or "-",
                row["created_at"],
            )
            for row in rows
        ),
        title="Guests",
    )


@cli.command("add-room")
@handle_db_errors
@click.option("--number", prompt=True, required=True, help="Room identifier")
@click.option("--type", "room_type", prompt=True, required=True, help="Room type e.g. deluxe")
@click.option("--rate", type=float, prompt=True, required=True, help="Nightly rate")
def add_room(number: str, room_type: str, rate: float) -> None:
    """Add a room to the inventory."""

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO rooms(room_number, room_type, rate) VALUES (?, ?, ?)",
            (number, room_type, rate),
        )
        conn.commit()
    echo(f"Room {number} added.", color="green")


@cli.command("list-rooms")
@handle_db_errors
def list_rooms() -> None:
    """List all rooms with availability."""

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, room_number, room_type, rate, status FROM rooms ORDER BY room_number"
        ).fetchall()

    if not rows:
        echo("No rooms found.", color="yellow")
        return

    render_table(
        ("ID", "Room", "Type", "Rate", "Status"),
        (
            (
                row["id"],
                row["room_number"],
                row["room_type"],
                f"{row['rate']:.2f}",
                row["status"],
            )
            for row in rows
        ),
        title="Rooms",
    )


def calculate_nights(check_in: str, check_out: str) -> int:
    start = dt.datetime.strptime(check_in, DATE_FORMAT).date()
    end = dt.datetime.strptime(check_out, DATE_FORMAT).date()
    delta = (end - start).days
    if delta <= 0:
        raise click.BadParameter("Check-out date must be after check-in date")
    return delta


@cli.command("create-booking")
@handle_db_errors
@click.option("--guest-id", type=int, prompt=True, required=True, help="Guest ID")
@click.option("--room-id", type=int, prompt=True, required=True, help="Room ID")
@click.option("--check-in", prompt=True, required=True, help="Check-in date (YYYY-MM-DD)")
@click.option("--check-out", prompt=True, required=True, help="Check-out date (YYYY-MM-DD)")
def create_booking(guest_id: int, room_id: int, check_in: str, check_out: str) -> None:
    """Create a booking and reserve the room."""

    check_in = parse_date(check_in, "Check-in date")
    check_out = parse_date(check_out, "Check-out date")
    nights = calculate_nights(check_in, check_out)

    with get_connection() as conn:
        room = conn.execute("SELECT rate, status FROM rooms WHERE id=?", (room_id,)).fetchone()
        if room is None:
            raise click.BadParameter("Room not found")
        if room["status"] == "occupied":
            raise click.BadParameter("Room is currently occupied")

        total = nights * float(room["rate"])
        conn.execute(
            """
            INSERT INTO bookings(guest_id, room_id, check_in, check_out, nights, room_total)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (guest_id, room_id, check_in, check_out, nights, total),
        )
        conn.execute("UPDATE rooms SET status='occupied' WHERE id=?", (room_id,))
        conn.commit()
    echo("Booking created successfully.", color="green")


@cli.command("list-bookings")
@handle_db_errors
def list_bookings() -> None:
    """Show bookings with room and guest details."""

    query = """
        SELECT b.id, g.name AS guest_name, r.room_number, b.check_in, b.check_out,
               b.status, b.nights, b.room_total
        FROM bookings b
        JOIN guests g ON g.id = b.guest_id
        JOIN rooms r ON r.id = b.room_id
        ORDER BY b.check_in DESC
    """

    with get_connection() as conn:
        rows = conn.execute(query).fetchall()

    if not rows:
        echo("No bookings available.", color="yellow")
        return

    render_table(
        ("ID", "Guest", "Room", "Check-in", "Check-out", "Status", "Nights", "Room Total"),
        (
            (
                row["id"],
                row["guest_name"],
                row["room_number"],
                row["check_in"],
                row["check_out"],
                row["status"],
                row["nights"],
                f"{row['room_total']:.2f}",
            )
            for row in rows
        ),
        title="Bookings",
    )


@cli.command("complete-booking")
@handle_db_errors
@click.option("--booking-id", type=int, prompt=True, required=True, help="Booking ID")
def complete_booking(booking_id: int) -> None:
    """Mark a booking as completed and free the room."""

    with get_connection() as conn:
        booking = conn.execute("SELECT room_id, status FROM bookings WHERE id=?", (booking_id,)).fetchone()
        if booking is None:
            raise click.BadParameter("Booking not found")
        if booking["status"] == "completed":
            echo("Booking already completed.", color="yellow")
            return
        conn.execute("UPDATE bookings SET status='completed' WHERE id=?", (booking_id,))
        conn.execute("UPDATE rooms SET status='available' WHERE id=?", (booking["room_id"],))
        conn.commit()
    echo("Booking completed and room released.", color="green")


@cli.group(help="Manage service catalogue")
def service() -> None:
    """Service management commands."""


@service.command("add")
@handle_db_errors
@click.option("--name", prompt=True, required=True, help="Service name")
@click.option("--price", type=float, prompt=True, required=True, help="Unit price")
@click.option("--category", default=None, help="Category e.g. dining")
def add_service(name: str, price: float, category: Optional[str]) -> None:
    """Add a service (restaurant item, spa, etc.)."""

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO services(name, price, category) VALUES (?, ?, ?)",
            (name, price, category),
        )
        conn.commit()
    echo(f"Service '{name}' added.", color="green")


@service.command("list")
@handle_db_errors
def list_services() -> None:
    """List all billable services."""

    with get_connection() as conn:
        rows = conn.execute("SELECT id, name, price, category FROM services ORDER BY name").fetchall()

    if not rows:
        echo("No services defined.", color="yellow")
        return

    render_table(
        ("ID", "Name", "Price", "Category"),
        (
            (
                row["id"],
                row["name"],
                f"{row['price']:.2f}",
                row["category"] or "-",
            )
            for row in rows
        ),
        title="Services",
    )


@cli.group(help="Manage service orders tied to bookings")
def order() -> None:
    """Order management commands."""


@order.command("add")
@handle_db_errors
@click.option("--booking-id", type=int, prompt=True, required=True, help="Booking ID")
@click.option("--service-id", type=int, prompt=True, required=True, help="Service ID")
@click.option("--quantity", type=int, default=1, show_default=True, help="Quantity")
@click.option("--notes", default=None, help="Special instructions")
def add_order(booking_id: int, service_id: int, quantity: int, notes: Optional[str]) -> None:
    """Create an order for a booking."""

    with get_connection() as conn:
        service_row = conn.execute("SELECT price FROM services WHERE id=?", (service_id,)).fetchone()
        if service_row is None:
            raise click.BadParameter("Service not found")
        total = float(service_row["price"]) * quantity
        conn.execute(
            """
            INSERT INTO orders(booking_id, service_id, quantity, total_price, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (booking_id, service_id, quantity, total, notes),
        )
        conn.commit()
    echo("Order recorded.", color="green")


@order.command("list")
@handle_db_errors
@click.option("--booking-id", type=int, default=None, help="Filter by booking")
def list_orders(booking_id: Optional[int]) -> None:
    """List service orders."""

    query = """
        SELECT o.id, o.booking_id, s.name AS service_name, o.quantity, o.total_price, o.created_at
        FROM orders o
        JOIN services s ON s.id = o.service_id
    """
    params: Iterable[object] = ()
    if booking_id is not None:
        query += " WHERE o.booking_id = ?"
        params = (booking_id,)
    query += " ORDER BY o.created_at DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    if not rows:
        echo("No orders found.", color="yellow")
        return

    render_table(
        ("ID", "Booking", "Service", "Qty", "Total", "Created"),
        (
            (
                row["id"],
                row["booking_id"],
                row["service_name"],
                row["quantity"],
                f"{row['total_price']:.2f}",
                row["created_at"],
            )
            for row in rows
        ),
        title="Orders",
    )


@cli.group(help="Handle invoicing and payments")
def invoice() -> None:
    """Invoice management commands."""


def _invoice_exists(conn: sqlite3.Connection, booking_id: int) -> bool:
    row = conn.execute("SELECT id FROM invoices WHERE booking_id=?", (booking_id,)).fetchone()
    return row is not None


def _add_invoice_item(conn: sqlite3.Connection, invoice_id: int, description: str, amount: float) -> None:
    conn.execute(
        "INSERT INTO invoice_items(invoice_id, description, amount) VALUES (?, ?, ?)",
        (invoice_id, description, amount),
    )


def _fetch_booking_summary(conn: sqlite3.Connection, booking_id: int) -> sqlite3.Row:
    booking = conn.execute(
        """
        SELECT b.id, b.guest_id, b.room_id, b.check_in, b.check_out, b.nights,
               b.room_total, g.name AS guest_name, r.room_number
        FROM bookings b
        JOIN guests g ON g.id = b.guest_id
        JOIN rooms r ON r.id = b.room_id
        WHERE b.id = ?
        """,
        (booking_id,),
    ).fetchone()
    if booking is None:
        raise click.BadParameter("Booking not found")
    return booking


@invoice.command("generate")
@handle_db_errors
@click.option("--booking-id", type=int, prompt=True, required=True, help="Booking ID")
@click.option("--issue-date", default=None, help="Invoice issue date (YYYY-MM-DD)")
@click.option("--due-date", default=None, help="Invoice due date (YYYY-MM-DD)")
def generate_invoice(booking_id: int, issue_date: Optional[str], due_date: Optional[str]) -> None:
    """Create an invoice for a booking using room charges and service orders."""

    issue = parse_date(issue_date or dt.date.today().isoformat(), "Issue date")
    if due_date is None:
        due = (dt.datetime.strptime(issue, DATE_FORMAT).date() + dt.timedelta(days=7)).isoformat()
    else:
        due = parse_date(due_date, "Due date")

    with get_connection() as conn:
        if _invoice_exists(conn, booking_id):
            raise click.BadParameter("Invoice already exists for booking")
        booking = _fetch_booking_summary(conn, booking_id)
        orders = conn.execute(
            """
            SELECT o.quantity, o.total_price, s.name FROM orders o
            JOIN services s ON s.id = o.service_id
            WHERE o.booking_id = ?
            """,
            (booking_id,)
        ).fetchall()

        room_charge = float(booking["room_total"])
        total = room_charge + sum(float(order["total_price"]) for order in orders)

        cursor = conn.execute(
            """
            INSERT INTO invoices(booking_id, issue_date, due_date, total_amount)
            VALUES (?, ?, ?, ?)
            """,
            (booking_id, issue, due, total),
        )
        invoice_id = cursor.lastrowid

        _add_invoice_item(
            conn,
            invoice_id,
            f"Room {booking['room_number']} x {booking['nights']} nights",
            room_charge,
        )
        for order in orders:
            _add_invoice_item(
                conn,
                invoice_id,
                f"{order['name']} x {order['quantity']}",
                float(order["total_price"]),
            )

        conn.commit()

    echo(f"Invoice {invoice_id} generated for booking {booking_id}.", color="green")


@invoice.command("list")
@handle_db_errors
def list_invoices() -> None:
    """List all invoices with balances."""

    query = """
        SELECT i.id, i.booking_id, i.issue_date, i.due_date, i.status, i.total_amount,
               g.name AS guest_name,
               IFNULL((SELECT SUM(p.amount) FROM payments p WHERE p.invoice_id = i.id), 0) AS paid
        FROM invoices i
        JOIN bookings b ON b.id = i.booking_id
        JOIN guests g ON g.id = b.guest_id
        ORDER BY i.issue_date DESC
    """

    with get_connection() as conn:
        rows = conn.execute(query).fetchall()

    if not rows:
        echo("No invoices found.", color="yellow")
        return

    render_table(
        ("ID", "Booking", "Guest", "Issue", "Due", "Status", "Total", "Paid", "Balance"),
        (
            (
                row["id"],
                row["booking_id"],
                row["guest_name"],
                row["issue_date"],
                row["due_date"],
                row["status"],
                f"{row['total_amount']:.2f}",
                f"{float(row['paid']):.2f}",
                f"{float(row['total_amount']) - float(row['paid']):.2f}",
            )
            for row in rows
        ),
        title="Invoices",
    )


@invoice.command("show")
@handle_db_errors
@click.option("--invoice-id", type=int, prompt=True, required=True, help="Invoice ID")
def show_invoice(invoice_id: int) -> None:
    """Display invoice details with line items and payments."""

    with get_connection() as conn:
        invoice_row = conn.execute(
            """
            SELECT i.id, i.issue_date, i.due_date, i.status, i.total_amount,
                   b.id AS booking_id, g.name AS guest_name
            FROM invoices i
            JOIN bookings b ON b.id = i.booking_id
            JOIN guests g ON g.id = b.guest_id
            WHERE i.id = ?
            """,
            (invoice_id,),
        ).fetchone()
        if invoice_row is None:
            raise click.BadParameter("Invoice not found")
        items = conn.execute(
            "SELECT description, amount FROM invoice_items WHERE invoice_id = ?",
            (invoice_id,),
        ).fetchall()
        payments = conn.execute(
            "SELECT payment_date, amount, method FROM payments WHERE invoice_id = ? ORDER BY payment_date",
            (invoice_id,),
        ).fetchall()

    echo(
        f"Invoice {invoice_row['id']} for booking {invoice_row['booking_id']} (Guest: {invoice_row['guest_name']})"
    )
    echo(
        f"Issue date: {invoice_row['issue_date']}  Due date: {invoice_row['due_date']}  Status: {invoice_row['status']}"
    )

    render_table(
        ("Description", "Amount"),
        ((item["description"], f"{item['amount']:.2f}") for item in items),
        title="Line items",
    )

    payment_rows = []
    total_paid = 0.0
    for payment in payments:
        amount = float(payment["amount"])
        total_paid += amount
        payment_rows.append((payment["payment_date"], f"{amount:.2f}", payment["method"]))

    if payment_rows:
        render_table(("Date", "Amount", "Method"), payment_rows, title="Payments")
    else:
        echo("No payments recorded yet.", color="yellow")

    echo(
        f"Total: {invoice_row['total_amount']:.2f}  Paid: {total_paid:.2f}  Balance: {invoice_row['total_amount'] - total_paid:.2f}"
    )


@cli.group(help="Track invoice payments")
def payment() -> None:
    """Payment management commands."""


@payment.command("add")
@handle_db_errors
@click.option("--invoice-id", type=int, prompt=True, required=True, help="Invoice ID")
@click.option("--amount", type=float, prompt=True, required=True, help="Amount received")
@click.option("--payment-date", default=None, help="Payment date (YYYY-MM-DD)")
@click.option("--method", default="cash", show_default=True, help="Payment method")
@click.option("--notes", default=None, help="Optional remarks")
def add_payment(
    invoice_id: int,
    amount: float,
    payment_date: Optional[str],
    method: str,
    notes: Optional[str],
) -> None:
    """Record a payment against an invoice."""

    with get_connection() as conn:
        invoice_row = conn.execute("SELECT total_amount FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        if invoice_row is None:
            raise click.BadParameter("Invoice not found")
        payment_date_value = parse_date(payment_date or dt.date.today().isoformat(), "Payment date")
        conn.execute(
            """
            INSERT INTO payments(invoice_id, payment_date, amount, method, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (invoice_id, payment_date_value, amount, method, notes),
        )
        total_paid = conn.execute(
            "SELECT SUM(amount) FROM payments WHERE invoice_id=?",
            (invoice_id,),
        ).fetchone()[0] or 0.0
        status = "paid" if total_paid >= invoice_row["total_amount"] else "partial"
        conn.execute("UPDATE invoices SET status=? WHERE id=?", (status, invoice_id))
        conn.commit()

    echo("Payment recorded.", color="green")


@payment.command("list")
@handle_db_errors
@click.option("--invoice-id", type=int, default=None, help="Filter by invoice")
def list_payments(invoice_id: Optional[int]) -> None:
    """List recorded payments."""

    query = """
        SELECT p.id, p.invoice_id, p.payment_date, p.amount, p.method
        FROM payments p
    """
    params: Iterable[object] = ()
    if invoice_id is not None:
        query += " WHERE p.invoice_id = ?"
        params = (invoice_id,)
    query += " ORDER BY p.payment_date DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    if not rows:
        echo("No payments found.", color="yellow")
        return

    render_table(
        ("ID", "Invoice", "Date", "Amount", "Method"),
        (
            (
                row["id"],
                row["invoice_id"],
                row["payment_date"],
                f"{row['amount']:.2f}",
                row["method"],
            )
            for row in rows
        ),
        title="Payments",
    )


@cli.group(help="Track hotel expenses")
def expense() -> None:
    """Expense management commands."""


@expense.command("add")
@handle_db_errors
@click.option("--category", prompt=True, required=True, help="Expense category")
@click.option("--amount", type=float, prompt=True, required=True, help="Expense amount")
@click.option("--expense-date", default=None, help="Expense date (YYYY-MM-DD)")
@click.option("--description", default=None, help="Expense details")
def add_expense(
    category: str,
    amount: float,
    expense_date: Optional[str],
    description: Optional[str],
) -> None:
    """Log an operational expense."""

    expense_date_value = parse_date(expense_date or dt.date.today().isoformat(), "Expense date")
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO expenses(category, amount, description, expense_date) VALUES (?, ?, ?, ?)",
            (category, amount, description, expense_date_value),
        )
        conn.commit()
    echo("Expense recorded.", color="green")


@expense.command("list")
@handle_db_errors
@click.option("--month", type=int, default=None, help="Filter by month (1-12)")
@click.option("--year", type=int, default=None, help="Filter by year")
def list_expenses(month: Optional[int], year: Optional[int]) -> None:
    """Summarise expenses with optional filters."""

    query = "SELECT id, category, amount, description, expense_date FROM expenses"
    params: list[object] = []
    filters: list[str] = []

    if month is not None:
        filters.append("strftime('%m', expense_date) = ?")
        params.append(f"{month:02d}")
    if year is not None:
        filters.append("strftime('%Y', expense_date) = ?")
        params.append(str(year))

    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY expense_date DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    if not rows:
        echo("No expenses found for the given filters.", color="yellow")
        return

    total = 0.0
    formatted_rows = []
    for row in rows:
        amount_value = float(row["amount"])
        total += amount_value
        formatted_rows.append(
            (
                row["id"],
                row["expense_date"],
                row["category"],
                f"{amount_value:.2f}",
                row["description"] or "-",
            )
        )

    render_table(("ID", "Date", "Category", "Amount", "Description"), formatted_rows, title="Expenses")
    echo(f"Total expenses: {total:.2f}")


if __name__ == "__main__":
    cli()
