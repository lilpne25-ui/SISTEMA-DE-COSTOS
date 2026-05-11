from __future__ import annotations

import re
from typing import Any

from app.data.repository import Repository

from .engine import convertir_solid_a_global_shop
from .models import LlmBomResult, LlmBomRow


class LlmGlobalShopRuntime:
    """
    Servicio headless para ejecutar la conversion SOLIDWORKS -> GLOBAL SHOP
    reutilizando las mismas reglas de precio/densidad que ya usa la UI.
    """

    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self._material_catalog: list[str] = []
        self._material_density_map: dict[str, float] = {}
        self._regla_cache: dict[tuple[str, str, str, float], float | None] = {}
        self._density_cache: dict[str, float | None] = {}
        self._load_material_catalog()

    def _load_material_catalog(self) -> None:
        catalog = self.repo.listar_catalogo_materiales()
        self._material_catalog = [i.nombre for i in catalog]
        density_map: dict[str, float] = {}
        for item in catalog:
            key = (item.nombre or "").strip().upper()
            density = float(item.densidad_kg_m3 or 0.0)
            if key and density > 0:
                density_map[key] = density
        self._material_density_map = density_map

    def convert(
        self,
        *,
        source_path: str,
        output_path: str | None,
        template_path: str | None = None,
        precio_default_kg: float = 0.0,
        fabricante_default: str = "INNOVAX",
    ) -> LlmBomResult:
        self._regla_cache = {}
        self._density_cache = {}
        self._load_material_catalog()
        return convertir_solid_a_global_shop(
            source_path,
            output_path,
            price_resolver=self.resolve_price,
            density_resolver=self.resolve_density,
            precio_default_kg=precio_default_kg,
            template_path=template_path,
            fabricante_default=fabricante_default,
        )

    @staticmethod
    def _compact_material(text: str) -> str:
        raw = (text or "").upper()
        return re.sub(r"[^A-Z0-9]+", "", raw)

    @staticmethod
    def _material_tokens(text: str) -> set[str]:
        raw = (text or "").upper()
        tokens = set(re.findall(r"[A-Z]+|\d+", raw))
        return {t for t in tokens if t and t != "T"}

    @staticmethod
    def _material_signature(text: str) -> tuple[str, str]:
        compact = LlmGlobalShopRuntime._compact_material(text)
        letters = "".join(re.findall(r"[A-Z]+", compact))
        digits = "".join(re.findall(r"\d+", compact))
        return letters, digits

    def _material_candidates(self, material_text: str) -> list[str]:
        raw = (material_text or "").strip()
        if not raw:
            return []
        candidates: list[str] = [raw]
        upper = raw.upper()
        raw_compact = self._compact_material(raw)
        raw_tokens = self._material_tokens(raw)
        raw_signature = self._material_signature(raw)

        def add_candidate(value: str) -> None:
            clean = (value or "").strip()
            if clean and clean not in candidates:
                candidates.append(clean)

        for name in self._material_catalog:
            ref = (name or "").strip()
            if not ref:
                continue
            ref_upper = ref.upper()
            ref_compact = self._compact_material(ref)
            ref_tokens = self._material_tokens(ref)
            ref_signature = self._material_signature(ref)
            ref_alpha, ref_digits = ref_signature
            raw_alpha, raw_digits = raw_signature

            if ref_upper in upper:
                add_candidate(ref)
                continue

            if ref_compact and (
                raw_compact == ref_compact
                or raw_compact.startswith(ref_compact)
                or ref_compact.startswith(raw_compact)
                or ref_compact in raw_compact
            ):
                add_candidate(ref)
                continue

            if raw_signature and ref_signature and raw_signature == ref_signature:
                add_candidate(ref)
                continue

            if ref_digits and raw_digits and ref_digits in raw_digits:
                if raw_alpha and ref_alpha:
                    left_raw = raw_alpha[:2]
                    left_ref = ref_alpha[:2]
                    if left_raw and left_ref and (
                        left_raw == left_ref
                        or raw_alpha.startswith(ref_alpha)
                        or ref_alpha.startswith(raw_alpha)
                    ):
                        add_candidate(ref)
                        continue

            if ref_tokens and raw_tokens and all(t in raw_tokens for t in ref_tokens):
                add_candidate(ref)

        first_token = raw.split(" ")[0].strip()
        if first_token and first_token not in candidates:
            candidates.append(first_token)
        return candidates

    @staticmethod
    def _shape_candidates(shape: str, shape_hint: str) -> list[str]:
        hints: list[str] = []
        hint = (shape_hint or "").strip()
        if hint:
            hints.append(hint)
        shape_norm = (shape or "").strip().upper()
        if shape_norm == "REDONDO":
            hints.extend(["REDONDO", "REDONDA", "BARRA REDONDA", "ROUND"])
        elif shape_norm == "TUBO":
            hints.extend(["TUBO", "HUECO", "PIPE", "TUBE"])
        elif shape_norm == "CUADRADO":
            hints.extend(["CUADRADO", "CUADRADA", "BARRA CUADRADA", "SQUARE"])
        else:
            hints.extend(["RECTANGULAR", "PLACA", "PLATINA", "SOLERA", "FLAT"])
        hints.append("")
        dedup: list[str] = []
        seen: set[str] = set()
        for value in hints:
            key = value.strip().upper()
            if key in seen:
                continue
            seen.add(key)
            dedup.append(value.strip())
        return dedup

    @staticmethod
    def _is_a36(material_text: str) -> bool:
        return "A36" in (material_text or "").strip().upper()

    @staticmethod
    def _mm_to_in(mm: float) -> float:
        return mm / 25.4

    def resolve_density(self, material_text: str) -> float | None:
        key = (material_text or "").strip().upper()
        if key in self._density_cache:
            return self._density_cache[key]
        for candidate in self._material_candidates(material_text):
            density = self._material_density_map.get(candidate.strip().upper())
            if density is not None and density > 0:
                self._density_cache[key] = density
                return density
        self._density_cache[key] = None
        return None

    def resolve_price(
        self,
        material_text: str,
        shape: str,
        shape_hint: str,
        thickness_mm: float,
    ) -> float | None:
        cache_key = (
            (material_text or "").strip().upper(),
            (shape or "").strip().upper(),
            (shape_hint or "").strip().upper(),
            round(float(thickness_mm or 0.0), 4),
        )
        if cache_key in self._regla_cache:
            return self._regla_cache[cache_key]

        shape_norm = (shape or "").strip().upper()
        if self._is_a36(material_text) and shape_norm in {"RECTANGULAR", "CUADRADO"} and thickness_mm > 0:
            espesor_pulg = self._mm_to_in(float(thickness_mm) + 10.0)
            tarifa = self.repo.buscar_precio_a36_placa(espesor_pulg)
            if tarifa is not None and float(tarifa.precio_kg) > 0:
                price = float(tarifa.precio_kg)
                self._regla_cache[cache_key] = price
                return price

        material_candidates = self._material_candidates(material_text)
        shape_candidates = self._shape_candidates(shape, shape_hint)
        for material in material_candidates:
            for forma in shape_candidates:
                regla = self.repo.buscar_regla_costo(material, forma)
                if regla is None:
                    continue
                price = float(regla.precio_kg)
                if price > 0:
                    self._regla_cache[cache_key] = price
                    return price

        self._regla_cache[cache_key] = None
        return None

    @staticmethod
    def row_to_payload(row: LlmBomRow) -> dict[str, Any]:
        return {
            "item": row.item,
            "part_no": row.part_no,
            "description": row.description,
            "material": row.material,
            "shape": row.shape,
            "qty": float(row.qty),
            "stock_size_raw": row.stock_size_raw,
            "length_mm": float(row.length_mm),
            "unit_weight_kg": float(row.unit_weight_kg),
            "total_weight_kg": float(row.total_weight_kg),
            "price_kg_mxn": float(row.price_kg_mxn),
            "unit_cost_mxn": float(row.unit_cost_mxn),
            "total_cost_mxn": float(row.total_cost_mxn),
            "source_row": int(row.source_row),
            "status": row.status,
            "is_stk": bool(row.is_stk),
        }

    @staticmethod
    def summarize(result: LlmBomResult) -> dict[str, Any]:
        warning_examples: list[str] = []
        for row in result.rows:
            if row.status != "OK":
                warning_examples.append(f"row={row.source_row} part={row.part_no} status={row.status}")
            if len(warning_examples) >= 12:
                break
        return {
            "source_sheet": result.source_sheet,
            "input_rows": int(result.total_rows),
            "output_rows": int(len(result.rows)),
            "converted_rows": int(result.converted_rows),
            "warning_rows": int(result.warning_rows),
            "warning_examples": warning_examples,
        }
