"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { API, api } from "@/lib/api";
import type { InvestigationRecord } from "@/lib/types";
import { EvidenceCard, SignalCard, humanize } from "./EvidencePresentation";

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
  const mireyeEvidence = state.evidence.filter((item) => item.source_type === "MIREYE");
  const supportingEvidence = state.evidence.filter((item) => item.source_type !== "MIREYE");
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
          [
            "map",
            "uses",
            "economics",
            "hazards",
            "alternatives",
            "evidence",
            "claims",
            "valuation",
            "strategy",
            "dossier",
          ] as const
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
          <section className="panel evidence-hero">
            <div className="section-title">
              <div>
                <p className="eyebrow">Physical-world intelligence</p>
                <h2>Mireye intelligence</h2>
              </div>
              <span className="pill">{mireyeEvidence.length} observations</span>
            </div>
            <p className="lede compact-lede">
              Human-readable physical context used to choose the next investigation. It is evidence—not a legal boundary, water-right determination, or final verdict.
            </p>
            {mireyeEvidence.length ? (
              <div className="stack">
                {mireyeEvidence.map((item) => <EvidenceCard item={item} featured key={item.id} />)}
              </div>
            ) : (
              <div className="empty-state">
                <b>Mireye evidence has not been returned.</b>
                <p>The investigation will show an explicit provider limitation rather than substitute synthetic data.</p>
              </div>
            )}
          </section>
          <section className="panel">
            <div className="section-title">
              <div>
                <p className="eyebrow">Independent sources</p>
                <h2>Evidence ledger</h2>
              </div>
              <span className="pill">{supportingEvidence.length} observations</span>
            </div>
            <div className="evidence-grid">
              {supportingEvidence.map((item) => <EvidenceCard item={item} key={item.id} />)}
            </div>
          </section>
          <section className="panel">
            <div className="section-title">
              <h2>Derived signals</h2>
              <span className="pill">{state.signals.length}</span>
            </div>
            {state.signals.length ? (
              <div className="signal-grid">
                {state.signals.map((signal) => <SignalCard signal={signal} key={signal.id} />)}
              </div>
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
              <article className="claim-row claim-card" key={claim.id}>
                <div>
                  <p className="eyebrow">{humanize(claim.claim_type)}</p>
                  <h3>{claim.claim_text}</h3>
                  <p className="muted">
                    {claim.materiality ? `${humanize(claim.materiality)} decision materiality` : "Materiality pending"}
                  </p>
                </div>
                <span className={`state-chip state-${claim.state.toLowerCase()}`}>{humanize(claim.state)}</span>
              </article>
            ))}
            {!state.claims.length && (
              <p className="muted">No seller or user claims were extracted.</p>
            )}
          </section>
          <section className="panel">
            <h2>Transition history</h2>
            {state.claim_transitions.map((x) => (
              <div className="trace-row refined-trace" key={x.id}>
                <b>
                  {humanize(x.from_state)} → {humanize(x.to_state)}
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
              <div className="metric status-heading">
                {state.decision_stability?.classification ? humanize(state.decision_stability.classification) : "Unassessed"}
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
              className={`verdict ${state.decision?.verdict === "ACQUIRE" || state.decision?.verdict === "ACQUIRE_CONDITIONALLY" ? "acquire" : state.decision?.verdict === "NEGOTIATE" || state.decision?.verdict === "INSUFFICIENT_EVIDENCE" ? "negotiate" : "do-not-acquire"}`}
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
