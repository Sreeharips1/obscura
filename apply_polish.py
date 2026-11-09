# apply_polish.py  -- run from the repo root
import os, re, sys

if not os.path.isdir("frontend/src"):
    sys.exit("Run this from the repo root.")


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(data)
    print("wrote", path)


# ====================================================================
# riskInfo.jsx
# ====================================================================
write("frontend/src/riskInfo.jsx", r'''const ICONS = {
  phone: <path d="M5 4h4l2 5-2.5 1.5a11 11 0 005 5L15 13l5 2v4a2 2 0 01-2 2A16 16 0 013 6a2 2 0 012-2z" />,
  mail: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M3 7l9 6 9-6" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0116 0" />
    </>
  ),
  idcard: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <circle cx="9" cy="11" r="2" />
      <path d="M6 16c.6-1.6 2-2.4 3-2.4s2.4.8 3 2.4M14 10h4M14 14h4" />
    </>
  ),
  card: (
    <>
      <rect x="2.5" y="5" width="19" height="14" rx="2" />
      <path d="M2.5 10h19M6 15h4" />
    </>
  ),
  bank: <path d="M3 10l9-6 9 6M5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 20h18" />,
  key: (
    <>
      <circle cx="8" cy="15" r="4" />
      <path d="M11 12l9-9M16 7l3 3" />
    </>
  ),
  lock: (
    <>
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V8a4 4 0 018 0v3" />
    </>
  ),
  link: <path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1M14 10a4 4 0 00-5.7 0l-3 3A4 4 0 0011 18.7l1-1" />,
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3a14 14 0 010 18M12 3a14 14 0 000 18" />
    </>
  ),
  device: (
    <>
      <rect x="7" y="2.5" width="10" height="19" rx="2" />
      <path d="M11 18.5h2" />
    </>
  ),
  pin: (
    <>
      <path d="M12 21s7-6.2 7-11a7 7 0 10-14 0c0 4.8 7 11 7 11z" />
      <circle cx="12" cy="10" r="2.5" />
    </>
  ),
  building: <path d="M4 21V5a1 1 0 011-1h8a1 1 0 011 1v16M14 10h5a1 1 0 011 1v10M3 21h18M8 8h2M8 12h2M8 16h2" />,
  briefcase: (
    <>
      <rect x="3" y="7" width="18" height="13" rx="2" />
      <path d="M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2M3 13h18" />
    </>
  ),
  folder: <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />,
  shield: (
    <>
      <path d="M12 3l8 3v6c0 4.5-3.2 8-8 9-4.8-1-8-4.5-8-9V6z" />
      <path d="M12 8v4M12 15.5v.01" />
    </>
  ),
  qr: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <path d="M14 14h3v3M21 14v.01M14 21h3M21 17v4" />
    </>
  ),
  barcode: <path d="M4 5v14M7 5v14M11 5v14M14 5v14M18 5v14M20 5v14" />,
  face: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M9 10h.01M15 10h.01M8.5 14.5a4.5 4.5 0 007 0" />
    </>
  ),
  car: <path d="M3 15v-3l2-5h14l2 5v3zM6 18v-3M18 18v-3M5 12h14" />,
  monitor: (
    <>
      <rect x="3" y="4" width="18" height="12" rx="2" />
      <path d="M8 20h8M12 16v4" />
    </>
  ),
  calendar: (
    <>
      <rect x="4" y="5" width="16" height="16" rx="2" />
      <path d="M4 10h16M8 3v4M16 3v4" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 8v.01" />
    </>
  ),
};

function Svg({ name, size = 16 }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {ICONS[name] || ICONS.shield}
    </svg>
  );
}

// type: [icon, group, title, why it is risky]
const INFO = {
  EMAIL: ["mail", "contact", "Email address", "It points straight to you. It is used for spam and phishing, and it links your messages to your accounts and identity."],
  PHONE: ["phone", "contact", "Phone number", "It identifies you directly and is used for scam calls, SIM-swap fraud and tracking. It is often tied to your bank and one-time codes."],
  AADHAAR_LIKE: ["idcard", "id", "Aadhaar-style ID number", "A national ID number. With a name it enables identity theft and fake KYC, and a leaked ID number cannot be changed."],
  PAN_LIKE: ["idcard", "id", "PAN-style tax ID", "A tax ID linked to your finances. Combined with other details it enables identity fraud and fake loan or account applications."],
  NATIONAL_ID: ["idcard", "id", "National ID", "A government ID number. It is used for identity theft and cannot easily be replaced once leaked."],
  PASSPORT_NUMBER: ["idcard", "id", "Passport number", "A passport number can be used for identity fraud and fake travel or account applications."],
  DRIVER_LICENSE: ["idcard", "id", "Driver licence number", "A licence number identifies you officially and is used for identity fraud."],
  IFSC_CODE: ["bank", "finance", "Bank branch code", "Low risk alone, but together with an account number it points to your bank account."],
  BANK_ACCOUNT: ["bank", "finance", "Bank account number", "Can be used for unauthorised debits, fraud and social-engineering calls pretending to be your bank."],
  UPI_ID: ["bank", "finance", "UPI ID", "Anyone with your UPI ID can send payment requests in your name, which helps payment scams."],
  CARD_NUMBER_LIKE: ["card", "finance", "Payment card number", "Card numbers can be used for fraudulent payments. Payment details should never be shared with an outside service."],
  IP_ADDRESS: ["globe", "device", "IP address", "Reveals your rough location and network, and can be used to track or target a device."],
  MAC_ADDRESS: ["device", "device", "Device MAC address", "A hardware ID for your device. It can follow one device across networks and be used to fingerprint it."],
  IMEI: ["device", "device", "Phone IMEI number", "A unique number for a phone handset. It identifies the device and is used in theft and cloning scams."],
  SENSITIVE_URL: ["link", "secret", "Link with a token", "This link seems to contain a token or key. Anyone who has it may be able to log in or see your data."],
  PERSON_NAME: ["user", "identity", "Person name", "A name ties the rest of your text to a real person. Together with other details it makes you identifiable."],
  USERNAME: ["user", "identity", "Username", "A username identifies an account and can be searched across websites to find you."],
  ADDRESS: ["pin", "location", "Address", "A home address shows where you live, which makes stalking, burglary and fraud easier."],
  LOCATION: ["pin", "location", "Location", "Places you live or visit reveal your routine and narrow down who you are."],
  FACILITY: ["pin", "location", "Named place", "Places such as your office or school reveal where you spend your time."],
  ORGANIZATION: ["building", "work", "Organization", "Your workplace or school helps identify you and may reveal confidential business relationships."],
  EMPLOYER: ["briefcase", "work", "Employer", "Your employer, together with your name, makes you easy to find and can expose company information."],
  PROJECT_NAME: ["folder", "work", "Project name", "Internal project names can expose unreleased or confidential work."],
  CONFIDENTIAL_CONTEXT: ["lock", "work", "Confidential wording", "The wording suggests this content is meant to stay private, such as internal or secret material."],
  DATE: ["calendar", "identity", "Date", "Dates such as birthdays are used to confirm identity and to answer security questions."],
  PASSWORD: ["key", "secret", "Password", "A password gives full access to an account. It is never sent to the AI."],
  API_KEY_OR_TOKEN: ["key", "secret", "API key or token", "Keys and tokens work like passwords. Anyone who sees one can use your services and run up costs. It is never sent."],
  JWT_TOKEN: ["key", "secret", "Login token", "Whoever holds this token can act as you until it expires. It is never sent."],
  PRIVATE_KEY: ["lock", "secret", "Private key", "A private key proves your identity to servers. If it leaks it must be replaced. It is never sent."],
  QR_CODE: ["qr", "visual", "QR code", "A QR code can hide a link, a payment request or a login. Scanning it can expose your account or data."],
  BARCODE: ["barcode", "visual", "Barcode", "Barcodes can encode tickets, IDs or account numbers that anyone can scan."],
  FACE: ["face", "visual", "Face", "A face identifies you and can be matched to your accounts and other photos. Other people's faces are private too."],
  LICENSE_PLATE: ["car", "visual", "License plate", "A plate links a vehicle to its owner and can be used to track movements."],
  DEVICE_SCREEN: ["monitor", "visual", "Screen", "Screens often show private messages, notifications, accounts and codes that can be read in a photo."],
};

const GROUP_ORDER = {
  secret: 0, id: 1, finance: 2, contact: 3, identity: 4,
  location: 5, device: 6, work: 7, visual: 8, general: 9,
};

function humanize(type) {
  const text = String(type || "").replace(/_/g, " ").toLowerCase();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function riskInfo(type) {
  const row = INFO[type];

  if (!row) {
    return {
      icon: "shield",
      group: "general",
      title: humanize(type) || "Sensitive information",
      why: "This looks like personal or sensitive information that could help identify you.",
    };
  }

  return { icon: row[0], group: row[1], title: row[2], why: row[3] };
}

export function TypeIcon({ type, size = 16 }) {
  const info = riskInfo(type);

  return (
    <span className={`typeIcon ${info.group}`} title={info.title}>
      <Svg name={info.icon} size={size} />
    </span>
  );
}

// Hover or focus the (i) to read why this kind of data is risky.
export function WhyTip({ type, risk }) {
  const info = riskInfo(type);

  return (
    <span className="whyTip">
      <button
        type="button"
        className="whyBtn"
        aria-label={`Why is ${info.title} risky?`}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
        }}
      >
        <Svg name="info" size={15} />
      </button>

      <span className="whyPop" role="tooltip">
        <b>{info.title}</b>
        <span>{info.why}</span>
        {risk && <em>Risk level: {String(risk).toLowerCase()}</em>}
      </span>
    </span>
  );
}

export function RiskExplainer({ kinds = [] }) {
  const unique = [...new Set(kinds)].sort(
    (a, b) =>
      (GROUP_ORDER[riskInfo(a).group] ?? 9) -
      (GROUP_ORDER[riskInfo(b).group] ?? 9),
  );

  if (unique.length === 0) return null;

  return (
    <details className="explain" open>
      <summary>Why these matter</summary>

      <ul className="explainList">
        {unique.map((kind) => {
          const info = riskInfo(kind);

          return (
            <li key={kind}>
              <TypeIcon type={kind} size={18} />

              <div>
                <b>{info.title}</b>
                <p>{info.why}</p>
              </div>
            </li>
          );
        })}
      </ul>
    </details>
  );
}
''')

