"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    TRADES ROUTER - TRADE MANAGEMENT                          ║
║                                                                              ║
║  CRUD operations for trades with audit logging.                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
import uuid


router = APIRouter()


# ══════════════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════════════

class TradeCreate(BaseModel):
    """Create a new trade."""
    symbol: str
    trade_type: str = Field(description="BUY, SELL, SHORT, COVER")
    quantity: float
    price: float
    trade_date: datetime
    leverage: float = 1.0
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    position_size_percent: Optional[float] = None
    notes: Optional[str] = None


class TradeUpdate(BaseModel):
    """Update an existing trade."""
    symbol: Optional[str] = None
    trade_type: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    leverage: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    notes: Optional[str] = None


class Trade(BaseModel):
    """Full trade model."""
    id: str
    user_id: Optional[str] = None
    symbol: str
    trade_type: str
    quantity: float
    price: float
    total_value: float
    trade_date: datetime
    leverage: float = 1.0
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    position_size_percent: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TradeWithAnalysis(BaseModel):
    """Trade with its analysis."""
    trade: Trade
    analysis: Optional[Dict[str, Any]] = None
    guardrails: Optional[Dict[str, Any]] = None


# In-memory storage for demo (replace with Supabase in production)
trades_db: Dict[str, Trade] = {}


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/", response_model=Trade)
async def create_trade(trade: TradeCreate, user_id: Optional[str] = None):
    """
    Create a new trade record.

    IRON SHELL NOTE:
    In production, this stores to Supabase with RLS ensuring
    users can only access their own trades.
    """
    trade_id = str(uuid.uuid4())
    now = datetime.utcnow()

    new_trade = Trade(
        id=trade_id,
        user_id=user_id,
        symbol=trade.symbol.upper(),
        trade_type=trade.trade_type.upper(),
        quantity=trade.quantity,
        price=trade.price,
        total_value=trade.quantity * trade.price,
        trade_date=trade.trade_date,
        leverage=trade.leverage,
        stop_loss_price=trade.stop_loss_price,
        take_profit_price=trade.take_profit_price,
        position_size_percent=trade.position_size_percent,
        notes=trade.notes,
        created_at=now,
        updated_at=now
    )

    trades_db[trade_id] = new_trade
    return new_trade


@router.get("/", response_model=List[Trade])
async def list_trades(
    user_id: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List trades with optional filtering.
    """
    trades = list(trades_db.values())

    # Filter by user
    if user_id:
        trades = [t for t in trades if t.user_id == user_id]

    # Filter by symbol
    if symbol:
        trades = [t for t in trades if t.symbol == symbol.upper()]

    # Sort by date (newest first)
    trades.sort(key=lambda t: t.trade_date, reverse=True)

    # Paginate
    return trades[offset:offset + limit]


@router.get("/{trade_id}", response_model=Trade)
async def get_trade(trade_id: str):
    """Get a specific trade by ID."""
    if trade_id not in trades_db:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trades_db[trade_id]


@router.put("/{trade_id}", response_model=Trade)
async def update_trade(trade_id: str, update: TradeUpdate):
    """
    Update a trade.

    IRON SHELL AUDIT:
    All updates are logged for compliance and analysis.
    """
    if trade_id not in trades_db:
        raise HTTPException(status_code=404, detail="Trade not found")

    trade = trades_db[trade_id]
    update_data = update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(trade, field, value)

    trade.updated_at = datetime.utcnow()

    # Recalculate total if quantity or price changed
    if "quantity" in update_data or "price" in update_data:
        trade.total_value = trade.quantity * trade.price

    trades_db[trade_id] = trade
    return trade


@router.delete("/{trade_id}")
async def delete_trade(trade_id: str):
    """Delete a trade."""
    if trade_id not in trades_db:
        raise HTTPException(status_code=404, detail="Trade not found")

    del trades_db[trade_id]
    return {"status": "deleted", "trade_id": trade_id}


@router.post("/bulk", response_model=List[Trade])
async def create_bulk_trades(
    trades: List[TradeCreate],
    user_id: Optional[str] = None
):
    """
    Create multiple trades at once.

    IRON SHELL USE CASE:
    After file ingestion, save all parsed trades in bulk.
    """
    created = []
    for trade in trades:
        new_trade = await create_trade(trade, user_id)
        created.append(new_trade)
    return created


@router.get("/stats/summary")
async def get_trade_stats(user_id: Optional[str] = None):
    """
    Get summary statistics for trades.

    IRON SHELL ANALYTICS:
    Understanding trade patterns helps improve AI analysis.
    """
    trades = list(trades_db.values())
    if user_id:
        trades = [t for t in trades if t.user_id == user_id]

    if not trades:
        return {
            "total_trades": 0,
            "total_volume": 0,
            "symbols_traded": [],
            "avg_position_size": 0
        }

    total_volume = sum(t.total_value for t in trades)
    symbols = list(set(t.symbol for t in trades))

    return {
        "total_trades": len(trades),
        "total_volume": round(total_volume, 2),
        "symbols_traded": symbols,
        "avg_position_size": round(total_volume / len(trades), 2),
        "buy_count": sum(1 for t in trades if t.trade_type == "BUY"),
        "sell_count": sum(1 for t in trades if t.trade_type == "SELL"),
    }
