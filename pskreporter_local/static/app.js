const form = document.querySelector("#report-form");
const callsignInput = document.querySelector("#callsign");
const callsignHistoryList = document.querySelector("#callsign-history");
const fetchButton = document.querySelector("#fetch-button");
const lookbackSelect = document.querySelector("#lookback");
const refreshIntervalSelect = document.querySelector("#refresh-interval");
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
const stationQueryPanel = document.querySelector("#station-query-panel");
const stationQuerySummary = stationQueryPanel.querySelector("summary");
const stationQuerySummaryContext = document.querySelector("#station-query-summary-context");
const adifSummary = document.querySelector("#adif-summary");
const adifPath = document.querySelector("#adif-path");
const adifStatus = document.querySelector("#adif-status");
const reloadAdifButton = document.querySelector("#reload-adif");
const statusMessage = document.querySelector("#status-message");
const resultsPanel = document.querySelector(".results-panel");
const tableWrap = document.querySelector("#table-wrap");
const reportRows = document.querySelector("#report-rows");
const tableViewButton = document.querySelector("#table-view-button");
const mapViewButton = document.querySelector("#map-view-button");
const mapWrap = document.querySelector("#map-wrap");
const reportMapElement = document.querySelector("#report-map");
const mapSummary = document.querySelector("#map-summary");
const mapEmpty = document.querySelector("#map-empty");
const clusteredMapButton = document.querySelector("#clustered-map-button");
const individualMapButton = document.querySelector("#individual-map-button");
const filterBar = document.querySelector("#filter-bar");
const resultsOptionsSummaryContext = document.querySelector("#results-options-summary-context");
const bandFilter = document.querySelector("#band-filter");
const modeFilter = document.querySelector("#mode-filter");
const sortFieldSelect = document.querySelector("#sort-field");
const sortDirectionButton = document.querySelector("#sort-direction");
const sortHeaders = document.querySelectorAll("th[data-sort-key]");
const fetchMeta = document.querySelector("#fetch-meta");
const resultCount = document.querySelector("#result-count");
const lastFetch = document.querySelector("#last-fetch");
const oldestReport = document.querySelector("#oldest-report");
const cacheBadge = document.querySelector("#cache-badge");
const tracePanel = document.querySelector("#xml-trace");
const traceSummary = document.querySelector("#trace-summary");
const traceContent = document.querySelector("#trace-content");
const lastDisplayRefreshTime = document.querySelector("#last-display-refresh-time");
const stationInspector = document.querySelector("#station-inspector");
const closeInspectorButton = document.querySelector("#close-inspector");
const inspectorCallsign = document.querySelector("#inspector-callsign");
const inspectorQrzLink = document.querySelector("#inspector-qrz-link");
const copyInspectorCallsignButton = document.querySelector("#copy-inspector-callsign");
const inspectorLastSeen = document.querySelector("#inspector-last-seen");
const inspectorLiveDetails = document.querySelector("#inspector-live-details");
const inspectorQsoSummary = document.querySelector("#inspector-qso-summary");
const inspectorQsoStatus = document.querySelector("#inspector-qso-status");
const inspectorQsoTableWrap = document.querySelector("#inspector-qso-table-wrap");
const inspectorQsoRows = document.querySelector("#inspector-qso-rows");
const toggleAllQsosButton = document.querySelector("#toggle-all-qsos");

let reports = [];
let fetchInProgress = false;
let refreshTimer = null;
let sortState = { key: "spot_time_utc", direction: "descending" };
let activeResultsView = "table";
let reportMap = null;
let reportMarkerLayer = null;
let reportMarkerLayerMode = null;
let mapNeedsInitialFit = true;
let mapTilesUnavailable = false;
let mapMarkerMode = "clustered";
let queryPanelHasAutoCollapsed = false;
let inspectorQsos = [];
let inspectorShowsAllQsos = false;
let inspectorRequestId = 0;
const stationQsoCache = new Map();
const LOOKBACK_STORAGE_KEY = "pskreporter-local.lookback-seconds";
const REFRESH_INTERVAL_STORAGE_KEY = "pskreporter-local.refresh-interval-seconds";
const CALLSIGN_HISTORY_STORAGE_KEY = "pskreporter-local.callsign-history";
const MAP_MARKER_MODE_STORAGE_KEY = "pskreporter-local.map-marker-mode";
const MAX_CALLSIGN_HISTORY = 10;
const MAX_LOCATION_CHARS = 22;
const QRZ_CALLSIGN_URL = "https://www.qrz.com/db/";
const MAP_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const MAP_TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>';
const MAP_OPPORTUNITY_RANK = {
  unknown: 0,
  worked: 1,
  "other-band": 2,
  unworked: 3,
};
const MAP_OPPORTUNITY_LABEL = {
  unknown: "Local log unavailable",
  worked: "Worked on this band",
  "other-band": "New on this band",
  unworked: "Unworked (0/0)",
};
const SORT_COLLATOR = new Intl.Collator(undefined, {
  numeric: true,
  sensitivity: "base",
});
const SORT_COLUMNS = {
  spot_time_utc: {
    label: "Report time (UTC)",
    value: (report) => Date.parse(report.spot_time_utc),
  },
  direction: {
    label: "Direction",
    value: (report) => relationshipLabel(report.directions),
  },
  sender_call: { label: "Sender", value: (report) => report.sender_call },
  sender_locator: {
    label: "Sender grid",
    value: (report) => report.sender_locator,
  },
  receiver_call: { label: "Recv", value: (report) => report.receiver_call },
  receiver_locator: {
    label: "Recv grid",
    value: (report) => report.receiver_locator,
  },
  qso_counts: {
    label: "QSOs B/T",
    value: (report) => [report.qso_count_band, report.qso_count_total],
  },
  sender_region: {
    label: "Sender region",
    value: (report) => report.sender_region,
  },
  sender_dxcc: {
    label: "Sender DXCC",
    value: (report) => report.sender_dxcc,
  },
  band: { label: "Band", value: (report) => report.band },
  snr_db: { label: "sNR (dB)", value: (report) => report.snr_db },
  mode: { label: "Mode", value: (report) => report.mode },
  frequency_hz: { label: "F (MHz)", value: (report) => report.frequency_hz },
};

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
    updateStationQuerySummary();
  } catch {
    // Configuration is optional; operators can always enter a callsign manually.
  }
}

