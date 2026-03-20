# Remove Split Payment (ticket_payement) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completely remove the multi-mode split payment system (`ticket_payement` table and all related code) so each POS ticket has exactly one payment mode, stored only in `tickets.payment_mode_id` and `tickets.ref_no`.

**Architecture:** Archive and drop `ticket_payement` table → add `ref_no` to `tickets` → strip backend schemas/service/model → replace frontend multi-row payment modal with a single payment mode selector + received amount + ref_no field.

**Tech Stack:** PostgreSQL 16, Alembic, FastAPI + SQLAlchemy 2.0 async, Next.js App Router, TypeScript, React 19, Tailwind CSS v4

---

## Pre-Flight: DB Validation

Before touching any code, run this query against production to confirm data is consistent:

```sql
SELECT t.id
FROM tickets t
JOIN ticket_payement tp ON tp.ticket_id = t.id
WHERE t.payment_mode_id != (
    SELECT payment_mode_id
    FROM ticket_payement
    WHERE ticket_id = t.id
    ORDER BY amount DESC
    LIMIT 1
);
```

**Expected result: 0 rows.** If rows returned → stop and fix data first.

---

## File Map

### Files to DELETE
- `backend/app/models/ticket_payement.py`

### Files to MODIFY

| File | What changes |
|---|---|
| `backend/alembic/versions/<new>.py` | **NEW** — archive + drop `ticket_payement`, add `ref_no` to `tickets` |
| `backend/app/models/ticket.py` | Add `ref_no: Mapped[str \| None]` column |
| `backend/app/schemas/ticket.py` | Remove `TicketPayementCreate`, `TicketPayementRead`; remove `payments` field from `TicketCreate`/`TicketRead`; add `ref_no` |
| `backend/app/services/ticket_service.py` | Remove `_enrich_ticket_payement()`, remove payment loading, remove payment insert block; use `data.payment_mode_id` directly; store `data.ref_no`; validate UPI requires ref_no |
| `frontend/src/types/index.ts` | Remove `TicketPayement`, `TicketPayementCreate`; remove `payments` from `Ticket`/`TicketCreate`; add `ref_no` |
| `frontend/src/app/dashboard/ticketing/page.tsx` | Replace multi-row payment modal with single-mode UI |
| `frontend/src/app/dashboard/multiticketing/page.tsx` | Remove `payments` array; remove `TicketPayementCreate` import |

---

## Task 1: DB Migration (archive + drop + add ref_no)

**Files:**
- Create: `backend/alembic/versions/<auto>_remove_ticket_payement_add_ref_no.py`

- [ ] **Step 1: Generate blank Alembic migration**

```bash
cd backend
alembic revision -m "remove_ticket_payement_add_ref_no"
```

- [ ] **Step 2: Fill the migration file**

Find the generated file in `backend/alembic/versions/` (will be named `<hash>_remove_ticket_payement_add_ref_no.py`). Replace its body with:

```python
"""remove ticket_payement, add ref_no to tickets

Revision ID: <keep the auto-generated ID>
Revises: f9a5b3c72d16
Create Date: 2026-03-20
"""
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # 1. Archive existing split-payment data (safe, non-destructive first)
    op.execute("""
        CREATE TABLE IF NOT EXISTS ticket_payement_archive AS
        SELECT * FROM ticket_payement
    """)

    # 2. Drop the split-payment table (no FK constraint in DDL, safe to drop directly)
    op.execute("DROP TABLE IF EXISTS ticket_payement")

    # 3. Add ref_no column to tickets for UPI transaction references
    op.add_column(
        "tickets",
        sa.Column("ref_no", sa.String(30), nullable=True),
    )


def downgrade() -> None:
    # Remove ref_no from tickets
    op.drop_column("tickets", "ref_no")
    # Note: ticket_payement_archive remains as backup but table is not recreated
```

- [ ] **Step 3: Run migration**

```bash
cd backend
alembic upgrade head
```

Expected output: migration completes without error.

- [ ] **Step 4: Verify in DB**

```bash
psql -U <user> -d <dbname> -c "\d tickets" | grep ref_no
psql -U <user> -d <dbname> -c "\dt ticket_payement"
psql -U <user> -d <dbname> -c "\dt ticket_payement_archive"
```