# ====================================================================
# markdown.jsx
# ====================================================================
write("frontend/src/markdown.jsx", r'''import { CopyButton } from "./ui.jsx";

// A small, safe Markdown renderer. It builds React elements only
// (no raw HTML), and links must be http, https or mailto.

const LIST_ITEM = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/;
const SEPARATOR = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/;

const INLINE_SOURCE =
  "(`+)([^`]+?)\\1" +
  "|\\*\\*([^\\s](?:[^\\n]*?[^\\s])?)\\*\\*" +
  "|~~([^\\s](?:[^\\n]*?[^\\s])?)~~" +
  "|\\[([^\\]\\n]+)\\]\\((https?:\\/\\/[^\\s)]+|mailto:[^\\s)]+)\\)" +
  "|(https?:\\/\\/[^\\s<>]+)" +
  "|\\*([^\\s*](?:[^*\\n]*?[^\\s*])?)\\*";

function inlineLine(line, depth, prefix) {
  const nodes = [];
  const re = new RegExp(INLINE_SOURCE, "g");
  let last = 0;
  let count = 0;
  let m;

  while ((m = re.exec(line)) !== null) {
    if (m.index > last) nodes.push(line.slice(last, m.index));

    const key = `${prefix}-${count++}`;
    const nested = (value) =>
      depth < 3 ? inlineLine(value, depth + 1, key) : value;

    if (m[2] !== undefined) {
      nodes.push(<code key={key} className="mdCode">{m[2]}</code>);
    } else if (m[3] !== undefined) {
      nodes.push(<strong key={key}>{nested(m[3])}</strong>);
    } else if (m[4] !== undefined) {
      nodes.push(<del key={key}>{nested(m[4])}</del>);
    } else if (m[5] !== undefined) {
      nodes.push(
        <a key={key} href={m[6]} target="_blank" rel="noopener noreferrer">
          {m[5]}
        </a>,
      );
    } else if (m[7] !== undefined) {
      let url = m[7];
      let trail = "";
      const t = url.match(/[.,;:!?)\]]+$/);

      if (t) {
        trail = t[0];
        url = url.slice(0, url.length - trail.length);
      }

      nodes.push(
        <a key={key} href={url} target="_blank" rel="noopener noreferrer">
          {url}
        </a>,
      );

      if (trail) nodes.push(trail);
    } else if (m[8] !== undefined) {
      nodes.push(<em key={key}>{nested(m[8])}</em>);
    }

    last = re.lastIndex;
  }

  if (last < line.length) nodes.push(line.slice(last));

  return nodes;
}

// Single line breaks are kept, because AI drafts (emails) rely on them.
function inline(text) {
  const out = [];

  String(text)
    .split("\n")
    .forEach((line, index) => {
      if (index > 0) out.push(<br key={`br${index}`} />);
      out.push(...inlineLine(line, 0, `l${index}`));
    });

  return out;
}

function isTableStart(lines, i) {
  return (
    lines[i].includes("|") &&
    i + 1 < lines.length &&
    lines[i + 1].includes("|") &&
    lines[i + 1].includes("-") &&
    SEPARATOR.test(lines[i + 1])
  );
}

function startsBlock(lines, i) {
  const line = lines[i];

  return (
    /^\s*(`{3,}|~{3,})/.test(line) ||
    /^\s{0,3}#{1,6}\s/.test(line) ||
    /^\s{0,3}>/.test(line) ||
    /^\s{0,3}([-*_])(\s*\1){2,}\s*$/.test(line) ||
    LIST_ITEM.test(line) ||
    isTableStart(lines, i)
  );
}

function collectList(lines, start) {
  const items = [];
  let i = start;

  while (i < lines.length) {
    const line = lines[i];
    const m = line.match(LIST_ITEM);

    if (m) {
      items.push({
        indent: m[1].replace(/\t/g, "    ").length,
        ordered: /\d/.test(m[2]),
        number: parseInt(m[2], 10),
        text: m[3],
        extra: [],
      });
      i++;
      continue;
    }

    if (!line.trim()) {
      let j = i + 1;
      while (j < lines.length && !lines[j].trim()) j++;

      if (j < lines.length && LIST_ITEM.test(lines[j])) {
        i = j;
        continue;
      }

      break;
    }

    if (items.length && /^\s{2,}\S/.test(line)) {
      items[items.length - 1].extra.push(line.trim());
      i++;
      continue;
    }

    break;
  }

  return [items, i];
}

function nestItems(items) {
  const root = { indent: -1, children: [] };
  const stack = [root];

  for (const item of items) {
    const node = { ...item, children: [] };

    while (stack.length > 1 && stack[stack.length - 1].indent >= node.indent) {
      stack.pop();
    }

    stack[stack.length - 1].children.push(node);
    stack.push(node);
  }

  return root.children;
}

function parseBlocks(source) {
  const lines = source.split("\n");
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) {
      i++;
      continue;
    }

    const fence = line.match(/^\s*(`{3,}|~{3,})\s*([\w+-]*)\s*$/);

    if (fence) {
      const closing = new RegExp("^\\s*" + fence[1][0] + "{3,}\\s*$");
      const code = [];
      i++;

      while (i < lines.length && !closing.test(lines[i])) {
        code.push(lines[i]);
        i++;
      }

      i++;
      blocks.push({ type: "code", lang: fence[2], text: code.join("\n") });
      continue;
    }

    const heading = line.match(/^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$/);

    if (heading) {
      blocks.push({ type: "heading", level: heading[1].length, text: heading[2] });
      i++;
      continue;
    }

    if (/^\s{0,3}([-*_])(\s*\1){2,}\s*$/.test(line)) {
      blocks.push({ type: "hr" });
      i++;
      continue;
    }

    if (/^\s{0,3}>/.test(line)) {
      const quote = [];

      while (i < lines.length && /^\s{0,3}>/.test(lines[i])) {
        quote.push(lines[i].replace(/^\s{0,3}>\s?/, ""));
        i++;
      }

      blocks.push({ type: "quote", blocks: parseBlocks(quote.join("\n")) });
      continue;
    }

    if (isTableStart(lines, i)) {
      const split = (row) =>
        row
          .trim()
          .replace(/^\|/, "")
          .replace(/\|$/, "")
          .split("|")
          .map((cell) => cell.trim());

      const head = split(line);
      const align = split(lines[i + 1]).map((c) =>
        c.startsWith(":") && c.endsWith(":")
          ? "center"
          : c.endsWith(":")
            ? "right"
            : "left",
      );

      i += 2;

      const rows = [];

      while (i < lines.length && lines[i].trim() && lines[i].includes("|")) {
        rows.push(split(lines[i]));
        i++;
      }

      blocks.push({ type: "table", head, align, rows });
      continue;
    }

    if (LIST_ITEM.test(line)) {
      const [items, next] = collectList(lines, i);
      blocks.push({ type: "list", items });
      i = next;
      continue;
    }

    const para = [line];
    i++;

    while (i < lines.length && lines[i].trim() && !startsBlock(lines, i)) {
      para.push(lines[i]);
      i++;
    }

    blocks.push({ type: "p", text: para.join("\n") });
  }

  return blocks;
}

function CodeBlock({ lang, text }) {
  return (
    <div className="codeBlock">
      <div className="codeHead">
        <span>{lang || "code"}</span>
        <CopyButton text={text} />
      </div>

      <pre>
        <code>{text}</code>
      </pre>
    </div>
  );
}

function renderList(nodes, key) {
  const ordered = nodes[0].ordered;
  const Tag = ordered ? "ol" : "ul";
  const props = ordered && nodes[0].number > 1 ? { start: nodes[0].number } : {};

  return (
    <Tag key={key} {...props}>
      {nodes.map((node, index) => (
        <li key={index}>
          {inline(node.text)}

          {node.extra.map((line, j) => (
            <span key={j}>
              <br />
              {inline(line)}
            </span>
          ))}

          {node.children.length > 0 && renderList(node.children, "nested")}
        </li>
      ))}
    </Tag>
  );
}

function renderBlock(block, key) {
  switch (block.type) {
    case "heading": {
      const Tag = `h${Math.min(block.level + 2, 6)}`;

      return (
        <Tag key={key} className={`mdH mdH${Math.min(block.level, 4)}`}>
          {inline(block.text)}
        </Tag>
      );
    }

    case "code":
      return <CodeBlock key={key} lang={block.lang} text={block.text} />;

    case "hr":
      return <hr key={key} />;

    case "quote":
      return (
        <blockquote key={key}>
          {block.blocks.map((b, i) => renderBlock(b, i))}
        </blockquote>
      );

    case "list":
      return renderList(nestItems(block.items), key);

    case "table":
      return (
        <div className="mdTableWrap" key={key}>
          <table className="mdTable">
            <thead>
              <tr>
                {block.head.map((cell, i) => (
                  <th key={i} style={{ textAlign: block.align[i] }}>
                    {inline(cell)}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {block.rows.map((row, r) => (
                <tr key={r}>
                  {block.head.map((_, i) => (
                    <td key={i} style={{ textAlign: block.align[i] }}>
                      {inline(row[i] ?? "")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );

    default:
      return <p key={key}>{inline(block.text)}</p>;
  }
}

export default function Markdown({ text }) {
  const source = String(text || "").replace(/\r\n?/g, "\n");

  return (
    <div className="mdRoot">
      {parseBlocks(source).map((block, i) => renderBlock(block, i))}
    </div>
  );
}
''')

