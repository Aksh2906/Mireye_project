"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type {
  FinancialInputsRecord,
  InvestigationRecord,
} from "@/lib/types";
import { EvidenceCard, humanize } from "./EvidencePresentation";

const MapPanel = dynamic(() => import("./MapPanel"), { ssr: false });
type Resource = "map" | "uses" | "economics" | "hazards" | "alternatives";

const money = (value: number | null | undefined) =>
  value == null ? "Unavailable" : `$${Math.round(value).toLocaleString()}`;
const percent = (value: number | null | undefined) =>
  value == null ? "Unavailable" : `${(value * 100).toFixed(1)}%`;

export default function DecisionIntelligenceView({
  id,
  resource,
}: {
  id: string;
  resource: Resource;
}) {
  const [state, setState] = useState<InvestigationRecord | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [financials, setFinancials] = useState<FinancialInputsRecord | null>(null);
  const [boundaryFileName, setBoundaryFileName] = useState("");
  const [assumptionForm, setAssumptionForm] = useState({
    activity: "corn",
    production_per_unit: 0,
    price_per_unit: 0,
    operating_cost_per_unit: 0,
    productive_units: 0,
    production_unit: "units/acre",
    price_unit: "USD/unit",
    cost_unit: "USD/acre",
    source_name: "",
    vintage: new Date().getFullYear().toString(),
    geography: "",
  });
  const load = async () => {
    const next = await api<InvestigationRecord>(`/investigations/${id}`);
    setState(next);
    setFinancials(next.financial_inputs);
  };
  useEffect(() => {
    let cancelled = false;
    const fetchState = async () => {
      try {
        const next = await api<InvestigationRecord>(`/investigations/${id}`);
        if (!cancelled) {
          setState(next);
          setFinancials(next.financial_inputs);
        }
      } catch (reason) {
        if (!cancelled)
          setError(reason instanceof Error ? reason.message : "Unable to load investigation");
      }
    };
    fetchState();
    return () => { cancelled = true; };
  }, [id]);
  const action = async (name: string, path: string, body?: unknown) => {
    setBusy(name);
    setError("");
    try {
      await api(path, {
        method: "POST",
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Action failed");
    } finally {
      setBusy("");
    }
  };
  const uploadBoundary = async (file: File) => {
    setBoundaryFileName(file.name);
    try {
      const geometry = await parseBoundaryFile(file);
      await action("boundary-upload", `/investigations/${id}/boundary`, {
        geometry,
        kind: "user_uploaded",
        source_name: `Uploaded ${file.name}`,
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Boundary file could not be read");
    }
  };
  if (!state)
    return <div className="shell"><p>{error || "Loading decision intelligence…"}</p></div>;
  const base = state.economic_scenarios.find((item) => item.name === "base");
  const baseCashFlows = base?.cash_flows || [];
  const bestSupportedCrop = state.crop_opportunities.find(
    (item) => item.recommendation === "preferred" && item.economic_scenarios.length > 0,
  );
  const mireyeHazardEvidence = state.evidence.filter(
    (item) => item.source_type === "MIREYE" && item.field_name === "mireye_hazard_report",
  );
  const property = state.property;
  return (
    <div className="shell">
      <p><Link href={`/investigation/${id}`}>← Investigation overview</Link></p>
      <div className="topline">
        <div>
          <p className="eyebrow">Agriculture decision intelligence</p>
          <h1 className="page-title">{humanize(resource)}</h1>
        </div>
        <span className="pill">{state.status}</span>
      </div>
      <nav className="subnav decision-subnav">
        {(["map", "uses", "economics", "hazards", "alternatives"] as Resource[]).map((item) => (
          <Link className={item === resource ? "active" : ""} href={`/investigation/${id}/${item}`} key={item}>
            {item}
          </Link>
        ))}
        <Link href={`/investigation/${id}/evidence`}>evidence</Link>
        <Link href={`/investigation/${id}/dossier`}>dossier</Link>
      </nav>
      {error && <div className="error" role="alert">{error}</div>}

      {resource === "map" && (
        <div className="dashboard map-workspace">
          <section className="panel">
            <div className="section-title"><h2>Property and evidence map</h2><span className="pill">Layered</span></div>
            {property?.latitude != null && property.longitude != null ? (
              <MapPanel
                latitude={property.latitude}
                longitude={property.longitude}
                evidence={state.evidence}
                boundary={state.boundary}
                alternatives={state.alternatives}
              />
            ) : <p className="muted">Coordinates have not been resolved.</p>}
          </section>
          <aside className="stack">
            <section className="panel">
              <h2>Boundary status</h2>
              {state.boundary ? (
                <>
                  <div className="metric">{state.boundary.area_acres.toLocaleString()} acres</div>
                  <p><b>{humanize(state.boundary.kind)}</b></p>
                  <p className="muted">{state.boundary.source_name}</p>
                  {state.boundary.acreage_difference_percent != null && (
                    <p className="warning compact-warning">
                      {percent(state.boundary.acreage_difference_percent)} difference from claimed acreage
                    </p>
                  )}
                  <p className="fine">Not a legal survey or ownership determination.</p>
                </>
              ) : <p className="muted">No boundary is available. The map shows a location marker and contextual evidence only.</p>}
              <button className="button" disabled={Boolean(busy)} onClick={() => action("boundary", `/investigations/${id}/actions/resolve-boundary`)}>
                {busy === "boundary" ? "Resolving…" : "Resolve best boundary"}
              </button>
              <label className="boundary-upload">
                <span>Upload GeoJSON or KML boundary</span>
                <input
                  accept=".geojson,.json,.kml,application/geo+json,application/json,application/vnd.google-earth.kml+xml"
                  disabled={Boolean(busy)}
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) uploadBoundary(file);
                  }}
                  type="file"
                />
                <small>{busy === "boundary-upload" ? "Validating and calculating acreage…" : boundaryFileName || "Polygon or MultiPolygon only"}</small>
              </label>
            </section>
            <section className="panel">
              <h2>Geometry evidence</h2>
              <div className="compact-source-list">
                {state.evidence.filter((item) => item.geometry).slice(0, 6).map((item) => (
                  <article key={item.id}>
                    <div><b>{humanize(item.field_name)}</b><small>{item.source.publisher} · {item.source.dataset}</small></div>
                    <span>{Math.round(item.confidence * 100)}%</span>
                  </article>
                ))}
              </div>
              {!state.evidence.some((item) => item.geometry) && <p className="muted">No source geometry is available.</p>}
              <p><Link href={`/investigation/${id}/evidence`}>Open full readable evidence →</Link></p>
            </section>
          </aside>
        </div>
      )}

      {resource === "uses" && (
        <div className="stack">
          <section className="panel decision-hero">
            <div>
              <p className="eyebrow">Best supported opportunity</p>
              <h2>{bestSupportedCrop ? humanize(bestSupportedCrop.crop) : "No profitable crop is supported yet"}</h2>
              <p className="lede">Ranked by feasibility, sourced economics, buyer constraints, risk, and evidence quality—not gross revenue alone.</p>
            </div>
            <button className="button" disabled={Boolean(busy)} onClick={() => action("uses", `/investigations/${id}/actions/evaluate-uses`)}>
              {busy === "uses" ? "Recalculating…" : "Recalculate uses"}
            </button>
          </section>
          <section className="panel">
            <div className="section-title"><h2>Crop opportunities</h2><span className="pill">{state.crop_opportunities.length}</span></div>
            <div className="opportunity-grid wide-grid">
              {state.crop_opportunities.map((crop) => {
                const cropBase = crop.economic_scenarios.find((item) => item.name === "base");
                return (
                  <article className="opportunity-card" key={crop.crop}>
                    <p className="eyebrow">{humanize(crop.recommendation)}</p>
                    <h3>{humanize(crop.crop)}</h3>
                    <p>Physical fit <b>{humanize(crop.physical_fit)}</b> · historical support <b>{humanize(crop.historical_support)}</b></p>
                    <div className="metric small-metric">{percent(cropBase?.roi)}</div>
                    <p className="muted">Base ROI · {Math.round(crop.confidence * 100)}% evidence confidence</p>
                    <details><summary>Requirements and risks</summary><ul className="list">{[...crop.infrastructure_needs, ...crop.major_risks].map((item) => <li key={item}>{item}</li>)}</ul></details>
                  </article>
                );
              })}
            </div>
          </section>
          <section className="panel">
            <div className="section-title"><h2>Beyond crop farming</h2><span className="pill">Dairy, livestock and diversified uses</span></div>
            <div className="opportunity-grid wide-grid">
              {state.activity_opportunities.map((item) => (
                <article className="opportunity-card" key={item.activity}>
                  <p className="eyebrow">{humanize(item.fit)} fit</p>
                  <h3>{humanize(item.activity)}</h3>
                  {item.rationale.map((text) => <p key={text}>{text}</p>)}
                  <p className="muted">{Math.round(item.confidence * 100)}% evidence confidence</p>
                  <details><summary>Infrastructure and risk</summary><ul className="list">{[...item.infrastructure_needs, ...item.risks].map((text) => <li key={text}>{text}</li>)}</ul></details>
                </article>
              ))}
            </div>
          </section>
        </div>
      )}

      {resource === "economics" && financials && (
        <div className="stack">
          <section className={`panel decision-hero decision-${state.investment_decision?.verdict.toLowerCase() || "pending"}`}>
            <div>
              <p className="eyebrow">Acquisition recommendation</p>
              <h2>{state.investment_decision?.label || "Economics pending"}</h2>
              <p className="lede">{state.investment_decision?.rationale[0] || "Sourced production economics are required before a buy decision."}</p>
            </div>
            <div><span className="fine">MAXIMUM DEFENSIBLE OFFER</span><div className="metric">{money(state.investment_decision?.maximum_defensible_offer)}</div></div>
          </section>
          <section className="panel">
            <div className="section-title"><h2>Add a sourced enterprise budget</h2><span className="pill">Optional manual input</span></div>
            <p className="muted">Use a current extension budget, provider record, operator budget, or supplier-backed estimate. The source remains visible in evidence.</p>
            <div className="financial-grid">
              <label><span>Crop or activity</span><input value={assumptionForm.activity} onChange={(event) => setAssumptionForm({ ...assumptionForm, activity: event.target.value })} /></label>
              <label><span>Yield / production per unit</span><input type="number" min="0" value={assumptionForm.production_per_unit || ""} onChange={(event) => setAssumptionForm({ ...assumptionForm, production_per_unit: Number(event.target.value) })} /></label>
              <label><span>Price per production unit</span><input type="number" min="0" step="0.01" value={assumptionForm.price_per_unit || ""} onChange={(event) => setAssumptionForm({ ...assumptionForm, price_per_unit: Number(event.target.value) })} /></label>
              <label><span>Operating cost per acre/head</span><input type="number" min="0" value={assumptionForm.operating_cost_per_unit || ""} onChange={(event) => setAssumptionForm({ ...assumptionForm, operating_cost_per_unit: Number(event.target.value) })} /></label>
              <label><span>Productive units / herd size</span><input type="number" min="0" value={assumptionForm.productive_units || ""} onChange={(event) => setAssumptionForm({ ...assumptionForm, productive_units: Number(event.target.value) })} /><small>Leave blank to use property acres.</small></label>
              <label><span>Production unit</span><input value={assumptionForm.production_unit} onChange={(event) => setAssumptionForm({ ...assumptionForm, production_unit: event.target.value })} /></label>
              <label><span>Price unit</span><input value={assumptionForm.price_unit} onChange={(event) => setAssumptionForm({ ...assumptionForm, price_unit: event.target.value })} /></label>
              <label><span>Cost unit</span><input value={assumptionForm.cost_unit} onChange={(event) => setAssumptionForm({ ...assumptionForm, cost_unit: event.target.value })} /></label>
              <label><span>Source name</span><input placeholder="Extension budget or provider" value={assumptionForm.source_name} onChange={(event) => setAssumptionForm({ ...assumptionForm, source_name: event.target.value })} /></label>
              <label><span>Source vintage</span><input value={assumptionForm.vintage} onChange={(event) => setAssumptionForm({ ...assumptionForm, vintage: event.target.value })} /></label>
              <label><span>Geography</span><input placeholder="County, state or planning region" value={assumptionForm.geography} onChange={(event) => setAssumptionForm({ ...assumptionForm, geography: event.target.value })} /></label>
            </div>
            <button className="button" disabled={Boolean(busy) || !assumptionForm.source_name || !assumptionForm.production_per_unit || !assumptionForm.price_per_unit || !assumptionForm.operating_cost_per_unit} onClick={() => action("assumptions", `/investigations/${id}/economic-assumptions`, { ...assumptionForm, productive_units: assumptionForm.productive_units || null })}>
              {busy === "assumptions" ? "Saving and comparing…" : "Save assumptions and compare profitability"}
            </button>
          </section>
          <section className="panel">
            <div className="section-title"><h2>Editable financing assumptions</h2><span className="pill">Recalculates all scenarios</span></div>
            <div className="financial-grid">
              {([
                ["down_payment_percent", "Down payment", true],
                ["interest_rate", "Interest rate", true],
                ["loan_term_years", "Loan term (years)", false],
                ["closing_cost_percent", "Closing costs", true],
                ["annual_property_tax", "Annual property tax", false],
                ["annual_insurance", "Annual insurance", false],
                ["annual_owner_labor", "Owner/labor cost", false],
                ["working_capital", "Working capital", false],
                ["initial_capex", "Initial improvements", false],
                ["annual_replacement_capex", "Annual replacement capex", false],
                ["discount_rate", "Discount rate", true],
                ["time_horizon_years", "Analysis horizon", false],
                ["annual_land_appreciation", "Land appreciation", true],
              ] as const).map(([key, label, isPercent]) => (
                <label key={key}><span>{label}</span><input type="number" step={isPercent ? "0.01" : "1"} value={financials[key]} onChange={(event) => setFinancials({ ...financials, [key]: Number(event.target.value) })} />{isPercent && <small>Enter as decimal, e.g. 0.08</small>}</label>
              ))}
            </div>
            <button className="button" disabled={Boolean(busy)} onClick={() => action("financials", `/investigations/${id}/financial-inputs`, { financial_inputs: financials })}>
              {busy === "financials" ? "Recalculating…" : "Save and recalculate ROI"}
            </button>
          </section>
          <section className="panel">
            <div className="section-title"><h2>Conservative, base and optimistic cases</h2><span className="pill">No single-point forecast</span></div>
            <div className="scenario-row">
              {state.economic_scenarios.map((scenario) => (
                <article className="scenario" key={scenario.name}>
                  <p className="eyebrow">{scenario.name}</p>
                  <div className="metric">{percent(scenario.roi)}</div><p className="muted">operating ROI</p>
                  <p>NPV <b>{money(scenario.npv)}</b></p><p>IRR <b>{percent(scenario.irr)}</b></p><p>Cash on cash <b>{percent(scenario.cash_on_cash_return)}</b></p><p>DSCR <b>{scenario.debt_service_coverage_ratio?.toFixed(2) || "Unavailable"}</b></p>
                </article>
              ))}
            </div>
          </section>
          {baseCashFlows.length > 0 && (
            <section className="panel table-scroll"><h2>Base-case cash flow</h2><table className="table"><thead><tr><th>Year</th><th>Revenue</th><th>Operating</th><th>Debt</th><th>Net cash flow</th></tr></thead><tbody>{baseCashFlows.map((year) => <tr key={year.year}><td>{year.year}</td><td>{money(year.revenue)}</td><td>{money(year.operating_cost)}</td><td>{money(year.debt_service)}</td><td>{money(year.net_cash_flow)}</td></tr>)}</tbody></table></section>
          )}
        </div>
      )}

      {resource === "hazards" && (
        <div className="stack">
          <section className="panel decision-hero"><div><p className="eyebrow">Activity-specific disaster intelligence</p><h2>{state.hazard_assessments.length ? `${state.hazard_assessments.length} material observations` : "Hazard evidence incomplete"}</h2><p className="lede">Missing data is kept distinct from no observed exposure.</p></div><button className="button" disabled={Boolean(busy)} onClick={() => action("hazards", `/investigations/${id}/actions/analyze-hazards`)}>{busy === "hazards" ? "Analyzing…" : "Run disaster analysis"}</button></section>
          <div className="hazard-grid">
            {state.hazard_assessments.map((hazard) => (
              <article className={`panel hazard-card hazard-${hazard.materiality.toLowerCase()}`} key={hazard.hazard}>
                <div className="section-title"><h2>{humanize(hazard.hazard)}</h2><span className={`materiality-chip materiality-${hazard.materiality.toLowerCase()}`}>{humanize(hazard.materiality)}</span></div>
                <div className="metric small-metric">{humanize(hazard.exposure)}</div>
                {hazard.agricultural_consequences.map((item) => <p key={item}>{item}</p>)}
                <p className="muted">Applies to {hazard.relevant_activities.map(humanize).join(", ")} · {Math.round(hazard.confidence * 100)}% confidence</p>
                {hazard.annual_profit_stress > 0 && <p><b>{percent(hazard.annual_profit_stress)} conservative production stress</b></p>}
                <h3>Mitigation and diligence</h3><ul className="list">{hazard.mitigation_actions.map((item) => <li key={item}>{item}</li>)}</ul>
                <p className="fine">{hazard.source_name || "Source details in evidence"}{hazard.source_vintage ? ` · ${hazard.source_vintage}` : ""}</p>
              </article>
            ))}
          </div>
          {mireyeHazardEvidence.map((item) => <EvidenceCard item={item} featured key={item.id} />)}
          {!state.hazard_assessments.length && <section className="panel empty-state"><b>No hazard observations are currently available.</b><p>Configure the hazard provider or use Mireye observations; absence of records is not interpreted as a safe property.</p></section>}
        </div>
      )}

      {resource === "alternatives" && (
        <div className="stack">
          <section className="panel decision-hero"><div><p className="eyebrow">Nearby opportunity discovery</p><h2>{state.alternatives.length ? `${state.alternatives.length} candidates evaluated` : "Find better nearby opportunities"}</h2><p className="lede">Adaptive search applies budget and acreage filters, then deep-analyzes the most relevant candidates using the same crop, hazard, and economics contracts.</p></div><button className="button" disabled={Boolean(busy)} onClick={() => action("alternatives", `/investigations/${id}/actions/search-nearby`)}>{busy === "alternatives" ? "Searching and analyzing…" : "Search nearby listings"}</button></section>
          {property?.latitude != null && property.longitude != null && <section className="panel"><MapPanel latitude={property.latitude} longitude={property.longitude} evidence={state.evidence} boundary={state.boundary} alternatives={state.alternatives} /><p className="muted">Searched radii: {state.searched_radii_miles.length ? state.searched_radii_miles.map((radius) => `${radius} mi`).join(" → ") : "Not run"}</p></section>}
          <div className="alternative-grid">
            {state.alternatives.map((item) => {
              const itemBase = item.economic_scenarios.find((scenario) => scenario.name === "base");
              return <article className="panel alternative-card" key={item.id}><div className="section-title"><div><p className="eyebrow">{humanize(item.investigation_depth)}</p><h2>{item.title || "Candidate property"}</h2></div><span className="pill">{item.distance_miles ?? "?"} mi</span></div><div className="columns"><div><span className="fine">PRICE</span><div className="metric small-metric">{money(item.price)}</div></div><div><span className="fine">PRICE / ACRE</span><div>{money(item.price_per_acre)}</div></div><div><span className="fine">BASE ROI</span><div>{percent(itemBase?.roi)}</div></div></div><h3>Advantages</h3><ul className="list positive-list">{item.advantages.map((text) => <li key={text}>{text}</li>)}</ul><h3>Risks and unknowns</h3><ul className="list">{[...item.disadvantages, ...item.unknowns].map((text) => <li key={text}>{text}</li>)}</ul><div className="card-actions">{item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">Open source listing</a>}<button className="button secondary-button" disabled={Boolean(busy)} onClick={() => action(`alternative-${item.id}`, `/investigations/${id}/alternatives/${item.id}/investigate`)}>{busy === `alternative-${item.id}` ? "Analyzing…" : "Run full analysis"}</button></div></article>;
            })}
          </div>
          {!state.alternatives.length && <section className="panel empty-state"><b>No nearby listings are available.</b><p>Set <code>LISTING_SEARCH_URL</code> to an authorized JSON feed/API. The application will not fabricate listings or bypass platform access rules.</p></section>}
        </div>
      )}
    </div>
  );
}

async function parseBoundaryFile(file: File): Promise<Record<string, unknown>> {
  const text = await file.text();
  if (file.name.toLowerCase().endsWith(".kml")) {
    const document = new DOMParser().parseFromString(text, "application/xml");
    if (document.querySelector("parsererror")) throw new Error("KML is not valid XML");
    const coordinateText = document.querySelector("Polygon coordinates")?.textContent;
    if (!coordinateText) throw new Error("KML must contain a Polygon with coordinates");
    const ring = coordinateText
      .trim()
      .split(/\s+/)
      .map((coordinate) => coordinate.split(",").slice(0, 2).map(Number))
      .filter((coordinate) => coordinate.length === 2 && coordinate.every(Number.isFinite));
    if (ring.length < 3) throw new Error("KML polygon requires at least three valid points");
    return { type: "Polygon", coordinates: [ring] };
  }
  const payload = JSON.parse(text) as {
    type?: string;
    geometry?: Record<string, unknown>;
    features?: Array<{ geometry?: Record<string, unknown> }>;
  };
  const geometry =
    payload.type === "Feature"
      ? payload.geometry
      : payload.type === "FeatureCollection"
        ? payload.features?.[0]?.geometry
        : payload;
  if (!geometry || !["Polygon", "MultiPolygon"].includes(String(geometry.type)))
    throw new Error("GeoJSON must contain a Polygon or MultiPolygon");
  return geometry;
}