Expected:
- `ref_no` column appears in `tickets`
- `ticket_payement` table does NOT exist
- `ticket_payement_archive` table DOES exist

---

## Task 2: Backend Model Updates

**Files:**
- Delete: `backend/app/models/ticket_payement.py`
- Modify: `backend/app/models/ticket.py`

- [ ] **Step 1: Add `ref_no` to Ticket ORM model**

In `backend/app/models/ticket.py`, add after the `boat_id` line (line 28):

```python
ref_no: Mapped[str | None] = mapped_column(String(30), nullable=True)
```

The full Ticket class `__tablename__` block should now include this column between `boat_id` and `__repr__`.

- [ ] **Step 2: Delete the TicketPayement model file**

Delete `backend/app/models/ticket_payement.py` entirely.

- [ ] **Step 3: Remove `TicketPayement` from `backend/app/models/__init__.py`**

```bash
grep -n "TicketPayement" backend/app/models/__init__.py
```

Remove TWO things from `__init__.py`:
1. The import line: `from app.models.ticket_payement import TicketPayement`
2. The `__all__` entry: `"TicketPayement"` (including its trailing comma)

Also check for any other model files:
```bash
grep -rn "TicketPayement\|ticket_payement" backend/app/models/ --include="*.py"
```

---

## Task 3: Backend Schema Updates

**Files:**
- Modify: `backend/app/schemas/ticket.py`

- [ ] **Step 1: Remove payment schemas and field from TicketCreate**

In `backend/app/schemas/ticket.py`:

**REMOVE entirely** (lines 50–72):
```python
# ── Ticket Payment schemas ──

class TicketPayementCreate(BaseModel):
    payment_mode_id: int = Field(...)
    amount: float = Field(...)
    ref_no: str | None = Field(None, ...)
    model_config = {...}

class TicketPayementRead(BaseModel):
    id: int = Field(...)
    ticket_id: int = Field(...)
    payment_mode_id: int = Field(...)
    amount: float = Field(...)
    ref_no: str | None = Field(None, ...)
    payment_mode_name: str | None = Field(None, ...)
    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Update `TicketCreate` schema**

Replace the current `TicketCreate` class with:

```python
class TicketCreate(BaseModel):
    branch_id: int = Field(..., description="Branch ID")
    ticket_date: date = Field(..., description="Ticket date")
    departure: str | None = Field(None, description="Departure time HH:MM")
    route_id: int = Field(..., description="Route ID")
    payment_mode_id: int = Field(..., description="Payment mode ID")
    ref_no: str | None = Field(None, max_length=30, description="Reference/transaction ID (for UPI payments)")
    discount: float | None = Field(0, ge=0, description="Discount amount")
    amount: float = Field(..., ge=1, description="Total amount (sum of item amounts, must be >= 1)")
    net_amount: float = Field(..., ge=1, description="Net amount (amount - discount, must be >= 1)")
    boat_id: int | None = Field(None, description="Boat ID (optional)")
    items: list[TicketItemCreate] = Field(..., min_length=1, description="Ticket items (at least 1)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "branch_id": 1,
                    "ticket_date": "2026-02-19",
                    "departure": "09:30",
                    "route_id": 1,
                    "payment_mode_id": 2,
                    "ref_no": "UPI123456",
                    "discount": 0,
                    "amount": 320.00,
                    "net_amount": 320.00,
                    "items": [
                        {"item_id": 1, "rate": 150.00, "levy": 10.00, "quantity": 2, "vehicle_no": None}
                    ],
                }
            ]
        }
    }
```

- [ ] **Step 3: Update `TicketRead` schema**

In `TicketRead`, replace:
```python
    payments: list[TicketPayementRead] | None = Field(None, description="Ticket payments (only in detail view)")
```
with:
```python
    ref_no: str | None = Field(None, description="UPI/online reference/transaction ID")