# ====================================================================
# ResponseView.jsx
# ====================================================================
write("frontend/src/ResponseView.jsx", r'''import { useMemo, useState } from "react";

import Markdown from "./markdown.jsx";

// Pulls a leading "Subject: ..." line out of an email-style answer.
function splitSubject(text) {
  const lines = String(text).replace(/\r\n?/g, "\n").split("\n");
  const first = lines.findIndex((line) => line.trim());

  if (first === -1) return { subject: "", body: text };

  const m = lines[first].match(
    /^\s*(?:\*\*|__)?\s*Subject\s*:\s*(?:\*\*|__)?\s*(.+?)\s*$/i,
  );

  if (!m) return { subject: "", body: text };

  return {
    subject: m[1].replace(/\*\*|__/g, "").trim(),
    body: lines.slice(first + 1).join("\n").replace(/^\s*\n/, ""),
  };
}

export default function ResponseView({ text }) {
  const [view, setView] = useState("formatted");

  const { subject, body } = useMemo(() => splitSubject(text), [text]);

  const words = String(text).trim().split(/\s+/).filter(Boolean).length;
  const minutes = Math.max(1, Math.round(words / 200));

  function download() {
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = "obscura-response.txt";
    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
  }

  return (
    <div className="respWrap">
      <div className="respBar">
        <div className="seg" role="tablist" aria-label="Response view">
          <button
            type="button"
            className={view === "formatted" ? "on" : ""}
            onClick={() => setView("formatted")}
          >
            Formatted
          </button>

          <button
            type="button"
            className={view === "plain" ? "on" : ""}
            onClick={() => setView("plain")}
          >
            Plain text
          </button>
        </div>

        <div className="row">
          <span className="respMeta">
            {words} words · {minutes} min read
          </span>

          <button type="button" className="btn small" onClick={download}>
            Download
          </button>
        </div>
      </div>

      <div className="respDoc">
        {view === "formatted" && subject && (
          <div className="respSubject">
            <span>Subject</span>
            <b>{subject}</b>
          </div>
        )}

        <div className="respBody">
          {view === "formatted" ? (
            <Markdown text={subject ? body : text} />
          ) : (
            <pre className="plainText">{text}</pre>
          )}
        </div>
      </div>
    </div>
  );
}
''')

