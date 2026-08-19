from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from app.agents.runtime import AgentRuntime
from app.config import get_settings
from app.connectors.agriculture import AgricultureAdapter
from app.connectors.market import MarketAdapter
from app.connectors.mireye import MireyeMCPAdapter
from app.domain.models import (
    AgentRunArtifact,
    ClaimState,
    ClaimTransitionProposal,
    Decision,
    DiligenceRequest,
    EvidenceRelationship,
    InvestigationEvent,
    InvestigationState,
    InvestigationStatus,
    Materiality,
    NegotiationRecommendation,
    ToolCallArtifact,
    ToolResult,
    Unknown,
    Verdict,
    utcnow,
)
from app.enrichment.engine import EnrichmentEngine
from app.investigation.engines import (
    ContradictionEngine,
    DecisionStabilityEngine,
    MaterialityEngine,
    UnknownEngine,
    ValuationEngine,
    ValueOfInformationEngine,
)
from app.investigation.input_resolver import InputResolver
from app.tools.registry import validate_tool_call
from app.world_model.repository import repository
from app.world_model.transitions import apply_claim_transition


class InvestigationOrchestrator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.resolver = InputResolver()
        self.agent = AgentRuntime()
        self.mireye = MireyeMCPAdapter()
        self.agriculture = AgricultureAdapter()
        self.market = MarketAdapter()
        self.enrichment = EnrichmentEngine()
        self.contradictions = ContradictionEngine()
        self.materiality = MaterialityEngine()
        self.voi = ValueOfInformationEngine()
        self.valuation = ValuationEngine()
        self.unknown_engine = UnknownEngine()
        self.stability = DecisionStabilityEngine()

    def event(self, state: InvestigationState, event_type: str, message: str, **data) -> None:
        state.events.append(InvestigationEvent(type=event_type, message=message, data=data))
        repository.save(state)

    async def _execute(self, state: InvestigationState, name: str) -> ToolResult:
        prop = state.property
        if not prop or prop.latitude is None or prop.longitude is None:
            raise ValueError("A resolved coordinate is required")
        if name == "agriculture.get_crop_history":
            current = datetime.now(UTC).year
            years = list(range(current - 5, current))
            arguments = {"latitude": prop.latitude, "longitude": prop.longitude, "years": years}
        else:
            arguments = {"latitude": prop.latitude, "longitude": prop.longitude}
        validate_tool_call(name, arguments)
        if name == "mireye.fetch_context":
            return await self.mireye.fetch_context(prop.latitude, prop.longitude)
        if name == "agriculture.get_crop_history":
            return await self.agriculture.get_crop_history(prop.latitude, prop.longitude, years)
        if name == "agriculture.get_soil_context":
            return await self.agriculture.get_soil_context(prop.latitude, prop.longitude)
        if name == "market.get_benchmark":
            return await self.market.get_benchmark(prop.state, prop.county)
        if name == "market.find_comparables":
            return await self.market.find_comparables(prop.state, prop.county, prop.acreage)
        raise ValueError(f"Unsupported tool: {name}")

    def _analyze(self, state: InvestigationState) -> None:
        state.signals = self.enrichment.derive(state)
        state.contradictions = self.contradictions.detect(state)
        for item in state.contradictions:
            self.materiality.assess(state, item)
            claim = next((claim for claim in state.claims if claim.id == item.claim_id), None)
            if claim and claim.state in {ClaimState.LOW_CONFIDENCE, ClaimState.UNDER_INVESTIGATION}:
                try:
                    apply_claim_transition(
                        state,
                        ClaimTransitionProposal(
                            claim_id=claim.id,
                            target_state=ClaimState.CONTRADICTED,
                            evidence_ids=item.evidence_ids,
                            confidence=0.75,
                            rationale="Compatible independent evidence materially diverges from the claim.",
                        ),
                    )
                except ValueError:
                    pass
        contradicted_claim_ids = {item.claim_id for item in state.contradictions}
        footprints = [
            item
            for item in state.evidence
            if item.field_name == "cultivated_acres"
            and isinstance(item.value, (int, float))
            and item.semantic_scope == "property cultivated footprint"
            and item.geometry
            and item.geometry.get("type") in {"Polygon", "MultiPolygon"}
        ]
        for claim in state.claims:
            if (
                claim.claim_type != "tillable_acres"
                or claim.id in contradicted_claim_ids
                or claim.state not in {ClaimState.LOW_CONFIDENCE, ClaimState.UNDER_INVESTIGATION}
            ):
                continue
            from app.investigation.engines import claimed_tillable_acres

            claimed = claimed_tillable_acres(claim)
            supporting = next(
                (
                    item
                    for item in footprints
                    if claimed is not None
                    and abs(float(item.value) - claimed) <= max(2.0, claimed * 0.05)
                ),
                None,
            )
            if supporting:
                apply_claim_transition(
                    state,
                    ClaimTransitionProposal(
                        claim_id=claim.id,
                        target_state=ClaimState.PARTIALLY_SUPPORTED,
                        evidence_ids=[supporting.id],
                        confidence=min(0.8, supporting.confidence),
                        rationale=(
                            "Compatible property-scope physical evidence is within the acreage "
                            "tolerance, but does not establish legal tillability."
                        ),
                    ),
                )
        state.unknowns = self.unknown_engine.identify(state)
        state.valuation = self.valuation.calculate(state)
        state.decision_stability = self.stability.evaluate(state)
        relationships: list[EvidenceRelationship] = []
        for signal in state.signals:
            relationships.extend(
                EvidenceRelationship(
                    source_id=evidence_id, target_id=signal.id, relationship="DERIVED_FROM"
                )
                for evidence_id in signal.evidence_ids
            )
        for contradiction in state.contradictions:
            relationships.append(
                EvidenceRelationship(
                    source_id=contradiction.claim_id,
                    target_id=contradiction.id,
                    relationship="AFFECTS",
                )
            )
            relationships.extend(
                EvidenceRelationship(
                    source_id=evidence_id, target_id=contradiction.id, relationship="CONTRADICTS"
                )
                for evidence_id in contradiction.evidence_ids
            )
        state.relationships = relationships

    def _mark_relevant_claims_under_investigation(
        self, state: InvestigationState, tool_name: str
    ) -> None:
        relevant_types = {
            "mireye.fetch_context": {"irrigation", "flood", "access"},
            "agriculture.get_crop_history": {"tillable_acres"},
            "agriculture.get_soil_context": {"drainage", "soil_quality"},
        }.get(tool_name, set())
        evidence_lookup = {str(item.id): item.id for item in state.evidence}
        for claim in state.claims:
            if claim.claim_type not in relevant_types or claim.state != ClaimState.LOW_CONFIDENCE:
                continue
            source_evidence = evidence_lookup.get(claim.source_id)
            if not source_evidence:
                continue
            apply_claim_transition(
                state,
                ClaimTransitionProposal(
                    claim_id=claim.id,
                    target_state=ClaimState.UNDER_INVESTIGATION,
                    evidence_ids=[source_evidence],
                    confidence=claim.extraction_confidence,
                    rationale=f"Selected {tool_name} to investigate this material claim.",
                ),
            )

    async def _run_selected_tool(
        self,
        state: InvestigationState,
        name: str,
        rationale: str,
        orchestrator_run: AgentRunArtifact,
        voi: float | None = None,
    ) -> ToolResult:
        self._mark_relevant_claims_under_investigation(state, name)
        self.event(
            state,
            "investigation.selected",
            f"Selected {name}: {rationale}",
            **({"voi": voi} if voi is not None else {}),
        )
        self.event(state, "tool.started", f"Running {name}")
        call_started = asyncio.get_running_loop().time()
        call = ToolCallArtifact(
            agent_run_id=orchestrator_run.id,
            tool_name=name,
            status="running",
        )
        state.tool_calls.append(call)
        result = await self._execute(state, name)
        call.completed_at = utcnow()
        call.latency_ms = int((asyncio.get_running_loop().time() - call_started) * 1000)
        call.status = "completed" if result.success else "unavailable"
        call.cost = result.cost
        call.evidence_ids = [item.id for item in result.observations]
        call.limitations = result.limitations
        state.evidence.extend(result.observations)
        state.limitations.extend(result.limitations)
        self.event(
            state,
            "tool.completed",
            f"{name} {'completed' if result.success else 'was unavailable'}",
            success=result.success,
        )
        if result.observations:
            self.event(
                state,
                "evidence.added",
                f"Added {len(result.observations)} evidence item(s)",
                evidence_ids=[str(item.id) for item in result.observations],
            )
        self._analyze(state)
        specialist_name = {
            "mireye.fetch_context": "property_intelligence",
            "agriculture.get_crop_history": "agricultural_intelligence",
            "agriculture.get_soil_context": "agricultural_intelligence",
            "market.get_benchmark": "market_valuation",
            "market.find_comparables": "market_valuation",
        }[name]
        assessment = await self.agent.assess(state, specialist_name)
        if assessment:
            state.agent_assessments.append(assessment)
            state.agent_runs.append(
                AgentRunArtifact(
                    agent_name=specialist_name,
                    status="completed",
                    completed_at=utcnow(),
                    output_summary=assessment.assessment,
                )
            )
            self.event(
                state,
                "agent.completed",
                f"{specialist_name.replace('_', ' ').title()} reviewed new evidence",
            )
        if state.contradictions:
            self.event(
                state,
                "contradiction.detected",
                f"Detected {len(state.contradictions)} evidence discrepancy or contradiction candidate(s)",
            )
        repository.save(state)
        return result

    def _synthesize(self, state: InvestigationState, critic: dict) -> None:
        valuation = state.valuation
        high_contradictions = [
            item for item in state.contradictions if item.materiality == Materiality.HIGH
        ]
        unresolved = list(
            dict.fromkeys(
                state.limitations
                + [item.question for item in state.unknowns if item.materiality == Materiality.HIGH]
            )
        )
        high_unknowns = [item for item in state.unknowns if item.materiality == Materiality.HIGH]
        buyer_mismatches: list[str] = []
        buyer = state.buyer_snapshot
        prop = state.property
        asking = valuation.asking_price if valuation else None
        if buyer:
            if buyer.budget_max is not None and asking is not None and asking > buyer.budget_max:
                buyer_mismatches.append("Asking price exceeds the buyer's maximum budget.")
            if prop and prop.acreage is not None:
                if buyer.minimum_acres is not None and prop.acreage < buyer.minimum_acres:
                    buyer_mismatches.append("Property acreage is below the buyer's minimum.")
                if buyer.maximum_acres is not None and prop.acreage > buyer.maximum_acres:
                    buyer_mismatches.append("Property acreage exceeds the buyer's maximum.")
            if buyer.target_states and prop and prop.state:
                targets = {item.casefold() for item in buyer.target_states}
                if prop.state.casefold() not in targets:
                    buyer_mismatches.append(
                        "Property state is outside the buyer's target geography."
                    )
        if valuation and valuation.high is not None and valuation.asking_price is not None:
            supported = (
                valuation.asking_price <= valuation.high
                and not high_contradictions
                and not high_unknowns
                and not buyer_mismatches
            )
            verdict = Verdict.ACQUIRE if supported else Verdict.DO_NOT_ACQUIRE
            qualification = (
                "Proceed with conditions"
                if supported
                else "Current price, buyer fit, or material uncertainty is not supported"
            )
            summary = (
                "The asking price falls within the evidence-backed indication and no unresolved high-materiality contradiction was detected."
                if supported
                else "The current asking price, buyer fit, or a material unresolved issue is not supported by the available evidence."
            )
            confidence = min(
                valuation.confidence,
                0.85 if state.decision_stability and state.decision_stability.stable else 0.65,
            )
        else:
            verdict = Verdict.DO_NOT_ACQUIRE
            qualification = "Material uncertainty is unresolved"
            summary = "The available evidence cannot yet bound a defensible value, so acquisition is not supported at this time."
            confidence = 0.55 if state.evidence else 0.3
        reasons = [summary, *buyer_mismatches]
        if critic.get("strongest_counterargument"):
            reasons.append(f"Critic: {critic['strongest_counterargument']}")
        state.decision = Decision(
            verdict=verdict,
            qualification=qualification,
            confidence=confidence,
            decision_summary=summary,
            critical_reasons=reasons,
            conditions=["Verify all P0 diligence items before closing"]
            if verdict == Verdict.ACQUIRE
            else [],
            unresolved_uncertainties=unresolved[:12],
        )
        requests: list[DiligenceRequest] = []
        for claim in state.claims:
            if claim.claim_type == "tillable_acres":
                requests.append(
                    DiligenceRequest(
                        priority="P0",
                        request="Obtain surveyed/tax documentation and field records supporting tillable acreage.",
                        reason="Tillable acreage directly affects productive-acre valuation.",
                    )
                )
            elif claim.claim_type == "drainage":
                requests.append(
                    DiligenceRequest(
                        priority="P0",
                        request="Obtain drainage maps, maintenance records, and field verification.",
                        reason="The listing's drainage claim is not a legal or engineering determination.",
                    )
                )
            elif claim.claim_type == "irrigation":
                requests.append(
                    DiligenceRequest(
                        priority="P0",
                        request="Verify irrigation equipment, permits, capacity, and transferable rights with authoritative records.",
                        reason="Physical indicators do not establish legal water rights.",
                    )
                )
        if not requests:
            requests.append(
                DiligenceRequest(
                    priority="P1",
                    request="Verify acreage, title, access, soils, drainage, flood history, and agricultural records.",
                    reason="Core transaction facts require authoritative diligence.",
                )
            )
        state.diligence = requests
        state.negotiation = [
            NegotiationRecommendation(
                action="Condition price and closing on P0 evidence verification.",
                rationale="Unverified productive acreage and operating conditions can materially affect value.",
            )
        ]

    async def run(self, investigation_id) -> None:
        state = repository.get(investigation_id)
        if not state:
            return
        started = asyncio.get_running_loop().time()
        try:
            state.status = InvestigationStatus.RUNNING
            orchestrator_run = AgentRunArtifact(
                agent_name="acquisition_orchestrator", status="running"
            )
            state.agent_runs.append(orchestrator_run)
            self.event(state, "investigation.started", "Investigation started")
            await self.resolver.resolve(state)
            evidence_lookup = {str(item.id): item.id for item in state.evidence}
            for claim in state.claims:
                source_evidence = evidence_lookup.get(claim.source_id)
                if source_evidence:
                    apply_claim_transition(
                        state,
                        ClaimTransitionProposal(
                            claim_id=claim.id,
                            target_state=ClaimState.LOW_CONFIDENCE,
                            evidence_ids=[source_evidence],
                            confidence=claim.extraction_confidence,
                            rationale="The claim was extracted from an unverified user or listing source.",
                        ),
                    )
                claim.materiality = (
                    Materiality.HIGH
                    if claim.claim_type in {"tillable_acres", "irrigation", "flood"}
                    else Materiality.MEDIUM
                )
            self.event(
                state,
                "property.resolved",
                "Property input normalized",
                resolved=bool(state.property and state.property.latitude is not None),
            )
            self.event(
                state,
                "claims.extracted",
                f"Extracted {len(state.claims)} material seller or user claims",
            )
            if (
                not state.property
                or state.property.latitude is None
                or state.property.longitude is None
            ):
                state.status = InvestigationStatus.NEEDS_INPUT
                state.unknowns.append(
                    Unknown(
                        question="What is the property's resolvable address or coordinate?",
                        materiality=Materiality.HIGH,
                        candidate_tools=[],
                    )
                )
                self._analyze(state)
                critic = await self.agent.critique(state)
                self._synthesize(state, critic)
                self.event(
                    state,
                    "investigation.needs_input",
                    "A property-level location is required before evidence collection can continue",
                )
                return

            available = [
                "mireye.fetch_context",
                "agriculture.get_crop_history",
                "agriculture.get_soil_context",
                "market.get_benchmark",
                "market.find_comparables",
            ]
            completed: set[str] = set()
            turns = 0
            while (
                available
                and turns < self.settings.max_agent_turns
                and len(state.tool_calls) < self.settings.max_tool_calls
                and len(state.tool_calls) < self.settings.max_external_requests
            ):
                if (
                    asyncio.get_running_loop().time() - started
                    > self.settings.max_wall_clock_seconds
                ):
                    state.limitations.append(
                        "Investigation stopped at the wall-clock safety limit."
                    )
                    break
                candidates = await self.agent.propose_investigations(state, available)
                ranked = self.voi.rank(candidates)
                if not ranked or ranked[0].value <= 0:
                    break
                selected = ranked[0]
                available.remove(selected.name)
                turns += 1
                await self._run_selected_tool(
                    state,
                    selected.name,
                    selected.rationale,
                    orchestrator_run,
                    selected.value,
                )
                completed.add(selected.name)

                if (
                    state.decision_stability
                    and state.decision_stability.stable
                    and not any(item.materiality == Materiality.HIGH for item in state.unknowns)
                ):
                    self.event(
                        state,
                        "investigation.stopping",
                        "Stopped evidence collection because the verdict is stable and no high-materiality unknown remains",
                    )
                    break

            self._analyze(state)
            self.event(
                state,
                "valuation.updated",
                "Valuation updated from traceable evidence",
                available=bool(state.valuation and state.valuation.estimated_value_total),
            )
            critic = await self.agent.critique(state)
            recommended = critic.get("recommended_tool")
            if (
                critic.get("requires_investigation")
                and isinstance(recommended, str)
                and recommended in available
                and len(state.tool_calls)
                < min(self.settings.max_tool_calls, self.settings.max_external_requests)
            ):
                available.remove(recommended)
                await self._run_selected_tool(
                    state,
                    recommended,
                    "The evidence critic identified this as the strongest remaining test.",
                    orchestrator_run,
                )
                completed.add(recommended)
                critic = await self.agent.critique(state)
            state.agent_runs.append(
                AgentRunArtifact(
                    agent_name="evidence_critic",
                    status="completed",
                    completed_at=utcnow(),
                    output_summary=str(critic.get("assessment", "")),
                )
            )
            self.event(
                state,
                "agent.completed",
                "Evidence critic reviewed the current thesis",
                assessment=critic.get("assessment"),
            )
            self._synthesize(state, critic)
            strategy_assessment = await self.agent.assess(state, "strategy")
            if strategy_assessment:
                state.agent_assessments.append(strategy_assessment)
                state.agent_runs.append(
                    AgentRunArtifact(
                        agent_name="strategy",
                        status="completed",
                        completed_at=utcnow(),
                        output_summary=strategy_assessment.assessment,
                    )
                )
            if state.decision is None:
                raise RuntimeError("Decision synthesis did not produce a decision")
            self.event(state, "decision.updated", f"Decision: {state.decision.verdict}")
            self.event(
                state, "strategy.generated", "Due diligence and negotiation strategy generated"
            )
            state.status = InvestigationStatus.COMPLETED
            orchestrator_run.status = "completed"
            orchestrator_run.completed_at = utcnow()
            orchestrator_run.output_summary = state.decision.decision_summary
            self.event(state, "investigation.completed", "Investigation completed")
        except Exception as exc:
            state.status = InvestigationStatus.FAILED
            if "orchestrator_run" in locals():
                orchestrator_run.status = "failed"
                orchestrator_run.completed_at = utcnow()
                orchestrator_run.error = f"{type(exc).__name__}: {exc}"
            state.limitations.append(f"Investigation failed safely: {type(exc).__name__}: {exc}")
            self.event(
                state,
                "investigation.failed",
                "Investigation stopped because an internal error occurred",
            )


orchestrator = InvestigationOrchestrator()
