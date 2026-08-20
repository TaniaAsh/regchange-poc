---
document_id: ACME-POL-MRM-003
title: Acme Bank Model Risk Management Standard
version: 3.0
status: approved
effective_date: 2025-06-15
expiry_date: 2027-06-15
jurisdiction: Global (Acme Bank Group)
classification: Internal
policy_owner: Head of Model Risk
access_groups: [model-risk, risk-management, all-staff]
---

# Acme Bank Model Risk Management Standard (v3.0)

## 1. Purpose

This Standard sets out the requirements for identifying, assessing, and managing
model risk across all quantitative models used by Acme Bank, including statistical,
machine learning, and AI-based models.

## 2. Model Risk Tiering

Every model is assigned a risk tier (Tier 1 to Tier 3) at initial validation based
on materiality of use, complexity, and potential impact if the model performs
incorrectly.

## 3. Initial Validation

Prior to first use, every model must undergo independent validation by the Model
Risk Function, covering:

- Conceptual soundness of the model design
- Data quality and representativeness of training/validation data
- Outcome analysis and benchmark comparison
- Identification of known limitations and boundary conditions

## 4. Model Risk Committee Approval

Tier 1 models require sign-off from the Model Risk Committee before deployment.
Tier 2 and Tier 3 models require sign-off from the Head of Model Risk.

## 5. Annual Revalidation

All Tier 1 and Tier 2 models are subject to a formal revalidation exercise on an
**annual basis**, repeating the initial validation steps in Section 3 against
current data and current model performance.

## 6. Model Performance Monitoring

Business units are responsible for monitoring the ongoing performance of models
under their ownership against the metrics agreed at validation, and escalating
material performance degradation to the Model Risk Function outside of the
scheduled annual revalidation cycle.

## 7. Documentation

Validation reports, revalidation reports, and any escalations are retained in the
Model Risk Register for a minimum of seven years.

---
*This is a synthetic policy document created for proof-of-concept purposes only.
Acme Bank is a fictional entity. Any resemblance to a real institution's actual
policy is coincidental.*
