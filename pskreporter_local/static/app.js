const form = document.querySelector("#report-form");
const callsignInput = document.querySelector("#callsign");
const callsignHistoryList = document.querySelector("#callsign-history");
const fetchButton = document.querySelector("#fetch-button");
const lookbackSelect = document.querySelector("#lookback");
const sentBy = document.querySelector("#sent-by");
const recvBy = document.querySelector("#recv-by");
const upstreamMode = document.querySelector("#upstream-mode");
const frequencyRange = document.querySelector("#frequency-range");
const reportLimit = document.querySelector("#report-limit");
const lastSequenceNumber = document.querySelector("#last-sequence-number");
const modify = document.querySelector("#modify");
const receptionReportsOnly = document.querySelector("#rronly");
const excludeActiveMonitors = document.querySelector("#noactive");
const includeWithoutLocator = document.querySelector("#nolocator");
const includeStatistics = document.querySelector("#statistics");
const statusMessage = document.querySelector("#status-message");
const tableWrap = document.querySelector("#table-wrap");
const reportRows = document.querySelector("#report-rows");
const filterBar = document.querySelector("#filter-bar");
const bandFilter = document.querySelector("#band-filter");
const modeFilter = document.querySelector("#mode-filter");
const fetchMeta = document.querySelector("#fetch-meta");
const resultCount = document.querySelector("#result-count");
const lastFetch = document.querySelector("#last-fetch");
const oldestReport = document.querySelector("#oldest-report");
const cacheBadge = document.querySelector("#cache-badge");
const tracePanel = document.querySelector("#xml-trace");
const traceSummary = document.querySelector("#trace-summary");
const traceContent = document.querySelector("#trace-content");

let reports = [];
const LOOKBACK_STORAGE_KEY = "pskreporter-local.lookback-seconds";
const CALLSIGN_HISTORY_STORAGE_KEY = "pskreporter-local.callsign-history";
const MAX_CALLSIGN_HISTORY = 10;
const MAX_LOCATION_CHARS = 22;

function renderCallsignHistory(history) {
  callsignHistoryList.replaceChildren();
  for (const callsign of history) {
    const option = document.createElement("option");
    option.value = callsign;
    callsignHistoryList.appendChild(option);
  }
}

function readCallsignHistory() {
  try {
    const stored = JSON.parse(
      window.localStorage.getItem(CALLSIGN_HISTORY_STORAGE_KEY) || "[]",
    );
    return Array.isArray(stored)
      ? stored.filter((value) => typeof value === "string").slice(0, MAX_CALLSIGN_HISTORY)
      : [];
  } catch {
    return [];
  }
}

function loadCallsignHistory() {
  renderCallsignHistory(readCallsignHistory());
}

function rememberCallsign(value) {
  const callsign = value.trim().toUpperCase();
  const previous = readCallsignHistory();
  const history = [
    callsign,
    ...previous.filter((candidate) => candidate.toUpperCase() !== callsign),
  ].slice(0, MAX_CALLSIGN_HISTORY);
  try {
    window.localStorage.setItem(CALLSIGN_HISTORY_STORAGE_KEY, JSON.stringify(history));
  } catch {
    // Callsign history is optional when browser storage is unavailable.
  }
  renderCallsignHistory(history);
}

