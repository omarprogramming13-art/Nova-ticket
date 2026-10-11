# Implementation Plan: New Ticket Features

## 1. View Deleted Ticket Info
- **File:** `bot/cogs/management.py`
- **Current status:** `ticket_info` command already handles `status='deleted'`.
- **Action:** Review `ticket_info` and ensure it displays all requested info: claimed by, commands used (audit logs), ticket changes, creation info, evidence, and transcript link. Add any missing pieces if necessary.

## 2. Restrict Ticket Claims by Role
- **File:** `bot/views/panel_view.py`, `bot/cogs/management.py`, `bot/database/db.py`
- **Action:**
  - Update `panels` table/logic to allow restricting specific roles from claiming tickets for a panel.
  - In `panel_view.py`, when creating a ticket, check if the user's roles are restricted.
  - In `management.py` (claim command), ensure staff role restrictions are enforced based on panel settings.

## 3. Staff DM Notifications for Ratings
- **File:** `bot/views/rating_view.py`
- **Action:**
  - Check `rating_view.py` and ensure the DM is sent to the staff member correctly with all requested details (who rated, rating, comments).
  - Add logic to send DM if not already doing so.

## 4. DM Button for Ticket Claimant
- **File:** `bot/views/ticket_controls.py`
- **Action:**
  - Add a button in `TicketControlView` (or a similar UI) for the ticket claimant to send a message to the ticket owner.
  - Create a modal for the message input.
  - Log the message and sender.

## 5. Automatic Inactivity Reminders
- **File:** `bot/main.py`
- **Action:**
  - Update `check_inactivity` in `main.py` to send a reminder message to the member if no interaction happens after a staff member claims the ticket.
