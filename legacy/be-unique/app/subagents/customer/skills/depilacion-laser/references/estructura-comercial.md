<!-- source: kb_be-unique/catálogo de servicio §1.10 -->

## 1.10 Estructura comercial

### Conceptos

1. **Sesión individual:** una zona durante una sesión, a tarifa regular.
2. **Paquete:** varias sesiones de una misma zona.
3. **Combo:** dos o más zonas diferentes realizadas en una misma sesión.
4. **Plan combinado:** dos o más zonas contratadas durante varias sesiones.
5. **Promoción:** beneficio temporal con condiciones y vigencia propias; se gestiona en `promociones_be-unique.md`.
6. **Plan o facilidad de pago:** modalidad de pago; no modifica por sí misma el precio del servicio.
7. **Ajuste comercial excepcional:** reducción menor autorizada sobre un precio final y evaluada únicamente durante la consulta; no modifica la tarifa regular ni constituye una promoción.

### Paquetes de una misma zona

| Modalidad | Estructura | Descuento sobre tarifa regular |
|---|---|---:|
| Sesión individual | 1 zona × 1 sesión | 0 % |
| Paquete 3 | 1 zona × 3 sesiones | 20 % |
| Paquete 6 | 1 zona × 6 sesiones | 25 % |
| Paquete 9 | 1 zona × 9 sesiones | 30 % |

Fórmulas de referencia cuando no existe un precio precomputado:

- **3 sesiones:** `precio regular × 3 × 0,80`
- **6 sesiones:** `precio regular × 6 × 0,75`
- **9 sesiones:** `precio regular × 9 × 0,70`

Los paquetes de 9 sesiones coinciden con la base inicial del tratamiento, pero **no significan que el tratamiento esté garantizado como concluido en 9 sesiones**.

### Cantidades distintas de 3, 6 o 9 sesiones

Para una sola zona:

- **4 o 5 sesiones:** puede estructurarse como paquete de 3 + sesiones individuales, o utilizar el paquete de 6.
- **7 u 8 sesiones:** puede estructurarse como paquete de 6 + sesiones individuales, o utilizar el paquete de 9.

No existe un porcentaje intermedio estándar para cantidades distintas de 3, 6 o 9.

### Combos

Un combo corresponde a **dos o más zonas independientes realizadas en una misma sesión**.

| Número de zonas | Descuento sobre la suma regular |
|---|---:|
| 2 zonas | 20 % |
| 3 zonas | 25 % |
| 4 o más zonas | 30 % |

Fórmulas:

- **2 zonas:** `suma de tarifas regulares × 0,80`
- **3 zonas:** `suma de tarifas regulares × 0,75`
- **4 o más zonas:** `suma de tarifas regulares × 0,70`

### Planes combinados

Un plan combinado corresponde a **dos o más zonas contratadas durante varias sesiones**.

| Número de sesiones | Descuento total |
|---|---:|
| 3 sesiones | 25 % |
| 6 sesiones | 30 % |
| 9 sesiones | 35 % |

Fórmulas:

- **3 sesiones:** `suma de tarifas regulares × 3 × 0,75`
- **6 sesiones:** `suma de tarifas regulares × 6 × 0,70`
- **9 sesiones:** `suma de tarifas regulares × 9 × 0,65`

Los descuentos estructurales **no se acumulan entre sí**. Cuando se contratan varias zonas durante varias sesiones, la modalidad aplicable es un **plan combinado**, no la suma de descuento de combo y descuento de paquete.

### Dos sesiones de varias zonas

Cuando se contratan varias zonas durante **1 o 2 sesiones**, se utiliza la estructura de combo en cada sesión.

Desde **3 sesiones**, la estructura estándar corresponde a un plan combinado.

### Redondeo comercial

Los precios calculados mediante fórmula se redondean al múltiplo de **10 Bs más cercano**.

- Si el cálculo queda exactamente a mitad entre dos múltiplos de 10, se utiliza el múltiplo superior.
- Cuando existe un precio precomputado en este documento, ese valor tiene prioridad sobre un nuevo cálculo.

### Combos frecuentes y precios precomputados

