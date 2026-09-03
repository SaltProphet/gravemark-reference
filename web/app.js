const $ = (selector) => document.querySelector(selector);
const dataset = $("#dataset");
const paste = $("#paste");
const runButton = $("#run");
const state = $("#state");
let fixtures = [];
let currentResult = null;

function setState(text, error = false) { state.textContent = text; state.className = `state${error ? " error" : ""}`; }
function escapeHtml(value) { return String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c])); }
function sourceRecords() {
  const text = paste.value.trim();
  if (text) return [{ source_id: "pasted_source", source_type: "paste_text", label: "Pasted source", text, provenance: { input: "paste" } }];
  return dataset.selectedOptions[0]?.dataset.records ? JSON.parse(dataset.selectedOptions[0].dataset.records) : [];
}
function renderEvidence(evidence, analysis = null) {
  const evidenceHtml = evidence.map((item) => `<div class="evidence"><p class="quote">“${escapeHtml(item.quote)}”</p><div class="detail"><span class="chip">${escapeHtml(item.pattern_id)}</span><span>score ${escapeHtml(item.deterministic_score)}</span><span>${escapeHtml(item.source_id)} · sentence ${item.sentence_index}</span><span>${escapeHtml(Object.entries(item.provenance || {}).map(([k,v]) => `${k}: ${v}`).join(" · "))}</span></div></div>`).join("");
  const local = analysis ? `<p><strong>${escapeHtml(analysis.theme_label)}</strong></p><p>${escapeHtml(analysis.root_cause_hypothesis)}</p><p>${escapeHtml(analysis.candidate_fix_notes)}</p><p class="muted">${(analysis.validation_questions || []).map(escapeHtml).join(" · ") || "Validation questions not supplied."}</p>` : `<p class="muted">Optional. Deterministic evidence is complete without local analysis.</p><button class="analyze">Add local analysis</button>`;
  return `<div class="columns"><div class="panel"><h3>Detected Evidence · authoritative</h3>${evidenceHtml}</div><div class="panel"><h3>Local Analysis · optional</h3><div class="analysis">${local}</div></div></div>`;
}
function render(result) {
  currentResult = result;
  const byId = Object.fromEntries(result.detected_evidence.map((item) => [item.evidence_id, item]));
  const findings = result.candidate_findings;
  if (!findings.length) { $("#results").innerHTML = `<div class="empty"><span class="empty-number">02</span><h2>No candidate findings</h2><p>REAPER found no matching deterministic evidence in this source.</p></div>`; return; }
  $("#results").innerHTML = `<div class="result-header"><h2>Candidate findings</h2><span class="result-meta">${findings.length} ranked · ${result.detected_evidence.length} evidence items</span></div>` + findings.map((finding) => { const evidence = finding.supporting_evidence_ids.map((id) => byId[id]).filter(Boolean); return `<details class="finding"><summary><span class="rank">${String(finding.rank).padStart(2,"0")}</span><span><span class="finding-title">${escapeHtml(finding.title_or_label)}</span><span class="finding-sub">${evidence.length} supporting evidence item${evidence.length === 1 ? "" : "s"}</span></span><span class="score">${escapeHtml(finding.score)}</span></summary><div class="finding-body" data-finding="${escapeHtml(finding.finding_id)}">${renderEvidence(evidence)}</div></details>`; }).join("");
  document.querySelectorAll(".analyze").forEach((button) => button.addEventListener("click", async (event) => { event.stopPropagation(); const body = button.closest(".finding-body"); const finding = findings.find((item) => item.finding_id === body.dataset.finding); setState("Requesting local analysis…"); button.disabled = true; try { const response = await fetch("/api/enrich", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ candidate_finding: finding, detected_evidence: finding.supporting_evidence_ids.map((id) => byId[id]) }) }); const enriched = await response.json(); body.innerHTML = renderEvidence(finding.supporting_evidence_ids.map((id) => byId[id]), enriched.local_analysis); setState(enriched.local_analysis.status === "disabled" ? "Local analysis is disabled" : `Local analysis: ${enriched.local_analysis.status}`); } catch (error) { setState("Local analysis failed", true); button.disabled = false; } }));
}
async function loadFixtures() { const response = await fetch("/api/fixtures"); const payload = await response.json(); fixtures = payload.fixtures; dataset.innerHTML = fixtures.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.label)} · ${item.records.length} records</option>`).join(""); fixtures.forEach((item, index) => dataset.options[index].dataset.records = JSON.stringify(item.records)); setState("Ready"); }
runButton.addEventListener("click", async () => { runButton.disabled = true; setState("Running deterministic REAPER…"); try { const response = await fetch("/api/run", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ source_records: sourceRecords() }) }); const result = await response.json(); if (!response.ok) throw new Error(result.error || "Run failed"); render(result); setState(`${result.detected_evidence.length} evidence items · deterministic result ready`); } catch (error) { setState(error.message, true); } finally { runButton.disabled = false; } });
paste.addEventListener("input", () => { if (paste.value.trim()) setState("Using pasted source"); });
loadFixtures().catch(() => setState("Could not load fixtures", true));
