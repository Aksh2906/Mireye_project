from __future__ import annotations

from math import isfinite
from typing import ClassVar

from app.connectors.agriculture import is_agricultural_category
from app.domain.models import (
    ActivityCategory,
    ActivityRequirement,
    AgriculturalActivity,
    AgriculturalActivityOpportunity,
    CropOpportunity,
    EconomicAssumption,
    EconomicScenario,
    HazardAssessment,
    InvestigationState,
    Materiality,
    SourceType,
)

CROP_REGISTRY = ("corn", "soybeans", "wheat", "hay", "alfalfa", "sorghum", "cotton", "rice")
ACTIVITY_REGISTRY = (
    AgriculturalActivity(
        id="row_crop",
        category=ActivityCategory.ROW_CROP,
        requirements=[
            ActivityRequirement(
                name="plantable_area", description="Usable field area and machinery access"
            )
        ],
        economics_model="per-acre crop scenario",
        risk_model="yield, price, water, and hazard sensitivity",
    ),
    AgriculturalActivity(
        id="grazing",
        category=ActivityCategory.GRAZING,
        requirements=[
            ActivityRequirement(
                name="forage_water", description="Forage continuity, water, fencing, and access"
            )
        ],
        economics_model="per-head or lease scenario",
        risk_model="carrying capacity, drought, and access",
    ),
    AgriculturalActivity(
        id="cattle",
        category=ActivityCategory.CATTLE,
        requirements=[
            ActivityRequirement(
                name="livestock_infrastructure",
                description="Water, fencing, handling, shelter, and access",
            )
        ],
        economics_model="herd scenario",
        risk_model="forage, health, market, and hazard exposure",
    ),
    AgriculturalActivity(
        id="dairy",
        category=ActivityCategory.DAIRY,
        requirements=[
            ActivityRequirement(
                name="dairy_infrastructure",
                description="High-capacity water, utilities, waste handling, housing, and access",
                materiality=Materiality.HIGH,
            )
        ],
        economics_model="milk production scenario",
        risk_model="capital, feed, water, utility, and milk-price exposure",
    ),
    AgriculturalActivity(
        id="hay",
        category=ActivityCategory.HAY,
        requirements=[
            ActivityRequirement(
                name="hay_area", description="Harvestable area, storage, and machinery access"
            )
        ],
        economics_model="per-acre hay scenario",
        risk_model="yield, weather, and price sensitivity",
    ),
    AgriculturalActivity(
        id="sheep",
        category=ActivityCategory.SHEEP,
        requirements=[
            ActivityRequirement(
                name="small_ruminant_infrastructure",
                description="Secure fencing, water, shelter, forage, handling, and predator controls",
            )
        ],
        economics_model="flock scenario",
        risk_model="forage, health, predation, labor, and market access",
    ),
    AgriculturalActivity(
        id="goat",
        category=ActivityCategory.GOAT,
        requirements=[
            ActivityRequirement(
                name="goat_infrastructure",
                description="Secure fencing, browse, water, shelter, handling, and market access",
            )
        ],
        economics_model="herd scenario",
        risk_model="browse, fencing, health, labor, and market access",
    ),
    AgriculturalActivity(
        id="orchard",
        category=ActivityCategory.ORCHARD,
        requirements=[
            ActivityRequirement(
                name="perennial_crop_system",
                description="Climate fit, irrigation, establishment capital, labor, and market access",
                materiality=Materiality.HIGH,
            )
        ],
        economics_model="multi-year bearing ramp",
        risk_model="frost, water, pests, labor, and delayed production",
    ),
    AgriculturalActivity(
        id="greenhouse",
        category=ActivityCategory.GREENHOUSE,
        requirements=[
            ActivityRequirement(
                name="controlled_environment",
                description="Power, water, structures, climate control, labor, and market access",
                materiality=Materiality.HIGH,
            )
        ],
        economics_model="controlled-environment production scenario",
        risk_model="capital, energy, water, labor, and market concentration",
    ),
    AgriculturalActivity(
        id="solar",
        category=ActivityCategory.SOLAR,
        requirements=[
            ActivityRequirement(
                name="solar_site",
                description="Solar resource, usable area, slope, grid proximity, access, zoning, and interconnection capacity",
                materiality=Materiality.HIGH,
            )
        ],
        economics_model="site-screening only until lease/PPA, capex, and interconnection terms are supplied",
        risk_model="interconnection, permitting, land-use conflict, offtake, and construction risk",
    ),
    AgriculturalActivity(
        id="wind",
        category=ActivityCategory.WIND,
        requirements=[
            ActivityRequirement(
                name="wind_site",
                description="Wind resource, setbacks, access, grid proximity, aviation constraints, zoning, and interconnection capacity",
                materiality=Materiality.HIGH,
            )
        ],
        economics_model="site-screening only until lease/PPA, capex, and interconnection terms are supplied",
        risk_model="resource, setback, aviation, permitting, interconnection, and offtake risk",
    ),
    AgriculturalActivity(
        id="mixed",
        category=ActivityCategory.MIXED,
        requirements=[
            ActivityRequirement(
                name="mixed_use_plan",
                description="Compatible land allocation, shared infrastructure, labor, and market plan",
            )
        ],
        economics_model="portfolio of supported activity scenarios",
        risk_model="operational complexity and correlated production risks",
    ),
)


