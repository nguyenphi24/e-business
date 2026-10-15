// Chuyển Markdown của báo cáo/phụ lục sang .docx theo style báo cáo Nhóm 2 (A4, Times New Roman).
// Chạy: cd docs/build && npm install && npm run docx  (hoặc node md2docx.js <config.json>)
// config: { "output": "...docx", "baseDir": "...", "title": "...", "parts": [{ "file": "...md", "appendix": "A" | null }] }
const fs = require("fs");
const path = require("path");
const {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, ImageRun, LevelFormat, Packer, PageBreak,
  PageNumber, PageOrientation, Paragraph, ShadingType, Table, TableCell, TableOfContents, TableRow, TextRun, WidthType,
} = require("docx");

const FONT = "Times New Roman";
const BODY_SIZE = 24; // 12pt
const CONTENT_WIDTH = 9026; // A4 11906 − 2 × 1440 lề
const MAX_IMG_W = 600;
const MAX_IMG_H = 820;
const NAVY = "1F3864";

function inlineRuns(text, base = {}) {
  const runs = [];
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  for (const match of text.matchAll(pattern)) {
    if (match.index > last) runs.push(new TextRun({ text: text.slice(last, match.index), font: FONT, ...base }));
    const token = match[0];
    if (token.startsWith("**")) runs.push(new TextRun({ text: token.slice(2, -2), bold: true, font: FONT, ...base }));
    else if (token.startsWith("`")) runs.push(new TextRun({ text: token.slice(1, -1), font: "Consolas", ...base, size: (base.size ?? BODY_SIZE) - 2 }));
    else runs.push(new TextRun({ text: token.replace(/^\[([^\]]+)\]\([^)]+\)$/, "$1"), font: FONT, ...base }));
    last = match.index + token.length;
  }
  if (last < text.length) runs.push(new TextRun({ text: text.slice(last), font: FONT, ...base }));
  return runs;
}

function pngSize(file) {
  const buffer = fs.readFileSync(file);
  return { buffer, width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

function jpgSize(file) {
  const buffer = fs.readFileSync(file);
  let offset = 2;
  while (offset < buffer.length) {
    const marker = buffer.readUInt16BE(offset);
    const length = buffer.readUInt16BE(offset + 2);
    if (marker >= 0xffc0 && marker <= 0xffc3) return { buffer, height: buffer.readUInt16BE(offset + 5), width: buffer.readUInt16BE(offset + 7) };
    offset += 2 + length;
  }
  throw new Error(`Không đọc được kích thước ${file}`);
}

function imageParagraph(file, maxWidth = MAX_IMG_W, maxHeight = MAX_IMG_H) {
  const isPng = file.toLowerCase().endsWith(".png");
  const { buffer, width, height } = isPng ? pngSize(file) : jpgSize(file);
  const scale = Math.min(maxWidth / width, maxHeight / height, 1);
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    keepNext: true,
    spacing: { before: 120, after: 60 },
    children: [new ImageRun({ type: isPng ? "png" : "jpg", data: buffer, transformation: { width: Math.round(width * scale), height: Math.round(height * scale) } })],
  });
}

function caption(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 80, after: 200 },
    children: [new TextRun({ text, italics: true, bold: true, font: FONT, size: 22, color: NAVY })],
  });
}

function tableCaption(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    keepNext: true,
    spacing: { before: 200, after: 80 },
    children: [new TextRun({ text, italics: true, bold: true, font: FONT, size: 22, color: NAVY })],
  });
}

function splitRow(line) {
  return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim());
}

