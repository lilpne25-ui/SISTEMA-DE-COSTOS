"""
Contrato de acceso a datos.
La UI solo habla con esta interfaz para mantener separado el motor de BD.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from app.models.catalogo_item import CatalogoItem
from app.models.costo import Costo
from app.models.material import Material
from app.models.precio_a36_placa import PrecioA36Placa
from app.models.regla_costo import ReglaCosto
from app.models.llm_bom_run import LlmBomRun


class Repository(ABC):
    # ---- Materiales -----------------------------------------------------
    @abstractmethod
    def listar_materiales(
        self,
        filtro_tipo: Optional[str] = None,
        busqueda: Optional[str] = None,
    ) -> List[Material]: ...

    @abstractmethod
    def obtener_material(self, material_id: int) -> Optional[Material]: ...

    @abstractmethod
    def crear_material(self, material: Material) -> int: ...

    @abstractmethod
    def crear_material_con_costo_inicial(
        self,
        material: Material,
        costo: Costo,
    ) -> int: ...

    @abstractmethod
    def actualizar_material(self, material: Material) -> None: ...

    @abstractmethod
    def eliminar_material(self, material_id: int) -> None: ...

    @abstractmethod
    def tipos_material(self) -> List[str]: ...

    @abstractmethod
    def actualizar_ficha_tecnica_pdf(
        self,
        material_id: int,
        nombre_archivo: str,
        contenido_pdf: bytes,
    ) -> None: ...

    @abstractmethod
    def obtener_ficha_tecnica_pdf(self, material_id: int) -> Optional[tuple[str, bytes]]: ...

    @abstractmethod
    def eliminar_ficha_tecnica_pdf(self, material_id: int) -> None: ...

    @abstractmethod
    def listar_catalogo_materiales(self) -> List[CatalogoItem]: ...

    @abstractmethod
    def crear_catalogo_material(self, item: CatalogoItem) -> int: ...

    @abstractmethod
    def actualizar_catalogo_material(self, item: CatalogoItem) -> None: ...

    @abstractmethod
    def eliminar_catalogo_material(self, item_id: int | str) -> None: ...

    @abstractmethod
    def listar_catalogo_formas(self) -> List[CatalogoItem]: ...

    @abstractmethod
    def crear_catalogo_forma(self, item: CatalogoItem) -> int: ...

    @abstractmethod
    def actualizar_catalogo_forma(self, item: CatalogoItem) -> None: ...

    @abstractmethod
    def eliminar_catalogo_forma(self, item_id: int | str) -> None: ...

    @abstractmethod
    def generar_codigo_material(self, material_nombre: str, forma_nombre: str) -> str: ...

    @abstractmethod
    def listar_precios_a36_placa(self) -> List[PrecioA36Placa]: ...

    @abstractmethod
    def buscar_precio_a36_placa(
        self,
        espesor_pulgadas: float,
    ) -> Optional[PrecioA36Placa]: ...

    @abstractmethod
    def crear_precio_a36_placa(self, precio: PrecioA36Placa) -> int: ...

    @abstractmethod
    def actualizar_precio_a36_placa(self, precio: PrecioA36Placa) -> None: ...

    @abstractmethod
    def eliminar_precio_a36_placa(self, precio_id: int) -> None: ...

    @abstractmethod
    def listar_reglas_costo(self) -> List[ReglaCosto]: ...

    @abstractmethod
    def buscar_regla_costo(
        self,
        material_nombre: str,
        forma_nombre: str,
    ) -> Optional[ReglaCosto]: ...

    @abstractmethod
    def crear_regla_costo(self, regla: ReglaCosto) -> int: ...

    @abstractmethod
    def actualizar_regla_costo(self, regla: ReglaCosto) -> None: ...

    @abstractmethod
    def eliminar_regla_costo(self, regla_id: int) -> None: ...

    @abstractmethod
    def registrar_llm_bom_run(self, run: LlmBomRun) -> int: ...

    @abstractmethod
    def actualizar_llm_bom_run(self, run: LlmBomRun) -> None: ...

    @abstractmethod
    def listar_llm_bom_runs(self, limite: int = 200) -> List[LlmBomRun]: ...

    # ---- Costos ---------------------------------------------------------
    @abstractmethod
    def listar_costos(self, material_id: int) -> List[Costo]: ...

    @abstractmethod
    def agregar_costo(self, costo: Costo) -> int: ...

    @abstractmethod
    def costo_actual(self, material_id: int) -> Optional[Costo]: ...

    @abstractmethod
    def listar_proveedores_historicos(self, limite: int = 50) -> List[str]: ...