| Combo | Aplicación | Valor regular por sesión | Combo 1 sesión | Plan 3 sesiones | Plan 6 sesiones | Plan 9 sesiones |
|---|---|---:|---:|---:|---:|---:|
| Axilas + Bikini completo | Mujeres | 480 Bs | **380 Bs** | 1.080 Bs | 2.020 Bs | 2.810 Bs |
| Bikini completo + Tira de cola | Mujeres | 460 Bs | **370 Bs** | 1.040 Bs | 1.930 Bs | 2.690 Bs |
| Axilas + Bikini completo + Tira de cola | Mujeres | 620 Bs | **470 Bs** | 1.400 Bs | 2.600 Bs | 3.630 Bs |
| Piernas completas + Axilas | Mujeres y hombres | 640 Bs | **510 Bs** | 1.440 Bs | 2.690 Bs | 3.740 Bs |
| Piernas completas + Bikini completo | Mujeres | 800 Bs | **640 Bs** | 1.800 Bs | 3.360 Bs | 4.680 Bs |
| Piernas completas + Axilas + Bikini completo | Mujeres | 960 Bs | **720 Bs** | 2.160 Bs | 4.030 Bs | 5.620 Bs |
| Piernas completas + Axilas + Bikini completo + Tira de cola | Mujeres | 1.100 Bs | **770 Bs** | 2.480 Bs | 4.620 Bs | 6.440 Bs |
| Bozo + Patillas | Mujeres | 200 Bs | **160 Bs** | 450 Bs | 840 Bs | 1.170 Bs |
| Bozo + Mentón + Línea mandibular | Mujeres | 340 Bs | **260 Bs** | 770 Bs | 1.430 Bs | 1.990 Bs |
| Rostro completo + Cuello | Mujeres y hombres | 520 Bs | **420 Bs** | 1.170 Bs | 2.180 Bs | 3.040 Bs |
| Pecho completo + Abdomen completo | Mujeres y hombres | 580 Bs | **460 Bs** | 1.310 Bs | 2.440 Bs | 3.390 Bs |
| Espalda completa + Hombros | Hombres | 580 Bs | **460 Bs** | 1.310 Bs | 2.440 Bs | 3.390 Bs |
| Barba completa + Cuello | Hombres | 460 Bs | **370 Bs** | 1.040 Bs | 1.930 Bs | 2.690 Bs |
| Perfilado de barba + Cuello | Hombres | 420 Bs | **340 Bs** | 950 Bs | 1.760 Bs | 2.460 Bs |
| Pecho completo + Abdomen completo + Espalda completa | Mujeres y hombres* | 980 Bs | **740 Bs** | 2.210 Bs | 4.120 Bs | 5.730 Bs |
| Pecho completo + Abdomen completo + Espalda completa + Hombros | Hombres | 1.160 Bs | **810 Bs** | 2.610 Bs | 4.870 Bs | 6.790 Bs |

\* Aplica únicamente cuando todas las zonas incluidas están disponibles para el paciente.

Los combos precomputados no limitan las combinaciones posibles. Otras combinaciones de zonas independientes con tarifa definida pueden calcularse mediante la estructura general correspondiente.

### Solapamiento anatómico

No se considera combo cuando una zona ya contiene a otra o cuando dos subzonas equivalen a una zona completa existente.

| Subzonas solicitadas | Zona aplicable |
|---|---|
| Medio brazo superior + medio brazo inferior | Brazos completos |
| Abdomen superior + abdomen inferior | Abdomen completo |
| Media espalda superior + media espalda inferior | Espalda completa |
| Media pierna superior + media pierna inferior | Piernas completas |
| Manos completas + dedos de las manos | Manos completas |
| Pies completos + dedos de los pies | Pies completos |
| Bikini completo + línea de bikini | Bikini completo, cuando la línea ya está comprendida en su cobertura |

Cuando las subzonas solicitadas corresponden o se aproximan a una zona completa existente, se utiliza la estructura de la **zona completa**.

### Promociones y ajustes excepcionales

- Las promociones son temporales y se documentan en `promociones_be-unique.md`.
- Una promoción no modifica permanentemente la tarifa regular.
- La promoción histórica de **6 sesiones + 3 adicionales** no forma parte de la estructura regular vigente.
- Cualquier acumulación entre una promoción y otra estructura comercial requiere una condición expresamente definida en la promoción.
- Los **ajustes comerciales excepcionales** son reducciones menores que requieren autorización y se evalúan únicamente durante la consulta; no son una tarifa, paquete ni promoción regular.