```

(Remove the `payments` field entirely from `TicketRead`.)

---

## Task 4: Backend Service Updates

**Files:**
- Modify: `backend/app/services/ticket_service.py`

- [ ] **Step 1: Remove TicketPayement import**

Remove line 10:
```python
from app.models.ticket_payement import TicketPayement
```

- [ ] **Step 2: Remove `_enrich_ticket_payement()` function**

Delete lines 97–106 (the entire `_enrich_ticket_payement` function).

- [ ] **Step 3: Update `_enrich_ticket()`**

In `_enrich_ticket()` (currently line 116), update the `data` dict to include `ref_no` and remove the payments block.

**BEFORE (lines 122–158):**
```python
    data = {
        "id": ticket.id,
        ...
        "created_by_username": created_by_username,
    }

    if include_items:
        result = await db.execute(...)
        items = result.scalars().all()
        data["items"] = [await _enrich_ticket_item(db, ti) for ti in items]

        pay_result = await db.execute(
            select(TicketPayement).where(TicketPayement.ticket_id == ticket.id)
        )
        payments = pay_result.scalars().all()
        data["payments"] = [await _enrich_ticket_payement(db, tp) for tp in payments]
    else:
        data["items"] = None
        data["payments"] = None

    return data
```

**AFTER:**
```python
    data = {
        "id": ticket.id,
        "branch_id": ticket.branch_id,
        "ticket_no": ticket.ticket_no,
        "ticket_date": ticket.ticket_date,
        "departure": _format_time(ticket.departure),
        "route_id": ticket.route_id,
        "amount": float(ticket.amount) if ticket.amount is not None else 0,
        "discount": float(ticket.discount) if ticket.discount is not None else 0,
        "payment_mode_id": ticket.payment_mode_id,
        "ref_no": ticket.ref_no,
        "is_cancelled": ticket.is_cancelled,
        "net_amount": float(ticket.net_amount) if ticket.net_amount is not None else 0,
        "status": ticket.status,
        "checked_in_at": ticket.checked_in_at,
        "branch_name": branch_name,
        "route_name": route_name,
        "payment_mode_name": pm_name,
        "verification_code": str(ticket.verification_code) if ticket.verification_code else None,
        "created_at": ticket.created_at,
        "created_by_username": created_by_username,
    }

    if include_items:
        result = await db.execute(
            select(TicketItem).where(TicketItem.ticket_id == ticket.id)
        )
        items = result.scalars().all()
        data["items"] = [await _enrich_ticket_item(db, ti) for ti in items]
    else:
        data["items"] = None

    return data
```

- [ ] **Step 4: Update `create_ticket()` — remove split payment derivation and insert block**

In `create_ticket()`, replace:

**BEFORE (lines 548–556):**
```python
async def create_ticket(db: AsyncSession, data: TicketCreate, user_id=None) -> dict:
    # Derive payment_mode_id from payments if provided (defensive: ensures
    # header payment_mode_id matches the actual payment, even if the client
    # sends a stale/default value).
    effective_payment_mode_id = data.payment_mode_id
    if data.payments:
        primary = max(data.payments, key=lambda p: p.amount)
        effective_payment_mode_id = primary.payment_mode_id
```

**AFTER:**
```python
async def create_ticket(db: AsyncSession, data: TicketCreate, user_id=None) -> dict:
    effective_payment_mode_id = data.payment_mode_id
```

- [ ] **Step 5: Add UPI ref_no validation in `create_ticket()`**

After the `effective_payment_mode_id` line and before `_validate_references(...)`, add UPI validation:

```python
    # Validate UPI payments require a ref_no
    upi_result = await db.execute(
        select(PaymentMode.description).where(PaymentMode.id == effective_payment_mode_id)
    )
    pm_description = upi_result.scalar_one_or_none() or ""
    if pm_description.upper() == "UPI" and not (data.ref_no and data.ref_no.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reference ID (ref_no) is required for UPI payments.",
        )
```

- [ ] **Step 6: Store `ref_no` when inserting Ticket**

In the `Ticket(...)` constructor call, add `ref_no=data.ref_no`:

```python
    ticket = Ticket(
        id=next_ticket_id,
        branch_id=data.branch_id,
        ticket_no=next_ticket_no,
        ticket_date=data.ticket_date,
        departure=departure_time,
        route_id=data.route_id,
        amount=computed_amount,
        discount=float(data.discount) if data.discount else 0,
        payment_mode_id=effective_payment_mode_id,
        ref_no=data.ref_no,                      # ← ADD THIS
        is_cancelled=False,
        net_amount=computed_net,
        verification_code=uuid_mod.uuid4(),
        boat_id=data.boat_id,
        created_by=user_id,
    )