def _number(state: InvestigationState, names: set[str], activity: str | None = None):
    candidates = []
    for item in state.evidence:
        if item.field_name not in names or not isinstance(item.value, (int, float)):
            continue
        tagged = str(item.raw_reference.get("activity", "")).casefold()
        if activity and tagged and tagged not in {activity.casefold(), "all"}:
            continue
        candidates.append(item)
    return max(candidates, key=lambda item: item.confidence) if candidates else None


class ScenarioEconomicsEngine:
    """Runs math only when sourced yield, price, and cost assumptions exist."""

    def calculate(self, state: InvestigationState, activity: str) -> list[EconomicScenario]:
        acres = state.property.acreage if state.property else None
        price = state.listing.asking_price if state.listing else None
        quantity_item = _number(state, {"productive_units", "herd_size"}, activity)
        production_units = float(quantity_item.value) if quantity_item else acres
        yield_item = _number(
            state,
            {"yield_per_acre", "expected_yield", "production_per_unit", "milk_yield_per_head"},
            activity,
        )
        commodity_item = _number(state, {"commodity_price", "price_per_unit"}, activity)
        cost_item = _number(
            state,
            {"operating_cost_per_acre", "operating_cost_per_unit", "operating_cost_per_head"},
            activity,
        )
        if (
            not production_units
            or not price
            or not yield_item
            or not commodity_item
            or not cost_item
        ):
            return []
        infrastructure_item = _number(
            state, {"initial_infrastructure_cost", "required_improvement_cost"}, activity
        )
        transaction_item = _number(state, {"transaction_cost"}, activity)
        infrastructure = float(infrastructure_item.value) if infrastructure_item else 0
        transaction_cost = float(transaction_item.value) if transaction_item else 0
        total_investment = price + infrastructure + transaction_cost
        scenarios: list[EconomicScenario] = []
        for name, factor in (("conservative", 0.8), ("base", 1.0), ("optimistic", 1.2)):
            annual_revenue = (
                production_units * float(yield_item.value) * float(commodity_item.value) * factor
            )
            annual_cost = (
                production_units
                * float(cost_item.value)
                * (1.1 if name == "conservative" else 0.95 if name == "optimistic" else 1)
            )
            profit = annual_revenue - annual_cost
            roi = profit / total_investment if total_investment else None
            payback = total_investment / profit if profit > 0 else None
            break_even_yield = annual_cost / (production_units * float(commodity_item.value))
            scenario_yield = float(yield_item.value) * factor
            break_even_price = annual_cost / (production_units * scenario_yield)
            break_even_acquisition = None
            if state.user_objective.return_target and state.user_objective.return_target > 0:
                break_even_acquisition = (
                    profit / state.user_objective.return_target - infrastructure - transaction_cost
                )
            elif state.user_objective.payback_target_years:
                break_even_acquisition = (
                    profit * state.user_objective.payback_target_years
                    - infrastructure
                    - transaction_cost
                )
            assumptions = [
                EconomicAssumption(
                    name="yield",
                    value=float(yield_item.value) * factor,
                    unit=yield_item.unit or "units/acre",
                    source=yield_item.source.dataset,
                    source_date=yield_item.source.vintage,
                    geography=yield_item.semantic_scope,
                    confidence=yield_item.confidence,
                    scenario_classification=name,
                ),
                EconomicAssumption(
                    name="commodity price",
                    value=float(commodity_item.value),
                    unit=commodity_item.unit or "USD/unit",
                    source=commodity_item.source.dataset,
                    source_date=commodity_item.source.vintage,
                    geography=commodity_item.semantic_scope,
                    confidence=commodity_item.confidence,
                    scenario_classification=name,
                ),
                EconomicAssumption(
                    name="operating cost",
                    value=float(cost_item.value),
                    unit=cost_item.unit or "USD/acre",
                    source=cost_item.source.dataset,
                    source_date=cost_item.source.vintage,
                    geography=cost_item.semantic_scope,
                    confidence=cost_item.confidence,
                    scenario_classification=name,
                ),
            ]
            if quantity_item:
                assumptions.append(
                    EconomicAssumption(
                        name="productive units",
                        value=float(quantity_item.value),
                        unit=quantity_item.unit or "head/units",
                        source=quantity_item.source.dataset,
                        source_date=quantity_item.source.vintage,
                        geography=quantity_item.semantic_scope,
                        confidence=quantity_item.confidence,
                        scenario_classification=name,
                    )
                )
            for assumption_name, item, default_unit in (
                ("initial infrastructure", infrastructure_item, "USD"),
                ("transaction cost", transaction_item, "USD"),
            ):
                if item:
                    assumptions.append(
                        EconomicAssumption(
                            name=assumption_name,
                            value=float(item.value),
                            unit=item.unit or default_unit,
                            source=item.source.dataset,
                            source_date=item.source.vintage,
                            geography=item.semantic_scope,
                            confidence=item.confidence,
                            scenario_classification=name,
                        )
                    )
            values = [annual_revenue, annual_cost, profit, total_investment, break_even_yield]
            if not all(isfinite(value) for value in values):
                continue
            scenarios.append(
                EconomicScenario(
                    name=name,
                    activity=activity,
                    annual_revenue=round(annual_revenue, -2),
                    annual_operating_cost=round(annual_cost, -2),
                    annual_operating_profit=round(profit, -2),
                    total_investment=round(total_investment, -2),
                    roi=round(roi, 4) if roi is not None else None,
                    payback_years=round(payback, 1) if payback is not None else None,
                    break_even_yield=round(break_even_yield, 2),
                    break_even_price=round(break_even_price, 2),
                    break_even_acquisition_price=round(break_even_acquisition, -2)
                    if break_even_acquisition is not None
                    else None,
                    key_sensitivities=["commodity price", "yield", "operating cost"],
                    assumptions=assumptions,
                    confidence=min(
                        item.confidence for item in (yield_item, commodity_item, cost_item)
                    ),
                    limitations=[
                        "Scenario ranges are estimates, not guaranteed returns.",
                        "Taxes, financing, and transaction costs are excluded unless supplied.",
                    ],
                )
            )
        return scenarios


