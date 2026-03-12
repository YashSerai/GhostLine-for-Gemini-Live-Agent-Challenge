import { useSessionWebSocket } from "./session/useSessionWebSocket";
import type {
  SessionConnectionStatus,
  TransportLogEntry,
} from "./session/sessionTypes";

const subtitleRows = [
  ["Operator", "Transcript feed will appear here once live audio is wired."],
  ["User", "User speech transcript will be shown here during the call."],
] as const;

const statusLabels: Record<SessionConnectionStatus, string> = {
  idle: "Idle",
  connecting: "Connecting",
  connected: "Connected",
  reconnecting: "Reconnecting",
  disconnected: "Disconnected",
  error: "Connection Error",
};

function formatTransportTime(timestamp: string): string {
  const parsedDate = new Date(timestamp);
  if (Number.isNaN(parsedDate.valueOf())) {
    return timestamp;
  }

  return parsedDate.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatEnvelopeSummary(entry: TransportLogEntry): string {
  if (entry.direction === "sent") {
    return `Sent ${entry.envelope.type}`;
  }

  return `Received ${entry.envelope.type}`;
}

function getOperatorPlaceholder(
  connectionStatus: SessionConnectionStatus,
  lastError: string | null,
): string {
  if (connectionStatus === "connected") {
    return "Session transport connected. Live operator audio is still a placeholder until later prompts wire the media path.";
  }

  if (
    connectionStatus === "connecting" ||
    connectionStatus === "reconnecting"
  ) {
    return "Connecting the hotline transport now. Operator audio, transcripts, and live guidance are intentionally not implemented yet.";
  }

  if (lastError) {
    return `Transport is waiting for a clean reconnect. Last transport error: ${lastError}`;
  }

  return "Operator text will render here before and during live speech playback. Permission requests, task instructions, and recovery lines are intentionally not implemented yet.";
}

function App() {
  const {
    connect,
    disconnect,
    lastError,
    recentMessages,
    reconnectAttempt,
    sessionId,
    sessionUrl,
    status,
  } = useSessionWebSocket();

  const isTransportActive =
    status === "connected" ||
    status === "connecting" ||
    status === "reconnecting";
  const connectionLabel = statusLabels[status];
  const operatorPlaceholder = getOperatorPlaceholder(status, lastError);

  const hudRows = [
    ["Protocol Step", "Awaiting session"],
    ["Transport", connectionLabel],
    ["Session ID", sessionId ? sessionId.slice(0, 8) : "Pending"],
    ["Reconnect Attempts", `${reconnectAttempt}`],
    ["Last Envelope", recentMessages[0]?.envelope.type ?? "None"],
    ["Verification", "Not started"],
    ["Operator State", isTransportActive ? "Linked" : "Standby"],
    ["Case Status", "Unclassified"],
  ] as const;

  const transportRows = recentMessages.slice(0, 4);

  return (
    <div className="hotline-shell">
      <header className="hero-panel panel">
        <div>
          <p className="eyebrow">Ghostline // Live Agent Shell</p>
          <h1>HauntLens Containment Hotline</h1>
          <p className="hero-copy">
            The Archivist, Containment Desk is standing by. This shell now
            includes a reusable client WebSocket session manager and transport
            state, while voice, camera, and Gemini remain intentionally out of
            scope for this prompt.
          </p>
        </div>

        <div className="hero-status">
          <span className={`status-pill status-pill-${status}`}>
            Transport {connectionLabel}
          </span>
          <span className="status-pill">ws/session gateway</span>
          <span className="status-pill">Reconnect {reconnectAttempt}/3</span>
          {lastError ? (
            <span className="status-pill status-pill-error">Last error recorded</span>
          ) : null}
        </div>
      </header>

      <main className="stage-grid">
        <section className="panel operator-panel" aria-label="Operator panel">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Operator Panel</p>
              <h2>The Archivist, Containment Desk</h2>
            </div>
            <span className={`panel-tag panel-tag-${status}`}>{connectionLabel}</span>
          </div>

          <div className="operator-script">
            <p className="operator-label">Reserved Operator Text</p>
            <blockquote>{operatorPlaceholder}</blockquote>
          </div>

          <div className="operator-meta">
            <div>
              <span className="meta-label">Call Mode</span>
              <strong>Voice-first placeholder</strong>
            </div>
            <div>
              <span className="meta-label">Transport</span>
              <strong>{sessionUrl}</strong>
            </div>
          </div>

          <div className="transport-monitor">
            <p className="operator-label">Session Bridge</p>
            <div className="transport-list">
              {transportRows.length > 0 ? (
                transportRows.map((entry) => (
                  <article className="transport-row" key={`${entry.timestamp}-${entry.envelope.type}`}>
                    <div>
                      <span className={`transport-direction transport-direction-${entry.direction}`}>
                        {entry.direction}
                      </span>
                      <strong>{formatEnvelopeSummary(entry)}</strong>
                    </div>
                    <span className="transport-time">{formatTransportTime(entry.timestamp)}</span>
                  </article>
                ))
              ) : (
                <article className="transport-row transport-row-empty">
                  Start Call opens the socket and immediately sends a
                  `client_connect` envelope. Incoming acknowledgements will be
                  listed here.
                </article>
              )}
            </div>
          </div>
        </section>

        <section className="panel camera-panel" aria-label="Camera preview area">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Camera Preview</p>
              <h2>Room Feed</h2>
            </div>
            <span className="panel-tag">Offline</span>
          </div>

          <div className="camera-frame">
            <div className="frame-overlay">
              <span>Preview reserved for in-call camera access</span>
              <small>No media stream connected</small>
            </div>
          </div>
        </section>

        <section className="panel subtitles-panel" aria-label="Subtitles area">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Subtitles</p>
              <h2>Conversation Transcript</h2>
            </div>
            <span className="panel-tag">Placeholder</span>
          </div>

          <div className="subtitle-list">
            {subtitleRows.map(([speaker, line]) => (
              <article className="subtitle-row" key={speaker}>
                <span className="subtitle-speaker">{speaker}</span>
                <p>{line}</p>
              </article>
            ))}
          </div>
        </section>

        <aside className="panel hud-panel" aria-label="Grounding HUD area">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Grounding HUD</p>
              <h2>Session Surface</h2>
            </div>
            <span className={`panel-tag panel-tag-${status}`}>{connectionLabel}</span>
          </div>

          <dl className="hud-grid">
            {hudRows.map(([label, value]) => (
              <div className="hud-row" key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </aside>
      </main>

      <footer className="panel control-bar" aria-label="Control bar">
        <div>
          <p className="panel-kicker">Control Bar</p>
          <h2>Session Controls</h2>
          <p className="control-copy">
            The button below controls the client transport lifecycle only. It
            opens the session socket after Start Call, closes it cleanly on
            disconnect, and avoids duplicate reconnect loops.
          </p>
        </div>

        <div className="control-actions">
          <button
            type="button"
            className={`start-call-button start-call-button-${status}`}
            onClick={isTransportActive ? disconnect : connect}
          >
            {isTransportActive ? "Disconnect" : "Start Call"}
          </button>
          <span className="control-chip">{connectionLabel}</span>
          <span className="control-chip">
            {recentMessages.length} transport event{recentMessages.length === 1 ? "" : "s"}
          </span>
        </div>
      </footer>
    </div>
  );
}

export default App;
