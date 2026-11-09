import { CopyButton } from "./ui.jsx";

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