class AgricultureOpportunityEngine:
    def __init__(self) -> None:
        self.economics = ScenarioEconomicsEngine()

    @staticmethod
    def _history(state: InvestigationState) -> tuple[list[str], list]:
        items = [item for item in state.evidence if item.source_type == SourceType.USDA_CDL]
        categories = [
            str(item.value.get("category", "")).casefold()
            for item in items
            if isinstance(item.value, dict) and item.value.get("category")
        ]
        return categories, items

    def evaluate(self, state: InvestigationState) -> None:
        categories, history = self._history(state)
        crops: list[CropOpportunity] = []
        for crop in CROP_REGISTRY:
            direct = sum(
                crop in category or (crop == "soybeans" and "soybean" in category)
                for category in categories
            )
            historical = (
                "strong"
                if direct >= 3
                else "moderate"
                if direct
                else "weak"
                if history
                else "unknown"
            )
            physical = "moderate" if history else "unknown"
            scenarios = self.economics.calculate(state, crop)
            confidence = min(0.85, 0.35 + 0.1 * direct) if history else 0
            recommendation = (
                "candidate"
                if scenarios or historical in {"strong", "moderate"}
                else "not_preferred"
                if history
                else "insufficient_evidence"
            )
            crops.append(
                CropOpportunity(
                    crop=crop,
                    physical_fit=physical,
                    historical_support=historical,
                    economic_scenarios=scenarios,
                    infrastructure_needs=[
                        "Verify water supply and activity-specific field infrastructure."
                    ],
                    major_risks=["Yield and commodity price may materially change returns."],
                    evidence_ids=[item.id for item in history],
                    confidence=confidence,
                    recommendation=recommendation,
                )
            )
        state.crop_opportunities = sorted(
            crops,
            key=lambda item: (
                0 if item.economic_scenarios else 1,
                -next(
                    (
                        scenario.roi if scenario.roi is not None else float("-inf")
                        for scenario in item.economic_scenarios
                        if scenario.name == "base"
                    ),
                    float("-inf"),
                ),
                -item.confidence,
            ),
        )
        most_profitable = next(
            (item for item in state.crop_opportunities if item.economic_scenarios), None
        )
        if most_profitable:
            base = next(
                (item for item in most_profitable.economic_scenarios if item.name == "base"), None
            )
            most_profitable.recommendation = (
                "preferred" if base and (base.roi or 0) > 0 else "not_preferred"
            )
        agricultural_years = sum(
            is_agricultural_category(str(item.value.get("category", "")))
            for item in history
            if isinstance(item.value, dict)
        )
        evidence_ids = [item.id for item in history]
        opportunities: list[AgriculturalActivityOpportunity] = []
        for definition in ACTIVITY_REGISTRY:
            activity = definition.category
            scenarios = self.economics.calculate(state, activity.value)
            activity_terms = {
                ActivityCategory.ROW_CROP: {
                    "cdl_",
                    "dominant_crop",
                    "soil_",
                    "slope_",
                    "drainage",
                },
                ActivityCategory.DAIRY: {
                    "water_service",
                    "wastewater",
                    "electric_utility",
                    "major_road",
                    "building_footprint",
                },
                ActivityCategory.CATTLE: {
                    "land_use",
                    "cdl_",
                    "water_service",
                    "tree_canopy",
                    "major_road",
                },
                ActivityCategory.GRAZING: {
                    "land_use",
                    "cdl_",
                    "water_service",
                    "tree_canopy",
                    "major_road",
                },
                ActivityCategory.HAY: {"cdl_", "land_use", "soil_", "slope_", "drainage"},
                ActivityCategory.SHEEP: {
                    "land_use",
                    "cdl_",
                    "water_service",
                    "tree_canopy",
                    "major_road",
                },
                ActivityCategory.GOAT: {
                    "land_use",
                    "cdl_",
                    "water_service",
                    "tree_canopy",
                    "major_road",
                },
                ActivityCategory.ORCHARD: {
                    "soil_",
                    "slope_",
                    "drainage",
                    "water_service",
                    "temperature",
                },
                ActivityCategory.GREENHOUSE: {"greenhouse", "power", "utility", "water"},
                ActivityCategory.SOLAR: {"solar", "ghi_", "pv_", "transmission_line"},
                ActivityCategory.WIND: {"wind_", "airport", "interconnect"},
                ActivityCategory.MIXED: {
                    "land_use",
                    "water_service",
                    "major_road",
                    "utility",
                },
            }.get(activity, set())
            activity_evidence = [
                item
                for item in state.evidence
                if any(term in item.field_name.casefold() for term in activity_terms)
            ]
            fit = (
                "moderate"
                if scenarios
                or activity_evidence
                or (
                    agricultural_years
                    and activity in {ActivityCategory.ROW_CROP, ActivityCategory.HAY}
                )
                else "unknown"
            )
            rationale = (
                [
                    f"Agricultural land-cover classes appear in {agricultural_years} historical observation(s)."
                ]
                if agricultural_years
                else ["Property-scope agricultural history is unavailable."]
            )
            if activity_terms and not activity_evidence:
                rationale.append(
                    "Activity-specific infrastructure and operating evidence is not yet available."
                )
            if activity_evidence:
                readable = ", ".join(
                    item.field_name.replace("_", " ") for item in activity_evidence[:4]
                )
                rationale.append(f"Mireye/provider site evidence available: {readable}.")
            opportunities.append(
                AgriculturalActivityOpportunity(
                    activity=activity,
                    fit=fit,
                    rationale=rationale,
                    economic_scenarios=scenarios,
                    infrastructure_needs=[item.description for item in definition.requirements],
                    risks=["Physical compatibility does not establish economic viability."],
                    evidence_ids=list(
                        dict.fromkeys([*evidence_ids, *(item.id for item in activity_evidence)])
                    ),
                    confidence=(
                        min(0.85, max(item.confidence for item in activity_evidence))
                        if activity_evidence
                        else min(0.75, 0.3 + agricultural_years * 0.08)
                        if history
                        else 0
                    ),
                )
            )
        state.activity_opportunities = opportunities
        state.economic_scenarios = next(
            (
                item.economic_scenarios
                for item in state.crop_opportunities
                if item.economic_scenarios
            ),
            [],
        )