# ====================================================================
# Patches to existing files
# ====================================================================
def patch_file(path, edits):
    if not os.path.exists(path):
        print(f"!! {path} not found")
        return

    data = read(path)
    changed = False

    for skip_marker, kind, old, new in edits:
        if skip_marker in data:
            continue

        if kind == "regex":
            data, n = re.subn(old, new, data, count=1)
            ok = n > 0
        else:
            ok = old in data
            if ok:
                data = data.replace(old, new, 1)

        if ok:
            changed = True
        else:
            print(f"!! {path}: could not find: {old[:60]!r}")

    if changed:
        write(path, data)
    else:
        print("no changes needed:", path)


IMPORT_OLD = '} from "./ui.jsx";'
IMPORT_NEW = (
    '} from "./ui.jsx";\n'
    'import { TypeIcon, WhyTip } from "./riskInfo.jsx";\n'
    'import ResponseView from "./ResponseView.jsx";'
)

RESPONSE_RE = r'<div className="responseText">\{(\w+)\}</div>'
RESPONSE_NEW = r'<ResponseView text={\1} />'

# Report: add the "Why these matter" list
patch_file("frontend/src/ui.jsx", [
    (
        "RiskExplainer",
        "text",
        'import { useRef, useState } from "react";',
        'import { useRef, useState } from "react";\nimport { RiskExplainer } from "./riskInfo.jsx";',
    ),
    (
        "kinds = []",
        "text",
        "export function Report({ total, risks = [], types = [], children }) {",
        "export function Report({ total, risks = [], types = [], kinds = [], children }) {",
    ),
    (
        "<RiskExplainer kinds",
        "text",
        "      )}\n\n      {children}",
        "      )}\n\n      {total > 0 && <RiskExplainer kinds={kinds} />}\n\n      {children}",
    ),
])

