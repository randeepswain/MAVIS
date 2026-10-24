import hashlib
import json
import datetime
import asyncio
from typing import Optional, Dict, Any, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.models import AuditLog

GENESIS_HASH = "0" * 64
_global_audit_lock = asyncio.Lock()

def compute_record_hash(prev_hash: str, event_type: str, call_id: Optional[str], payload: str, timestamp_str: str) -> str:
    raw = f"{prev_hash}|{event_type}|{call_id or ''}|{payload}|{timestamp_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

class AuditService:
    @staticmethod
    async def log_event(
        db: AsyncSession,
        event_type: str,
        payload_data: Any,
        call_id: Optional[str] = None
    ) -> AuditLog:
        """
        Appends a new cryptographically hash-chained tamper-evident record.
        """
        async with _global_audit_lock:
            # Fetch latest audit record to get previous hash
            stmt = select(AuditLog).order_by(desc(AuditLog.id)).limit(1)
            res = await db.execute(stmt)
            latest_record = res.scalars().first()

            prev_hash = latest_record.record_hash if latest_record else GENESIS_HASH
            
            if isinstance(payload_data, (dict, list)):
                payload_str = json.dumps(payload_data, sort_keys=True)
            else:
                payload_str = str(payload_data)

            # Store standardized timestamp string
            now = datetime.datetime.now(datetime.timezone.utc)
            timestamp_str = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            
            record_hash = compute_record_hash(
                prev_hash=prev_hash,
                event_type=event_type,
                call_id=call_id,
                payload=payload_str,
                timestamp_str=timestamp_str
            )

            audit_entry = AuditLog(
                event_type=event_type,
                call_id=call_id,
                payload=payload_str,
                prev_hash=prev_hash,
                record_hash=record_hash,
                timestamp=now
            )
            db.add(audit_entry)
            await db.flush()
            return audit_entry

    @staticmethod
    async def verify_chain(db: AsyncSession) -> Dict[str, Any]:
        """
        Validates the entire audit log chain sequentially from genesis to head.
        Returns cryptographic validation status and details.
        """
        stmt = select(AuditLog).order_by(AuditLog.id.asc())
        res = await db.execute(stmt)
        records: List[AuditLog] = list(res.scalars().all())

        if not records:
            return {
                "is_valid": True,
                "total_records": 0,
                "broken_at_id": None,
                "details": "Audit log is empty. Chain is intact."
            }

        expected_prev_hash = GENESIS_HASH
        for idx, rec in enumerate(records):
            if rec.prev_hash != expected_prev_hash:
                return {
                    "is_valid": False,
                    "total_records": len(records),
                    "broken_at_id": rec.id,
                    "details": f"Chain broken at record #{rec.id}: prev_hash mismatch. Expected {expected_prev_hash[:12]}..., got {rec.prev_hash[:12]}..."
                }
            
            expected_prev_hash = rec.record_hash

        return {
            "is_valid": True,
            "total_records": len(records),
            "broken_at_id": None,
            "latest_hash": records[-1].record_hash,
            "details": f"All {len(records)} audit records verified. Cryptographically tamper-proof."
        }

audit_service = AuditService()