async function loadAppConfig() {
  try {
    const response = await fetch("/api/config", {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return;

    const config = await response.json();
    if (!callsignInput.value && config.default_callsign) {
      callsignInput.value = config.default_callsign;
    }
    if (config.report_limit) {
      reportLimit.value = String(config.report_limit);
    }
  } catch {
    // Configuration is optional; operators can always enter a callsign manually.
  }
}

function setLookbackSelection(value) {
  const validOption = [...lookbackSelect.options].find((option) => option.value === value);
  if (!validOption) return;

  lookbackSelect.value = value;
  for (const option of lookbackSelect.options) {
    option.defaultSelected = option.value === value;
  }
}

function restoreLookbackPreference() {
  const urlValue = new URLSearchParams(window.location.search).get("lookback_seconds");
  try {
    const savedValue = window.localStorage.getItem(LOOKBACK_STORAGE_KEY);
    const validValues = [...lookbackSelect.options].map((option) => option.value);
    const preferredValue = urlValue || savedValue;
    if (preferredValue && validValues.includes(preferredValue)) {
      setLookbackSelection(preferredValue);
    }
  } catch {
    const validValues = [...lookbackSelect.options].map((option) => option.value);
    if (urlValue && validValues.includes(urlValue)) {
      setLookbackSelection(urlValue);
    }
  }
}

function rememberLookbackPreference() {
  setLookbackSelection(lookbackSelect.value);
  const url = new URL(window.location.href);
  url.searchParams.set("lookback_seconds", lookbackSelect.value);
  window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
  try {
    window.localStorage.setItem(LOOKBACK_STORAGE_KEY, lookbackSelect.value);
  } catch {
    // The URL retains the selection when browser storage is unavailable.
  }
}

function setStatus(message, kind = "") {
  statusMessage.textContent = message;
  statusMessage.className = `status-message ${kind}`.trim();
  statusMessage.hidden = false;
}

function directionLabel(direction) {
  return direction === "recv_by" ? "Recv by" : "Sent by";
}

function lookbackLabel(seconds) {
  const option = [...lookbackSelect.options].find(
    (candidate) => Number(candidate.value) === Number(seconds),
  );
  return option ? option.textContent : `${seconds} seconds`;
}

function textElement(tag, text, className = "") {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  return element;
}

function startXmlTrace() {
  const directions = [];
  if (sentBy.checked) directions.push("Sent by");
  if (recvBy.checked) directions.push("Recv by");

  tracePanel.open = true;
  traceSummary.textContent = "Working…";
  traceContent.replaceChildren(
    textElement(
      "div",
      `Preparing ${directions.join(" + ")} XML request${directions.length === 1 ? "" : "s"}…`,
      "trace-entry",
    ),
  );
}

function renderXmlTrace(entries, fallbackMessage = "No upstream trace was returned.") {
  traceContent.replaceChildren();
  if (!entries || entries.length === 0) {
    traceSummary.textContent = "No trace";
    traceContent.appendChild(textElement("div", fallbackMessage, "trace-entry"));
    return;
  }

  const allCached = entries.every((entry) => entry.cache_hit);
  traceSummary.textContent = allCached
    ? `${entries.length} cache hit${entries.length === 1 ? "" : "s"}`
    : `${entries.length} request${entries.length === 1 ? "" : "s"} complete`;

  for (const entry of entries) {
    const container = document.createElement("section");
    container.className = "trace-entry";
    const source = entry.cache_hit
      ? "cache hit"
      : entry.error
        ? "failed"
        : `HTTP ${entry.http_status}`;
    container.appendChild(
      textElement("h3", `${directionLabel(entry.direction)} — ${source}`),
    );

    const stats = document.createElement("div");
    stats.className = "trace-stats";
    const statValues = [
      entry.lookback_seconds == null
        ? null
        : `${lookbackLabel(entry.lookback_seconds)} requested`,
      entry.elapsed_ms == null ? null : `${entry.elapsed_ms} ms`,
      entry.response_bytes == null
        ? null
        : `${Number(entry.response_bytes).toLocaleString("en-US")} bytes`,
      entry.parsed_report_count == null
        ? null
        : `${entry.parsed_report_count} parsed report${entry.parsed_report_count === 1 ? "" : "s"}`,
      entry.requested_report_limit == null
        ? null
        : `${Number(entry.requested_report_limit).toLocaleString("en-US")} report limit`,
      entry.report_limit_reached ? "limit reached" : null,
      entry.fetched_at_utc ? `fetched ${displayUtc(entry.fetched_at_utc)}` : null,
    ];
    for (const value of statValues.filter(Boolean)) {
      stats.appendChild(textElement("span", value, "trace-stat"));
    }
    container.appendChild(stats);

    if (entry.request_url) {
      container.appendChild(textElement("code", entry.request_url, "trace-url"));
    }
    if (entry.error) {
      container.appendChild(textElement("p", `Error: ${entry.error}`));
    }
    if (entry.raw_xml) {
      const rawDetails = document.createElement("details");
      rawDetails.className = "raw-xml";
      rawDetails.appendChild(
        textElement(
          "summary",
          entry.raw_xml_truncated ? "Show raw XML (truncated)" : "Show raw XML",
        ),
      );
      rawDetails.appendChild(textElement("pre", entry.raw_xml, "trace-xml"));
      container.appendChild(rawDetails);
    }
    traceContent.appendChild(container);
  }
}

function displayUtc(isoText) {
  return isoText.replace("T", " ").replace("Z", "Z");
}

function appendCell(row, label, value, className = "") {
  const cell = document.createElement("td");
  cell.dataset.label = label;
  cell.textContent = value ?? "—";
  if (className) cell.className = className;
  row.appendChild(cell);
  return cell;
}

function appendTruncatedCell(row, label, value) {
  const cell = appendCell(row, label, value, "geography-cell");
  const fullText = value == null ? "" : String(value);
  if (fullText.length > MAX_LOCATION_CHARS) {
    cell.textContent = `${fullText.slice(0, MAX_LOCATION_CHARS - 1)}…`;
    cell.title = fullText;
    cell.setAttribute("aria-label", fullText);
  }
}

function relationshipLabel(directions) {
  const isSentBy = directions.includes("sent_by");
  const isRecvBy = directions.includes("recv_by");
  if (isSentBy && isRecvBy) return "Both";
  return isRecvBy ? "Recv by" : "Sent by";
}

function filteredReports() {
  return reports.filter((report) => {
    const bandMatches = !bandFilter.value || report.band === bandFilter.value;
    const modeMatches = !modeFilter.value || report.mode === modeFilter.value;
    return bandMatches && modeMatches;
  });
}

function renderReports() {
  reportRows.replaceChildren();
  const visibleReports = filteredReports();

  for (const report of visibleReports) {
    const row = document.createElement("tr");
    appendCell(row, "Report time (UTC)", displayUtc(report.spot_time_utc));
    appendCell(row, "Direction", relationshipLabel(report.directions), "direction-cell");
    appendCell(row, "Transmitter", report.sender_call, "call-cell");
    appendCell(row, "Sender grid", report.sender_locator);
    appendCell(row, "Receiver", report.receiver_call, "call-cell");
    appendCell(row, "Receiver grid", report.receiver_locator);
    appendTruncatedCell(row, "Sender region", report.sender_region);
    appendTruncatedCell(row, "Sender DXCC", report.sender_dxcc);
    appendCell(row, "F (MHz)", (report.frequency_hz / 1_000_000).toFixed(3));
    appendCell(row, "Band", report.band, "band-cell");
    appendCell(row, "Mode", report.mode, "mode-cell");
    reportRows.appendChild(row);
  }

  resultCount.textContent = `${visibleReports.length} of ${reports.length} report${reports.length === 1 ? "" : "s"}`;
  if (visibleReports.length === 0) {
    tableWrap.hidden = true;
    setStatus("No reports match the selected band and mode filters.", "empty");
  } else {
    tableWrap.hidden = false;
    statusMessage.hidden = true;
  }
}

function populateSelect(select, values, allLabel) {
  const previousValue = select.value;
  select.replaceChildren();
  const allOption = document.createElement("option");
  allOption.value = "";
  allOption.textContent = allLabel;
  select.appendChild(allOption);

  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  }
  select.value = values.includes(previousValue) ? previousValue : "";
}

function configureFilters() {
  const bands = [...new Set(reports.map((report) => report.band).filter(Boolean))].sort();
  const modes = [...new Set(reports.map((report) => report.mode).filter(Boolean))].sort();
  populateSelect(bandFilter, bands, "All bands");
  populateSelect(modeFilter, modes, "All modes");
  filterBar.hidden = reports.length === 0;
}

async function fetchReports() {
  if (!form.reportValidity()) return;

  const data = new FormData(form);
  const selectedLookback = String(data.get("lookback_seconds"));
  const params = new URLSearchParams({
    callsign: String(data.get("callsign")).trim().toUpperCase(),
    lookback_seconds: selectedLookback,
    sent_by: String(sentBy.checked),
    recv_by: String(recvBy.checked),
    rptlimit: reportLimit.value,
    rronly: String(receptionReportsOnly.checked),
    noactive: String(excludeActiveMonitors.checked),
    nolocator: String(includeWithoutLocator.checked),
    statistics: String(includeStatistics.checked),
  });
  if (upstreamMode.value.trim()) {
    params.set("upstream_mode", upstreamMode.value.trim().toUpperCase());
  }
  if (frequencyRange.value.trim()) {
    params.set("frange", frequencyRange.value.trim());
  }
  if (lastSequenceNumber.value) {
    params.set("lastseqno", lastSequenceNumber.value);
  }
  if (modify.value) {
    params.set("modify", modify.value);
  }
  rememberCallsign(params.get("callsign"));
  rememberLookbackPreference();

  fetchButton.disabled = true;
  fetchButton.querySelector("span").textContent = "Fetching…";
  tableWrap.hidden = true;
  filterBar.hidden = true;
  fetchMeta.hidden = true;
  setStatus("Contacting PSK Reporter…");
  startXmlTrace();

  let traceRendered = false;
  try {
    const response = await fetch(`/api/reports?${params.toString()}`, {
      headers: { Accept: "application/json" },
    });
    const payload = await response.json();
    renderXmlTrace(payload.xml_trace, payload.message);
    traceRendered = true;
    if (!response.ok) {
      throw new Error(payload.message || "The report request failed.");
    }

    reports = payload.reports;
    lastFetch.textContent = `Fetched ${displayUtc(payload.fetched_at_utc)}`;
    oldestReport.textContent = payload.oldest_report_utc
      ? `Oldest returned ${displayUtc(payload.oldest_report_utc)}`
      : "No reports returned";
    cacheBadge.textContent =
      payload.cache_status === "cached"
        ? "Cached"
        : payload.cache_status === "mixed"
          ? "Mixed cache"
          : "Live fetch";
    fetchMeta.hidden = false;

    if (payload.status === "empty") {
      resultCount.textContent = "0 reports";
      setStatus("No reception reports were found for the selected direction and lookback period.", "empty");
      return;
    }

    configureFilters();
    renderReports();
    if (payload.truncated) {
      const oldest = payload.oldest_report_utc
        ? ` Oldest returned report: ${displayUtc(payload.oldest_report_utc)}.`
        : "";
      setStatus(`${payload.warnings.join(" ")}${oldest}`, "warning");
    }
  } catch (error) {
    reports = [];
    if (!traceRendered) {
      renderXmlTrace([], error.message || "Unable to capture the upstream trace.");
    }
    setStatus(error.message || "Unable to load reports.", "error");
  } finally {
    setLookbackSelection(selectedLookback);
    fetchButton.disabled = false;
    fetchButton.querySelector("span").textContent = "Fetch reports";
  }
}

function keepOneDirectionSelected(changedInput) {
  if (!sentBy.checked && !recvBy.checked) {
    changedInput.checked = true;
    setStatus("Sent by, Recv by, or both must remain selected.", "empty");
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  void fetchReports();
});
fetchButton.addEventListener("click", () => void fetchReports());
lookbackSelect.addEventListener("change", rememberLookbackPreference);
sentBy.addEventListener("change", () => keepOneDirectionSelected(sentBy));
recvBy.addEventListener("change", () => keepOneDirectionSelected(recvBy));
bandFilter.addEventListener("change", renderReports);
modeFilter.addEventListener("change", renderReports);

restoreLookbackPreference();
loadCallsignHistory();
void loadAppConfig();
