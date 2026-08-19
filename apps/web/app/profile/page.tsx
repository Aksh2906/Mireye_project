"use client";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { BuyerProfile } from "@/lib/types";
const initial = {
  name: "",
  target_states: "",
  minimum_acres: "",
  maximum_acres: "",
  budget_max: "",
  preferred_crops: "",
  risk_tolerance: "moderate",
  flood_risk_tolerance: "moderate",
  desired_land_use: "",
};
export default function Profile() {
  const [form, setForm] = useState(initial);
  const [items, setItems] = useState<BuyerProfile[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const load = () => api<BuyerProfile[]>("/buyer-profiles").then(setItems);
  useEffect(() => {
    load();
  }, []);
  async function save(e: FormEvent) {
    e.preventDefault();
    await api(editingId ? `/buyer-profiles/${editingId}` : "/buyer-profiles", {
      method: editingId ? "PUT" : "POST",
      body: JSON.stringify({
        ...form,
        target_states: form.target_states
          .split(",")
          .map((x) => x.trim())
          .filter(Boolean),
        preferred_crops: form.preferred_crops
          .split(",")
          .map((x) => x.trim())
          .filter(Boolean),
        minimum_acres: form.minimum_acres ? Number(form.minimum_acres) : null,
        maximum_acres: form.maximum_acres ? Number(form.maximum_acres) : null,
        budget_max: form.budget_max ? Number(form.budget_max) : null,
      }),
    });
    setForm(initial);
    setEditingId(null);
    load();
  }
  function edit(profile: BuyerProfile) {
    setEditingId(profile.id);
    setForm({
      name: profile.name,
      target_states: profile.target_states.join(", "),
      minimum_acres: profile.minimum_acres?.toString() || "",
      maximum_acres: profile.maximum_acres?.toString() || "",
      budget_max: profile.budget_max?.toString() || "",
      preferred_crops: profile.preferred_crops.join(", "),
      risk_tolerance: profile.risk_tolerance,
      flood_risk_tolerance: profile.flood_risk_tolerance,
      desired_land_use: profile.desired_land_use || "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  return (
    <div className="shell">
      <div className="hero">
        <div>
          <p className="eyebrow">Persistent buyer context</p>
          <h1 style={{ fontSize: 52 }}>Buyer profiles</h1>
        </div>
        <p className="lede">
          An immutable snapshot is attached to each investigation. Profiles are
          never silently changed by an agent.
        </p>
      </div>
      <div className="dashboard">
        <form className="panel" onSubmit={save}>
          <label>Name</label>
          <input
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <div className="columns" style={{ marginTop: 16 }}>
            <div>
              <label>Target states</label>
              <input
                value={form.target_states}
                onChange={(e) =>
                  setForm({ ...form, target_states: e.target.value })
                }
                placeholder="IA, IL"
              />
            </div>
            <div>
              <label>Preferred crops</label>
              <input
                value={form.preferred_crops}
                onChange={(e) =>
                  setForm({ ...form, preferred_crops: e.target.value })
                }
              />
            </div>
            <div>
              <label>Minimum acres</label>
              <input
                type="number"
                value={form.minimum_acres}
                onChange={(e) =>
                  setForm({ ...form, minimum_acres: e.target.value })
                }
              />
            </div>
            <div>
              <label>Maximum acres</label>
              <input
                type="number"
                value={form.maximum_acres}
                onChange={(e) =>
                  setForm({ ...form, maximum_acres: e.target.value })
                }
              />
            </div>
            <div>
              <label>Maximum budget</label>
              <input
                type="number"
                value={form.budget_max}
                onChange={(e) =>
                  setForm({ ...form, budget_max: e.target.value })
                }
              />
            </div>
            <div>
              <label>Desired land use</label>
              <input
                value={form.desired_land_use}
                onChange={(e) =>
                  setForm({ ...form, desired_land_use: e.target.value })
                }
              />
            </div>
            <div>
              <label>Risk tolerance</label>
              <select
                value={form.risk_tolerance}
                onChange={(e) =>
                  setForm({ ...form, risk_tolerance: e.target.value })
                }
              >
                <option>low</option>
                <option>moderate</option>
                <option>high</option>
              </select>
            </div>
            <div>
              <label>Flood tolerance</label>
              <select
                value={form.flood_risk_tolerance}
                onChange={(e) =>
                  setForm({ ...form, flood_risk_tolerance: e.target.value })
                }
              >
                <option>low</option>
                <option>moderate</option>
                <option>high</option>
              </select>
            </div>
          </div>
          <div className="actions">
            <span />
            {editingId && (
              <button
                type="button"
                onClick={() => {
                  setEditingId(null);
                  setForm(initial);
                }}
              >
                Cancel edit
              </button>
            )}
            <button className="button">
              {editingId ? "Update" : "Save"} buyer profile
            </button>
          </div>
        </form>
        <div className="stack">
          {items.map((x) => (
            <div className="card" key={x.id}>
              <h3>{x.name}</h3>
              <p>
                {x.target_states.join(", ") || "Any geography"} · Up to{" "}
                {x.budget_max
                  ? `$${x.budget_max.toLocaleString()}`
                  : "unbounded budget"}{" "}
                · {x.risk_tolerance} risk tolerance
              </p>
              <p>
                <button type="button" onClick={() => edit(x)}>
                  Edit profile
                </button>
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
