"""
Calculador de comisiones para endorsements.
Las comisiones en NowCerts se almacenan como PORCENTAJES, no montos absolutos.
Este módulo calcula los montos reales aplicando los porcentajes al endorsement amount.
"""

def calculate_agency_commission(agency_commissions_list, endorsement_amount):
    """
    Calcula el monto total de comisión de agencia.
    
    La API devuelve porcentajes en 'commissionValue'.
    Calculamos: endorsement_amount * (commissionValue / 100)
    
    Args:
        agency_commissions_list: Lista de diccionarios con comisiones de agencia
        endorsement_amount: Monto del endorsement al que aplicar el porcentaje
        
    Returns:
        float: Total de comisión de agencia en dólares
    """
    total = 0.0
    
    if not agency_commissions_list or not endorsement_amount:
        return total
    
    try:
        amount = float(endorsement_amount)
    except (ValueError, TypeError):
        return total
    
    for comm in agency_commissions_list:
        commission_percent = comm.get("commissionValue")
        
        # Saltar si no hay valor o es None
        if commission_percent is None:
            continue
            
        try:
            percent = float(commission_percent)
            commission_amount = amount * (percent / 100.0)
            total += commission_amount
        except (ValueError, TypeError):
            continue
    
    return total


def calculate_agent_commission(agent_commissions_list, endorsement_amount, agency_commission_amount=None):
    """
    Calcula el monto total de comisión de agentes.
    
    Los agentes pueden recibir comisión de dos formas:
    1. "From Base Premium": Se calcula sobre el endorsement_amount
    2. "From Agency Commission": Se calcula sobre la comisión de agencia
    
    Args:
        agent_commissions_list: Lista de diccionarios con comisiones de agentes
        endorsement_amount: Monto del endorsement
        agency_commission_amount: Monto de comisión de agencia (para cálculo "From Agency Commission")
        
    Returns:
        float: Total de comisión de agentes en dólares
    """
    total = 0.0
    
    if not agent_commissions_list:
        return total
    
    try:
        base_amount = float(endorsement_amount) if endorsement_amount else 0
    except (ValueError, TypeError):
        base_amount = 0
        
    try:
        agency_amount = float(agency_commission_amount) if agency_commission_amount else 0
    except (ValueError, TypeError):
        agency_amount = 0
    
    for comm in agent_commissions_list:
        commission_percent = comm.get("commissionValue")
        payment_type = comm.get("policyCommissionAgentPaymentTypeText", "")
        
        # Saltar si no hay valor o es None
        if commission_percent is None:
            continue
            
        try:
            percent = float(commission_percent)
            
            # Determinar la base sobre la cual calcular
            if "From Agency Commission" in payment_type:
                # Se calcula sobre la comisión de agencia
                calculation_base = agency_amount
            else:
                # "From Base Premium" o cualquier otro: se calcula sobre el monto del endorsement
                calculation_base = base_amount
            
            commission_amount = calculation_base * (percent / 100.0)
            total += commission_amount
            
        except (ValueError, TypeError):
            continue
    
    return total


def calculate_commissions(agency_list, agent_list, endorsement_amount):
    """
    Calcula ambas comisiones de una vez.
    
    IMPORTANTE: Primero calcula la comisión de agencia, luego la de agentes,
    ya que algunos agentes calculan su comisión sobre la comisión de agencia.
    
    Args:
        agency_list: Lista de comisiones de agencia (con porcentajes)
        agent_list: Lista de comisiones de agentes (con porcentajes)
        endorsement_amount: Monto del endorsement
        
    Returns:
        tuple: (agency_commission_amount, agent_commission_amount)
    """
    # Primero calcular comisión de agencia
    agency_total = calculate_agency_commission(agency_list, endorsement_amount)
    
    # Luego calcular comisión de agentes (puede depender de agency_total)
    agent_total = calculate_agent_commission(agent_list, endorsement_amount, agency_total)
    
    return agency_total, agent_total