function renderAdifStatus(status) {
  adifPath.textContent = status.path || "Not configured";
  reloadAdifButton.disabled = !status.configured;

  if (status.status === "loaded") {
    const qsoLabel = `${status.qso_count.toLocaleString("en-US")} QSO${status.qso_count === 1 ? "" : "s"}`;
    adifSummary.textContent = `${qsoLabel} loaded`;
    adifStatus.textContent = status.file_modified_at_utc
      ? `${qsoLabel}; file modified ${displayUtc(status.file_modified_at_utc)}.`
      : `${qsoLabel} loaded.`;
    adifStatus.className = "loaded";
    return;
  }

  if (status.status === "error") {
    adifSummary.textContent = "Load failed";
    adifStatus.textContent = status.message || "The configured ADI file could not be loaded.";
    adifStatus.className = "error";
    return;
  }

  adifSummary.textContent = "Not configured";
  adifStatus.innerHTML = "Set <code>adif_file_path</code> in <code>config.json</code> and restart the application.";
  adifStatus.className = "";
}

async function loadAdifStatus() {
  try {
    const response = await fetch("/api/adif", {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error("Unable to read ADIF status.");
    renderAdifStatus(await response.json());
  } catch (error) {
    adifSummary.textContent = "Status unavailable";
    adifStatus.textContent = error.message || "Unable to read ADIF status.";
    adifStatus.className = "error";
  }
}

async function reloadAdif() {
  reloadAdifButton.disabled = true;
  reloadAdifButton.textContent = "Reloading…";
  adifStatus.textContent = "Reading the configured ADI file…";
  adifStatus.className = "";
  try {
    const response = await fetch("/api/adif/reload", {
      method: "POST",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error("Unable to reload the ADI file.");
    renderAdifStatus(await response.json());
    stationQsoCache.clear();
  } catch (error) {
    adifSummary.textContent = "Reload failed";
    adifStatus.textContent = error.message || "Unable to reload the ADI file.";
    adifStatus.className = "error";
  } finally {
    reloadAdifButton.textContent = "Reload ADIF";
    if (adifPath.textContent !== "Not configured") reloadAdifButton.disabled = false;
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

function restoreRefreshPreference() {
  try {
    const savedValue = window.localStorage.getItem(REFRESH_INTERVAL_STORAGE_KEY);
    const validValues = [...refreshIntervalSelect.options].map((option) => option.value);
    if (savedValue && validValues.includes(savedValue)) {
      refreshIntervalSelect.value = savedValue;
    }
  } catch {
    // The selected HTML option remains the default when storage is unavailable.
  }
}

function scheduleAutoRefresh() {
  if (refreshTimer !== null) window.clearTimeout(refreshTimer);
  const intervalMilliseconds = Number(refreshIntervalSelect.value) * 1000;
  refreshTimer = window.setTimeout(() => {
    refreshTimer = null;
    void fetchReports({ automatic: true });
  }, intervalMilliseconds);
}

function rememberRefreshPreference() {
  try {
    window.localStorage.setItem(
      REFRESH_INTERVAL_STORAGE_KEY,
      refreshIntervalSelect.value,
    );
  } catch {
    // Refresh scheduling still works when browser storage is unavailable.
  }
  scheduleAutoRefresh();
}

function selectedOptionLabel(select) {
  return select.selectedOptions[0]?.textContent?.trim() || select.value;
}

function updateStationQuerySummary() {
  const callsign = callsignInput.value.trim().toUpperCase() || "Enter a callsign";
  const direction = sentBy.checked && recvBy.checked
    ? "Both directions"
    : recvBy.checked
      ? "Recv by"
      : "Sent by";
  stationQuerySummaryContext.textContent = [
    callsign,
    direction,
    selectedOptionLabel(lookbackSelect),
    `Auto ${selectedOptionLabel(refreshIntervalSelect)}`,
  ].join(" · ");
}

function updateResultsOptionsSummary() {
  const band = bandFilter.value || "All bands";
  const mode = modeFilter.value || "All modes";
  const sortLabel = sortState.key === "spot_time_utc"
    ? "UTC"
    : SORT_COLUMNS[sortState.key].label;
  const sortArrow = sortState.direction === "ascending" ? "↑" : "↓";
  resultsOptionsSummaryContext.textContent = `${band} · ${mode} · ${sortLabel} ${sortArrow}`;
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

  tracePanel.open = false;
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

function fallbackCopyText(text) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.readOnly = true;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  textarea.style.pointerEvents = "none";
  document.body.appendChild(textarea);
  let copied = false;
  try {
    textarea.select();
    textarea.setSelectionRange(0, text.length);
    copied = document.execCommand("copy");
  } finally {
    textarea.remove();
  }
  if (!copied) throw new Error("The browser denied clipboard access.");
}

function showCopyFeedback(button, copied) {
  const defaultText = button.dataset.defaultText || button.textContent;
  button.dataset.defaultText = defaultText;
  button.textContent = copied ? "Copied!" : "Copy failed";
  button.classList.toggle("copied", copied);
  window.setTimeout(() => {
    if (!button.isConnected) return;
    button.textContent = defaultText;
    button.classList.remove("copied");
  }, 1400);
}

async function copyCallsign(callsign, button) {
  try {
    if (window.isSecureContext && navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(callsign);
      } catch {
        fallbackCopyText(callsign);
      }
    } else {
      fallbackCopyText(callsign);
    }
    showCopyFeedback(button, true);
  } catch {
    showCopyFeedback(button, false);
  }
}

function appendQrzCallsignCell(row, label, callsign, copyable = false) {
  const cell = appendCell(row, label, callsign, "call-cell");
  if (!callsign) return cell;

  const contents = document.createElement("div");
  contents.className = "call-cell-content";
  const link = document.createElement("a");
  link.className = "callsign-link";
  link.href = `${QRZ_CALLSIGN_URL}${encodeURIComponent(callsign)}`;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = callsign;
  link.title = `Open ${callsign} on QRZ`;
  link.setAttribute("aria-label", `Open ${callsign} on QRZ in a new tab`);
  contents.appendChild(link);
  if (copyable) {
    const copyButton = document.createElement("button");
    copyButton.className = "copy-callsign-button";
    copyButton.type = "button";
    copyButton.textContent = "Copy";
    copyButton.title = `Copy ${callsign} to the clipboard`;
    copyButton.setAttribute("aria-label", `Copy ${callsign} to the clipboard`);
    copyButton.addEventListener("click", () => void copyCallsign(callsign, copyButton));
    contents.appendChild(copyButton);
  }
  cell.replaceChildren(contents);
  return cell;
}

function relationshipLabel(directions) {
  const isSentBy = directions.includes("sent_by");
  const isRecvBy = directions.includes("recv_by");
  if (isSentBy && isRecvBy) return "Both";
  return isRecvBy ? "Recv by" : "Sent by";
}

function opportunityState(report) {
  if (report.qso_count_total == null) return "unknown";
  if (report.qso_count_total === 0) return "unworked";
  if (report.qso_count_band === 0) return "other-band";
  return "worked";
}

function groupedMapStations(visibleReports) {
  const groups = new Map();
  let missingReportCount = 0;
  for (const report of visibleReports) {
    if (
      !report.qso_call
      || !report.qso_locator
      || !Number.isFinite(report.qso_latitude)
      || !Number.isFinite(report.qso_longitude)
    ) {
      missingReportCount += 1;
      continue;
    }

    const key = `${report.qso_call.toUpperCase()}|${report.qso_locator.toUpperCase()}`;
    const state = opportunityState(report);
    const previous = groups.get(key);
    if (!previous) {
      groups.set(key, { report, state, reportCount: 1 });
      continue;
    }

    previous.reportCount += 1;
    const previousRank = MAP_OPPORTUNITY_RANK[previous.state];
    const currentRank = MAP_OPPORTUNITY_RANK[state];
    const currentIsNewer = Date.parse(report.spot_time_utc)
      > Date.parse(previous.report.spot_time_utc);
    if (currentRank > previousRank || (currentRank === previousRank && currentIsNewer)) {
      previous.report = report;
      previous.state = state;
    }
  }
  return { stations: [...groups.values()], missingReportCount };
}

function markerTooltip(station) {
  const report = station.report;
  const tooltip = document.createElement("div");
  tooltip.className = "station-map-tooltip";
  tooltip.appendChild(textElement("strong", report.qso_call));
  tooltip.appendChild(
    textElement(
      "span",
      [report.qso_locator, report.band, report.mode].filter(Boolean).join(" · "),
    ),
  );
  tooltip.appendChild(textElement("small", MAP_OPPORTUNITY_LABEL[station.state]));
  if (station.reportCount > 1) {
    tooltip.appendChild(
      textElement(
        "small",
        `${station.reportCount.toLocaleString("en-US")} visible reports`,
      ),
    );
  }
  return tooltip;
}

function stationMarkerIcon(state) {
  return window.L.divIcon({
    className: "station-marker-icon",
    html: `<span class="station-map-marker ${state}" aria-hidden="true"></span>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}

function clusterOpportunityState(cluster) {
  let bestState = "unknown";
  for (const marker of cluster.getAllChildMarkers()) {
    const state = marker.options.stationOpportunity || "unknown";
    if (MAP_OPPORTUNITY_RANK[state] > MAP_OPPORTUNITY_RANK[bestState]) {
      bestState = state;
    }
  }
  return bestState;
}

function clusterIcon(cluster) {
  const count = cluster.getChildCount();
  const state = clusterOpportunityState(cluster);
  const size = count < 10 ? 38 : count < 100 ? 44 : 50;
  return window.L.divIcon({
    className: "station-cluster-icon",
    html: `<span class="station-map-cluster ${state}">${count.toLocaleString("en-US")}</span>`,
    iconSize: [size, size],
  });
}

function locatorCellDimensions(locator) {
  const precision = locator?.trim().length;
  if (precision === 2) return { latitude: 10, longitude: 20 };
  if (precision === 4) return { latitude: 1, longitude: 2 };
  if (precision === 6) return { latitude: 1 / 24, longitude: 1 / 12 };
  if (precision === 8) return { latitude: 1 / 240, longitude: 1 / 120 };
  return { latitude: 0, longitude: 0 };
}

function individualStationPositions(stations) {
  const collisionGroups = new Map();
  for (const station of stations) {
    const report = station.report;
    const key = `${report.qso_latitude.toFixed(8)}|${report.qso_longitude.toFixed(8)}`;
    if (!collisionGroups.has(key)) collisionGroups.set(key, []);
    collisionGroups.get(key).push(station);
  }

  const positions = new Map();
  for (const group of collisionGroups.values()) {
    group.sort((left, right) => (
      MAP_OPPORTUNITY_RANK[right.state] - MAP_OPPORTUNITY_RANK[left.state]
      || SORT_COLLATOR.compare(left.report.qso_call, right.report.qso_call)
      || SORT_COLLATOR.compare(left.report.qso_locator, right.report.qso_locator)
    ));
    for (let index = 0; index < group.length; index += 1) {
      const station = group[index];
      const report = station.report;
      if (index === 0) {
        positions.set(station, [report.qso_latitude, report.qso_longitude]);
        continue;
      }

      let ring = 1;
      let slot = index - 1;
      while (slot >= ring * 6) {
        slot -= ring * 6;
        ring += 1;
      }
      const slotsInRing = ring * 6;
      const angle = (2 * Math.PI * slot) / slotsInRing - Math.PI / 2;
      const radius = Math.min(0.42, 0.1 + ring * 0.07);
      const cell = locatorCellDimensions(report.qso_locator);
      positions.set(station, [
        report.qso_latitude + Math.sin(angle) * cell.latitude * radius,
        report.qso_longitude + Math.cos(angle) * cell.longitude * radius,
      ]);
    }
  }
  return positions;
}

function createReportMarkerLayer() {
  reportMarkerLayerMode = mapMarkerMode;
  if (mapMarkerMode === "clustered" && typeof window.L.markerClusterGroup === "function") {
    return window.L.markerClusterGroup({
      chunkedLoading: true,
      iconCreateFunction: clusterIcon,
      maxClusterRadius: 46,
      showCoverageOnHover: false,
      spiderfyOnMaxZoom: true,
    });
  }
  return window.L.layerGroup();
}

function prepareReportMarkerLayer() {
  if (reportMarkerLayer && reportMarkerLayerMode === mapMarkerMode) {
    reportMarkerLayer.clearLayers();
    return;
  }
  if (reportMarkerLayer) reportMap.removeLayer(reportMarkerLayer);
  reportMarkerLayer = createReportMarkerLayer();
  reportMarkerLayer.addTo(reportMap);
}

function ensureReportMap() {
  if (reportMap) return true;
  if (!window.L) return false;

  reportMap = window.L.map(reportMapElement, {
    center: [20, 0],
    zoom: 2,
    minZoom: 2,
    worldCopyJump: true,
  });
  const tileLayer = window.L.tileLayer(MAP_TILE_URL, {
    attribution: MAP_TILE_ATTRIBUTION,
    maxZoom: 19,
    detectRetina: false,
  });
  tileLayer.once("tileerror", () => {
    mapTilesUnavailable = true;
    if (!mapSummary.textContent.includes("Base-map tiles unavailable")) {
      mapSummary.textContent += " · Base-map tiles unavailable";
    }
  });
  tileLayer.addTo(reportMap);

  reportMarkerLayer = createReportMarkerLayer();
  reportMarkerLayer.addTo(reportMap);
  return true;
}

function mapSummaryText(stationCount, reportCount, missingReportCount) {
  const stationLabel = `${stationCount.toLocaleString("en-US")} mapped station${stationCount === 1 ? "" : "s"}`;
  const reportLabel = `${reportCount.toLocaleString("en-US")} located report${reportCount === 1 ? "" : "s"}`;
  const missingLabel = missingReportCount
    ? ` · ${missingReportCount.toLocaleString("en-US")} report${missingReportCount === 1 ? "" : "s"} without a usable station grid`
    : "";
  const tileLabel = mapTilesUnavailable ? " · Base-map tiles unavailable" : "";
  return `${stationLabel} from ${reportLabel}${missingLabel}${tileLabel}`;
}

function renderReportMap(visibleReports) {
  const { stations, missingReportCount } = groupedMapStations(visibleReports);
  const locatedReportCount = stations.reduce(
    (total, station) => total + station.reportCount,
    0,
  );
  mapSummary.textContent = mapSummaryText(
    stations.length,
    locatedReportCount,
    missingReportCount,
  );

  if (stations.length === 0) {
    reportMapElement.hidden = true;
    mapEmpty.hidden = false;
    mapEmpty.textContent = visibleReports.length
      ? "None of the filtered reports includes a usable locator for the other station."
      : "No filtered reports are available to map.";
    return;
  }

  mapEmpty.hidden = true;
  reportMapElement.hidden = false;
  if (!ensureReportMap()) {
    reportMapElement.hidden = true;
    mapEmpty.hidden = false;
    mapEmpty.textContent = "The local Leaflet map library could not be loaded.";
    return;
  }

  prepareReportMarkerLayer();
  const bounds = [];
  const markers = [];
  const individualPositions = mapMarkerMode === "individual"
    ? individualStationPositions(stations)
    : null;
  for (const station of stations) {
    const report = station.report;
    const center = [report.qso_latitude, report.qso_longitude];
    const position = individualPositions?.get(station) || center;
    const description = `${report.qso_call} in ${report.qso_locator}; ${MAP_OPPORTUNITY_LABEL[station.state]}; open station inspector`;
    const marker = window.L.marker(position, {
      alt: description,
      icon: stationMarkerIcon(station.state),
      keyboard: true,
      riseOnHover: true,
      stationOpportunity: station.state,
      title: description,
      zIndexOffset: mapMarkerMode === "individual"
        ? MAP_OPPORTUNITY_RANK[station.state] * 10_000
        : 0,
    });
    marker.bindTooltip(markerTooltip(station), {
      direction: "top",
      offset: [0, -12],
      opacity: 1,
    });
    marker.on("click", () => void openStationInspector(report));
    marker.on("add", () => {
      const markerElement = marker.getElement();
      if (markerElement) {
        markerElement.setAttribute("aria-label", description);
        markerElement.setAttribute("role", "button");
      }
    });
    markers.push(marker);
    bounds.push(center);
  }
  if (typeof reportMarkerLayer.addLayers === "function") {
    reportMarkerLayer.addLayers(markers);
  } else {
    for (const marker of markers) reportMarkerLayer.addLayer(marker);
  }

  window.requestAnimationFrame(() => {
    reportMap.invalidateSize();
    if (!mapNeedsInitialFit) return;
    if (bounds.length === 1) {
      reportMap.setView(bounds[0], 7);
    } else {
      reportMap.fitBounds(bounds, { maxZoom: 8, padding: [34, 34] });
    }
    mapNeedsInitialFit = false;
  });
}

function updateMapMarkerModeControls() {
  const isClustered = mapMarkerMode === "clustered";
  clusteredMapButton.classList.toggle("active", isClustered);
  individualMapButton.classList.toggle("active", !isClustered);
  clusteredMapButton.setAttribute("aria-pressed", String(isClustered));
  individualMapButton.setAttribute("aria-pressed", String(!isClustered));
}

function setMapMarkerMode(mode, { persist = true } = {}) {
  if (!["clustered", "individual"].includes(mode) || mode === mapMarkerMode) return;
  mapMarkerMode = mode;
  updateMapMarkerModeControls();
  if (persist) {
    try {
      window.localStorage.setItem(MAP_MARKER_MODE_STORAGE_KEY, mode);
    } catch {
      // The mode still applies for this page when browser storage is unavailable.
    }
  }
  if (activeResultsView === "map" && reports.length > 0) {
    renderReportMap(sortedFilteredReports());
  }
}

function restoreMapMarkerMode() {
  try {
    const savedMode = window.localStorage.getItem(MAP_MARKER_MODE_STORAGE_KEY);
    if (["clustered", "individual"].includes(savedMode)) mapMarkerMode = savedMode;
  } catch {
    // Clustered remains the default when browser storage is unavailable.
  }
  updateMapMarkerModeControls();
}

function updateResultsViewControls() {
  const hasReports = reports.length > 0;
  if (!hasReports) activeResultsView = "table";
  tableViewButton.classList.toggle("active", activeResultsView === "table");
  mapViewButton.classList.toggle("active", activeResultsView === "map");
  tableViewButton.setAttribute("aria-pressed", String(activeResultsView === "table"));
  mapViewButton.setAttribute("aria-pressed", String(activeResultsView === "map"));
  mapViewButton.disabled = !hasReports;
}

function setResultsView(view) {
  if (!["table", "map"].includes(view)) return;
  if (view === "map" && reports.length === 0) return;
  activeResultsView = view;
  renderReports();
}

function inspectorDetail(label, value) {
  const group = document.createElement("div");
  const term = document.createElement("dt");
  const detail = document.createElement("dd");
  term.textContent = label;
  detail.textContent = value ?? "—";
  group.append(term, detail);
  return group;
}

function stationDetailsFor(report) {
  const otherIsSender = report.qso_call
    && report.sender_call.toUpperCase() === report.qso_call.toUpperCase();
  return {
    grid: otherIsSender ? report.sender_locator : report.receiver_locator,
    region: otherIsSender ? report.sender_region : null,
    dxcc: otherIsSender ? report.sender_dxcc : null,
  };
}

function renderInspectorLiveReport(report) {
  const station = stationDetailsFor(report);
  const frequency = report.frequency_hz == null
    ? null
    : `${(report.frequency_hz / 1_000_000).toFixed(3)} MHz`;
  inspectorLiveDetails.replaceChildren(
    inspectorDetail("Direction", relationshipLabel(report.directions)),
    inspectorDetail("Grid", station.grid),
    inspectorDetail("Region", station.region),
    inspectorDetail("DXCC", station.dxcc),
    inspectorDetail("Band", report.band),
    inspectorDetail("Mode", report.mode),
    inspectorDetail("sNR", report.snr_db == null ? null : `${report.snr_db} dB`),
    inspectorDetail("Frequency", frequency),
  );
  inspectorLastSeen.textContent = `Last seen ${displayUtc(report.spot_time_utc)}`;
}

function formatAdifQsoTime(qso) {
  if (!qso.qso_date) return "—";
  return qso.time_on_utc ? `${qso.qso_date} ${qso.time_on_utc}` : qso.qso_date;
}

function renderInspectorQsoRows() {
  inspectorQsoRows.replaceChildren();
  const visibleQsos = inspectorShowsAllQsos ? inspectorQsos : inspectorQsos.slice(0, 10);
  for (const qso of visibleQsos) {
    const row = document.createElement("tr");
    appendCell(row, "Date / time (UTC)", formatAdifQsoTime(qso));
    appendCell(row, "Band", qso.band, "band-cell");
    appendCell(row, "sNR (dB)", qso.snr_db);
    const mode = qso.submode && qso.submode !== qso.mode
      ? `${qso.mode || "—"} / ${qso.submode}`
      : qso.mode;
    appendCell(row, "Mode", mode, "mode-cell");
    appendCell(row, "Frequency (MHz)", qso.frequency_mhz);
    inspectorQsoRows.appendChild(row);
  }
  toggleAllQsosButton.hidden = inspectorQsos.length <= 10;
  toggleAllQsosButton.textContent = inspectorShowsAllQsos
    ? "Show recent 10"
    : `Show all ${inspectorQsos.length.toLocaleString("en-US")}`;
}

function renderInspectorQsoPayload(payload, report) {
  inspectorQsos = payload.qsos || [];
  inspectorShowsAllQsos = false;
  const bandCount = payload.qso_count_band == null
    ? "—"
    : payload.qso_count_band.toLocaleString("en-US");
  const totalCount = payload.qso_count_total == null
    ? "—"
    : payload.qso_count_total.toLocaleString("en-US");
  inspectorQsoSummary.textContent = `${bandCount} on ${report.band || "this band"} / ${totalCount} total`;

  if (payload.status === "not_configured") {
    inspectorQsoStatus.textContent = "Configure an ADI log to see contacts with this station.";
    inspectorQsoStatus.hidden = false;
    inspectorQsoTableWrap.hidden = true;
    toggleAllQsosButton.hidden = true;
    return;
  }
  if (inspectorQsos.length === 0) {
    inspectorQsoStatus.textContent = payload.status === "error"
      ? (payload.message || "The ADI log could not be read.")
      : `No logged QSOs with ${payload.callsign}.`;
    inspectorQsoStatus.hidden = false;
    inspectorQsoTableWrap.hidden = true;
    toggleAllQsosButton.hidden = true;
    return;
  }

  inspectorQsoStatus.hidden = true;
  inspectorQsoTableWrap.hidden = false;
  renderInspectorQsoRows();
}

async function openStationInspector(report) {
  const callsign = report.qso_call;
  if (!callsign) return;

  inspectorRequestId += 1;
  const requestId = inspectorRequestId;
  inspectorCallsign.textContent = callsign;
  copyInspectorCallsignButton.textContent = "Copy call";
  copyInspectorCallsignButton.dataset.defaultText = "Copy call";
  copyInspectorCallsignButton.classList.remove("copied");
  inspectorQrzLink.href = `${QRZ_CALLSIGN_URL}${encodeURIComponent(callsign)}`;
  inspectorQrzLink.setAttribute("aria-label", `Open ${callsign} on QRZ in a new tab`);
  renderInspectorLiveReport(report);
  inspectorQsoSummary.textContent = "Loading local log…";
  inspectorQsoStatus.textContent = "Loading local log…";
  inspectorQsoStatus.hidden = false;
  inspectorQsoTableWrap.hidden = true;
  toggleAllQsosButton.hidden = true;
  if (!stationInspector.open) stationInspector.showModal();

  const cacheKey = `${callsign.toUpperCase()}|${report.band || ""}`;
  try {
    let payload = stationQsoCache.get(cacheKey);
    if (!payload) {
      const params = new URLSearchParams();
      if (report.band) params.set("band", report.band);
      const query = report.band ? `?${params.toString()}` : "";
      const response = await fetch(
        `/api/stations/${encodeURIComponent(callsign)}/qsos${query}`,
        { headers: { Accept: "application/json" } },
      );
      payload = await response.json();
      if (!response.ok) throw new Error(payload.message || "Unable to load QSO history.");
      stationQsoCache.set(cacheKey, payload);
    }
    if (requestId === inspectorRequestId) renderInspectorQsoPayload(payload, report);
  } catch (error) {
    if (requestId !== inspectorRequestId) return;
    inspectorQsoSummary.textContent = "Local log unavailable";
    inspectorQsoStatus.textContent = error.message || "Unable to load QSO history.";
    inspectorQsoStatus.hidden = false;
    inspectorQsoTableWrap.hidden = true;
  }
}

function filteredReports() {
  return reports.filter((report) => {
    const bandMatches = !bandFilter.value || report.band === bandFilter.value;
    const modeMatches = !modeFilter.value || report.mode === modeFilter.value;
    return bandMatches && modeMatches;
  });
}

function isMissingSortValue(value) {
  return value == null
    || value === ""
    || (typeof value === "number" && Number.isNaN(value));
}

function compareSortValues(left, right) {
  const leftIsMissing = isMissingSortValue(left);
  const rightIsMissing = isMissingSortValue(right);
  if (leftIsMissing || rightIsMissing) {
    if (leftIsMissing && rightIsMissing) return 0;
    return leftIsMissing ? 1 : -1;
  }

  const comparison = typeof left === "number" && typeof right === "number"
    ? left - right
    : SORT_COLLATOR.compare(String(left), String(right));
  return sortState.direction === "ascending" ? comparison : -comparison;
}

function compareReports(left, right) {
  const column = SORT_COLUMNS[sortState.key];
  const leftValue = column.value(left);
  const rightValue = column.value(right);
  const leftValues = Array.isArray(leftValue) ? leftValue : [leftValue];
  const rightValues = Array.isArray(rightValue) ? rightValue : [rightValue];

  for (let index = 0; index < leftValues.length; index += 1) {
    const comparison = compareSortValues(leftValues[index], rightValues[index]);
    if (comparison !== 0) return comparison;
  }
  return 0;
}

function sortedFilteredReports() {
  return filteredReports()
    .map((report, index) => ({ report, index }))
    .sort(
      (left, right) => compareReports(left.report, right.report) || left.index - right.index,
    )
    .map(({ report }) => report);
}

function updateSortControls() {
  const activeColumn = SORT_COLUMNS[sortState.key];
  const nextDirection = sortState.direction === "ascending" ? "descending" : "ascending";

  for (const header of sortHeaders) {
    const isActive = header.dataset.sortKey === sortState.key;
    if (isActive) {
      header.setAttribute("aria-sort", sortState.direction);
    } else {
      header.removeAttribute("aria-sort");
    }
    const button = header.querySelector("button");
    const headerKey = header.dataset.sortKey;
    const initialDirection = headerKey === "spot_time_utc" ? "descending" : "ascending";
    button.title = isActive
      ? `${activeColumn.label}: sorted ${sortState.direction}; activate to sort ${nextDirection}`
      : `${SORT_COLUMNS[headerKey].label}: activate to sort ${initialDirection}`;
  }

  sortFieldSelect.value = sortState.key;
  sortDirectionButton.textContent = sortState.direction === "ascending"
    ? "Ascending ↑"
    : "Descending ↓";
  sortDirectionButton.setAttribute(
    "aria-label",
    `${activeColumn.label} is sorted ${sortState.direction}; activate to sort ${nextDirection}`,
  );
  updateResultsOptionsSummary();
}

function setReportSort(key, direction) {
  if (!SORT_COLUMNS[key] || !["ascending", "descending"].includes(direction)) return;
  sortState = { key, direction };
  updateSortControls();
  renderReports();
}

function toggleReportSort(key) {
  const direction = key === sortState.key
    ? (sortState.direction === "ascending" ? "descending" : "ascending")
    : (key === "spot_time_utc" ? "descending" : "ascending");
  setReportSort(key, direction);
}

function renderReports() {
  reportRows.replaceChildren();
  const visibleReports = sortedFilteredReports();
  updateSortControls();
  updateResultsViewControls();

  for (const report of visibleReports) {
    const row = document.createElement("tr");
    appendCell(row, "Report time (UTC)", displayUtc(report.spot_time_utc));
    appendCell(row, "Direction", relationshipLabel(report.directions), "direction-cell");
    const senderIsOtherStation = report.qso_call === report.sender_call;
    const receiverIsOtherStation = report.qso_call === report.receiver_call;
    appendQrzCallsignCell(row, "Sender", report.sender_call, senderIsOtherStation);
    appendCell(row, "Sender grid", report.sender_locator);
    appendQrzCallsignCell(row, "Recv", report.receiver_call, receiverIsOtherStation);
    appendCell(row, "Recv grid", report.receiver_locator);
    const qsoText = report.qso_count_total == null
      ? null
      : `${report.qso_count_band == null ? "—" : report.qso_count_band.toLocaleString("en-US")}/${report.qso_count_total.toLocaleString("en-US")}`;
    const isUnworked = report.qso_count_band === 0 && report.qso_count_total === 0;
    const qsoClass = isUnworked
      ? "qso-cell unworked-station"
      : report.qso_count_band > 0
        ? "qso-cell band-worked"
        : report.qso_count_total > 0
          ? "qso-cell other-band-worked"
          : "qso-cell";
    if (isUnworked) row.classList.add("unworked-station-row");
    const qsoCell = appendCell(row, "QSOs B/T", null, qsoClass);
    if (report.qso_call) {
      const bandLabel = report.band || "this band";
      const qsoDescription = report.qso_count_total == null
        ? `No ADIF count available for ${report.qso_call}`
        : `${report.qso_count_band ?? 0} QSOs with ${report.qso_call} on ${bandLabel}; ${report.qso_count_total} across all bands`;
      const button = document.createElement("button");
      button.className = "qso-inspector-button";
      button.type = "button";
      button.textContent = qsoText ?? "—";
      button.title = `${qsoDescription}. Open station inspector.`;
      button.setAttribute("aria-label", `${qsoDescription}. Open station inspector.`);
      button.addEventListener("click", () => void openStationInspector(report));
      qsoCell.replaceChildren(button);
    }
    appendTruncatedCell(row, "Sender region", report.sender_region);
    appendTruncatedCell(row, "Sender DXCC", report.sender_dxcc);
    appendCell(row, "Band", report.band, "band-cell");
    appendCell(row, "sNR (dB)", report.snr_db, "snr-cell");
    appendCell(row, "Mode", report.mode, "mode-cell");
    appendCell(row, "F (MHz)", (report.frequency_hz / 1_000_000).toFixed(3));
    reportRows.appendChild(row);
  }

  resultCount.textContent = `${visibleReports.length} of ${reports.length} report${reports.length === 1 ? "" : "s"}`;
  if (visibleReports.length === 0) {
    tableWrap.hidden = true;
    mapWrap.hidden = true;
    setStatus("No reports match the selected band and mode filters.", "empty");
  } else {
    statusMessage.hidden = true;
    tableWrap.hidden = activeResultsView !== "table";
    mapWrap.hidden = activeResultsView !== "map";
    if (activeResultsView === "map") renderReportMap(visibleReports);
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
  updateResultsOptionsSummary();
}

async function fetchReports({ automatic = false } = {}) {
  if (fetchInProgress) return;
  const formIsValid = automatic ? form.checkValidity() : form.reportValidity();
  if (!formIsValid) {
    scheduleAutoRefresh();
    return;
  }

  const hasCurrentResults = reports.length > 0;
  fetchInProgress = true;
  resultsPanel.setAttribute("aria-busy", "true");
  if (refreshTimer !== null) {
    window.clearTimeout(refreshTimer);
    refreshTimer = null;
  }

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
  if (!hasCurrentResults) {
    tableWrap.hidden = true;
    mapWrap.hidden = true;
    filterBar.hidden = true;
    fetchMeta.hidden = true;
    setStatus("Contacting PSK Reporter…");
  }
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

    if (!queryPanelHasAutoCollapsed) {
      const focusWasInsideQueryPanel = stationQueryPanel.contains(document.activeElement);
      stationQueryPanel.open = false;
      queryPanelHasAutoCollapsed = true;
      if (!automatic && focusWasInsideQueryPanel) stationQuerySummary.focus();
    }

    const refreshedAtUtc = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
    lastDisplayRefreshTime.dateTime = refreshedAtUtc;
    lastDisplayRefreshTime.textContent = displayUtc(refreshedAtUtc);
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
      configureFilters();
      updateResultsViewControls();
      resultCount.textContent = "0 reports";
      tableWrap.hidden = true;
      mapWrap.hidden = true;
      setStatus("No reception reports were found for the selected direction and report interval.", "empty");
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
    if (!traceRendered) {
      renderXmlTrace([], error.message || "Unable to capture the upstream trace.");
    }
    const message = error.message || "Unable to load reports.";
    setStatus(
      hasCurrentResults
        ? `Refresh failed; continuing to show the previous results. ${message}`
        : message,
      "error",
    );
  } finally {
    setLookbackSelection(selectedLookback);
    fetchInProgress = false;
    resultsPanel.removeAttribute("aria-busy");
    fetchButton.disabled = false;
    fetchButton.querySelector("span").textContent = "Fetch reports";
    scheduleAutoRefresh();
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
form.addEventListener("input", updateStationQuerySummary);
form.addEventListener("change", updateStationQuerySummary);
fetchButton.addEventListener("click", () => void fetchReports());
lookbackSelect.addEventListener("change", rememberLookbackPreference);
refreshIntervalSelect.addEventListener("change", rememberRefreshPreference);
sentBy.addEventListener("change", () => keepOneDirectionSelected(sentBy));
recvBy.addEventListener("change", () => keepOneDirectionSelected(recvBy));
bandFilter.addEventListener("change", () => {
  updateResultsOptionsSummary();
  renderReports();
});
modeFilter.addEventListener("change", () => {
  updateResultsOptionsSummary();
  renderReports();
});
tableViewButton.addEventListener("click", () => setResultsView("table"));
mapViewButton.addEventListener("click", () => setResultsView("map"));
clusteredMapButton.addEventListener("click", () => setMapMarkerMode("clustered"));
individualMapButton.addEventListener("click", () => setMapMarkerMode("individual"));
for (const header of sortHeaders) {
  header.querySelector("button").addEventListener("click", () => {
    toggleReportSort(header.dataset.sortKey);
  });
}
sortFieldSelect.addEventListener("change", () => {
  const key = sortFieldSelect.value;
  const direction = key === sortState.key
    ? sortState.direction
    : (key === "spot_time_utc" ? "descending" : "ascending");
  setReportSort(key, direction);
});
sortDirectionButton.addEventListener("click", () => toggleReportSort(sortState.key));
reloadAdifButton.addEventListener("click", () => void reloadAdif());
closeInspectorButton.addEventListener("click", () => stationInspector.close());
copyInspectorCallsignButton.addEventListener("click", () => {
  void copyCallsign(inspectorCallsign.textContent, copyInspectorCallsignButton);
});
stationInspector.addEventListener("click", (event) => {
  if (event.target === stationInspector) stationInspector.close();
});
toggleAllQsosButton.addEventListener("click", () => {
  inspectorShowsAllQsos = !inspectorShowsAllQsos;
  renderInspectorQsoRows();
});

updateSortControls();
updateResultsViewControls();
restoreMapMarkerMode();
restoreLookbackPreference();
restoreRefreshPreference();
updateStationQuerySummary();
updateResultsOptionsSummary();
loadCallsignHistory();
void loadAppConfig();
void loadAdifStatus();
scheduleAutoRefresh();