class HazardIntelligenceEngine:
    KEYWORDS: ClassVar[dict[str, tuple[str, ...]]] = {
        "flood": ("flood", "inundation"),
        "wetland": ("wetland",),
        "wildfire": ("wildfire", "fire"),
        "drought": ("drought", "water stress"),
        "heat": ("extreme_heat", "heat"),
        "cold": ("extreme_cold", "freeze"),
        "storm": ("storm", "hail", "tornado", "hurricane"),
        "erosion": ("erosion",),
        "landslide": ("landslide",),
    }
    CONSEQUENCES: ClassVar[dict[str, str]] = {
        "flood": "May reduce usable area, interrupt access, damage facilities, and increase production-loss variability.",
        "wetland": "May constrain usable area, drainage changes, construction, and permitting; a mapped intersection is not a jurisdictional determination.",
        "drought": "May constrain forage or yields, increase feed costs, and increase irrigation dependence.",
        "wildfire": "May threaten forage, livestock, structures, air quality, and operating continuity.",
        "heat": "May reduce crop yield, create livestock heat stress, and increase cooling and water demand.",
        "cold": "May cause freeze injury, livestock stress, and facility or water-system disruption.",
        "storm": "May damage crops and structures and interrupt power, access, harvest, or livestock operations.",
        "erosion": "May reduce productive soil, field accessibility, and long-term yield potential.",
        "landslide": "May affect usable acreage, structures, roads, and safe equipment access.",
    }
    MITIGATIONS: ClassVar[dict[str, list[str]]] = {
        "flood": [
            "Verify flood-zone and insurance status.",
            "Confirm usable acres and all-weather access.",
        ],
        "wetland": [
            "Request a professional wetland delineation before drainage or construction.",
            "Review applicable federal, state, and local permits.",
        ],
        "drought": [
            "Validate water rights and dependable supply.",
            "Stress-test forage, feed, and irrigation costs.",
        ],
        "wildfire": [
            "Review defensible space and emergency access.",
            "Confirm structure and livestock coverage.",
        ],
        "heat": ["Assess shade, ventilation, cooling, and water capacity."],
        "cold": [
            "Assess frost protection, shelter, backup power, and freeze-resistant water systems."
        ],
        "storm": ["Review building standards, backup power, drainage, and crop insurance."],
        "erosion": ["Obtain a conservation plan and verify slope-specific field practices."],
        "landslide": ["Obtain site-specific geotechnical review before siting improvements."],
    }

    @staticmethod
    def _classify_exposure(evidence: list) -> str:
        values = [item.value for item in evidence]
        text = " ".join(str(value).casefold().strip() for value in values)
        if any(word in text for word in ("very high", "severe", "extreme", "high")):
            return "high"
        if "moderate" in text:
            return "moderate"
        if any(value is True for value in values):
            return "present"
        numeric_values = [
            float(value)
            for value in values
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        ]
        if numeric_values and len(numeric_values) == len(values) and max(numeric_values) == 0:
            return "low"
        negative_text = {"false", "none", "no", "low", "minimal", "x", "not mapped"}
        if values and all(
            value is False or str(value).casefold().strip() in negative_text for value in values
        ):
            return "low"
        return "observed"

    def evaluate(self, state: InvestigationState) -> None:
        activities = [item.value for item in state.user_objective.agricultural_activities] or [
            "row_crop",
            "grazing",
        ]
        assessments: list[HazardAssessment] = []
        for hazard, keywords in self.KEYWORDS.items():
            evidence = [
                item
                for item in state.evidence
                if any(word in item.field_name.casefold() for word in keywords)
            ]
            if not evidence:
                continue
            exposure = self._classify_exposure(evidence)
            materiality = (
                Materiality.HIGH
                if exposure == "high"
                else Materiality.LOW
                if exposure == "low"
                else Materiality.MEDIUM
            )
            structured = [item.value for item in evidence if isinstance(item.value, dict)]
            affected_area = next(
                (
                    float(item["affected_area_acres"])
                    for item in structured
                    if isinstance(item.get("affected_area_acres"), (int, float))
                ),
                None,
            )
            most_specific = max(evidence, key=lambda item: item.confidence)
            stress = (
                0.2
                if materiality == Materiality.HIGH
                else 0
                if materiality == Materiality.LOW
                else 0.08
            )
            assessments.append(
                HazardAssessment(
                    hazard=hazard,
                    exposure=exposure,
                    relevant_activities=activities,
                    agricultural_consequences=[self.CONSEQUENCES[hazard]],
                    materiality=materiality,
                    evidence_ids=[item.id for item in evidence],
                    confidence=max(item.confidence for item in evidence),
                    limitations=[
                        "Hazard evidence is contextual and does not prove a hazard is present or absent across the exact parcel."
                    ],
                    source_name=(
                        f"{most_specific.source.publisher} — {most_specific.source.dataset}"
                    ),
                    source_vintage=most_specific.source.vintage,
                    geometry=most_specific.geometry,
                    affected_area_acres=affected_area,
                    mitigation_actions=self.MITIGATIONS.get(hazard, []),
                    annual_profit_stress=stress,
                )
            )
        state.hazard_assessments = assessments