function buildTable(rows) {
  const header = rows[0];
  const body = rows.slice(2);
  const columns = header.length;
  const weights = Array.from({ length: columns }, (_, c) => {
    const longest = Math.max(...[header, ...body].map((row) => (row[c] ?? "").length), 4);
    return Math.sqrt(Math.min(longest, 160));
  });
  const total = weights.reduce((a, b) => a + b, 0);
  const widths = weights.map((w) => Math.max(900, Math.round((w / total) * CONTENT_WIDTH)));
  const scale = CONTENT_WIDTH / widths.reduce((a, b) => a + b, 0);
  const columnWidths = widths.map((w) => Math.floor(w * scale));
  columnWidths[columnWidths.length - 1] += CONTENT_WIDTH - columnWidths.reduce((a, b) => a + b, 0);
  const border = { style: BorderStyle.SINGLE, size: 4, color: "8FA3C7" };
  const borders = { top: border, bottom: border, left: border, right: border };
  const makeRow = (cells, isHeader) => new TableRow({
    tableHeader: isHeader,
    cantSplit: true,
    children: Array.from({ length: columns }, (_, c) => new TableCell({
      borders,
      width: { size: columnWidths[c], type: WidthType.DXA },
      shading: isHeader ? { fill: "DBE4F3", type: ShadingType.CLEAR, color: "auto" } : undefined,
      margins: { top: 60, bottom: 60, left: 90, right: 90 },
      children: [new Paragraph({ spacing: { before: 0, after: 0, line: 264 }, children: inlineRuns(cells[c] ?? "", { size: 21, bold: isHeader || undefined }) })],
    })),
  });
  return new Table({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    columnWidths,
    rows: [makeRow(header, true), ...body.map((row) => makeRow(row, false))],
  });
}

function bodyParagraph(text) {
  return new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 120 }, children: inlineRuns(text) });
}

function convertMarkdown(markdown, baseDir, appendix) {
  const blocks = [];
  const lines = markdown.replace(/\r/g, "").split("\n");
  let i = 0;
  let firstHeading = true;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i += 1; continue; }
    if (line.startsWith("```")) {
      const code = [];
      i += 1;
      while (i < lines.length && !lines[i].startsWith("```")) { code.push(lines[i]); i += 1; }
      i += 1;
      for (const [index, codeLine] of code.entries()) {
        blocks.push(new Paragraph({
          shading: { fill: "F3F6FB", type: ShadingType.CLEAR, color: "auto" },
          spacing: { before: index === 0 ? 120 : 0, after: index === code.length - 1 ? 160 : 0, line: 240 },
          children: [new TextRun({ text: codeLine || " ", font: "Consolas", size: 17 })],
        }));
      }
      continue;
    }
    const heading = line.match(/^(#{1,3}) (.+)$/);
    if (heading) {
      let level = heading[1].length;
      let text = heading[2].trim();
      if (appendix && level === 1 && firstHeading) text = `PHỤ LỤC ${appendix} – ${text}`;
      if (appendix && level === 1 && !firstHeading) level = 2;
      firstHeading = false;
      const headingLevel = [HeadingLevel.HEADING_1, HeadingLevel.HEADING_2, HeadingLevel.HEADING_3][level - 1];
      blocks.push(new Paragraph({ heading: headingLevel, pageBreakBefore: Boolean(appendix) && level === 1, children: [new TextRun({ text, font: FONT })] }));
      i += 1;
      continue;
    }
    const image = line.match(/^!\[([^\]]*)\]\(([^)]+)\)( \{landscape\})?$/);
    if (image) {
      if (image[3]) {
        // Sơ đồ ngang: đặt trên một trang xoay ngang riêng để chữ đủ lớn
        blocks.push({ landscape: [imageParagraph(path.join(baseDir, image[2]), 930, 560), ...(image[1] ? [caption(image[1])] : [])] });
      } else {
        blocks.push(imageParagraph(path.join(baseDir, image[2])));
        if (image[1]) blocks.push(caption(image[1]));
      }
      i += 1;
      continue;
    }
    if (line.trim().startsWith("|")) {
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) { rows.push(splitRow(lines[i])); i += 1; }
      blocks.push(buildTable(rows));
      blocks.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
      continue;
    }
    if (/^- /.test(line)) {
      while (i < lines.length && /^- /.test(lines[i])) {
        blocks.push(new Paragraph({ numbering: { reference: "bullets", level: 0 }, alignment: AlignmentType.JUSTIFIED, spacing: { after: 80 }, children: inlineRuns(lines[i].slice(2)) }));
        i += 1;
      }
      continue;
    }
    if (/^\d+\. /.test(line)) {
      const instance = blocks.length;
      while (i < lines.length && /^\d+\. /.test(lines[i])) {
        blocks.push(new Paragraph({ numbering: { reference: "numbers", level: 0, instance }, alignment: AlignmentType.JUSTIFIED, spacing: { after: 80 }, children: inlineRuns(lines[i].replace(/^\d+\. /, "")) }));
        i += 1;
      }
      continue;
    }
    if (/^Bảng \d+(\.\d+)*\. /.test(line)) { blocks.push(tableCaption(line.trim())); i += 1; continue; }
    // gộp các dòng liền nhau thành một đoạn
    const paragraph = [line.trim()];
    i += 1;
    while (i < lines.length && lines[i].trim() && !/^(#|\||- |\d+\. |!\[|```)/.test(lines[i])) { paragraph.push(lines[i].trim()); i += 1; }
    blocks.push(bodyParagraph(paragraph.join(" ")));
  }
  return blocks;
}

