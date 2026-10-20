import { css } from "lit";

// Uses Home Assistant theme variables so the panel follows light/dark themes.
export const styles = css`
  :host {
    display: block;
    height: 100vh;
    height: 100dvh;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    font-family: var(--paper-font-body1_-_font-family, system-ui, sans-serif);
    --radius: 12px;
    --line: var(--divider-color, rgba(127, 127, 127, 0.25));
    --card: var(--card-background-color, #fff);
    --accent: var(--primary-color, #03a9f4);
    --muted: var(--secondary-text-color, #777);
    --danger: var(--error-color, #db4437);
    --ok: var(--success-color, #43a047);
    --warn: var(--warning-color, #ffa600);
  }
  .layout {
    display: flex;
    height: 100%;
    position: relative;
  }
  nav {
    width: 260px;
    flex: none;
    border-right: 1px solid var(--line);
    display: flex;
    flex-direction: column;
    padding: 12px;
    gap: 8px;
    box-sizing: border-box;
    background: var(--sidebar-background-color, var(--card));
  }
  .narrow nav {
    position: absolute;
    z-index: 3;
    top: 57px;
    bottom: 0;
    left: 0;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  }
  .convs {
    overflow-y: auto;
    flex: 1;
  }
  .conv {
    display: flex;
    align-items: center;
    padding: 8px 10px;
    border-radius: 8px;
    cursor: pointer;
    gap: 4px;
  }
  .conv:hover,
  .conv.active {
    background: rgba(127, 127, 127, 0.12);
  }
  .conv-title {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 14px;
  }
  .conv .icon {
    visibility: hidden;
  }
  .conv:hover .icon {
    visibility: visible;
  }
  main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  header {
    height: 56px;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 12px;
    border-bottom: 1px solid var(--line);
    flex: none;
  }
  .title {
    flex: 1;
    font-size: 18px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px max(16px, calc((100% - 820px) / 2));
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .msg {
    line-height: 1.5;
    overflow-wrap: anywhere;
  }
  .msg.user {
    align-self: flex-end;
    background: var(--accent);
    color: var(--text-primary-color, #fff);
    padding: 8px 14px;
    border-radius: var(--radius) var(--radius) 4px var(--radius);
    max-width: 80%;
    white-space: pre-wrap;
  }
  .md :first-child {
    margin-top: 0;
  }
  .md :last-child {
    margin-bottom: 0;
  }
  .md pre,
  pre {
    background: rgba(127, 127, 127, 0.1);
    padding: 8px 10px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 12.5px;
    margin: 6px 0;
    white-space: pre;
  }
  .msg-actions {
    align-self: flex-end;
    display: flex;
    gap: 4px;
    margin-top: -4px;
  }
  .editing {
    color: var(--accent);
  }
  .md pre {
    position: relative;
  }
  .md pre .copy {
    position: absolute;
    top: 4px;
    right: 4px;
    opacity: 0;
    background: var(--card);
  }
  .md pre:hover .copy,
  .md pre .copy:focus-visible {
    opacity: 1;
  }
  @media (hover: none) {
    .md pre .copy {
      opacity: 1;
    }
  }
  .md code {
    font-size: 0.92em;
  }
  .md table {
    border-collapse: collapse;
  }
  .md td,
  .md th {
    border: 1px solid var(--line);
    padding: 4px 8px;
  }
  .md a {
    color: var(--accent);
  }
  .typing span {
    display: inline-block;
    width: 6px;
    height: 6px;
    margin-right: 4px;
    border-radius: 50%;
    background: var(--muted);
    animation: blink 1.2s infinite;
  }
  .typing span:nth-child(2) {
    animation-delay: 0.2s;
  }
  .typing span:nth-child(3) {
    animation-delay: 0.4s;
  }
  @keyframes blink {
    50% {
      opacity: 0.2;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .typing span {
      animation: none;
    }
  }
  .tool {
    border: 1px solid var(--line);
    border-radius: 10px;
    background: var(--card);
    font-size: 13.5px;
    position: relative;
  }
  .tool.waiting {
    border-color: var(--accent);
  }
  .tool.waiting.risky {
    border-color: var(--warn);
  }
  .tool summary {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    cursor: pointer;
    list-style: none;
  }
  .tool summary::-webkit-details-marker {
    display: none;
  }
  .tool details > :not(summary) {
    margin: 0 10px 8px;
  }
  .badge {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    flex: none;
    background: rgba(127, 127, 127, 0.18);
  }
  .ok .badge {
    background: var(--ok);
    color: #fff;
  }
  .error .badge {
    background: var(--danger);
    color: #fff;
  }
  .tool-name {
    font-weight: 500;
    flex: none;
  }
  .tool-summary {
    color: var(--muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
  }
  .tag {
    font-size: 11px;
    color: var(--muted);
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0 6px;
  }
  .diff span {
    display: block;
  }
  .diff .add {
    color: var(--ok);
  }
  .diff .del {
    color: var(--danger);
  }
  .diff .hunk {
    color: var(--muted);
  }
  pre.result,
  pre.args {
    max-height: 240px;
    overflow: auto;
    white-space: pre-wrap;
  }
  .approval {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    padding: 0 10px 10px;
  }
  .approval .reason {
    width: 100%;
    font-size: 13px;
  }
  .approval input {
    flex: 1;
    min-width: 140px;
  }
  .undo {
    position: absolute;
    right: 8px;
    top: 6px;
  }
  .notice {
    font-size: 13px;
    color: var(--muted);
    text-align: center;
  }
  .notice.error {
    color: var(--danger);
  }
  .welcome {
    margin: auto 0;
    text-align: center;
    color: var(--muted);
  }
  .welcome h2 {
    color: var(--primary-text-color);
    font-weight: 500;
  }
  .tips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    margin-top: 16px;
  }
  .tip {
    border: 1px solid var(--line);
    background: var(--card);
    color: var(--primary-text-color);
    border-radius: 18px;
    padding: 8px 14px;
    cursor: pointer;
    font: inherit;
    font-size: 13.5px;
  }
  footer {
    padding: 8px max(16px, calc((100% - 820px) / 2)) 12px;
    flex: none;
  }
  .composer {
    display: flex;
    gap: 8px;
    align-items: flex-end;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    padding: 8px;
    background: var(--card);
  }
  textarea {
    flex: 1;
    border: none;
    resize: none;
    background: transparent;
    color: inherit;
    font: inherit;
    font-size: 15px;
    outline: none;
    max-height: 240px;
    padding: 6px;
  }
  .meta {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-top: 6px;
    font-size: 12.5px;
    color: var(--muted);
    flex-wrap: wrap;
  }
  .usage {
    margin-left: auto;
    white-space: nowrap;
  }
  select,
  input {
    background: var(--card);
    color: inherit;
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 4px 6px;
    font: inherit;
  }
  input.model {
    width: 200px;
  }
  button {
    font: inherit;
    cursor: pointer;
    border-radius: 8px;
    border: 1px solid transparent;
    padding: 6px 14px;
  }
  button.primary {
    background: var(--accent);
    color: var(--text-primary-color, #fff);
  }
  button.danger {
    background: var(--danger);
    color: #fff;
  }
  button.ghost {
    background: transparent;
    color: var(--primary-text-color);
    border-color: var(--line);
  }
  button.icon {
    background: transparent;
    color: var(--muted);
    padding: 4px 8px;
  }
  button.small {
    padding: 2px 8px;
    font-size: 12px;
  }
  button.wide {
    width: 100%;
  }
  button:focus-visible,
  .tip:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .empty {
    padding: 32px;
    color: var(--muted);
  }
`;