# Text tab
patch_file("frontend/src/TextPanel.jsx", [
    ("riskInfo.jsx", "text", IMPORT_OLD, IMPORT_NEW),
    (
        "kinds={detections",
        "text",
        "total={detections.length}",
        "total={detections.length}\n              kinds={detections.map((d) => d.type)}",
    ),
    (
        "<TypeIcon type={d.type}",
        "text",
        '<span className="mono">{d.value}</span>',
        '<span className="valueWithIcon">\n'
        '                                <TypeIcon type={d.type} />\n'
        '                                <span className="mono">{d.value}</span>\n'
        '                                <WhyTip type={d.type} risk={d.risk} />\n'
        '                              </span>',
    ),
    ("<ResponseView", "regex", RESPONSE_RE, RESPONSE_NEW),
])

# Image and PDF tabs
for panel in ("ImagePanel", "PdfPanel"):
    patch_file(f"frontend/src/{panel}.jsx", [
        ("riskInfo.jsx", "text", IMPORT_OLD, IMPORT_NEW),
        (
            "kinds={regions",
            "text",
            "total={regions.length}",
            "total={regions.length}\n              kinds={regions.map((r) => r.type)}",
        ),
        (
            "<TypeIcon type={region.type}",
            "text",
            "<span>{region.label}</span>",
            '<span className="valueWithIcon">\n'
            '                                <TypeIcon type={region.type} />\n'
            '                                <span>{region.label}</span>\n'
            '                                <WhyTip type={region.type} />\n'
            '                              </span>',
        ),
        ("<ResponseView", "regex", RESPONSE_RE, RESPONSE_NEW),
    ])