function coverPage(lines, baseDir) {
  const blocks = [];
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    if (line === "[logo]") { blocks.push(imageParagraph(path.join(baseDir, "figures/logo_uit.jpg"), 130, 130)); continue; }
    const upper = line === line.toUpperCase() && /[A-ZĐ]/.test(line);
    const isTitle = line.startsWith("Đề tài");
    const isMember = /^\d\. /.test(line);
    blocks.push(new Paragraph({
      alignment: isMember ? AlignmentType.LEFT : AlignmentType.CENTER,
      indent: isMember ? { left: 2600 } : undefined,
      spacing: { before: isTitle ? 360 : 60, after: isTitle ? 120 : 60 },
      children: [new TextRun({ text: line, font: FONT, bold: upper || isTitle, size: isTitle ? 34 : upper ? 28 : 26, color: isTitle ? NAVY : undefined })],
    }));
  }
  blocks.push(new Paragraph({ children: [new PageBreak()] }));
  return blocks;
}

function tocBlock() {
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: "MỤC LỤC", bold: true, font: FONT, size: 28 })] }),
    new TableOfContents("Mục lục", { hyperlink: true, headingStyleRange: "1-2" }),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

async function main() {
  const config = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  const baseDir = path.resolve(path.dirname(process.argv[2]), config.baseDir ?? ".");
  const children = [];
  for (const part of config.parts) {
    let markdown = fs.readFileSync(path.join(baseDir, part.file), "utf8");
    if (markdown.includes("[toc]")) {
      const [cover, rest] = markdown.split("[toc]");
      children.push(...coverPage(cover.split("\n"), baseDir), ...(config.toc === false ? [] : tocBlock()));
      markdown = rest;
    }
    children.push(...convertMarkdown(markdown, baseDir, part.appendix ?? null));
  }
  const footer = () => new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 20 })] })] });
  const margin = { top: 1440, bottom: 1440, left: 1440, right: 1440 };
  const sections = [];
  let current = [];
  const flush = () => {
    if (current.length) sections.push({ properties: { page: { size: { width: 11906, height: 16838 }, margin } }, footers: { default: footer() }, children: current });
    current = [];
  };
  for (const block of children) {
    if (block && block.landscape) {
      flush();
      sections.push({ properties: { page: { size: { width: 11906, height: 16838, orientation: PageOrientation.LANDSCAPE }, margin } }, footers: { default: footer() }, children: block.landscape });
    } else {
      current.push(block);
    }
  }
  flush();
  const doc = new Document({
    creator: "Nhóm 2 – IS6101.11.CH",
    title: config.title,
    features: { updateFields: true },
    styles: {
      default: { document: { run: { font: FONT, size: BODY_SIZE }, paragraph: { spacing: { line: config.lineSpacing ?? 312 } } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 28, bold: true, color: "000000" }, paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 360, after: 200 }, keepNext: true, outlineLevel: 0 } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 26, bold: true, color: "000000" }, paragraph: { spacing: { before: 260, after: 120 }, keepNext: true, outlineLevel: 1 } },
        { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 24, bold: true, italics: true, color: "000000" }, paragraph: { spacing: { before: 200, after: 100 }, keepNext: true, outlineLevel: 2 } },
      ],
    },
    numbering: {
      config: [
        { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
        { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
      ],
    },
    sections,
  });
  const output = path.join(baseDir, config.output);
  fs.writeFileSync(output, await Packer.toBuffer(doc));
  console.log(output);
}

main().catch((error) => { console.error(error); process.exit(1); });