```

- [ ] **Step 7: Remove entire `ticket_payement` insert block**

Delete lines 614–636:
```python
    # Insert ticket_payement rows
    if data.payments:
        await db.execute(text("SELECT pg_advisory_xact_lock(hashtext('ticket_payement_id'))"))
        pay_id_result = await db.execute(select(func.coalesce(func.max(TicketPayement.id), 0)))
        next_pay_id = pay_id_result.scalar() + 1

        for pay_data in data.payments:
            pm_check = await db.execute(select(PaymentMode.id).where(PaymentMode.id == pay_data.payment_mode_id))
            if not pm_check.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Payment Mode ID {pay_data.payment_mode_id} not found",
                )
            tp = TicketPayement(
                id=next_pay_id,
                ticket_id=next_ticket_id,
                payment_mode_id=pay_data.payment_mode_id,
                amount=pay_data.amount,
                ref_no=pay_data.ref_no,
            )
            db.add(tp)
            next_pay_id += 1
```

- [ ] **Step 8: Verify the service runs with no imports of TicketPayement**

```bash
cd backend
grep -n "TicketPayement\|ticket_payement\|payments" app/services/ticket_service.py
```

Expected: zero matches.

---

## Task 5: Frontend Types Update

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Remove `TicketPayement` and `TicketPayementCreate` interfaces**

Delete lines 262–277:
```typescript
// ── Ticket Payment types ──

export interface TicketPayement {
  id: number;
  ticket_id: number;
  payment_mode_id: number;
  amount: number;
  ref_no: string | null;
  payment_mode_name: string | null;
}

export interface TicketPayementCreate {
  payment_mode_id: number;
  amount: number;
  ref_no?: string | null;
}
```

- [ ] **Step 2: Update `Ticket` interface**

Replace:
```typescript
  payments: TicketPayement[] | null;
```
with:
```typescript
  ref_no: string | null;
```

- [ ] **Step 3: Update `TicketCreate` interface**

Replace:
```typescript
export interface TicketCreate {
  branch_id: number;
  ticket_date: string;
  departure?: string | null;
  route_id: number;
  payment_mode_id: number;
  discount?: number;
  amount: number;
  net_amount: number;
  items: TicketItemCreate[];
  payments?: TicketPayementCreate[];
}
```
with:
```typescript
export interface TicketCreate {
  branch_id: number;
  ticket_date: string;
  departure?: string | null;
  route_id: number;
  payment_mode_id: number;
  ref_no?: string | null;
  discount?: number;
  amount: number;
  net_amount: number;
  items: TicketItemCreate[];
}
```

---

## Task 6: Frontend — Ticketing Page (Major Surgery)

**Files:**
- Modify: `frontend/src/app/dashboard/ticketing/page.tsx`

This is the largest change. Work through it section by section.

### 6a — Imports

- [ ] **Step 1: Remove `TicketPayementCreate` import**

In the import block at lines 1–20, remove `TicketPayementCreate` from the `@/types` import list.

### 6b — State Cleanup

- [ ] **Step 2: Remove `paymentRows` state**

Delete lines 288–290:
```typescript
  const [paymentRows, setPaymentRows] = useState<
    { tempId: string; payment_mode_id: number; amount: number; amountStr: string; reference_id: string }[]
  >([]);
```

- [ ] **Step 3: Remove `paymentError` state**

Delete line 291:
```typescript
  const [paymentError, setPaymentError] = useState("");
```

- [ ] **Step 4: Remove `receivedAmount` computed var**

Delete line 920–921:
```typescript
  const receivedAmount = paymentRows.reduce((sum, pr) => sum + pr.amount, 0);
  const receivedAmountRounded = Math.round(receivedAmount * 100) / 100;
```

- [ ] **Step 5: Add new single-payment state variables**

After the `formDiscount`/`discountStr` state lines (currently around line 308), add:
```typescript
  // Payment confirmation modal state (single payment mode)
  const [formConfirmPaymentModeId, setFormConfirmPaymentModeId] = useState(0);
  const [formReceivedAmount, setFormReceivedAmount] = useState(0);
  const [formReceivedAmountStr, setFormReceivedAmountStr] = useState("0.00");
  const [formRefNo, setFormRefNo] = useState("");
  const [paymentError, setPaymentError] = useState("");
