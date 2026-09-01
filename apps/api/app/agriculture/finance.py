from __future__ import annotations

from math import isfinite

from app.domain.models import (
    CashFlowYear,
    InvestigationState,
    InvestmentDecision,
    Materiality,
    RiskTolerance,
    Verdict,
)


def _annual_payment(principal: float, rate: float, term: int) -> float:
    if principal <= 0:
        return 0
    if rate == 0:
        return principal / term
    factor = (1 + rate) ** term
    return principal * rate * factor / (factor - 1)


def _remaining_balance(principal: float, rate: float, payment: float, years: int) -> float:
    balance = principal
    for _ in range(years):
        interest = balance * rate
        balance = max(0, balance + interest - payment)
    return balance


def _npv(rate: float, cash_flows: list[float]) -> float:
    return sum(value / ((1 + rate) ** index) for index, value in enumerate(cash_flows))


def _irr(cash_flows: list[float]) -> float | None:
    if (
        not cash_flows
        or not any(value < 0 for value in cash_flows)
        or not any(value > 0 for value in cash_flows)
    ):
        return None
    low, high = -0.99, 10.0
    low_value, high_value = _npv(low, cash_flows), _npv(high, cash_flows)
    if low_value * high_value > 0:
        return None
    for _ in range(120):
        middle = (low + high) / 2
        value = _npv(middle, cash_flows)
        if abs(value) < 0.01:
            return middle
        if value * low_value > 0:
            low, low_value = middle, value
        else:
            high = middle
    return (low + high) / 2


