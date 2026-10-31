from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Union
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr, model_validator

VENDOR_FIELDS = ("turnover_cr", "years_experience", "registration_class")
TENDER_FIELDS = ("bid_days", "emd_pct")
REG_CLASSES = ("MSE", "Class-A", "Class-B", "Class-C")

ALL_FIELDS = Literal["turnover_cr", "years_experience", "registration_class", "bid_days", "emd_pct"]
ALL_OPS = Literal[">=", "<=", "==", "in"]


class Atom(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^CL\d+\.\d+$")
    clause_id: str = Field(pattern=r"^CL\d+$")
    field: ALL_FIELDS
    op: ALL_OPS
    value: Union[StrictInt, StrictFloat, StrictStr, list[StrictStr]]
    source_text: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_atom(self) -> Atom:
        if not self.id.startswith(self.clause_id + "."):
            raise ValueError(f"id '{self.id}' must start with clause_id '{self.clause_id}.'")

        if self.field != "registration_class":
            if self.op not in (">=", "<=", "=="):
                raise ValueError(
                    f"Numeric field '{self.field}' does not support op '{self.op}'; expected '>=', '<=', or '=='"
                )
            if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
                raise ValueError(f"Field '{self.field}' requires a numeric value, got {type(self.value).__name__}")
        else:
            if self.op == "==":
                if not isinstance(self.value, str) or self.value not in REG_CLASSES:
                    raise ValueError(
                        f"registration_class with '==' requires a value in {REG_CLASSES}, got {self.value!r}"
                    )
            elif self.op == "in":
                if not isinstance(self.value, list) or len(self.value) == 0:
                    raise ValueError("registration_class with 'in' requires a non-empty list of strings")
                for item in self.value:
                    if not isinstance(item, str) or item not in REG_CLASSES:
                        raise ValueError(
                            f"registration_class with 'in' contains invalid class {item!r}; expected one of {REG_CLASSES}"
                        )
            else:
                raise ValueError(f"registration_class does not support op '{self.op}'; expected '==' or 'in'")

        return self


def load_atoms(path: str | Path) -> list[Atom]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array of atom objects in {path}, got {type(data).__name__}")
    return [Atom.model_validate(item) for item in data]
