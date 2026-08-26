"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { API, api } from "@/lib/api";
import type { InvestigationRecord } from "@/lib/types";
import MarkdownView from "./MarkdownView";

const money = (value: number | null | undefined) =>
  value == null ? "Unavailable" : `$${Math.round(value).toLocaleString()}`;

export default function ResourceView({
  id,
  resource,
  title,
}: {
  id: string;
  resource: "evidence" | "valuation" | "strategy" | "claims" | "dossier";
  title: string;
}) {
  const [state, setState] = useState<InvestigationRecord | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api<InvestigationRecord>(`/investigations/${id}`)
      .then(setState)
      .catch((e) => setError(e.message));
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
        <p className="eyebrow">Loading {title}</p>
      </div>
    );
  return (
    <div className="shell">
      <p>
        <Link href={`/investigation/${id}`}>← Investigation overview</Link>
      </p>
      <div className="topline">
        <div>
          <p className="eyebrow">Decision workspace</p>
          <h1 className="page-title">{title}</h1>
        </div>
        <span className="pill">{state.status}</span>
      </div>
      <nav className="subnav">
        {(
          ["evidence", "claims", "valuation", "strategy", "dossier"] as const
        ).map((item) => (
          <Link
            className={item === resource ? "active" : ""}
            key={item}
            href={`/investigation/${id}/${item}`}
          >
            {item}
          </Link>
        ))}
      </nav>
      {resource === "evidence" && (
        <div className="stack">
          <section className="panel">
            <div className="section-title">
              <h2>Evidence ledger</h2>
              <span className="pill">{state.evidence.length} observations</span>
            </div>
            <div className="evidence-grid">
              {state.evidence.map((item) => (
                <article className="evidence-card" key={item.id}>
                  <p className="eyebrow">
                    {item.source_type} · {Math.round(item.confidence * 100)}%
                    confidence
                  </p>
                  <h3>{item.field_name.replaceAll("_", " ")}</h3>
                  {item.source_type === "MIREYE" &&
                  typeof item.value === "string" ? (
                    <MarkdownView content={item.value} />
                  ) : (
                    <p className="evidence-value">
                      {typeof item.value === "object"
                        ? JSON.stringify(item.value)
                        : String(item.value)}{" "}
                      {item.unit || ""}
                    </p>
                  )}
                  <p className="muted">
                    {item.source.publisher} — {item.source.dataset}
                    {item.source.vintage ? ` · ${item.source.vintage}` : ""}
                  </p>
                  <p className="fine">
                    Scope: {item.semantic_scope || "not specified"} · Spatial:{" "}
                    {item.spatial_resolution || "not specified"}
                  </p>
                  {item.limitations.map((x) => (
                    <div className="warning" key={x}>
                      {x}
                    </div>
                  ))}
                </article>
              ))}
            </div>
          </section>
          <section className="panel">
            <div className="section-title">
              <h2>Derived signals</h2>
              <span className="pill">{state.signals.length}</span>
            </div>
            {state.signals.length ? (
              <table className="table">
                <thead>
                  <tr>
                    <th>Signal</th>
                    <th>Value</th>
                    <th>Materiality</th>
                    <th>Interpretation</th>
                  </tr>
                </thead>
                <tbody>
                  {state.signals.map((x) => (
                    <tr key={x.id}>
                      <td>{x.name}</td>
                      <td>{String(x.value)}</td>
                      <td>{x.materiality}</td>
                      <td>{x.interpretation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="muted">No derived signals yet.</p>
            )}
          </section>
        </div>
      )}
      {resource === "claims" && (
        <div className="stack">
          <section className="panel">
            <div className="section-title">
              <h2>Claim state ledger</h2>
              <span className="pill">{state.claims.length} claims</span>
            </div>
            {state.claims.map((claim) => (
              <article className="claim-row" key={claim.id}>
                <div>
                  <h3>{claim.claim_text}</h3>
                  <p className="muted">
                    {claim.claim_type.replaceAll("_", " ")} ·{" "}
                    {claim.materiality || "unscored"} materiality
                  </p>
                </div>
                <span className="pill">{claim.state}</span>
              </article>
            ))}
            {!state.claims.length && (
              <p className="muted">No seller or user claims were extracted.</p>
            )}
          </section>
          <section className="panel">
            <h2>Transition history</h2>
            {state.claim_transitions.map((x) => (
              <div className="trace-row" key={x.id}>
                <b>
                  {x.from_state} → {x.to_state}
                </b>
                <span>{x.rationale}</span>
                <time>{new Date(x.created_at).toLocaleString()}</time>
              </div>
            ))}
          </section>
        </div>
      )}
      {resource === "valuation" && (
        <div className="dashboard">
          <section className="panel">
            <p className="eyebrow">Evidence-backed indication</p>
            <div className="metric hero-metric">
              {money(state.valuation?.low)}–{money(state.valuation?.high)}
            </div>
            <p>
              Central indication {money(state.valuation?.estimated_value_total)}{" "}
              · {money(state.valuation?.estimated_value_per_acre)} per acre
            </p>
            <p className="muted">
              Asking {money(state.valuation?.asking_price)} · Confidence{" "}
              {Math.round((state.valuation?.confidence || 0) * 100)}%
            </p>
            <h3>Value drivers</h3>
            <ul className="list">
              {state.valuation?.key_value_drivers.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
            <h3>Downside drivers</h3>
            <ul className="list">
              {state.valuation?.key_downside_drivers.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          </section>
          <aside className="stack">
            <section className="panel">
              <h2>Decision stability</h2>
              <div className="metric">
                {state.decision_stability?.classification || "Unassessed"}
              </div>
              <p className="muted">{state.decision_stability?.explanation}</p>
            </section>
            <section className="panel">
              <h2>Comparables</h2>
              {state.comparables.map((x) => (
                <div className="comparable" key={x.id}>
                  <b>{x.location || "Comparable transaction"}</b>
                  <span>
                    {money(x.sale_price)} · {x.acreage} acres ·{" "}
                    {money(x.price_per_acre)}/acre
                  </span>
                </div>
              ))}
              {!state.comparables.length && (
                <p className="muted">
                  No traceable comparable transactions were returned.
                </p>
              )}
            </section>
          </aside>
        </div>
      )}
      {resource === "strategy" && (
        <div className="dashboard">
          <section className="panel">
            <h2>Due diligence queue</h2>
            {state.diligence.map((x, i) => (
              <article className="claim-row" key={`${x.priority}-${i}`}>
                <span className="priority">{x.priority}</span>
                <div>
                  <h3>{x.request}</h3>
                  <p className="muted">{x.reason}</p>
                </div>
              </article>
            ))}
          </section>
          <section className="panel">
            <h2>Negotiation strategy</h2>
            {state.negotiation.map((x, i) => (
              <article className="warning" key={i}>
                <b>{x.action}</b>
                <p>{x.rationale}</p>
              </article>
            ))}
          </section>
        </div>
      )}
      {resource === "dossier" && (
        <div className="stack">
          <section className="panel">
            <p className="eyebrow">Investment committee dossier</p>
            <h2>
              {state.decision?.decision_summary || "Investigation incomplete"}
            </h2>
            <p className="lede">{state.decision?.qualification}</p>
            <div
              className={`verdict ${state.decision?.verdict === "ACQUIRE" ? "acquire" : "do-not-acquire"}`}
            >
              {state.decision?.verdict || state.status}
            </div>
          </section>
          <section className="panel">
            <h2>Critical reasons</h2>
            <ul className="list">
              {state.decision?.critical_reasons.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
            <h2>Unresolved uncertainties</h2>
            <ul className="list">
              {state.unknowns.map((x) => (
                <li key={x.id}>
                  <b>{x.materiality}</b> — {x.question}
                </li>
              ))}
            </ul>
            <p>
              <a
                className="button inline-button"
                href={`${API}/api/investigations/${id}/dossier`}
                target="_blank"
              >
                Download source dossier JSON
              </a>
            </p>
          </section>
        </div>
      )}
    </div>
  );
}