class InvestmentEconomicsEngine:
    """Adds financing-aware, multi-year cash flows to sourced operating scenarios."""

    def enrich(self, state: InvestigationState) -> None:
        if not state.economic_scenarios or not state.listing or not state.listing.asking_price:
            state.investment_decision = self._insufficient(state)
            return
        asking_price = float(state.listing.asking_price)
        inputs = state.financial_inputs
        horizon = state.user_objective.time_horizon_years or inputs.time_horizon_years
        loan = asking_price * (1 - inputs.down_payment_percent)
        equity = asking_price - loan
        closing = asking_price * inputs.closing_cost_percent
        initial_cash = equity + closing + inputs.initial_capex + inputs.working_capital
        payment = _annual_payment(loan, inputs.interest_rate, inputs.loan_term_years)
        high_hazard_stress = max(
            (
                item.annual_profit_stress
                for item in state.hazard_assessments
                if item.materiality == Materiality.HIGH
            ),
            default=0,
        )
        for scenario in state.economic_scenarios:
            if scenario.annual_revenue is None or scenario.annual_operating_cost is None:
                continue
            revenue = float(scenario.annual_revenue)
            operating = float(scenario.annual_operating_cost)
            stress = high_hazard_stress if scenario.name == "conservative" else 0
            stressed_revenue = revenue * (1 - stress)
            annual_fixed = (
                inputs.annual_property_tax
                + inputs.annual_insurance
                + inputs.annual_owner_labor
                + inputs.annual_replacement_capex
            )
            annual_noi = stressed_revenue - operating - annual_fixed
            flows = [
                CashFlowYear(
                    year=0,
                    capital_cost=initial_cash,
                    net_cash_flow=-initial_cash,
                )
            ]
            values = [-initial_cash]
            for year in range(1, horizon + 1):
                debt_service = payment if year <= inputs.loan_term_years else 0
                net = annual_noi - debt_service
                if year == horizon:
                    residual = (
                        inputs.residual_value
                        if inputs.residual_value is not None
                        else asking_price * ((1 + inputs.annual_land_appreciation) ** horizon)
                    )
                    residual -= _remaining_balance(
                        loan, inputs.interest_rate, payment, min(horizon, inputs.loan_term_years)
                    )
                    net += residual
                flows.append(
                    CashFlowYear(
                        year=year,
                        revenue=round(stressed_revenue, 2),
                        operating_cost=round(operating + annual_fixed, 2),
                        debt_service=round(debt_service, 2),
                        capital_cost=round(inputs.annual_replacement_capex, 2),
                        net_cash_flow=round(net, 2),
                    )
                )
                values.append(net)
            scenario.cash_flows = flows
            scenario.cash_on_cash_return = (
                round(annual_noi - payment, 2) / initial_cash if initial_cash else None
            )
            scenario.npv = round(_npv(inputs.discount_rate, values), 2)
            scenario.irr = _irr(values)
            scenario.debt_service_coverage_ratio = annual_noi / payment if payment else None
            scenario.total_investment = round(
                asking_price + closing + inputs.initial_capex + inputs.working_capital, 2
            )
            scenario.annual_operating_profit = round(annual_noi, 2)
            scenario.roi = (
                annual_noi / scenario.total_investment if scenario.total_investment else None
            )
            scenario.key_sensitivities = list(
                dict.fromkeys(
                    [
                        *scenario.key_sensitivities,
                        "purchase price",
                        "financing cost",
                        "initial capital",
                        "hazard-adjusted production",
                    ]
                )
            )
            scenario.limitations = list(
                dict.fromkeys(
                    [
                        *scenario.limitations,
                        "Land appreciation is separated from annual operating performance.",
                        "Tax treatment and income taxes require professional review.",
                    ]
                )
            )
        state.investment_decision = self.decide(state)

    def decide(self, state: InvestigationState) -> InvestmentDecision:
        scenarios = {item.name: item for item in state.economic_scenarios}
        base = scenarios.get("base")
        downside = scenarios.get("conservative")
        if not base or base.roi is None:
            return self._insufficient(state)
        target = state.user_objective.return_target or 0.08
        high_unknowns = [
            item.question for item in state.unknowns if item.materiality == Materiality.HIGH
        ]
        severe_hazards = [
            item for item in state.hazard_assessments if item.materiality == Materiality.HIGH
        ]
        maximum_offer = base.break_even_acquisition_price
        if maximum_offer is None and base.annual_operating_profit and target > 0:
            non_purchase = (
                state.financial_inputs.initial_capex + state.financial_inputs.working_capital
            )
            maximum_offer = max(0, base.annual_operating_profit / target - non_purchase)
        asking = state.listing.asking_price if state.listing else None
        rationale: list[str] = []
        if base.npv is not None:
            rationale.append(
                f"Base-case NPV is ${base.npv:,.0f} at a {state.financial_inputs.discount_rate:.1%} discount rate."
            )
        rationale.append(f"Base operating ROI is {base.roi:.1%} versus a {target:.1%} target.")
        if downside and downside.roi is not None:
            rationale.append(f"Conservative operating ROI is {downside.roi:.1%}.")
        if severe_hazards:
            rationale.append(
                f"{len(severe_hazards)} high-materiality hazard assessment(s) require mitigation or pricing protection."
            )
        if (
            downside
            and downside.annual_operating_profit is not None
            and downside.annual_operating_profit < 0
        ):
            verdict, label = Verdict.DO_NOT_ACQUIRE, "Pass"
        elif maximum_offer is not None and asking is not None and asking > maximum_offer:
            verdict, label = Verdict.NEGOTIATE, "Negotiate"
            rationale.append(
                f"The ${asking:,.0f} asking price exceeds the approximately ${maximum_offer:,.0f} defensible offer."
            )
        elif high_unknowns or severe_hazards:
            verdict, label = Verdict.ACQUIRE_CONDITIONALLY, "Investigate"
        elif base.roi >= target and (base.npv is None or base.npv >= 0):
            if (
                state.user_objective.risk_tolerance == RiskTolerance.LOW
                and downside
                and (downside.roi or -1) < target
            ):
                verdict, label = Verdict.ACQUIRE_CONDITIONALLY, "Investigate"
            else:
                verdict, label = Verdict.ACQUIRE, "Buy"
        else:
            verdict, label = Verdict.DO_NOT_ACQUIRE, "Pass"
        confidence_values = [item.confidence for item in state.economic_scenarios]
        confidence = min(confidence_values) if confidence_values else 0
        return InvestmentDecision(
            verdict=verdict,
            label=label,
            rationale=rationale,
            maximum_defensible_offer=(
                round(maximum_offer, -2) if maximum_offer is not None else None
            ),
            base_case_roi=base.roi,
            base_case_npv=base.npv,
            base_case_irr=base.irr if base.irr is None or isfinite(base.irr) else None,
            downside_roi=downside.roi if downside else None,
            evidence_confidence=confidence,
            material_unknowns=high_unknowns,
            limitations=[
                "This is decision support, not a guarantee, appraisal, tax opinion, or lending commitment."
            ],
        )

    @staticmethod
    def _insufficient(state: InvestigationState) -> InvestmentDecision:
        missing = [
            "Sourced yield/production, price, and operating-cost evidence is required.",
            *[item.question for item in state.unknowns if item.materiality == Materiality.HIGH],
        ]
        return InvestmentDecision(
            verdict=Verdict.INSUFFICIENT_EVIDENCE,
            label="Insufficient evidence",
            rationale=["A defensible multi-year investment model could not be calculated."],
            material_unknowns=list(dict.fromkeys(missing)),
            limitations=["No acquisition recommendation was inferred from missing economics."],
        )
