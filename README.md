# Tabakh Lazeez Hotel Management Toolkit

A free, open-source command-line system for Tabakh Lazeez Hotel in Jazan to manage guests, rooms, bookings, orders, invoicing, payments, and expenses from a single place.

## Features

- SQLite-backed storage (no external services required)
- Guest and room registry management
- Booking lifecycle tracking with automatic room availability updates
- Service catalog for restaurant, spa, housekeeping add-ons
- Order logging tied to bookings
- Automated invoice generation with line items and payment tracking
- Expense tracking with monthly/yearly filters

## Getting Started

1. **Clone the repository** (already done if you're reading this).
2. **Create a virtual environment** (recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\\Scripts\\activate`
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**:

   ```bash
   python hotel_management.py init-db
   ```

   This will create `hotel.db` in the project directory with all tables ready to use.

## Usage Examples

Add guests and rooms:

```bash
python hotel_management.py add-guest --name "Ahmed Khan" --phone "+966500000000" --email "ahmed@example.com"
python hotel_management.py add-room --number 101 --type deluxe --rate 350
```

Create a booking and attach orders:

```bash
python hotel_management.py create-booking --guest-id 1 --room-id 1 --check-in 2024-06-01 --check-out 2024-06-05
python hotel_management.py service add --name "Chicken Biryani" --price 55 --category dining
python hotel_management.py order add --booking-id 1 --service-id 1 --quantity 2 --notes "Extra spicy"
```

Generate an invoice and register a payment:

```bash
python hotel_management.py invoice generate --booking-id 1 --issue-date 2024-06-05
python hotel_management.py invoice show --invoice-id 1
python hotel_management.py payment add --invoice-id 1 --amount 500 --method card
```

Track expenses:

```bash
python hotel_management.py expense add --category utilities --amount 1200 --description "Electricity bill"
python hotel_management.py expense list --month 6 --year 2024
```

Run `python hotel_management.py --help` to see the full command tree.

## Roadmap Ideas

- Role-based user authentication for staff members
- PDF invoice export
- Integration with WhatsApp/SMS for guest notifications
- Basic dashboard visualizations using Streamlit or FastAPI

Contributions are welcome! Feel free to fork, improve, and share with the Tabakh Lazeez community.
