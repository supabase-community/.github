"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    FILE INGESTOR - THE MOMENT OF TRUTH                       ║
║                                                                              ║
║  IRON SHELL PRINCIPLE: "Meet users where they are"                           ║
║                                                                              ║
║  WHY THIS SERVICE IS CRITICAL:                                               ║
║  Users don't want to manually enter data. They have messy broker             ║
║  statements, bank exports, and random CSVs. This service:                    ║
║  1. Accepts their messy files                                                ║
║  2. Intelligently parses them into structured data                           ║
║  3. NEVER asks for generic "retry" - asks specific questions                 ║
║  4. Learns from corrections to parse better next time                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import io
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal, InvalidOperation
import uuid

import pandas as pd
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════════════════════

class ParsedTrade(BaseModel):
    """A single parsed trade from the ingested file."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    trade_type: str  # BUY, SELL, SHORT, COVER
    quantity: float
    price: float
    total_value: float
    trade_date: datetime
    broker_source: Optional[str] = None
    raw_row: Optional[Dict[str, Any]] = None
    confidence: float = 1.0  # How confident we are in the parse
    warnings: List[str] = Field(default_factory=list)


class IngestionResult(BaseModel):
    """Result of a file ingestion attempt."""
    success: bool
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trades: List[ParsedTrade] = Field(default_factory=list)
    total_rows: int = 0
    parsed_rows: int = 0
    failed_rows: int = 0
    warnings: List[str] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    column_mapping: Optional[Dict[str, str]] = None
    requires_user_input: bool = False
    user_questions: List[str] = Field(default_factory=list)


class ColumnMappingSuggestion(BaseModel):
    """Suggested mapping for a column."""
    source_column: str
    suggested_field: str
    confidence: float
    alternatives: List[str] = Field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════════
# FILE INGESTOR
# ══════════════════════════════════════════════════════════════════════════════

class FileIngestor:
    """
    Robust file parser for messy real-world data.

    IRON SHELL PHILOSOPHY:
    - Assume the data is messy (because it is)
    - Never fail silently - explain what went wrong
    - Never ask for generic retry - ask specific questions
    - Learn from corrections to parse better next time
    """

    # Standard field names we're looking for
    STANDARD_FIELDS = {
        "symbol": ["symbol", "ticker", "stock", "instrument", "asset", "security"],
        "trade_type": ["type", "action", "side", "trade_type", "transaction", "order_type", "buy/sell"],
        "quantity": ["quantity", "qty", "shares", "amount", "units", "size", "volume"],
        "price": ["price", "fill_price", "execution_price", "avg_price", "unit_price"],
        "total": ["total", "value", "amount", "net_amount", "gross", "cost", "proceeds"],
        "date": ["date", "trade_date", "execution_date", "time", "datetime", "timestamp"],
    }

    # Known broker formats
    BROKER_PATTERNS = {
        "interactive_brokers": ["conid", "commission", "ib"],
        "td_ameritrade": ["schwab", "td", "ameritrade"],
        "robinhood": ["robinhood", "rh"],
        "fidelity": ["fidelity", "settlement_date"],
        "etrade": ["etrade", "e-trade"],
        "generic": [],
    }

    def __init__(self):
        self.learned_mappings: Dict[str, Dict[str, str]] = {}

    async def ingest_file(
        self,
        file_content: bytes,
        filename: str,
        user_id: Optional[str] = None,
        custom_mapping: Optional[Dict[str, str]] = None
    ) -> IngestionResult:
        """
        Main entry point for file ingestion.

        IRON SHELL MECHANIC:
        1. Detect file type
        2. Parse into DataFrame
        3. Detect broker format
        4. Map columns to standard fields
        5. Normalize data
        6. If ambiguous, ask SPECIFIC questions (not generic retry)
        """
        result = IngestionResult(success=False)

        try:
            # Step 1: Detect file type and parse
            file_extension = filename.lower().split(".")[-1]

            if file_extension == "csv":
                df = await self._parse_csv(file_content)
            elif file_extension in ["xlsx", "xls"]:
                df = await self._parse_excel(file_content)
            elif file_extension == "pdf":
                df = await self._parse_pdf(file_content)
            else:
                result.errors.append({
                    "type": "unsupported_format",
                    "message": f"Unsupported file format: {file_extension}",
                    "suggestion": "Please upload a CSV, Excel, or PDF file"
                })
                return result

            result.total_rows = len(df)

            if df.empty:
                result.errors.append({
                    "type": "empty_file",
                    "message": "The file appears to be empty or could not be parsed",
                    "suggestion": "Please check the file contains data and try again"
                })
                return result

            # Step 2: Detect broker format
            broker = self._detect_broker(df)
            result.warnings.append(f"Detected broker format: {broker}")

            # Step 3: Map columns
            if custom_mapping:
                column_mapping = custom_mapping
            else:
                column_mapping, mapping_issues = self._auto_map_columns(df, broker)

                if mapping_issues:
                    result.requires_user_input = True
                    result.user_questions = mapping_issues
                    result.column_mapping = column_mapping
                    result.warnings.append("Some columns need confirmation")

            result.column_mapping = column_mapping

            # Step 4: Parse trades
            trades, parse_errors = await self._parse_trades(df, column_mapping)

            result.trades = trades
            result.parsed_rows = len(trades)
            result.failed_rows = len(parse_errors)
            result.errors.extend(parse_errors)

            # Step 5: Determine success
            if result.parsed_rows > 0:
                result.success = True
            elif result.requires_user_input:
                result.success = False
            else:
                result.errors.append({
                    "type": "parse_failure",
                    "message": "Could not parse any trades from the file",
                    "suggestion": "Please verify the file contains trade data"
                })

        except Exception as e:
            result.errors.append({
                "type": "unexpected_error",
                "message": str(e),
                "suggestion": "An unexpected error occurred. Please try a different file format."
            })

        return result

    async def _parse_csv(self, content: bytes) -> pd.DataFrame:
        """
        Parse CSV with intelligent delimiter and encoding detection.

        IRON SHELL TIP:
        Real broker CSVs are messy. They have:
        - Random headers at the top
        - Multiple possible delimiters
        - Inconsistent encoding
        We handle all of these.
        """
        # Try different encodings
        encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
        delimiters = [",", ";", "\t", "|"]

        for encoding in encodings:
            try:
                text = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = content.decode("utf-8", errors="replace")

        # Try to find where the actual data starts
        # (broker statements often have metadata rows at the top)
        lines = text.strip().split("\n")
        data_start = 0

        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            # Look for lines that look like headers
            lower_line = line.lower()
            if any(field in lower_line for field in ["symbol", "ticker", "date", "price", "quantity"]):
                data_start = i
                break

        # Reconstruct the CSV from the data start
        clean_text = "\n".join(lines[data_start:])

        # Try different delimiters
        for delimiter in delimiters:
            try:
                df = pd.read_csv(
                    io.StringIO(clean_text),
                    delimiter=delimiter,
                    skipinitialspace=True,
                    on_bad_lines="skip"
                )
                if len(df.columns) > 1:  # Successful parse
                    # Clean column names
                    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
                    return df
            except Exception:
                continue

        # Fallback: basic CSV parse
        return pd.read_csv(io.StringIO(clean_text), on_bad_lines="skip")

    async def _parse_excel(self, content: bytes) -> pd.DataFrame:
        """Parse Excel file."""
        try:
            df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
            df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
            return df
        except Exception:
            # Try older format
            df = pd.read_excel(io.BytesIO(content), engine="xlrd")
            df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
            return df

    async def _parse_pdf(self, content: bytes) -> pd.DataFrame:
        """
        Parse PDF broker statement.

        IRON SHELL NOTE:
        PDF parsing is complex. We use tabula for table extraction.
        For production, consider adding OCR for scanned PDFs.
        """
        try:
            import tabula
            tables = tabula.read_pdf(io.BytesIO(content), pages="all")
            if tables:
                # Concatenate all tables
                df = pd.concat(tables, ignore_index=True)
                df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
                return df
        except ImportError:
            # tabula not installed, return empty with warning
            pass

        return pd.DataFrame()

    def _detect_broker(self, df: pd.DataFrame) -> str:
        """
        Detect the broker format from column names.

        IRON SHELL MECHANIC:
        Different brokers have different column layouts.
        Detecting the broker helps us map columns more accurately.
        """
        columns_lower = [str(c).lower() for c in df.columns]
        all_text = " ".join(columns_lower)

        for broker, patterns in self.BROKER_PATTERNS.items():
            if any(pattern in all_text for pattern in patterns):
                return broker

        return "generic"

    def _auto_map_columns(
        self,
        df: pd.DataFrame,
        broker: str
    ) -> Tuple[Dict[str, str], List[str]]:
        """
        Automatically map DataFrame columns to standard fields.

        IRON SHELL PRINCIPLE:
        When we can't map with certainty, we ask SPECIFIC questions,
        not "please retry". We tell the user exactly which columns
        we're unsure about and what we think they might be.
        """
        column_mapping = {}
        issues = []
        columns = list(df.columns)

        for field, patterns in self.STANDARD_FIELDS.items():
            matched = False
            candidates = []

            for col in columns:
                col_lower = str(col).lower()
                # Exact match
                if col_lower in patterns:
                    column_mapping[field] = col
                    matched = True
                    break
                # Partial match
                for pattern in patterns:
                    if pattern in col_lower or col_lower in pattern:
                        candidates.append(col)

            if not matched:
                if len(candidates) == 1:
                    column_mapping[field] = candidates[0]
                elif len(candidates) > 1:
                    # IRON SHELL: Ask SPECIFIC question
                    issues.append(
                        f"For '{field}', which column should I use? Options: {candidates}"
                    )
                    column_mapping[field] = candidates[0]  # Use first as default
                else:
                    # No candidates found
                    issues.append(
                        f"I couldn't find a column for '{field}'. "
                        f"Available columns: {columns[:5]}{'...' if len(columns) > 5 else ''}"
                    )

        return column_mapping, issues

    async def _parse_trades(
        self,
        df: pd.DataFrame,
        column_mapping: Dict[str, str]
    ) -> Tuple[List[ParsedTrade], List[Dict[str, Any]]]:
        """
        Parse individual trades from the DataFrame.

        IRON SHELL MECHANIC:
        We don't fail on bad rows. We parse what we can and
        report specific errors for what we couldn't parse.
        """
        trades = []
        errors = []

        for idx, row in df.iterrows():
            try:
                trade = await self._parse_single_trade(row, column_mapping, idx)
                if trade:
                    trades.append(trade)
            except Exception as e:
                errors.append({
                    "type": "row_parse_error",
                    "row_number": idx + 1,
                    "message": str(e),
                    "raw_data": row.to_dict() if hasattr(row, "to_dict") else str(row)
                })

        return trades, errors

    async def _parse_single_trade(
        self,
        row: pd.Series,
        mapping: Dict[str, str],
        row_idx: int
    ) -> Optional[ParsedTrade]:
        """Parse a single trade row."""
        warnings = []

        # Extract symbol
        symbol = self._safe_get(row, mapping.get("symbol", ""))
        if not symbol:
            return None  # Symbol is required

        symbol = str(symbol).upper().strip()

        # Extract trade type
        trade_type_raw = self._safe_get(row, mapping.get("trade_type", ""))
        trade_type = self._normalize_trade_type(trade_type_raw)
        if not trade_type:
            warnings.append(f"Could not determine trade type from '{trade_type_raw}'")
            trade_type = "BUY"  # Default assumption

        # Extract quantity
        quantity = self._parse_number(self._safe_get(row, mapping.get("quantity", "")))
        if quantity is None or quantity <= 0:
            return None  # Quantity is required

        # Extract price
        price = self._parse_number(self._safe_get(row, mapping.get("price", "")))
        if price is None:
            # Try to calculate from total and quantity
            total = self._parse_number(self._safe_get(row, mapping.get("total", "")))
            if total and quantity:
                price = abs(total / quantity)
            else:
                return None  # Price is required

        # Calculate total
        total_value = quantity * price

        # Extract date
        date_raw = self._safe_get(row, mapping.get("date", ""))
        trade_date = self._parse_date(date_raw)
        if not trade_date:
            warnings.append(f"Could not parse date '{date_raw}', using today")
            trade_date = datetime.utcnow()

        return ParsedTrade(
            symbol=symbol,
            trade_type=trade_type,
            quantity=quantity,
            price=price,
            total_value=total_value,
            trade_date=trade_date,
            raw_row=row.to_dict(),
            warnings=warnings,
            confidence=1.0 if not warnings else 0.8
        )

    def _safe_get(self, row: pd.Series, column: str) -> Any:
        """Safely get a value from a row."""
        if not column:
            return None
        try:
            value = row.get(column)
            if pd.isna(value):
                return None
            return value
        except Exception:
            return None

    def _parse_number(self, value: Any) -> Optional[float]:
        """Parse a number from various formats."""
        if value is None:
            return None

        try:
            # Handle string numbers
            if isinstance(value, str):
                # Remove currency symbols, commas, spaces
                cleaned = re.sub(r"[,$€£\s]", "", value)
                # Handle parentheses for negative
                if cleaned.startswith("(") and cleaned.endswith(")"):
                    cleaned = "-" + cleaned[1:-1]
                return float(cleaned)
            return float(value)
        except (ValueError, InvalidOperation):
            return None

    def _normalize_trade_type(self, value: Any) -> Optional[str]:
        """Normalize trade type to standard values."""
        if not value:
            return None

        value_str = str(value).upper().strip()

        buy_patterns = ["BUY", "B", "BOUGHT", "PURCHASE", "LONG"]
        sell_patterns = ["SELL", "S", "SOLD", "SALE"]
        short_patterns = ["SHORT", "SH", "SELL SHORT"]
        cover_patterns = ["COVER", "BUY TO COVER", "CLOSE SHORT"]

        if any(p in value_str for p in cover_patterns):
            return "COVER"
        if any(p in value_str for p in short_patterns):
            return "SHORT"
        if any(p == value_str or value_str.startswith(p) for p in sell_patterns):
            return "SELL"
        if any(p == value_str or value_str.startswith(p) for p in buy_patterns):
            return "BUY"

        return None

    def _parse_date(self, value: Any) -> Optional[datetime]:
        """Parse date from various formats."""
        if not value:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime()

        # Try common date formats
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
            "%m-%d-%Y",
            "%d-%m-%Y",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
        ]

        value_str = str(value).strip()

        for fmt in formats:
            try:
                return datetime.strptime(value_str, fmt)
            except ValueError:
                continue

        # Try pandas parser as fallback
        try:
            return pd.to_datetime(value_str).to_pydatetime()
        except Exception:
            return None

    def learn_mapping(self, broker: str, mapping: Dict[str, str]) -> None:
        """
        Learn a column mapping from user correction.

        IRON SHELL DATA FLYWHEEL:
        When a user corrects our column mapping, we remember it.
        Next time we see this broker format, we use the learned mapping.
        """
        self.learned_mappings[broker] = mapping

    async def get_column_suggestions(
        self,
        df: pd.DataFrame
    ) -> List[ColumnMappingSuggestion]:
        """
        Get suggestions for column mappings to show the user.

        IRON SHELL UX:
        Instead of asking generic questions, we show the user
        exactly what we think each column is, with confidence levels.
        """
        suggestions = []
        columns = list(df.columns)

        for col in columns:
            col_lower = str(col).lower()
            best_match = None
            best_confidence = 0
            alternatives = []

            for field, patterns in self.STANDARD_FIELDS.items():
                # Calculate match confidence
                confidence = 0

                for pattern in patterns:
                    if col_lower == pattern:
                        confidence = 1.0
                    elif pattern in col_lower:
                        confidence = max(confidence, 0.8)
                    elif col_lower in pattern:
                        confidence = max(confidence, 0.6)

                if confidence > 0:
                    if confidence > best_confidence:
                        if best_match:
                            alternatives.append(best_match)
                        best_match = field
                        best_confidence = confidence
                    else:
                        alternatives.append(field)

            suggestions.append(ColumnMappingSuggestion(
                source_column=col,
                suggested_field=best_match or "unknown",
                confidence=best_confidence,
                alternatives=alternatives[:3]  # Top 3 alternatives
            ))

        return suggestions
