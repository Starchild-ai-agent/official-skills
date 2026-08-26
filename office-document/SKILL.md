---
name: office-document
version: 1.0.1
description: |
  Route editable PDF, DOCX, XLSX, and PPTX creation or modification tasks to the
  appropriate official Hermes document skill. Use when the user asks to create,
  edit, format, convert, fill, annotate, review, or otherwise produce an
  editable office document. Do not activate for simple read-only extraction or
  summarization. For presentation-only output where the user does not need an
  editable PowerPoint file, use Starchild's official slide-creator skill.
metadata:
  starchild:
    emoji: "📄"
    skillKey: office-document
---

# Office document routing

Use this skill as a routing decision, not as a replacement for the document
engines. The official Hermes skills are separate skills:

| User task | Hermes skill |
|---|---|
| Create, read, edit, template, or review Word `.docx` | `docx` |
| Create, read, or edit Excel `.xlsx` / CSV | `xlsx` |
| Create, read, or edit editable PowerPoint `.pptx` | `powerpoint` |
| Create, read, merge, fill, secure, or otherwise manipulate PDF | `pdf` |
| Read-only extraction or summarization | Do not route here; read the file directly |
| Visual presentation that does not need an editable `.pptx` | Starchild `slide-creator` |

## Decision rules

1. Determine whether the user needs an editable output or only information.
   Read-only is not a document-production task. Do not install or invoke a
   document skill merely to extract or summarize file contents.
2. Select exactly one format-specific Hermes skill from the table above.
3. For a mixed request, route each artifact to its own format-specific skill;
   do not use `powerpoint` for a PDF or `docx` for a general presentation.
4. For scanned or image-only PDFs, use Hermes `ocr-and-documents` before or
   instead of `pdf`; a PDF skill cannot invent a missing text layer.
5. After any edit or creation, follow the selected skill's verification steps.
   Do not claim format fidelity without read-back and, where applicable,
   render/visual inspection.

## Installing the official Hermes skills

These are the official skills from `NousResearch/hermes-agent`, not similarly
named community skills.

## Skills CLI installation

Install **only the one skill required by the current task**. Do not install all
format-specific skills in advance.

Use the matching command:

- DOCX task：`npx skills add NousResearch/hermes-agent --skill docx`
- XLSX／CSV task：`npx skills add NousResearch/hermes-agent --skill xlsx`
- Editable PPTX task：`npx skills add NousResearch/hermes-agent --skill powerpoint`
- PDF task：`npx skills add NousResearch/hermes-agent --skill pdf`
- Scanned or image-only PDF：install `ocr-and-documents` only when OCR is actually needed：
  `npx skills add NousResearch/hermes-agent --skill ocr-and-documents`

Do not substitute a community package with a similar name unless the user
explicitly asks for that package. After installation, confirm the selected
skill's `SKILL.md` is present and use its own scripts and verification commands.

## Official source mapping

The upstream source paths are:

- `https://github.com/NousResearch/hermes-agent/tree/main/skills/productivity/docx`
- `https://github.com/NousResearch/hermes-agent/tree/main/skills/productivity/xlsx`
- `https://github.com/NousResearch/hermes-agent/tree/main/skills/productivity/powerpoint`
- `https://github.com/NousResearch/hermes-agent/tree/main/skills/productivity/pdf`
- `https://github.com/NousResearch/hermes-agent/tree/main/skills/productivity/ocr-and-documents`

The Hermes `docx` skill uses `python-docx` helpers and package health checks;
`xlsx` uses `openpyxl`; `powerpoint` uses `python-pptx`; and `pdf` uses
`pypdf`, `reportlab`, and `pdfplumber`. These implementation details describe
the official skills and should not be replaced with guessed local commands.

---

## Final visual QA — where layout matters

The runtime tool is `vision_analyze(image_url=<workspace image path or public URL>, question=<specific QA rubric>)`. It analyzes an existing image only — it does NOT render documents.

Scope rule:

- **Read-only extraction** (text dump, summarization, table-to-CSV) is out of scope for this skill and out of scope for visual QA. No render needed.
- **Anything that produces a layout the user will see** — DOCX, XLSX, PPTX, PDF — must pass visual QA before delivery.

For a layout-relevant task, after the format-specific Hermes skill has produced its output:

1. **Render representative pages/slides/sheets to PNG.** At minimum: first page, a content-dense page, a table/chart page, last page. For spreadsheets, also render the active sheet at a couple of zoom levels if the sheet is wide. Save under a `qa/` folder in the project so the artifacts are reproducible.
2. **Run vision review.** Call `vision_analyze(image_url=<workspace-relative PNG path>, question=<rubric>)` with a rubric appropriate to the format:
   - **DOCX / PDF (flowing layout)** — text overflow / clipping, header-footer collision, page-break placement, image wrapping, table column widths, contrast on watermarks or color blocks.
   - **PPTX** — slide overflow, tiny text, alignment consistency, image cropping, chart legibility, transition-safe positioning of placeholders.
   - **XLSX** — header row visibility, frozen panes respected, column widths not truncating data, conditional formatting legible, number formatting consistent, merged cells not hiding content.
3. **Triage & fix.** Fix every Critical / Major finding in the format-specific skill's source (template, layout code, or content). Re-render the PNG(s) and re-run `vision_analyze` until the new pass returns no Critical or Major findings.
4. **Honest reporting.** If the format-specific skill cannot produce a renderable artifact (missing converter, locked/encrypted input, image-only PDF without OCR), state plainly: "Final visual QA was not run — <reason>." Do not claim fidelity from the binary alone.

Pure OCR pipelines (`ocr-and-documents`) are text-extraction work; visual QA applies to the downstream edited document, not the OCR step itself.
