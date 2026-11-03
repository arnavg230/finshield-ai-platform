def calculate_aml_score(rule_score, behavior_score, network_score, rule_weight=0.45, behavior_weight=0.35, network_weight=0.20):
    total = rule_weight + behavior_weight + network_weight
    score = (rule_score*rule_weight + behavior_score*behavior_weight + network_score*network_weight)/total
    return round(max(0.0,min(1.0,score)),4)

def risk_level(score):
    if score >= 0.70: return "HIGH"
    if score >= 0.40: return "MEDIUM"
    return "LOW"
