"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { InvestigationRecord } from "@/lib/types";
export default function History() {
  const [items, setItems] = useState<InvestigationRecord[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    api<InvestigationRecord[]>("/investigations")
      .then((data) => {
        if (!cancelled) setItems(data);
      })
      .catch((e) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Unable to load history");
      });
    return () => {
      cancelled = true;
    };
  }, []);
  return (
    <div className="shell">
      <div className="topline">
        <div>
          <p className="eyebrow">Durable record</p>
          <h1 style={{ fontSize: 52 }}>Investigation history</h1>
        </div>
      </div>
      <div className="panel">
        {error && <p className="error">Could not load history: {error}</p>}
        {items.length ? (
          <table className="table">
            <thead>
              <tr>
                <th>Property</th>
                <th>Status</th>
                <th>Verdict</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((x) => (
                <tr key={x.id}>
                  <td>
                    <Link href={`/investigation/${x.id}`}>
                      {x.property?.address || x.raw_input.slice(0, 70)}
                    </Link>
                  </td>
                  <td>{x.status}</td>
                  <td>{x.decision?.verdict || "—"}</td>
                  <td>{new Date(x.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">No investigations yet.</p>
        )}
      </div>
    </div>
  );
}
