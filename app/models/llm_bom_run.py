from dataclasses import dataclass
from typing import Optional


@dataclass
class LlmBomRun:
    id: Optional[int] = None
    created_at: str = ""
    project_name: str = ""
    actor: str = ""
    status: str = "completed"
    source_path: str = ""
    output_path: str = ""
    source_hash: str = ""
    output_hash: str = ""
    total_rows: int = 0
    ok_rows: int = 0
    warn_rows: int = 0
    total_cost_mxn: float = 0.0
    notes: str = ""
