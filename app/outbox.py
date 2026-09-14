from app.db import db


ALLOWED_DECISIONS = {"approved_for_gmail_draft", "rejected"}


def queue(opportunity_id: int, interaction_id: int) -> dict:
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO outbox_approvals(opportunity_id,interaction_id,provider,status)
               VALUES(?,?, 'chatgpt_gmail','pending')""",
            (opportunity_id, interaction_id),
        )
        return dict(conn.execute(
            "SELECT * FROM outbox_approvals WHERE id=?", (cur.lastrowid,)
        ).fetchone())


def list_pending() -> list[dict]:
    with db() as conn:
        return [dict(r) for r in conn.execute(
            """SELECT o.*, i.subject, i.body
               FROM outbox_approvals o JOIN lead_interactions i ON i.id=o.interaction_id
               WHERE o.status='pending' ORDER BY o.id DESC"""
        )]


def decide(approval_id: int, approved: bool, note: str = "") -> dict:
    status = "approved_for_gmail_draft" if approved else "rejected"
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM outbox_approvals WHERE id=?", (approval_id,)
        ).fetchone()
        if not row:
            raise ValueError("Outbox approval not found")
        if row["status"] != "pending":
            raise ValueError("Outbox approval is already decided")
        conn.execute(
            """UPDATE outbox_approvals SET status=?,note=?,decided_at=CURRENT_TIMESTAMP
               WHERE id=?""", (status, note, approval_id)
        )
        conn.execute(
            "UPDATE lead_interactions SET status=? WHERE id=?",
            (status, row["interaction_id"]),
        )
        return dict(conn.execute(
            "SELECT * FROM outbox_approvals WHERE id=?", (approval_id,)
        ).fetchone())