```

### 6c — `lastTicketInfo` update

The `lastTicketInfo` state currently uses `t.payments` from the API. After removal it must use `t.payment_mode_name` and `t.ref_no`.

- [ ] **Step 6: Update `openCreateModal` — last ticket info fetch**

Find lines 682–699:
```typescript
      const t = detailRes.data;
      const totalPaid = (t.payments || []).reduce((s, p) => s + p.amount, 0);
      const change = Math.round((totalPaid - t.net_amount) * 100) / 100;
      const modes = [...new Set((t.payments || []).map((p) => p.payment_mode_name || "-"))];
      const upiPayment = (t.payments || []).find(
        (p) => p.payment_mode_name?.toUpperCase() === "UPI"
      );
      setLastTicketInfo({
        paymentModes: modes.length > 0 ? modes : [t.payment_mode_name || "-"],
        amount: t.net_amount,
        repayment: change,
        refNo: upiPayment?.ref_no || null,
      });
```

Replace with:
```typescript
      const t = detailRes.data;
      setLastTicketInfo({
        paymentModes: [t.payment_mode_name || "-"],
        amount: t.net_amount,
        repayment: 0,
        refNo: t.ref_no || null,
      });
```

### 6d — `openCreateModal` — payment modal init

- [ ] **Step 7: Replace paymentRows init with single-mode init**

Find lines 903–915 in `handleSubmit` (the else branch for create mode):
```typescript
      // Create mode: show payment confirmation modal
      const cashMode = paymentModes.find((pm) => pm.description.toUpperCase() === "CASH");
      setPaymentRows([
        {
          tempId: crypto.randomUUID(),
          payment_mode_id: cashMode?.id || (paymentModes.length > 0 ? paymentModes[0].id : 0),
          amount: formNetAmount,
          amountStr: formNetAmount.toFixed(2),
          reference_id: "",
        },
      ]);
      setPaymentError("");
      setShowPaymentModal(true);
```

Replace with:
```typescript
      // Create mode: show payment confirmation modal
      const cashMode = paymentModes.find((pm) => pm.description.toUpperCase() === "CASH");
      setFormConfirmPaymentModeId(cashMode?.id || (paymentModes.length > 0 ? paymentModes[0].id : 0));
      setFormReceivedAmount(formNetAmount);
      setFormReceivedAmountStr(formNetAmount.toFixed(2));
      setFormRefNo("");
      setPaymentError("");
      setShowPaymentModal(true);
