# 📊 Sistema de Cálculo de Comisiones - Reporte Automatizado

Este proyecto automatiza la generación de reportes de comisiones para endorsements de pólizas, calculando tanto las comisiones de agencia como las comisiones de agentes individuales.

## 📋 Tabla de Contenidos

- [Descripción General](#-descripción-general)
- [Cómo se Calculan las Comisiones](#-cómo-se-calculan-las-comisiones)
- [Ejemplos Detallados](#-ejemplos-detallados)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Instalación y Uso](#-instalación-y-uso)

---

## 🎯 Descripción General

El sistema obtiene datos de la API de NowCerts y calcula automáticamente:

1. **Comisión de Agencia** (Agency Commission)
2. **Comisión de Agente** (Agent Commission)

### Características Principales

- ✅ Filtra endorsements por rango de fechas
- ✅ Calcula comisiones basadas en porcentajes almacenados en NowCerts
- ✅ Genera 1 fila por agente en cada endorsement
- ✅ Exporta resultados a Excel con formato profesional
- ✅ Maneja endorsements de cancelación (valores negativos)

---

## 💰 Cómo se Calculan las Comisiones

### 1️⃣ Comisión de Agencia (Agency Commission)

La comisión de agencia se calcula aplicando un **porcentaje** al monto del endorsement.

#### Fórmula:
```
Agency Commission = Endorsement Amount × (Commission Percentage / 100)
```

#### Proceso:
1. Se obtienen las comisiones de agencia desde el endpoint `/PolicyEndorsementAgencyCommissionDetailList`
2. Cada comisión tiene un campo `commissionValue` que contiene el **porcentaje**
3. Se aplica el porcentaje al `endorsement_amount`
4. Si hay múltiples comisiones de agencia, se suman todas

#### Código Relevante:
```python
# app/services/commision_calculator.py
def calculate_agency_commission(agency_commissions_list, endorsement_amount):
    total = 0.0
    
    for comm in agency_commissions_list:
        commission_percent = comm.get("commissionValue")
        percent = float(commission_percent)
        commission_amount = endorsement_amount * (percent / 100.0)
        total += commission_amount
    
    return total
```

---

### 2️⃣ Comisión de Agente (Agent Commission)

La comisión de agente puede calcularse de **dos formas diferentes**, dependiendo del tipo de pago configurado:

#### Tipo 1: "From Base Premium" (Desde la Prima Base)
Se calcula sobre el **monto del endorsement**.

```
Agent Commission = Endorsement Amount × (Commission Percentage / 100)
```

#### Tipo 2: "From Agency Commission" (Desde la Comisión de Agencia)
Se calcula sobre la **comisión de agencia** previamente calculada.

```
Agent Commission = Agency Commission × (Commission Percentage / 100)
```

#### Proceso:
1. Se obtienen las comisiones de agente desde el endpoint `/PolicyEndorsementAgentsCommissionDetailList`
2. Cada comisión tiene:
   - `commissionValue`: el porcentaje
   - `policyCommissionAgentPaymentTypeText`: el tipo de pago ("From Base Premium" o "From Agency Commission")
3. Se determina la base de cálculo según el tipo de pago
4. Se aplica el porcentaje correspondiente

#### Código Relevante:
```python
# app/services/commision_calculator.py
def calculate_agent_commission(agent_commissions_list, endorsement_amount, agency_commission_amount):
    total = 0.0
    
    for comm in agent_commissions_list:
        commission_percent = comm.get("commissionValue")
        payment_type = comm.get("policyCommissionAgentPaymentTypeText", "")
        
        percent = float(commission_percent)
        
        # Determinar la base de cálculo
        if "From Agency Commission" in payment_type:
            calculation_base = agency_commission_amount
        else:
            calculation_base = endorsement_amount
        
        commission_amount = calculation_base * (percent / 100.0)
        total += commission_amount
    
    return total
```

---

## 📚 Ejemplos Detallados

### Ejemplo 1: Comisión Simple "From Base Premium"

**Datos del Endorsement:**
- Endorsement Amount: **$10,000**
- Agency Commission Percentage: **15%**
- Agent Commission Percentage: **10%** (From Base Premium)

**Cálculos:**

1. **Agency Commission:**
   ```
   $10,000 × (15 / 100) = $1,500
   ```

2. **Agent Commission:**
   ```
   $10,000 × (10 / 100) = $1,000
   ```

**Resultado:**
- Agency Commission: **$1,500**
- Agent Commission: **$1,000**
- Total Commission: **$2,500**

---

### Ejemplo 2: Comisión "From Agency Commission"

**Datos del Endorsement:**
- Endorsement Amount: **$20,000**
- Agency Commission Percentage: **12%**
- Agent Commission Percentage: **25%** (From Agency Commission)

**Cálculos:**

1. **Agency Commission (primero):**
   ```
   $20,000 × (12 / 100) = $2,400
   ```

2. **Agent Commission (sobre la comisión de agencia):**
   ```
   $2,400 × (25 / 100) = $600
   ```

**Resultado:**
- Agency Commission: **$2,400**
- Agent Commission: **$600**
- Total Commission: **$3,000**

> ⚠️ **Importante:** En este caso, el agente recibe el 25% de la comisión de agencia, NO del endorsement amount.

---

### Ejemplo 3: Múltiples Comisiones de Agencia

**Datos del Endorsement:**
- Endorsement Amount: **$15,000**
- Agency Commission 1: **10%**
- Agency Commission 2: **5%**
- Agent Commission: **8%** (From Base Premium)

**Cálculos:**

1. **Agency Commission Total:**
   ```
   Comisión 1: $15,000 × (10 / 100) = $1,500
   Comisión 2: $15,000 × (5 / 100)  = $750
   Total: $1,500 + $750 = $2,250
   ```

2. **Agent Commission:**
   ```
   $15,000 × (8 / 100) = $1,200
   ```

**Resultado:**
- Agency Commission: **$2,250**
- Agent Commission: **$1,200**
- Total Commission: **$3,450**

---

### Ejemplo 4: Endorsement de Cancelación

**Datos del Endorsement:**
- Endorsement Amount: **$5,000** (cancelación)
- Endorsement Type: **"Policy Cancellation"**
- Agency Commission Percentage: **15%**
- Agent Commission Percentage: **10%**

**Cálculos:**

1. **Agency Commission:**
   ```
   $5,000 × (15 / 100) = $750
   Aplicar negativo: -$750
   ```

2. **Agent Commission:**
   ```
   $5,000 × (10 / 100) = $500
   Aplicar negativo: -$500
   ```

**Resultado:**
- Endorsement Amount: **-$5,000** (negativo)
- Agency Commission: **-$750** (negativo)
- Agent Commission: **-$500** (negativo)
- Total Commission: **-$1,250** (negativo)

> 📌 **Nota:** Los endorsements de cancelación se muestran en rojo en el Excel.

---

### Ejemplo 5: Múltiples Agentes en una Póliza

**Datos del Endorsement:**
- Endorsement Amount: **$30,000**
- Agency Commission: **12%**
- Agentes en la póliza: **Juan Pérez, María García, Carlos López**
- Agent Commission (Juan): **5%** (From Base Premium)
- Agent Commission (María): **20%** (From Agency Commission)
- Agent Commission (Carlos): **0%** (sin comisión configurada)

**Cálculos:**

1. **Agency Commission:**
   ```
   $30,000 × (12 / 100) = $3,600
   ```

2. **Agent Commissions:**
   - **Juan Pérez:**
     ```
     $30,000 × (5 / 100) = $1,500
     ```
   - **María García:**
     ```
     $3,600 × (20 / 100) = $720
     ```
   - **Carlos López:**
     ```
     Sin comisión configurada = $0
     ```

**Resultado en Excel (3 filas):**

| Agents | Agency Commission | Agent Commission |
|--------|-------------------|------------------|
| Juan Pérez | $3,600 | $1,500 |
| María García | $3,600 | $720 |
| Carlos López | $3,600 | $0 |

> 📌 **Nota:** La Agency Commission se repite en cada fila, pero la Agent Commission es individual.

---

## 🏗️ Estructura del Proyecto

```
Commissions-Report-Automated/
│
├── app/
│   ├── api/
│   │   ├── client.py                    # Cliente de NowCerts API
│   │   └── policies.py                  # Obtención de datos de pólizas
│   │
│   ├── services/
│   │   ├── commision_calculator.py      # ⭐ Lógica de cálculo de comisiones
│   │   └── endorsement_report_service.py # Generación del reporte
│   │
│   └── exports/
│       └── excel_reporter.py            # Exportación a Excel
│
├── run_report.py                        # Script principal
├── requirements.txt                     # Dependencias
└── README.md                            # Este archivo
```

### Archivos Clave

#### 1. `commision_calculator.py`
Contiene las funciones principales de cálculo:
- `calculate_agency_commission()`: Calcula comisión de agencia
- `calculate_agent_commission()`: Calcula comisión de agente
- `calculate_commissions()`: Calcula ambas comisiones

#### 2. `endorsement_report_service.py`
- Obtiene datos de la API de NowCerts
- Filtra endorsements por fecha
- Genera 1 fila por agente
- Aplica los cálculos de comisiones

#### 3. `excel_reporter.py`
- Exporta datos a Excel
- Aplica formato profesional
- Maneja valores negativos (cancelaciones)

---

## 🚀 Instalación y Uso

### Requisitos Previos

- Python 3.8+
- Credenciales de NowCerts API

### Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone <repository-url>
   cd Commissions-Report-Automated
   ```

2. **Crear entorno virtual:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar credenciales:**
   Crear archivo `.env` con:
   ```env
   NOWCERTS_API_KEY=tu_api_key
   NOWCERTS_AGENCY_ID=tu_agency_id
   ```

### Uso

**Generar reporte desde una fecha específica:**

```bash
python run_report.py
```

Por defecto, genera el reporte desde `2025-12-01` hasta hoy.

**Cambiar la fecha de inicio:**

Editar `run_report.py`:
```python
if __name__ == "__main__":
    # Desde enero 2026
    main(date_from="2026-01-01")
```

### Salida

El reporte se genera en:
```
output/endorsements_commission_report_YYYYMMDD_to_today.xlsx
```

**Columnas del Excel:**
- Endorsement ID
- Endorsement Date
- Endorsement Amount
- Endorsement Type
- MGA
- Policy Number
- Policy Effective
- Policy Expiration
- Insured
- Agents (1 por fila)
- CSRs (1 por fila)
- **Agency Commission** ⭐
- **Agent Commission** ⭐
- Total Commission

---

## 📝 Notas Importantes

1. **Orden de Cálculo:** Siempre se calcula primero la Agency Commission, ya que algunos agentes pueden calcular su comisión sobre ella.

2. **Porcentajes vs Montos:** NowCerts almacena `commissionValue` como **porcentajes**, no como montos absolutos.

3. **Cancelaciones:** Los endorsements de tipo "Cancel" muestran valores negativos en todas las columnas de montos.

4. **Filtrado:** Solo se incluyen endorsements con comisiones mayores a $0.

5. **Múltiples Agentes:** Cada agente genera una fila separada en el reporte.

---

## 🤝 Contribuciones

Para contribuir al proyecto:
1. Fork el repositorio
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

---

## 📧 Contacto

Para preguntas o soporte, contacta al equipo de desarrollo.

---

**Última actualización:** Febrero 2026