# ====================================================================
# CSS
# ====================================================================
css = "frontend/src/styles.css"
data = read(css)

if ".mdRoot" in data:
    print("styles already added")
else:
    data += '''

/* ============================================================
   Risk icons and explanations
   ============================================================ */

.valueWithIcon {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.typeIcon {
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 28px;
  flex: none;
  border-radius: 8px;
  background: var(--accent-soft);
  color: var(--accent);
}

.typeIcon.secret {
  background: var(--bad-bg);
  color: var(--bad);
}

.typeIcon.id,
.typeIcon.finance {
  background: var(--warn-bg);
  color: var(--warn);
}

.whyTip {
  position: relative;
  display: inline-flex;
}

.whyBtn {
  display: inline-grid;
  place-items: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--muted);
  cursor: help;
}

.whyBtn:hover,
.whyBtn:focus-visible {
  color: var(--accent);
  background: var(--accent-soft);
}

.whyPop {
  display: none;
  position: absolute;
  left: -8px;
  top: calc(100% + 6px);
  z-index: 30;
  width: min(300px, 72vw);
  padding: 12px 14px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.18);
  font-size: 13px;
  font-weight: 400;
  line-height: 1.5;
  color: var(--ink);
  text-align: left;
}

.whyPop b {
  display: block;
  margin-bottom: 3px;
  font-size: 13.5px;
}

.whyPop span,
.whyPop em {
  display: block;
}

.whyPop em {
  margin-top: 6px;
  font-style: normal;
  font-size: 12px;
  color: var(--muted);
}

.whyTip:hover .whyPop,
.whyTip:focus-within .whyPop {
  display: block;
}

.explain summary {
  cursor: pointer;
  font-weight: 700;
  font-size: 14.5px;
  margin-bottom: 10px;
}

.explainList {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 10px;
}

.explainList li {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 10px 12px;
  background: var(--surface2);
  border: 1px solid var(--line);
  border-radius: 12px;
}

.explainList b {
  font-size: 14px;
}

.explainList p {
  margin: 2px 0 0;
  color: var(--muted);
  font-size: 13.5px;
  line-height: 1.5;
}

/* ============================================================
   AI response
   ============================================================ */

.respWrap {
  display: grid;
  gap: 12px;
}

.respBar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.seg {
  display: inline-flex;
  padding: 3px;
  background: var(--surface2);
  border: 1px solid var(--line);
  border-radius: 10px;
}

.seg button {
  border: 0;
  background: transparent;
  padding: 5px 12px;
  border-radius: 7px;
  font-weight: 600;
  font-size: 13px;
  color: var(--muted);
  cursor: pointer;
}

.seg button.on {
  background: var(--surface);
  color: var(--ink);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.14);
}

.respMeta {
  color: var(--muted);
  font-size: 13px;
}

.respDoc {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
}

.respSubject {
  display: grid;
  gap: 2px;
  padding: 12px 20px;
  background: var(--surface2);
  border-bottom: 1px solid var(--line);
}

.respSubject span {
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
}

.respSubject b {
  font-size: 16px;
}

.respBody {
  padding: 18px 20px;
}

.plainText {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--mono);
  font-size: 13.5px;
  line-height: 1.7;
}

/* Rendered Markdown */

.mdRoot {
  font-size: 15.5px;
  line-height: 1.75;
  overflow-wrap: anywhere;
}

.mdRoot > :first-child {
  margin-top: 0;
}

.mdRoot > :last-child {
  margin-bottom: 0;
}

.mdRoot p {
  margin: 0 0 14px;
}

.mdH {
  margin: 22px 0 8px;
  line-height: 1.3;
  font-weight: 700;
}

.mdH1 {
  font-size: 21px;
}

.mdH2 {
  font-size: 18.5px;
}

.mdH3 {
  font-size: 16.5px;
}

.mdH4 {
  font-size: 15.5px;
}

.mdRoot ul,
.mdRoot ol {
  margin: 0 0 14px;
  padding-left: 24px;
}

.mdRoot li {
  margin: 4px 0;
}

.mdRoot li > ul,
.mdRoot li > ol {
  margin: 4px 0 0;
}

.mdRoot a {
  color: var(--accent);
  text-underline-offset: 2px;
}

.mdRoot hr {
  border: 0;
  border-top: 1px solid var(--line);
  margin: 20px 0;
}

.mdRoot blockquote {
  margin: 0 0 14px;
  padding: 4px 16px;
  border-left: 3px solid var(--accent);
  background: var(--surface2);
  border-radius: 0 10px 10px 0;
  color: var(--muted);
}

.mdCode {
  font-family: var(--mono);
  font-size: 0.88em;
  background: var(--surface2);
  border: 1px solid var(--line);
  border-radius: 5px;
  padding: 1px 6px;
}

.codeBlock {
  margin: 0 0 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  background: var(--surface2);
}

.codeHead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px 6px 14px;
  border-bottom: 1px solid var(--line);
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
}

.codeBlock pre {
  margin: 0;
  padding: 14px;
  overflow-x: auto;
  font-family: var(--mono);
  font-size: 13.5px;
  line-height: 1.6;
}

.mdTableWrap {
  overflow-x: auto;
  margin: 0 0 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
}

.mdTable {
  border-collapse: collapse;
  width: 100%;
  font-size: 14.5px;
}

.mdTable th,
.mdTable td {
  padding: 9px 14px;
  border-bottom: 1px solid var(--line);
}

.mdTable th {
  background: var(--surface2);
  font-weight: 700;
}

.mdTable tr:last-child td {
  border-bottom: 0;
}
'''
    write(css, data)

print("\nDone. If the dev server is running, just look at the browser.")