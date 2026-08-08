"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    INGEST ROUTER - MOMENT OF TRUTH ENDPOINT                  ║
║                                                                              ║
║  IRON SHELL PRINCIPLE: "Meet users where they are"                           ║
║  Users have messy broker statements. This endpoint accepts them.             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Form
from pydantic import BaseModel

from app.services.ingestor import FileIngestor, IngestionResult


router = APIRouter()

# Initialize ingestor
ingestor = FileIngestor()


class ColumnMappingUpdate(BaseModel):
    """User-provided column mapping corrections."""
    batch_id: str
    mapping: Dict[str, str]


@router.post("/file", response_model=IngestionResult)
async def ingest_file(
    request: Request,
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None)
):
    """
    Ingest a file (CSV, Excel, PDF) containing trade data.

    IRON SHELL MECHANICS:
    1. Accept messy real-world files
    2. Parse intelligently with error handling
    3. If ambiguous, ask SPECIFIC questions (not generic retry)
    4. Return structured trade data

    Returns:
    - success: Whether parsing was successful
    - trades: List of parsed trades
    - requires_user_input: Whether we need clarification
    - user_questions: Specific questions to ask the user
    """
    # Validate file size
    content = await file.read()
    max_size = 10 * 1024 * 1024  # 10MB
    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {max_size // 1024 // 1024}MB"
        )

    # Validate file type
    filename = file.filename or "unknown.csv"
    extension = filename.split(".")[-1].lower()
    allowed_types = ["csv", "xlsx", "xls", "pdf"]

    if extension not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Allowed: {allowed_types}"
        )

    # Process the file
    result = await ingestor.ingest_file(
        file_content=content,
        filename=filename,
        user_id=user_id
    )

    return result


@router.post("/file/with-mapping", response_model=IngestionResult)
async def ingest_file_with_mapping(
    request: Request,
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
    column_mapping: Optional[str] = Form(None)  # JSON string
):
    """
    Ingest a file with custom column mapping.

    IRON SHELL FLOW:
    When initial ingestion asks for clarification, the user
    can provide explicit column mappings here.
    """
    import json

    content = await file.read()
    filename = file.filename or "unknown.csv"

    # Parse custom mapping if provided
    custom_mapping = None
    if column_mapping:
        try:
            custom_mapping = json.loads(column_mapping)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid column mapping JSON"
            )

    result = await ingestor.ingest_file(
        file_content=content,
        filename=filename,
        user_id=user_id,
        custom_mapping=custom_mapping
    )

    return result


@router.post("/learn-mapping")
async def learn_column_mapping(mapping_update: ColumnMappingUpdate):
    """
    Learn a column mapping from user correction.

    IRON SHELL DATA FLYWHEEL:
    When users correct our column mapping, we remember it.
    This improves future parsing accuracy.
    """
    # In a full implementation, this would:
    # 1. Store the mapping in the database
    # 2. Associate it with the broker format
    # 3. Use it for future files from this broker
    ingestor.learn_mapping("user_corrected", mapping_update.mapping)

    return {
        "status": "learned",
        "message": "Column mapping saved for future use"
    }


@router.get("/supported-formats")
async def get_supported_formats():
    """
    Get list of supported file formats and known broker formats.

    IRON SHELL UX:
    Help users understand what files they can upload
    and what to expect.
    """
    return {
        "supported_file_types": [
            {
                "extension": "csv",
                "description": "Comma-separated values",
                "notes": "Most broker exports are CSV"
            },
            {
                "extension": "xlsx",
                "description": "Excel spreadsheet",
                "notes": "Excel 2007+ format"
            },
            {
                "extension": "xls",
                "description": "Legacy Excel",
                "notes": "Excel 97-2003 format"
            },
            {
                "extension": "pdf",
                "description": "PDF statement",
                "notes": "Best effort parsing via table extraction"
            }
        ],
        "known_broker_formats": [
            "Interactive Brokers",
            "TD Ameritrade / Schwab",
            "Robinhood",
            "Fidelity",
            "E*TRADE",
            "Generic CSV"
        ],
        "required_columns": [
            "symbol (stock ticker)",
            "trade_type (buy/sell)",
            "quantity (number of shares)",
            "price (per share)",
            "date (trade date)"
        ],
        "optional_columns": [
            "stop_loss_price",
            "take_profit_price",
            "leverage",
            "notes"
        ]
    }