```

### 6e — `handleSaveAndPrint()` rewrite

This is the core save function. Currently lines 923–1093.

- [ ] **Step 8: Replace `handleSaveAndPrint()` with simplified version**

Delete the entire current `handleSaveAndPrint` function and replace with:

```typescript
  // Derived values for payment modal
  const changeAmount = Math.round((formReceivedAmount - formNetAmount) * 100) / 100;

  // Save and print handler (called from payment modal)
  const handleSaveAndPrint = async () => {
    // Validate
    if (!formConfirmPaymentModeId) {
      setPaymentError("Please select a payment mode.");
      return;
    }
    if (formReceivedAmount <= 0) {
      setPaymentError("Received amount must be greater than zero.");
      return;
    }
    if (formReceivedAmount < formNetAmount) {
      setPaymentError("Received amount cannot be less than net amount.");
      return;
    }
    const upiMode = paymentModes.find((pm) => pm.description.toUpperCase() === "UPI");
    if (upiMode && formConfirmPaymentModeId === upiMode.id && !formRefNo.trim()) {
      setPaymentError("Reference ID is required for UPI payments.");
      return;
    }
    setPaymentError("");
    setSubmitting(true);
    try {
      const activeItems = formItems.filter((fi) => !fi.is_cancelled);
      const create: TicketCreate = {
        branch_id: formBranchId,
        ticket_date: formTicketDate,
        departure: formDeparture || null,
        route_id: formRouteId,
        payment_mode_id: formConfirmPaymentModeId,
        ref_no: formRefNo.trim() || null,
        discount: formDiscount || 0,
        amount: formAmount,
        net_amount: formNetAmount,
        items: activeItems.map((fi): TicketItemCreate => ({
          item_id: fi.item_id,
          rate: fi.rate,
          levy: fi.levy,
          quantity: fi.quantity,
          vehicle_no: fi.vehicle_no || null,
          vehicle_name: fi.vehicle_name || null,
        })),
      };
      const res = await api.post<Ticket>("/api/tickets", create);
      const savedTicket = res.data;

      // Determine From -> To direction
      const route = allRoutes.find((r) => r.id === formRouteId);
      let fromTo = "";
      if (route) {
        const isFromBranchOne = formBranchId === route.branch_id_one;
        fromTo = isFromBranchOne
          ? `${route.branch_one_name} To ${route.branch_two_name}`
          : `${route.branch_two_name} To ${route.branch_one_name}`;
      }

      const branch = branches.find((b) => b.id === formBranchId);
      const branchName = branch?.name || "";
      const branchPhone = branch?.contact_nos || "";

      const paymentModeLabel =
        paymentModes.find((m) => m.id === formConfirmPaymentModeId)?.description || "-";

      const receiptData: ReceiptData = {
        ticketId: savedTicket.id,
        ticketNo: savedTicket.ticket_no,
        branchName,
        branchPhone,
        fromTo,
        ticketDate: formTicketDate,
        createdAt: savedTicket.created_at || null,
        departure: formDeparture || null,
        items: activeItems.map((fi) => ({
          name: items.find((i) => i.id === fi.item_id)?.name || `Item #${fi.item_id}`,
          quantity: fi.quantity,
          rate: fi.rate,
          levy: fi.levy,
          amount: Math.round(fi.quantity * (fi.rate + fi.levy) * 100) / 100,
          vehicleNo: fi.vehicle_no || null,
        })),
        netAmount: formNetAmount,
        createdBy: savedTicket.created_by_username || user?.username || "",
        paperWidth,
        paymentModeName: paymentModeLabel,
      };

      printReceipt(receiptData).catch(() => { /* non-fatal */ });

      // Update last-ticket info
      setLastTicketInfo({
        paymentModes: [paymentModeLabel],
        amount: formNetAmount,
        repayment: changeAmount,
        refNo: formRefNo.trim() || null,
      });

      // Reset form for next ticket (keep modal open)
      isSavingRef.current = true;
      setShowPaymentModal(false);
      const newTempId = crypto.randomUUID();
      setFormItems([{
        tempId: newTempId,
        id: null,
        item_id: 0,
        rate: 0,
        levy: 0,
        quantity: 1,
        vehicle_name: "",
        vehicle_no: "",
        is_cancelled: false,
      }]);
      setFormDiscount(0);
      setDiscountStr("0.00");
      setFormError("");
      setPaymentError("");
      setFormRefNo("");

      requestAnimationFrame(() => {
        document.getElementById(`item-id-${newTempId}`)?.focus();
        isSavingRef.current = false;
      });

      fetchTickets();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "Failed to save ticket. Please try again.";
      setPaymentError(msg);
    } finally {
      setSubmitting(false);
    }
  };
```

### 6f — Reprint function update

- [ ] **Step 9: Update `handleReprint` to use `ref_no` instead of `payments`**

Find lines 754–757:
```typescript
      const reprintPaymentLabel = t.payments && t.payments.length > 0
        ? [...new Set(t.payments.map((p) => p.payment_mode_name || "-"))].join(" / ")
        : t.payment_mode_name || "-";
```

Replace with:
```typescript
      const reprintPaymentLabel = t.payment_mode_name || "-";
