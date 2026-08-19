"use client";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { InvestigationRecord } from "@/lib/types";
const MapPanel = dynamic(() => import("./MapPanel"), { ssr: false });
export default function InvestigationView({ id }: { id: string }) {
  const [state, setState] = useState<InvestigationRecord | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const load = () =>
      api<InvestigationRecord>(`/investigations/${id}`)
        .then((data) => {
          setState(data);
          if (!["completed", "failed", "needs_input"].includes(data.status))
            timer = setTimeout(load, 1500);
        })
        .catch((e) => setError(e.message));
    load();
    return () => clearTimeout(timer);
  }, [id]);
  if (error)
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
    decision?.verdict === "ACQUIRE"
      ? "acquire"
      : decision
        ? "do-not-acquire"
        : "pending";
  const p = state.property;
  const valuation = state.valuation;
  return (
    <div className="shell">
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
      <div className="dashboard">
        <div className="stack">
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
            {state.limitations.slice(-8).map((x) => (
              <div className="warning" key={x}>
                {x}
              </div>
            ))}
          </section>
        </aside>
      </div>
    </div>
  );
}
