"use client";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { InvestigationRecord } from "@/lib/types";
import { EvidenceCard } from "./EvidencePresentation";
const MapPanel = dynamic(() => import("./MapPanel"), { ssr: false });
export default function InvestigationView({ id }: { id: string }) {
  const [state, setState] = useState<InvestigationRecord | null>(null);
  const [error, setError] = useState("");
  const [buyerUpdate, setBuyerUpdate] = useState("");
  const [updating, setUpdating] = useState(false);
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    let cancelled = false;
    let failures = 0;
    const load = async () => {
      try {
        const data = await api<InvestigationRecord>(`/investigations/${id}`);
        if (cancelled) return;
        failures = 0;
        setError("");
          setState(data);
        if (!["completed", "failed", "needs_input"].includes(data.status))
          timer = setTimeout(load, 2500);
      } catch (e) {
        if (cancelled) return;
        failures += 1;
        setError(e instanceof Error ? e.message : "Unable to refresh investigation");
        timer = setTimeout(load, Math.min(30000, 2500 * 2 ** failures));
      }
    };
    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id]);
  if (error && !state)
    return (
      <div className="shell">
        <p className="error">{error}</p>
      </div>
    );
  if (!state)
    return (
      <div className="shell">
        <p className="eyebrow">Loading investigation</p>
      </div>
    );
  const decision = state.decision;
  const verdictClass =
    decision?.verdict === "ACQUIRE" || decision?.verdict === "ACQUIRE_CONDITIONALLY"
      ? "acquire"
      : decision?.verdict === "NEGOTIATE" || decision?.verdict === "INSUFFICIENT_EVIDENCE"
        ? "negotiate"
      : decision
        ? "do-not-acquire"
        : "pending";
  const p = state.property;
  const valuation = state.valuation;
  const cropOpportunities = state.crop_opportunities.slice(0, 4);
  const mireyeEvidence = state.evidence.filter((item) => item.source_type === "MIREYE");
  return (
    <div className="shell">
      {error && (
        <div className="warning" role="status">
          Live refresh is temporarily unavailable: {error}. Showing the latest
          saved investigation and retrying automatically.
        </div>
      )}
      <div className="topline">
        <div>
          <p className="eyebrow">Investigation · {state.status}</p>
          <h2>{p?.address || "Resolving property"}</h2>
          <p className="muted">
            Created {new Date(state.created_at).toLocaleString()}
          </p>
        </div>
        <div className={`verdict ${verdictClass}`}>
          {decision?.verdict || "Investigation underway"}
          {decision && (
            <>
              <br />
              <small>
                {decision.qualification} ·{" "}
                {Math.round(decision.confidence * 100)}% confidence
              </small>
            </>
          )}
        </div>
      </div>
      {decision && (
        <div className="panel" style={{ marginBottom: 20 }}>
          <p className="eyebrow">Executive thesis</p>
          <h2>{decision.decision_summary}</h2>
          {decision.critical_reasons.slice(1).map((x) => (
            <p className="muted" key={x}>
              {x}
            </p>
          ))}
        </div>
      )}
      <section className="panel objective-strip">
        <div>
          <span className="fine">OBJECTIVE</span>
          <strong>{state.user_objective.objective.replaceAll("_", " ")}</strong>
        </div>
        <div>
          <span className="fine">RISK TOLERANCE</span>
          <strong>{state.user_objective.risk_tolerance}</strong>
        </div>
        <div>
          <span className="fine">AGENT ITERATIONS</span>
          <strong>{state.iteration}</strong>
        </div>
        <div>
          <span className="fine">STOPPING BASIS</span>
          <strong>{state.termination_reason || "Investigation in progress"}</strong>
        </div>
      </section>
      <nav className="intelligence-nav" aria-label="Decision intelligence sections">
        {[
          ["map", "Boundary & map"],
          ["uses", "Crops & uses"],
          ["economics", "ROI & buy decision"],
          ["hazards", "Disaster analysis"],
          ["alternatives", "Nearby listings"],
          ["evidence", "Readable evidence"],
        ].map(([path, label]) => (
          <Link href={`/investigation/${id}/${path}`} key={path}>{label} →</Link>
        ))}
      </nav>
      {state.investment_decision && (
        <section className="panel investment-banner">
          <div>
            <p className="eyebrow">Agricultural investment decision</p>
            <h2>{state.investment_decision.label}</h2>
            <p className="muted">{state.investment_decision.rationale[0]}</p>
          </div>
          <div>
            <span className="fine">MAXIMUM DEFENSIBLE OFFER</span>
            <div className="metric">
              {state.investment_decision.maximum_defensible_offer == null
                ? "Unavailable"
                : `$${Math.round(state.investment_decision.maximum_defensible_offer).toLocaleString()}`}
            </div>
            <Link href={`/investigation/${id}/economics`}>Review economics →</Link>
          </div>
        </section>
      )}
      <div className="dashboard">
        <div className="stack">
          <section className="panel">
            <div className="section-title">
              <h2>Active hypotheses</h2>
              <span className="pill">{state.hypotheses.length}</span>
            </div>
            {state.hypotheses.map((hypothesis) => (
              <div className="hypothesis" key={hypothesis.id}>
                <span className={`status-dot ${hypothesis.status}`} />
                <div>
                  <strong>{hypothesis.statement}</strong>
                  <p className="muted">
                    {hypothesis.status.replaceAll("_", " ")} · {Math.round(hypothesis.confidence * 100)}% evidence confidence
                  </p>
                </div>
              </div>
            ))}
          </section>
          <section className="panel">
            <div className="section-title">
              <h2>Agricultural opportunities</h2>
              <span className="pill">Evidence-led</span>
            </div>
            <div className="opportunity-grid">
              {cropOpportunities.map((crop) => (
                <article className="opportunity-card" key={crop.crop}>
                  <p className="eyebrow">{crop.recommendation.replaceAll("_", " ")}</p>
                  <h3>{crop.crop}</h3>
                  <p>Physical fit: <b>{crop.physical_fit}</b></p>
                  <p>Historical support: <b>{crop.historical_support}</b></p>
                  <p className="muted">Confidence {Math.round(crop.confidence * 100)}%</p>
                </article>
              ))}
            </div>
            <h3 style={{ marginTop: 22 }}>Activity comparison</h3>
            <table className="table">
              <thead><tr><th>Activity</th><th>Fit</th><th>Evidence</th></tr></thead>
              <tbody>
                {state.activity_opportunities.map((item) => (
                  <tr key={item.activity}>
                    <td>{item.activity.replaceAll("_", " ")}</td>
                    <td>{item.fit}</td>
                    <td>{Math.round(item.confidence * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          {state.economic_scenarios.length > 0 && (
            <section className="panel">
              <div className="section-title"><h2>Scenario economics</h2><span className="pill">No single-point forecast</span></div>
              <div className="scenario-row">
                {state.economic_scenarios.map((scenario) => (
                  <div className="scenario" key={scenario.name}>
                    <p className="eyebrow">{scenario.name}</p>
                    <div className="metric">{scenario.annual_operating_profit == null ? "Unknown" : `$${Math.round(scenario.annual_operating_profit).toLocaleString()}`}</div>
                    <p className="muted">annual operating profit</p>
                    <p>{scenario.roi == null ? "ROI unknown" : `${(scenario.roi * 100).toFixed(1)}% ROI`}</p>
                  </div>
                ))}
              </div>
            </section>
          )}
          {state.hazard_assessments.length > 0 && (
            <section className="panel">
              <div className="section-title"><h2>Activity-specific hazards</h2></div>
              {state.hazard_assessments.map((hazard) => (
                <div className="warning" key={hazard.hazard}>
                  <b>{hazard.hazard}</b> · {hazard.exposure} exposure · {hazard.materiality.toLowerCase()} materiality
                  <br /><small>{hazard.agricultural_consequences.join(" ")}</small>
                </div>
              ))}
            </section>
          )}
          {state.alternatives.length > 0 && (
            <section className="panel">
              <div className="section-title"><h2>Nearby alternatives</h2><span className="pill">{state.alternatives.length}</span></div>
              <div className="opportunity-grid">
                {state.alternatives.slice(0, 3).map((alternative) => (
                  <article className="opportunity-card" key={alternative.id}>
                    <p className="eyebrow">{alternative.investigation_depth}</p>
                    <h3>{alternative.title || "Candidate property"}</h3>
                    <p>{alternative.acreage ? `${alternative.acreage} acres` : "Acreage unknown"} · {alternative.price ? `$${alternative.price.toLocaleString()}` : "Price unknown"}</p>
                    {alternative.advantages.map((item) => <p key={item}>+ {item}</p>)}
                    {alternative.disadvantages.map((item) => <p className="muted" key={item}>− {item}</p>)}
                    <p className="fine">Evidence quality {Math.round(alternative.evidence_quality * 100)}%</p>
                  </article>
                ))}
              </div>
            </section>
          )}
          <section className="panel">
            <div className="section-title">
              <h2>Investigation trace</h2>
              <span className="pill">{state.events.length} events</span>
            </div>
            <ol className="timeline">
              {[...state.events].reverse().map((e) => (
                <li key={e.id}>
                  <time>{new Date(e.created_at).toLocaleTimeString()}</time>
                  <p>{e.message}</p>
                </li>
              ))}
            </ol>
          </section>
          {mireyeEvidence.length > 0 && (
            <section className="panel">
              <div className="section-title">
                <h2>Mireye property intelligence</h2>
                <Link href={`/investigation/${id}/evidence`}>Sources →</Link>
              </div>
              <div className="stack">
                {mireyeEvidence.slice(0, 2).map((item) => (
                  <EvidenceCard item={item} featured key={item.id} />
                ))}
              </div>
            </section>
          )}
          <section className="panel">
            <div className="section-title">
              <h2>Claims & evidence</h2>
              <Link href={`/investigation/${id}/evidence`}>View all →</Link>
            </div>
            {state.claims.length ? (
              <table className="table">
                <thead>
                  <tr>
                    <th>Claim</th>
                    <th>Status</th>
                    <th>Materiality</th>
                  </tr>
                </thead>
                <tbody>
                  {state.claims.map((c) => (
                    <tr key={c.id}>
                      <td>{c.claim_text}</td>
                      <td>
                        <span className="pill">{c.state}</span>
                      </td>
                      <td>{c.materiality || "Pending"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="muted">No material listing claims extracted yet.</p>
            )}
            {state.contradictions.map((c) => (
              <div className="warning danger" key={c.id}>
                {c.description}
                <br />
                <small>{c.decision_impact}</small>
              </div>
            ))}
          </section>
          <section className="panel">
            <div className="section-title">
              <h2>Due diligence</h2>
              <Link href={`/investigation/${id}/strategy`}>Strategy →</Link>
            </div>
            <ul className="list">
              {state.diligence.map((d, i) => (
                <li key={i}>
                  <b>{d.priority}</b> — {d.request}
                  <br />
                  <span className="muted">{d.reason}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
        <aside className="stack">
          <section className="panel">
            <div className="section-title">
              <h2>Property context</h2>
            </div>
            {p?.latitude != null && p?.longitude != null ? (
              <MapPanel
                latitude={p.latitude}
                longitude={p.longitude}
                evidence={state.evidence}
                boundary={state.boundary}
                alternatives={state.alternatives}
              />
            ) : (
              <p className="muted">
                Reliable coordinates have not been resolved. No parcel boundary
                is implied.
              </p>
            )}
            <div className="columns" style={{ marginTop: 16 }}>
              <div>
                <span className="fine">TOTAL ACRES</span>
                <div className="metric">{p?.acreage || "Unknown"}</div>
              </div>
              <div>
                <span className="fine">COUNTY</span>
                <div>{p?.county || "Unknown"}</div>
              </div>
            </div>
          </section>
          <section className="panel">
            <div className="section-title">
              <h2>Valuation</h2>
              <Link href={`/investigation/${id}/valuation`}>Details →</Link>
            </div>
            {valuation?.estimated_value_total &&
            valuation.low != null &&
            valuation.high != null &&
            valuation.estimated_value_per_acre != null ? (
              <>
                <span className="fine">INDICATED RANGE</span>
                <div className="metric">
                  ${Math.round(valuation.low).toLocaleString()}–$
                  {Math.round(valuation.high).toLocaleString()}
                </div>
                <p className="muted">
                  $
                  {Math.round(
                    valuation.estimated_value_per_acre,
                  ).toLocaleString()}{" "}
                  per acre · Asking $
                  {valuation.asking_price?.toLocaleString() || "unknown"}
                </p>
              </>
            ) : (
              <>
                <div className="metric">Unavailable</div>
                <p className="muted">
                  {valuation?.limitations.join(" ") ||
                    "Investigation in progress."}
                </p>
              </>
            )}
          </section>
          <section className="panel">
            <h2>Known limitations</h2>
            {Array.from(new Set(state.limitations)).slice(-8).map((x, index) => (
              <div className="warning" key={`${index}-${x}`}>
                {x}
              </div>
            ))}
          </section>
          <section className="panel">
            <h2>Update buyer context</h2>
            <p className="muted">Add information only when it can change the decision—for example, an irrigation budget or operating model.</p>
            <textarea value={buyerUpdate} onChange={(event) => setBuyerUpdate(event.target.value)} placeholder="I can invest another $100,000 in irrigation…" />
            <button
              className="button"
              style={{ marginTop: 10 }}
              disabled={updating || !buyerUpdate.trim()}
              onClick={async () => {
                setUpdating(true);
                try {
                  await api(`/investigations/${id}/question`, { method: "POST", body: JSON.stringify({ answer: buyerUpdate }) });
                  setBuyerUpdate("");
                  window.location.reload();
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Unable to update objective");
                } finally { setUpdating(false); }
              }}
            >{updating ? "Updating…" : "Update & reconsider"}</button>
          </section>
        </aside>
      </div>
    </div>
  );
}