```

### 6g — Payment Modal UI replacement

- [ ] **Step 10: Replace the payment confirmation modal JSX**

Find the `{/* Payment Confirmation Modal */}` block starting at line 1599. Replace the entire `<Dialog>` for payment confirmation with this simplified version:

```tsx
      {/* Payment Confirmation Modal */}
      <Dialog open={showPaymentModal} onOpenChange={(open) => !open && setShowPaymentModal(false)}>
        <DialogContent className="max-w-md" onCloseAutoFocus={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>Payment Confirmation</DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {/* Net Amount (display only) */}
            <div>
              <Label>Net Amount</Label>
              <div className="w-full border border-border rounded-lg px-4 py-2.5 text-right font-semibold text-lg bg-muted">
                {formNetAmount.toFixed(2)}
              </div>
            </div>

            {/* Payment Mode */}
            <div>
              <Label htmlFor="confirm-payment-mode">Payment Mode</Label>
              <select
                id="confirm-payment-mode"
                value={formConfirmPaymentModeId}
                onChange={(e) => {
                  setFormConfirmPaymentModeId(Number(e.target.value));
                  setFormRefNo("");
                }}
                className="w-full border border-input rounded-md px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring mt-1"
              >
                <option value={0}>-- Select --</option>
                {paymentModes.map((pm) => (
                  <option key={pm.id} value={pm.id}>{pm.description}</option>
                ))}
              </select>
            </div>

            {/* Ref No (UPI only) */}
            {paymentModes.find((pm) => pm.id === formConfirmPaymentModeId)?.description.toUpperCase() === "UPI" && (
              <div>
                <Label htmlFor="confirm-ref-no">Reference / Transaction ID</Label>
                <Input
                  id="confirm-ref-no"
                  type="text"
                  placeholder="UPI Transaction ID"
                  value={formRefNo}
                  onChange={(e) => setFormRefNo(e.target.value)}
                  className="mt-1"
                  onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleSaveAndPrint(); } }}
                />
              </div>
            )}

            {/* Amount Received */}
            <div>
              <Label htmlFor="confirm-received">Amount Received</Label>
              <Input
                id="confirm-received"
                type="text"
                inputMode="decimal"
                value={formReceivedAmountStr}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === "" || /^\d*\.?\d{0,2}$/.test(val)) {
                    setFormReceivedAmountStr(val);
                    setFormReceivedAmount(parseFloat(val) || 0);
                  }
                }}
                onFocus={(e) => e.target.select()}
                onBlur={() => setFormReceivedAmountStr(formReceivedAmount.toFixed(2))}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleSaveAndPrint(); } }}
                className="text-right mt-1"
                autoFocus
              />
            </div>

            {/* Change */}
            <div>
              <Label>Change / Re-Payment</Label>
              <div
                className={`w-full border border-border rounded-lg px-4 py-2.5 text-right font-semibold text-lg bg-muted ${
                  changeAmount >= 0 ? "text-green-700" : "text-destructive"
                }`}
              >
                {changeAmount.toFixed(2)}
              </div>
            </div>
          </div>

          {paymentError && (
            <p className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded p-2 mt-4">
              {paymentError}
            </p>
          )}

          <DialogFooter className="mt-6 flex items-center justify-between sm:justify-between">
            <div className="flex items-center gap-2">
              <Label className="text-xs text-muted-foreground whitespace-nowrap">Paper:</Label>
              <select
                value={paperWidth}
                onChange={(e) => {
                  const w = e.target.value as PaperWidth;
                  setPaperWidth(w);
                  setReceiptPaperWidth(w);
                }}
                className="h-8 border border-input rounded-md px-2 py-1 text-xs bg-background focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="80mm">80mm</option>
                <option value="58mm">58mm</option>
              </select>
            </div>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowPaymentModal(false)}
              >
                Cancel
              </Button>
              <Button
                type="button"
                disabled={submitting}
                onClick={handleSaveAndPrint}
              >
                <Printer className="h-4 w-4 mr-2" />
                {submitting ? "Saving..." : "Save & Print"}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
```

- [ ] **Step 11: Ensure `Plus` import is no longer needed in ticketing page**

Check if `Plus` is still used elsewhere in the file. If not, remove it from the lucide-react import.

```bash
grep -n "<Plus" frontend/src/app/dashboard/ticketing/page.tsx
```

If `Plus` is only used in the payment table (now removed), delete it from the import.

---

## Task 7: Frontend — Multi-Ticketing Page Update

**Files:**
- Modify: `frontend/src/app/dashboard/multiticketing/page.tsx`

- [ ] **Step 1: Remove `TicketPayementCreate` import**

Line 11: Remove `TicketPayementCreate,` from the `@/types` import.

- [ ] **Step 2: Remove `payments` array from `handleSaveAndPrint` payload**

Find lines 458–473:
```typescript
      const payments: TicketPayementCreate[] = [
        { payment_mode_id: t.paymentModeId, amount: total },
      ];

      return {
        branch_id: initData.branch_id,
        ticket_date: today,
        departure: null,
        route_id: initData.route_id,
        payment_mode_id: t.paymentModeId,
        discount: 0,
        amount: total,
        net_amount: total,
        items: validItems,
        payments,
      };
