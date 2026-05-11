# F0 Baseline - LLM SOLID -> GLOBAL SHOP

- Fecha: 2026-04-29 13:09:37
- Source SOLID: `C:\Users\TI\Documents\PRUEBAS LLSMSS\LDM507-473 SOLID .xlsx`
- Template GLOBAL SHOP: `C:\Users\TI\Documents\PRUEBAS LLSMSS\LDM507-473 GLOBAL SHOP.xlsx`
- Output baseline: `E:\SISTEMA DE COSTOS\tmp_f0_baseline_output.xlsx`

## Resultado de conversion
- `source_sheet`: `LDM507-473`
- `total_rows`: `70`
- `converted_rows`: `34`
- `warning_rows`: `36`
- `rows_exported_excel`: `106`

## Encabezados ERP
1. `PartNo`
2. `Revision`
3. `Description`
4. `AltDescription1`
5. `AltDescription2`
6. `DescExtra`
7. `Quantity`
8. `IssueUM`
9. `ConsumptionConv`
10. `UM`
11. `Cost`
12. `Source`
13. `Drawing`
14. `Leadtime`
15. `Level`
16. `Location`
17. `Memo1`
18. `Memo2`
19. `Parent`
20. `Productline`
21. `Sequence`
22. `ShotCode`
23. `Tag`
24. `Category`
25. `fabricante`
26. `filepat`
27. `Material`
28. `Peso`
29. `largo`
30. `ancho`
31. `espesor`
32. `tratamiento`

## Conteo por Productline
- `MP`: 36
- `AC`: 36
- `SU`: 30
- `HI`: 3
- `PT`: 1

## Muestra de 20 filas clave (MP/AC/SU/HI/PT)
| ExcelRow | PartNo | Productline | Source | Level | Parent | fabricante | Cost | Description |
|---:|---|---|---|---:|---|---|---:|---|
| 2 | 507-473 | PT | F | 0 | 507-473 | INNOVAX | 0 | CAMBIO RAP OP10 CAL T51 FRONT |
| 3 | B18.3.1M12x45E | SU | J | 1 | 507-473 | ANSI | 0 | T.HUECO.HEX.M12x1.75x45H45 |
| 4 | B18.3.1M5x12E | SU | J | 1 | 507-473 | ANSI | 0 | T.HUECO.HEX.M5x0.8x12H12 |
| 5 | B18.3.1M5x16E | SU | J | 1 | 507-473 | ANSI | 0 | T.HUECO.HEX.M5x0.8x16H16 |
| 6 | B18.3.1M5x20E | SU | J | 1 | 507-473 | ANSI | 0 | T.HUECO.HEX.M5x0.8x20H20 |
| 7 | B18.3.1M5x25E | SU | J | 1 | 507-473 | ANSI | 0 | T.HUECO.HEX.M5x0.8x25H25 |
| 8 | B18.3.1M6x16E | SU | J | 1 | 507-473 | ANSI | 0 | T.HUECO.HEX.M6x1x16H16 |
| 9 | B18.3.1M6x20E | SU | J | 1 | 507-473 | ANSI | 0 | T.HUECO.HEX.M6x1x20H20 |
| 10 | B18.3.1M6x25E | SU | J | 1 | 507-473 | ANSI | 0 | T.HUECO.HEX.M6x1x25H25 |
| 11 | B18.3.1M6x30E | SU | J | 1 | 507-473 | ANSI | 0 | T.HUECO.HEX.M6x1x30H24 |
| 12 | B18.3.1M6x35E | SU | J | 1 | 507-473 | ANSI | 0 | T.HUECO.HEX.M6x1x35H24 |
| 13 | B18.3.1M8x20E | SU | J | 1 | 507-473 | ANSI | 0 | T.HUECO.HEX.M8x1.25x20H20 |
| 14 | B18.3.1M8x25E | SU | J | 1 | 507-473 | ANSI | 0 | T.HUECO.HEX.M8x1.25x25H25 |
| 15 | B18.3.1M8x30E | SU | J | 1 | 507-473 | ANSI | 0 | T.HUECO.HEX.M8x1.25x30H30 |
| 16 | B18.3.1M8x35E | SU | J | 1 | 507-473 | ANSI | 0 | T.HUECO.HEX.M8x1.25x35H35 |
| 17 | B18.3.1M8x55E | SU | J | 1 | 507-473 | ANSI | 0 | T.HUECO.HEX.M8x1.25x55H28 |
| 18 | B18.3.4M5x8E | SU | J | 1 | 507-473 | ANSI | 0 | T.CAB.ABOMBADAM5x0.8x8 |
| 19 | B18.3.6M5x6 | SU | J | 1 | 507-473 | ANSI | 0 | T.FIJADOR COPAM5x0.8x6 |
| 20 | B18.3.6M5x8 | SU | J | 1 | 507-473 | ANSI | 0 | T.FIJADOR COPAM5x0.8x8 |
| 21 | B18.3.6M6x10 | SU | J | 1 | 507-473 | ANSI | 0 | T.FIJADOR COPAM6x1x10 |

## Checklist F0 (estado)
- [x] Baseline generado con archivo SOLID real
- [x] Encabezados ERP documentados
- [x] Conteo por Productline documentado
- [x] Muestra de filas clave documentada

## Comando de validacion
```powershell
python -m py_compile "E:\SISTEMA DE COSTOS\app\services\llm_bom_service.py"
```