```

Replace with:
```typescript
      return {
        branch_id: initData.branch_id,
        ticket_date: today,
        departure: null,
        route_id: initData.route_id,
        payment_mode_id: t.paymentModeId,
        ref_no: null,
        discount: 0,
        amount: total,
        net_amount: total,
        items: validItems,
      };
```

---

## Task 8: Cleanup Sweep

- [ ] **Step 1: Global grep for any remaining references**

```bash
# Backend
grep -rn "TicketPayement\|ticket_payement\|\.payments" backend/app/ --include="*.py"

# Frontend
grep -rn "TicketPayement\|ticket_payement\|paymentRows\|\.payments" frontend/src/ --include="*.tsx" --include="*.ts"
```

Expected: zero matches (or only matches in migration files, which is fine).

- [ ] **Step 2: TypeScript compilation check**

```bash
cd frontend
npm run lint
```

Expected: no type errors related to removed types.

- [ ] **Step 3: Backend import check**

```bash
cd backend
python -c "from app.services.ticket_service import create_ticket; print('OK')"
```

Expected: no ImportError.

---

## Task 9: End-to-End Verification

- [ ] **Step 1: Start backend**

```bash
cd backend
uvicorn app.main:app --reload
```

Confirm: no startup errors.

- [ ] **Step 2: Start frontend**

```bash
cd frontend
npm run dev
```

Confirm: no compile errors.

- [ ] **Step 3: Manual smoke test**

1. Log in as billing_operator
2. Open Ticketing page
3. Create a new ticket with items
4. Submit → payment modal opens
5. Verify: single payment mode dropdown, amount received input, ref_no field (hidden for CASH, visible for UPI)
6. Select CASH → enter amount → Save & Print
7. Verify receipt prints with "PAYMENT MODE: CASH"
8. Repeat with UPI → enter ref_no → Save & Print
9. Verify ticket created, receipt shows "PAYMENT MODE: UPI"
10. Check: `GET /api/tickets/{id}` — response has `ref_no` field, NO `payments` array

- [ ] **Step 4: Verify portal is untouched**

```bash
grep -rn "ticket_payement\|TicketPayement" backend/app/routers/portal* backend/app/services/booking*
```

Expected: no matches.

---

## Task 10: Commit

- [ ] **Step 1: Stage changes**

```bash
git add backend/alembic/versions/
git add backend/app/models/ticket.py
git add backend/app/schemas/ticket.py
git add backend/app/services/ticket_service.py
git add frontend/src/types/index.ts
git add frontend/src/app/dashboard/ticketing/page.tsx
git add frontend/src/app/dashboard/multiticketing/page.tsx
# Stage the deleted model file
git add backend/app/models/ticket_payement.py
```

- [ ] **Step 2: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat: remove split payment (ticket_payement) — single payment mode per ticket

- Archive and drop ticket_payement table via Alembic migration
- Add ref_no column to tickets for UPI transaction references
- Remove TicketPayement ORM model, TicketPayementCreate/Read schemas
- Remove split payment derivation logic from ticket_service.py
- Replace multi-row payment modal with single-mode + received amount UI
- Remove TicketPayementCreate from multiticketing page payload
- Update types/index.ts to remove TicketPayement interfaces

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Notes for Executor

1. **`ticket_payement_archive` stays forever** — do not drop it. It is the safety net.
2. **UPI validation** is now server-side enforced (ref_no required for UPI mode).
3. **Reports are unaffected** — all report queries already use `Ticket.payment_mode_id` header.
4. **Portal is completely untouched** — no files in `routers/portal*`, `services/booking*`, or `apps/customer*` are modified.
5. **SF item split in multiticketing is untouched** — only the `payments[]` array construction is removed; `recalcSfSplit()` logic is preserved.
6. **`lastTicketInfo` display** — the "Last Ticket" info panel in the ticketing page still works; it now shows single payment mode name and ref_no (if UPI).
